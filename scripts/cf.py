#!/usr/bin/env python3
"""Creative Factory CLI.

One brief → one or two short product films per run.

Examples:
    cf gen --image references/slot1_hero.jpg --brand persillo
    cf gen --image refs/x.jpg --brand persillo --engine seedance2
    cf gen --image refs/x.jpg --brand persillo --engine both
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

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.brand_loader import load_brand
from lib.prompt_builder import build_prompt


ENGINE_CHOICES = ["veo3", "seedance2", "both"]


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
    # Load .env from project root, then fall back to the Persillo .env that already
    # holds GEMINI_API_KEY (so existing keys are reused without re-typing).
    _load_env_file(ROOT / ".env")
    persillo_env = pathlib.Path(
        os.path.expanduser(
            "~/Library/CloudStorage/OneDrive-ADClient/AI agents HQ/Persillo/Produkter/.env"
        )
    )
    _load_env_file(persillo_env)


def _run_engine(
    script: pathlib.Path,
    image: pathlib.Path,
    prompt: str,
    out_dir: pathlib.Path,
    aspect: str,
    duration: int,
) -> tuple[str, int, str]:
    """Run an engine script as a subprocess; return (engine_name, returncode, stdout+stderr)."""
    name = script.stem.replace("_gen", "")
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


def cmd_gen(args: argparse.Namespace) -> int:
    image = pathlib.Path(args.image).expanduser().resolve()
    if not image.exists():
        print(f"[cf] image not found: {image}", file=sys.stderr)
        return 2

    brands_root = ROOT / "brands"
    try:
        brand = load_brand(args.brand, brands_root)
    except FileNotFoundError as exc:
        print(f"[cf] {exc}", file=sys.stderr)
        return 2

    prompts = build_prompt(brand, image, user_steer=args.prompt)

    ts = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = ROOT / "output" / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    # Persist the full brief
    brief_path = run_dir / "brief.json"
    brief_path.write_text(
        json.dumps(
            {
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

    scripts_dir = ROOT / "scripts"
    jobs: list[tuple[str, pathlib.Path, str, pathlib.Path]] = []
    if args.engine in ("veo3", "both"):
        jobs.append(
            ("veo3", scripts_dir / "veo3_gen.py", prompts.veo3, run_dir / "veo3")
        )
    if args.engine in ("seedance2", "both"):
        if not (os.environ.get("FAL_API_KEY") or os.environ.get("FAL_KEY")):
            print(
                "[cf] FAL_API_KEY missing — seedance2 skipped. "
                "Add it to .env to enable.",
                file=sys.stderr,
            )
            if args.engine == "seedance2":
                return 2
        else:
            jobs.append(
                (
                    "seedance2",
                    scripts_dir / "seedance_gen.py",
                    prompts.seedance2,
                    run_dir / "seedance2",
                )
            )

    if not jobs:
        print("[cf] nothing to run", file=sys.stderr)
        return 2

    results: list[tuple[str, int, str]] = []
    with cf.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        future_map = {
            pool.submit(
                _run_engine,
                script,
                image,
                prompt,
                out,
                args.aspect,
                args.duration,
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cf", description="Creative Factory CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", help="Generate ad-video(s) from a product image.")
    g.add_argument("--image", required=True, help="Path to product reference image.")
    g.add_argument("--brand", required=True, help="Brand slug, e.g. 'persillo'.")
    g.add_argument(
        "--engine",
        default="veo3",
        choices=ENGINE_CHOICES,
        help="Which engine(s) to run. 'both' runs them in parallel.",
    )
    g.add_argument(
        "--prompt", default="", help="Optional extra steering for this run."
    )
    g.add_argument("--aspect", default="9:16", choices=["9:16", "16:9", "1:1"])
    g.add_argument("--duration", type=int, default=8, choices=[4, 6, 8])
    g.set_defaults(func=cmd_gen)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    _bootstrap_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
