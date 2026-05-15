#!/usr/bin/env python3
"""Creative Factory CLI — flow router.

    cf <flow> <command> [options]

Examples:
    cf editorial gen --image references/slot1_hero.jpg --brand persillo
    cf editorial gen --image refs/x.jpg --brand persillo --engine seedance2
    cf editorial gen --image refs/x.jpg --brand persillo --engine both
    cf list
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
from typing import Optional


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.brand_loader import load_brand
from flows.editorial_cinematic.prompt_builder import build_prompt  # type: ignore


# Engine name → engine client script
ENGINES: dict[str, pathlib.Path] = {
    "veo3": ROOT / "engines" / "gemini-veo" / "client.py",
    "seedance2": ROOT / "engines" / "fal" / "client.py",
}
ENGINE_CHOICES = list(ENGINES.keys()) + ["both"]


def _load_env_file(path: pathlib.Path) -> None:
    """Minimal .env loader (KEY=VALUE per line). Does not overwrite existing env."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _bootstrap_env() -> None:
    _load_env_file(ROOT / ".env")
    persillo_env = pathlib.Path(
        os.path.expanduser(
            "~/Library/CloudStorage/OneDrive-ADClient/AI agents HQ/Persillo/Produkter/.env"
        )
    )
    _load_env_file(persillo_env)


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

    jobs: list[tuple[str, pathlib.Path, str, pathlib.Path]] = []
    if args.engine in ("veo3", "both"):
        jobs.append(("veo3", ENGINES["veo3"], prompts.veo3, run_dir / "veo3"))
    if args.engine in ("seedance2", "both"):
        if not (os.environ.get("FAL_API_KEY") or os.environ.get("FAL_KEY")):
            print(
                "[cf] FAL_API_KEY missing — seedance2 skipped. Add it to .env to enable.",
                file=sys.stderr,
            )
            if args.engine == "seedance2":
                return 2
        else:
            jobs.append(
                ("seedance2", ENGINES["seedance2"], prompts.seedance2, run_dir / "seedance2")
            )

    if not jobs:
        print("[cf] nothing to run", file=sys.stderr)
        return 2

    results: list[tuple[str, int, str]] = []
    with cf.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        future_map = {
            pool.submit(
                _run_engine, name, script, image, prompt, out, args.aspect, args.duration
            ): name
            for name, script, prompt, out in jobs
        }
        for fut in cf.as_completed(future_map):
            name = future_map[fut]
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append((name, 1, f"[cf] engine crashed: {exc}"))

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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cf", description="Creative Factory CLI")
    flow_sub = p.add_subparsers(dest="flow", required=True)

    # cf editorial <command>
    editorial = flow_sub.add_parser("editorial", help="Editorial cinematic flow (Veo 3 / Seedance via fal)")
    e_sub = editorial.add_subparsers(dest="cmd", required=True)
    e_gen = e_sub.add_parser("gen", help="Generate cinematic clip(s) from a product image.")
    e_gen.add_argument("--image", required=True, help="Path to product reference image.")
    e_gen.add_argument("--brand", required=True, help="Brand slug, e.g. 'persillo'. REQUIRED.")
    e_gen.add_argument(
        "--engine",
        default="veo3",
        choices=ENGINE_CHOICES,
        help="Which engine(s) to run. 'both' runs them in parallel.",
    )
    e_gen.add_argument("--prompt", default="", help="Optional extra steering for this run.")
    e_gen.add_argument("--aspect", default="9:16", choices=["9:16", "16:9", "1:1"])
    e_gen.add_argument("--duration", type=int, default=8, choices=[4, 6, 8])
    e_gen.set_defaults(func=cmd_editorial_gen)

    # cf list
    lst = flow_sub.add_parser("list", help="List installed flows, engines, brands.")
    lst.set_defaults(func=cmd_list)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    _bootstrap_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
