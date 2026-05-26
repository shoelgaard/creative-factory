#!/usr/bin/env python3
"""Creative Factory CLI — flow router.

    cf <flow> <command> [options]

Examples:
    cf editorial gen --image references/slot1_hero.jpg --brand persillo
    cf editorial gen --image refs/x.jpg --brand persillo --engine both
    cf list
    cf cost report
    cf cost report --since 2026-05-01 --engine gemini-veo
    cf doctor
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
from collections import defaultdict
from typing import Optional


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.brand_loader import load_brand
from shared.cost_estimator import estimate
from shared.gates import CreditEstimate, credit_gate
from shared.run_log import RunEntry, append_run, now_iso, read_all
from flows.editorial_cinematic.prompt_builder import build_prompt  # type: ignore
from flows.statics.render import cmd_statics_gen  # type: ignore


# Engine name (CLI flag) → (engine directory, default model id)
ENGINES: dict[str, tuple[str, str]] = {
    "veo3": ("gemini-veo", "veo-3.1-generate-preview"),
    "seedance2": ("fal", "fal-ai/bytedance/seedance/v1/pro/image-to-video"),
}
ENGINE_SCRIPTS: dict[str, pathlib.Path] = {
    name: ROOT / "engines" / engine_dir / "client.py"
    for name, (engine_dir, _) in ENGINES.items()
}
ENGINE_CHOICES = list(ENGINES.keys()) + ["both"]


def _load_env_file(path: pathlib.Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Skip empty values so they don't shadow a real value in another .env
        if key and value and key not in os.environ:
            os.environ[key] = value


def _bootstrap_env() -> None:
    _load_env_file(ROOT / ".env")
    persillo_env = pathlib.Path(
        os.path.expanduser(
            "~/Library/CloudStorage/OneDrive-ADClient/AI agents HQ/Persillo/Produkter/.env"
        )
    )
    _load_env_file(persillo_env)


def _read_brand_defaults(brand_slug: str) -> dict:
    """Read brands/<slug>/MASTER_CONTEXT.md and extract simple `key: value` defaults
    from the '## Defaults' section. Conservative parser — no YAML dep."""
    path = ROOT / "brands" / brand_slug / "MASTER_CONTEXT.md"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    m = re.search(r"##\s+Defaults\s*\n(.*?)(?=\n##\s|\Z)", text, re.DOTALL)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        ml = re.match(r"\s*-\s*`([^`]+)`\s*:\s*(.+)", line)
        if ml:
            out[ml.group(1).strip()] = ml.group(2).strip().strip("`")
    return out


def _run_engine(
    name: str,
    script: pathlib.Path,
    image: pathlib.Path,
    prompt: str,
    out_dir: pathlib.Path,
    aspect: str,
    duration: int,
) -> tuple[str, int, str]:
    cmd = [
        sys.executable,
        str(script),
        "--image",
        str(image),
        "--prompt",
        prompt,
        "--out-dir",
        str(out_dir),
        "--aspect",
        aspect,
        "--duration",
        str(duration),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return name, proc.returncode, out


def cmd_editorial_gen(args: argparse.Namespace) -> int:
    image = pathlib.Path(args.image).expanduser().resolve()
    if not image.exists():
        print(f"[cf] image not found: {image}", file=sys.stderr)
        return 2

    try:
        brand = load_brand(args.brand, ROOT / "brands")
    except FileNotFoundError as exc:
        print(f"[cf] {exc}", file=sys.stderr)
        return 2

    defaults = _read_brand_defaults(brand.slug)
    max_per_run_str = defaults.get("max_cost_per_run_usd")
    try:
        max_per_run = float(max_per_run_str) if max_per_run_str else None
    except ValueError:
        max_per_run = None

    prompts = build_prompt(brand, image, user_steer=args.prompt)

    ts = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = ROOT / "output" / ts / "editorial-cinematic" / brand.slug / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    brief_path = run_dir / "brief.json"
    brief_path.write_text(
        json.dumps(
            {
                "flow": "editorial-cinematic",
                "flow_version": "0.1.0",
                "brand": brand.slug,
                "image": str(image),
                "engine": args.engine,
                "aspect": args.aspect,
                "duration": args.duration,
                "user_steer": args.prompt or "",
                "veo3_prompt": prompts.veo3,
                "seedance2_prompt": prompts.seedance2,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[cf] run dir: {run_dir}")
    print(f"[cf] brief:   {brief_path}")

    jobs: list[tuple[str, pathlib.Path, str, pathlib.Path, str]] = []  # (engine_alias, script, prompt, out, model)
    if args.engine in ("veo3", "both"):
        _, default_model = ENGINES["veo3"]
        jobs.append(("veo3", ENGINE_SCRIPTS["veo3"], prompts.veo3, run_dir / "veo3", default_model))
    if args.engine in ("seedance2", "both"):
        if not (os.environ.get("FAL_API_KEY") or os.environ.get("FAL_KEY")):
            print(
                "[cf] FAL_API_KEY missing — seedance2 skipped. Add it to .env to enable.",
                file=sys.stderr,
            )
            if args.engine == "seedance2":
                return 2
        else:
            _, default_model = ENGINES["seedance2"]
            jobs.append(
                ("seedance2", ENGINE_SCRIPTS["seedance2"], prompts.seedance2, run_dir / "seedance2", default_model)
            )

    if not jobs:
        print("[cf] nothing to run", file=sys.stderr)
        return 2

    # Cost estimate + credit gate
    cost_estimates: list[CreditEstimate] = []
    for engine_alias, _, _, _, model in jobs:
        engine_dir, _ = ENGINES[engine_alias]
        est_usd, source = estimate(
            project_root=ROOT,
            engine=engine_dir,
            model=model,
            duration_s=args.duration,
        )
        cost_estimates.append(
            CreditEstimate(
                engine=engine_dir,
                model=model,
                duration_s=args.duration,
                estimate_usd=est_usd,
                source=source,
            )
        )

    if not credit_gate(cost_estimates, max_per_run_usd=max_per_run, assume_yes=args.yes):
        print("[cf] aborted at credit gate", file=sys.stderr)
        return 1

    # Run engines in parallel
    results: list[tuple[str, int, str]] = []
    with cf.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        future_map = {
            pool.submit(
                _run_engine,
                engine_alias,
                script,
                image,
                prompt,
                out,
                args.aspect,
                args.duration,
            ): (engine_alias, model, out)
            for engine_alias, script, prompt, out, model in jobs
        }
        for fut in cf.as_completed(future_map):
            engine_alias, model, out = future_map[fut]
            engine_dir, _ = ENGINES[engine_alias]
            try:
                name, rc, output = fut.result()
            except Exception as exc:
                name, rc, output = engine_alias, 1, f"[cf] engine crashed: {exc}"
            results.append((name, rc, output))

            # Find produced video for the log entry
            video_path = None
            if out.exists():
                mp4s = sorted(out.glob("*.mp4"))
                if mp4s:
                    video_path = str(mp4s[-1])

            # Pull elapsed from engine's stdout if present
            elapsed_s = 0.0
            m = re.search(r"\(([\d.]+)s\)", output)
            if m:
                try:
                    elapsed_s = float(m.group(1))
                except ValueError:
                    pass

            ce = next(c for c in cost_estimates if c.engine == engine_dir and c.model == model)
            append_run(
                ROOT / "logs",
                RunEntry(
                    ts=now_iso(),
                    engine=engine_dir,
                    flow="editorial-cinematic",
                    brand=brand.slug,
                    run_id=ts,
                    model=model,
                    params={"aspect": args.aspect, "duration": args.duration},
                    status="ok" if rc == 0 else "failed",
                    elapsed_s=elapsed_s,
                    cost_estimate_usd=ce.estimate_usd,
                    cost_actual_usd=None,
                    asset_id=None,
                    video_path=video_path,
                    error=None if rc == 0 else output[-500:],
                ),
            )

    overall_rc = 0
    for name, rc, output in results:
        print(f"\n===== {name} (rc={rc}) =====")
        print(output.strip())
        if rc != 0:
            overall_rc = rc

    print(f"\n[cf] done. outputs in: {run_dir}")
    return overall_rc


def cmd_list(args: argparse.Namespace) -> int:
    print("Flows:")
    flows_root = ROOT / "flows"
    for entry in sorted(flows_root.iterdir()) if flows_root.exists() else []:
        if entry.is_dir() and (entry / "flow.yaml").exists():
            print(f"  - {entry.name}")
    print("\nEngines:")
    engines_root = ROOT / "engines"
    for entry in sorted(engines_root.iterdir()) if engines_root.exists() else []:
        if entry.is_dir() and (entry / "engine.yaml").exists():
            print(f"  - {entry.name}")
    print("\nBrands:")
    brands_root = ROOT / "brands"
    for entry in sorted(brands_root.iterdir()) if brands_root.exists() else []:
        if entry.is_dir() and (entry / "brand.md").exists():
            print(f"  - {entry.name}")
    return 0


def cmd_cost_report(args: argparse.Namespace) -> int:
    rows = read_all(ROOT / "logs", engine=args.engine)
    if args.since:
        rows = [r for r in rows if r.get("ts", "") >= f"{args.since}T00:00:00Z"]
    if args.flow:
        rows = [r for r in rows if r.get("flow") == args.flow]
    if args.brand:
        rows = [r for r in rows if r.get("brand") == args.brand]

    if not rows:
        print("[cf cost] no matching log entries")
        return 0

    totals: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"runs": 0, "estimated": 0.0, "actual": 0.0, "actual_known": False}
    )
    for r in rows:
        k = (r.get("engine", "?"), r.get("brand", "?"))
        totals[k]["runs"] += 1
        totals[k]["estimated"] += float(r.get("cost_estimate_usd") or 0)
        if r.get("cost_actual_usd") is not None:
            totals[k]["actual"] += float(r["cost_actual_usd"])
            totals[k]["actual_known"] = True

    print(f"{'engine':14s}  {'brand':14s}  {'runs':>5s}  {'estimated':>10s}  {'actual':>10s}")
    print("-" * 60)
    grand_est = 0.0
    grand_act = 0.0
    for (engine, brand), v in sorted(totals.items()):
        actual = f"${v['actual']:.2f}" if v["actual_known"] else "n/a"
        print(f"{engine:14s}  {brand:14s}  {v['runs']:>5d}  ${v['estimated']:>9.2f}  {actual:>10s}")
        grand_est += v["estimated"]
        grand_act += v["actual"]
    print("-" * 60)
    print(f"{'TOTAL':14s}  {'':14s}  {sum(v['runs'] for v in totals.values()):>5d}  ${grand_est:>9.2f}  ${grand_act:>9.2f}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    hard_fail = False

    def check(label: str, condition: bool, fix: str = "", required: bool = True) -> None:
        nonlocal hard_fail
        if condition:
            mark = "✓"
        else:
            mark = "✗" if required else "·"
        print(f"  [{mark}] {label}")
        if not condition:
            if required:
                hard_fail = True
            if fix:
                print(f"       → {fix}")

    print("Creative Factory doctor:\n")

    check("Python >= 3.10", sys.version_info >= (3, 10))
    try:
        import certifi  # noqa: F401
        check("certifi installed", True)
    except ImportError:
        check("certifi installed", False, "pip install --user certifi")

    check(".env present", (ROOT / ".env").exists(), "cp .env.example .env")
    check("GEMINI_API_KEY set", bool(os.environ.get("GEMINI_API_KEY")), "add to .env")
    check(
        "FAL_API_KEY set (optional)",
        bool(os.environ.get("FAL_API_KEY") or os.environ.get("FAL_KEY")),
        "needed for seedance2 engine; ignore if you only use veo3",
        required=False,
    )

    check("flows/ exists", (ROOT / "flows").is_dir())
    check("engines/gemini-veo/client.py", (ROOT / "engines" / "gemini-veo" / "client.py").exists())
    check("engines/fal/client.py", (ROOT / "engines" / "fal" / "client.py").exists())
    check("engines/gemini-image/client.py", (ROOT / "engines" / "gemini-image" / "client.py").exists())
    check("brands/persillo/brand.md", (ROOT / "brands" / "persillo" / "brand.md").exists())
    check("logs/ ledger present", (ROOT / "logs").is_dir())

    print("\n" + ("OK" if not hard_fail else "ISSUES FOUND"))
    return 0 if not hard_fail else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cf", description="Creative Factory CLI")
    p.add_argument("-y", "--yes", action="store_true", help="Auto-approve gates (use sparingly).")
    flow_sub = p.add_subparsers(dest="flow", required=True)

    # cf editorial gen
    editorial = flow_sub.add_parser("editorial", help="Editorial cinematic flow")
    e_sub = editorial.add_subparsers(dest="cmd", required=True)
    e_gen = e_sub.add_parser("gen", help="Generate cinematic clip(s) from a product image.")
    e_gen.add_argument("--image", required=True)
    e_gen.add_argument("--brand", required=True, help="Brand slug. REQUIRED.")
    e_gen.add_argument("--engine", default="veo3", choices=ENGINE_CHOICES)
    e_gen.add_argument("--prompt", default="")
    e_gen.add_argument("--aspect", default="9:16", choices=["9:16", "16:9", "1:1"])
    e_gen.add_argument("--duration", type=int, default=8, choices=[4, 6, 8])
    e_gen.set_defaults(func=cmd_editorial_gen)

    # cf statics gen
    statics = flow_sub.add_parser("statics", help="Static ad images (Nano Banana Pro)")
    s_sub = statics.add_subparsers(dest="cmd", required=True)
    s_gen = s_sub.add_parser("gen", help="Bulk-render statics from a concepts file.")
    s_gen.add_argument("--brand", required=True, help="Brand slug. REQUIRED.")
    s_gen.add_argument("--concepts", required=True, help="Path to concepts markdown file.")
    s_gen.add_argument("--product", default=None, help="Product slug (inferred from filename if omitted).")
    s_gen.add_argument("--only", default=None, help="CSV of concept IDs to render (overrides --only-checked).")
    s_gen.add_argument("--only-checked", action="store_true", help="Only render concepts marked [x].")
    s_gen.add_argument("--aspect", default="4:5", choices=["1:1", "4:5", "9:16", "16:9"])
    s_gen.add_argument("--size", default="2K", choices=["512px", "1K", "2K", "4K"])
    s_gen.add_argument("--use-template-ref", dest="use_template_ref", action="store_true", default=True)
    s_gen.add_argument("--no-template-ref", dest="use_template_ref", action="store_false")
    s_gen.add_argument("--parallel", type=int, default=8, help="Max concurrent renders.")
    s_gen.add_argument("--max-retries", dest="max_retries", type=int, default=2, help="Auto-retry failed IDs this many times.")
    s_gen.set_defaults(func=cmd_statics_gen)

    # cf list
    lst = flow_sub.add_parser("list", help="List installed flows, engines, brands.")
    lst.set_defaults(func=cmd_list)

    # cf cost report
    cost = flow_sub.add_parser("cost", help="Cost reporting from logs/<engine>.jsonl")
    c_sub = cost.add_subparsers(dest="cmd", required=True)
    c_report = c_sub.add_parser("report", help="Summarise spend across engines/brands.")
    c_report.add_argument("--engine", default=None)
    c_report.add_argument("--brand", default=None)
    c_report.add_argument("--flow", default=None)
    c_report.add_argument("--since", default=None, help="YYYY-MM-DD")
    c_report.set_defaults(func=cmd_cost_report)

    # cf doctor
    doc = flow_sub.add_parser("doctor", help="Check env, keys, structure.")
    doc.set_defaults(func=cmd_doctor)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    _bootstrap_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "yes"):
        args.yes = False
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
