"""Statics flow orchestration — bulk-render ad concepts.

Reads a concepts markdown file, builds engine prompts, fires N gemini-image
calls in parallel, saves outputs + log entries.

Called by `cf statics gen`.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import pathlib
import sys
import time

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "engines" / "gemini-image"))

import client as gemini_image  # type: ignore  # engines/gemini-image/client.py
from shared.brand_loader import load_brand
from shared.cost_estimator import estimate as cost_estimate
from shared.gates import CreditEstimate, credit_gate
from shared.run_log import RunEntry, append_run, now_iso

from .concept_parser import filter_concepts, parse_concepts
from .prompt_builder import build_for_concept


def _detect_product_slug(concept_file: pathlib.Path) -> str:
    """Infer product slug from filename like 'grenen-round-1.md' → 'grenen'."""
    stem = concept_file.stem.lower()
    for part in stem.split("-"):
        if part not in ("round", "v1", "v2", "v3", "test"):
            try:
                int(part)
                continue
            except ValueError:
                pass
            return part
    return stem


def cmd_statics_gen(args: argparse.Namespace) -> int:
    try:
        brand = load_brand(args.brand, _PROJECT_ROOT / "brands")
    except FileNotFoundError as exc:
        print(f"[statics] {exc}", file=sys.stderr)
        return 2

    concept_file = pathlib.Path(args.concepts).expanduser().resolve()
    if not concept_file.exists():
        print(f"[statics] concept file not found: {concept_file}", file=sys.stderr)
        return 2

    concepts = parse_concepts(concept_file)
    only = [s.strip() for s in (args.only.split(",") if args.only else []) if s.strip()]
    selected = filter_concepts(concepts, only_ids=only or None, only_checked=args.only_checked)

    if not selected:
        print(f"[statics] no concepts selected (parsed {len(concepts)} total)", file=sys.stderr)
        return 2

    product_slug = args.product or _detect_product_slug(concept_file)
    print(f"[statics] brand={brand.slug} product={product_slug} concepts={len(selected)} aspect={args.aspect}")

    # Build prompts up front so we can show cost estimate
    built = []
    for c in selected:
        try:
            bp = build_for_concept(
                brand=brand,
                product_slug=product_slug,
                concept=c,
                project_root=_PROJECT_ROOT,
                use_template_ref=args.use_template_ref,
                aspect=args.aspect,
            )
            built.append((c, bp))
        except Exception as exc:
            print(f"[statics] {c.id} prompt build failed: {exc}", file=sys.stderr)

    if not built:
        return 1

    # Cost gate
    per_call_est, source = cost_estimate(
        project_root=_PROJECT_ROOT,
        engine="gemini-image",
        model="gemini-3.1-flash-image-preview",
        duration_s=1,  # not duration — but estimator expects it
    )
    # estimator returned per-second; for image we treat it as per-image
    total_estimate = per_call_est * len(built)
    print(f"[statics] cost estimate: ${per_call_est:.3f}/image × {len(built)} = ${total_estimate:.2f}")

    if not credit_gate(
        [
            CreditEstimate(
                engine="gemini-image",
                model="gemini-3.1-flash-image-preview",
                duration_s=len(built),  # piggyback total count in duration_s for display
                estimate_usd=total_estimate,
                source=source,
            )
        ],
        max_per_run_usd=None,  # set by global cap; bypass per-run for batches
        assume_yes=args.yes,
    ):
        print("[statics] aborted at credit gate", file=sys.stderr)
        return 1

    ts = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = _PROJECT_ROOT / "output" / ts / "statics" / brand.slug / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save full run manifest (which concepts were rendered)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "flow": "statics",
                "flow_version": "0.1.0",
                "brand": brand.slug,
                "product": product_slug,
                "aspect": args.aspect,
                "size": args.size,
                "use_template_ref": args.use_template_ref,
                "concept_file": str(concept_file),
                "rendered_ids": [c.id for c, _ in built],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    api_key = __import__("os").environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[statics] GEMINI_API_KEY missing in env", file=sys.stderr)
        return 1

    # Fire in parallel
    def _one(concept, bp):
        started = time.monotonic()
        try:
            img_bytes, mime = gemini_image.generate(
                prompt=bp.text,
                refs=bp.refs,
                api_key=api_key,
                aspect=bp.aspect,
                size=args.size,
                timeout=360,
            )
            elapsed = round(time.monotonic() - started, 1)
            ext = ".png" if "png" in mime else ".jpg"
            out_path = run_dir / f"{concept.id}{ext}"
            out_path.write_bytes(img_bytes)

            # Save the prompt + brief alongside the image
            (run_dir / f"{concept.id}.prompt.txt").write_text(bp.text, encoding="utf-8")
            (run_dir / f"{concept.id}.brief.json").write_text(
                json.dumps(
                    {
                        "id": concept.id,
                        "template_ref": concept.template_ref,
                        "variant": concept.variant,
                        "copy_mode": concept.copy_mode,
                        "headline": concept.headline,
                        "primary": concept.primary,
                        "description": concept.description,
                        "refs": [str(r) for r in bp.refs],
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            append_run(
                _PROJECT_ROOT / "logs",
                RunEntry(
                    ts=now_iso(),
                    engine="gemini-image",
                    flow="statics",
                    brand=brand.slug,
                    run_id=ts,
                    model="gemini-3.1-flash-image-preview",
                    params={
                        "aspect": args.aspect,
                        "size": args.size,
                        "concept_id": concept.id,
                        "variant": concept.variant,
                        "template_ref": concept.template_ref,
                        "n_refs": len(bp.refs),
                    },
                    status="ok",
                    elapsed_s=elapsed,
                    cost_estimate_usd=per_call_est,
                    cost_actual_usd=None,
                    asset_id=None,
                    video_path=str(out_path),
                    error=None,
                ),
            )
            return (concept.id, "ok", out_path, elapsed, None)
        except Exception as exc:
            elapsed = round(time.monotonic() - started, 1)
            append_run(
                _PROJECT_ROOT / "logs",
                RunEntry(
                    ts=now_iso(),
                    engine="gemini-image",
                    flow="statics",
                    brand=brand.slug,
                    run_id=ts,
                    model="gemini-3.1-flash-image-preview",
                    params={"concept_id": concept.id},
                    status="failed",
                    elapsed_s=elapsed,
                    cost_estimate_usd=per_call_est,
                    cost_actual_usd=None,
                    asset_id=None,
                    video_path=None,
                    error=str(exc)[-500:],
                ),
            )
            return (concept.id, "failed", None, elapsed, str(exc))

    n_workers = min(args.parallel, len(built))
    print(f"[statics] dispatching {len(built)} renders, {n_workers} parallel workers")
    results = []
    with cf.ThreadPoolExecutor(max_workers=n_workers) as pool:
        futs = [pool.submit(_one, c, bp) for c, bp in built]
        for fut in cf.as_completed(futs):
            r = fut.result()
            results.append(r)
            if r[1] == "ok":
                print(f"[statics] {r[0]} OK ({r[3]}s) → {r[2].name}")
            else:
                print(f"[statics] {r[0]} FAILED ({r[3]}s): {r[4]}", file=sys.stderr)

    n_ok = sum(1 for r in results if r[1] == "ok")
    n_fail = len(results) - n_ok
    print(f"\n[statics] done. {n_ok} ok, {n_fail} failed. outputs in: {run_dir}")
    return 0 if n_fail == 0 else 1
