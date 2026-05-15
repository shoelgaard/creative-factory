"""UGC talking-head flow orchestration.

Called by `cf ugc gen`. Owns:
  - persona → situation+voice resolution (with caching per brand)
  - script_builder invocation
  - dialogue gate (separate from credit gate)
  - Arcads engine calls
  - log + meta + brief persistence
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
from typing import Optional

# engines/ is not a Python package on its own — import via path manipulation
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "engines" / "arcads"))

import client as arcads  # type: ignore  # engines/arcads/client.py
from shared.brand_loader import Brand, load_brand
from shared.cost_estimator import estimate as cost_estimate
from shared.gates import CreditEstimate, credit_gate, dialogue_gate
from shared.run_log import RunEntry, append_run, now_iso

from .script_builder import UgcBrief, build_script


PERSONA_FILTERS = {
    "female-adult": {"actor_gender": "Female", "actor_age": "Adult"},
    "female-young-adult": {"actor_gender": "Female", "actor_age": "Young Adult"},
    "male-adult": {"actor_gender": "Male", "actor_age": "Adult"},
}


def _read_brand_defaults(brand_slug: str) -> dict:
    """Parse '## Defaults' section of brands/<slug>/MASTER_CONTEXT.md."""
    path = _PROJECT_ROOT / "brands" / brand_slug / "MASTER_CONTEXT.md"
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


def _resolve_persona(brand: Brand, persona_arg: str) -> str:
    if persona_arg != "auto":
        return persona_arg
    defaults = _read_brand_defaults(brand.slug)
    return defaults.get("ugc_default_persona", "female-adult")


def _pick_situation_voice(persona: str) -> tuple[str, str, dict, dict]:
    """Return (situation_id, voice_id, situation_obj, voice_obj).

    Picks the first available Danish voice and first talking situation matching
    the persona filters. Caches none — caller may cache the chosen pair in the
    brand's MASTER_CONTEXT for stability.
    """
    filters = PERSONA_FILTERS.get(persona)
    if not filters:
        raise ValueError(f"Unknown persona: {persona}")

    voices = arcads.list_voices(gender=filters["actor_gender"], language="da")
    if not voices:
        # Try alternate language codes commonly used by TTS providers
        for lang_try in ("da-DK", "dan", "danish"):
            voices = arcads.list_voices(gender=filters["actor_gender"], language=lang_try)
            if voices:
                break
    if not voices:
        raise RuntimeError(
            "No Danish voices returned by Arcads for the chosen gender. "
            "Run `python3 engines/arcads/client.py voices-da` to debug."
        )

    sits = arcads.list_situations(
        actor_gender=filters["actor_gender"].lower(),
        actor_age=filters["actor_age"].lower().replace(" ", "_"),
        talking_actor_enabled=True,
    )
    if not sits:
        raise RuntimeError(
            f"No talking-actor situations match persona={persona}. "
            "Run `python3 engines/arcads/client.py situations --gender female --age adult`."
        )

    voice = voices[0]
    sit = sits[0]
    voice_id = voice.get("id") or voice.get("_id") or voice.get("voiceId")
    sit_id = sit.get("id") or sit.get("_id") or sit.get("situationId")
    if not (voice_id and sit_id):
        raise RuntimeError(f"Could not extract ids: voice={voice}, situation={sit}")
    return sit_id, voice_id, sit, voice


def _resolve_product_and_project(brand: Brand) -> tuple[str, str]:
    """Find or create the Arcads productId + the dated folder/project for today."""
    products = arcads.list_products()
    target = None
    for p in products:
        name = (p.get("name") or "").lower()
        if brand.name.lower() in name or brand.slug in name:
            target = p
            break
    if not target and products:
        # No exact match — use the first product. User will likely create a
        # proper "Persillo" product in Arcads after first run.
        target = products[0]
    if not target:
        raise RuntimeError(
            "No products in your Arcads account. Create one at app.arcads.ai first."
        )
    product_id = target.get("id") or target.get("_id")

    folder_name = dt.datetime.now().strftime("Creative Factory UGC - %Y-%m-%d")
    folder = arcads.create_folder(product_id=product_id, name=folder_name)
    folder_id = folder.get("id") or folder.get("_id")

    project_name = f"{folder_name} – {brand.name}"
    project = arcads.create_project(
        product_id=product_id, folder_id=folder_id, name=project_name
    )
    project_id = project.get("id") or project.get("_id")
    if not project_id:
        raise RuntimeError(f"Could not extract project_id from {project}")
    return product_id, project_id


def _load_brief_file(path: pathlib.Path, brand_slug: str) -> UgcBrief:
    """Tiny YAML parser — only enough for our flat schema. Avoids PyYAML dep."""
    data: dict[str, object] = {"brand": brand_slug}
    current_list_key: Optional[str] = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if current_list_key and line.startswith("  -"):
            data.setdefault(current_list_key, []).append(  # type: ignore[arg-type]
                line.split("-", 1)[1].strip().strip('"').strip("'")
            )
            continue
        current_list_key = None
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if not v:
                current_list_key = k
                data[k] = []
            else:
                data[k] = v.strip('"').strip("'")
    return UgcBrief(
        brand=str(data.get("brand", brand_slug)),
        product=str(data["product"]),
        persona=str(data.get("persona", "auto")),
        hook=data.get("hook") if isinstance(data.get("hook"), str) else None,  # type: ignore
        beats=data.get("beats") if isinstance(data.get("beats"), list) else None,  # type: ignore
        cta=data.get("cta") if isinstance(data.get("cta"), str) else None,  # type: ignore
    )


def cmd_ugc_gen(args: argparse.Namespace) -> int:
    # 1. Brand
    try:
        brand = load_brand(args.brand, _PROJECT_ROOT / "brands")
    except FileNotFoundError as exc:
        print(f"[ugc] {exc}", file=sys.stderr)
        return 2

    # 2. Brief
    if args.brief_file:
        brief = _load_brief_file(pathlib.Path(args.brief_file).expanduser().resolve(), brand.slug)
    else:
        if not args.product:
            print("[ugc] --product is required when --brief-file is not given", file=sys.stderr)
            return 2
        brief = UgcBrief(
            brand=brand.slug,
            product=args.product,
            persona=args.persona,
            hook=args.hook,
            beats=args.beats,
            cta=args.cta,
        )

    # 3. Script
    try:
        script = build_script(brand, brief, project_root=_PROJECT_ROOT)
    except ValueError as exc:
        print(f"[ugc] {exc}", file=sys.stderr)
        return 1

    print(f"[ugc] brand={brand.slug}  product={brief.product}  persona={brief.persona}")
    print(f"[ugc] script: {script.word_count} words ≈ {script.estimated_seconds}s spoken")

    # 4. Dialogue gate (separate from credit)
    if not dialogue_gate(
        script.lines,
        target_duration_s=int(script.estimated_seconds) + 2,
        assume_yes=args.yes,
    ):
        print("[ugc] aborted at dialogue gate", file=sys.stderr)
        return 1

    # 5. Persona → Arcads situation + voice
    persona = _resolve_persona(brand, brief.persona)
    try:
        situation_id, voice_id, situation, voice = _pick_situation_voice(persona)
    except Exception as exc:
        print(f"[ugc] persona resolution failed: {exc}", file=sys.stderr)
        return 1
    print(f"[ugc] situation={situation_id}  voice={voice_id} ({voice.get('name', '?')})")

    # 6. Cost gate (Arcads doesn't expose per-call price; use estimator)
    est_usd, est_source = cost_estimate(
        project_root=_PROJECT_ROOT,
        engine="arcads",
        model="v1/scripts",
        duration_s=int(script.estimated_seconds),
    )
    defaults = _read_brand_defaults(brand.slug)
    max_per_run_str = defaults.get("max_cost_per_run_usd")
    try:
        max_per_run = float(max_per_run_str) if max_per_run_str else None
    except ValueError:
        max_per_run = None

    if not credit_gate(
        [
            CreditEstimate(
                engine="arcads",
                model="v1/scripts",
                duration_s=int(script.estimated_seconds),
                estimate_usd=est_usd,
                source=est_source,
            )
        ],
        max_per_run_usd=max_per_run,
        assume_yes=args.yes,
    ):
        print("[ugc] aborted at credit gate", file=sys.stderr)
        return 1

    # 7. Resolve product + project on Arcads side
    try:
        product_id, project_id = _resolve_product_and_project(brand)
    except Exception as exc:
        print(f"[ugc] project setup failed: {exc}", file=sys.stderr)
        return 1
    print(f"[ugc] arcads product={product_id}  project={project_id}")

    # 8. Output dir + brief.json + script.txt
    ts = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = _PROJECT_ROOT / "output" / ts / "ugc-talking-head" / brand.slug / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "brief.json").write_text(
        json.dumps(
            {
                "flow": "ugc-talking-head",
                "flow_version": "0.1.0",
                "brand": brand.slug,
                "product": brief.product,
                "persona": persona,
                "hook": brief.hook,
                "beats": brief.beats,
                "cta": brief.cta,
                "situation_id": situation_id,
                "voice_id": voice_id,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "script.txt").write_text(script.text, encoding="utf-8")

    # 9. Create + generate
    script_name = f"{brand.name} {brief.product} {ts}"
    try:
        script_obj = arcads.create_script(
            name=script_name,
            text=script.text,
            project_id=project_id,
            videos=[{"situationId": situation_id, "voiceId": voice_id}],
        )
        script_id = script_obj.get("id") or script_obj.get("_id")
        if not script_id:
            raise RuntimeError(f"No script id in response: {script_obj}")
        arcads.generate_script(script_id)
    except Exception as exc:
        print(f"[ugc] script create/generate failed: {exc}", file=sys.stderr)
        return 1
    print(f"[ugc] arcads script={script_id} — generating ...")

    # 10. Poll
    started_at = time.monotonic()
    try:
        videos = arcads.poll_script_videos(script_id, poll_interval=8.0, max_wait=900.0)
    except Exception as exc:
        print(f"[ugc] poll failed: {exc}", file=sys.stderr)
        return 1
    elapsed_s = round(time.monotonic() - started_at, 1)

    # 11. Download + log
    saved_paths: list[pathlib.Path] = []
    for i, v in enumerate(videos, start=1):
        url = v.get("videoUrl") or (v.get("data", {}) or {}).get("videoUrl")
        status = v.get("videoStatus")
        if not url:
            print(f"[ugc] WARN: video {i} has no url, status={status}", file=sys.stderr)
            continue
        dest = run_dir / f"arcads_{ts}_v{i:02d}.mp4"
        arcads.download(url, dest)
        saved_paths.append(dest)
        print(f"[ugc] saved: {dest}")

    append_run(
        _PROJECT_ROOT / "logs",
        RunEntry(
            ts=now_iso(),
            engine="arcads",
            flow="ugc-talking-head",
            brand=brand.slug,
            run_id=ts,
            model="v1/scripts",
            params={
                "situationId": situation_id,
                "voiceId": voice_id,
                "wordCount": script.word_count,
                "estimatedSeconds": script.estimated_seconds,
            },
            status="ok" if saved_paths else "failed",
            elapsed_s=elapsed_s,
            cost_estimate_usd=est_usd,
            cost_actual_usd=None,
            asset_id=script_id,
            video_path=str(saved_paths[0]) if saved_paths else None,
            error=None if saved_paths else "no video urls in poll response",
        ),
    )

    print(f"[ugc] done in {elapsed_s}s. outputs in: {run_dir}")
    return 0 if saved_paths else 1
