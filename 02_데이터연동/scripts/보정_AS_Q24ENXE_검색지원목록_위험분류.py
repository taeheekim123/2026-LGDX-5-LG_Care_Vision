from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
MOCK_DIR = DATA_DIR / "mock_data"
SEARCH_DIR = DATA_DIR / "source_data" / "official_lg_india" / "rag_corpus_extension" / "search_support_html"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_refrigerant_risk(text: str) -> bool:
    lower = (text or "").lower()
    return (
        "smell gas" in lower
        or "gas smell" in lower
        or "refrigerant (gas) leaks" in lower
        or ("ventilate" in lower and "service technician" in lower)
    )


def main() -> None:
    assets_path = MOCK_DIR / "official_assets_db.json"
    chunks_path = MOCK_DIR / "official_document_chunks.json"
    manifest_path = SEARCH_DIR / "AS-Q24ENXE_search_support_manifest.json"
    summary_path = SEARCH_DIR / "AS-Q24ENXE_search_support_summary.json"

    assets = read_json(assets_path)
    chunks = read_json(chunks_path)
    manifest = read_json(manifest_path)
    summary = read_json(summary_path)

    manual_procedure_override = {
        "CHUNK_LGIN_SEARCH_0005_001": "support_search_result",
        "CHUNK_LGIN_SEARCH_0009_001": "noise_self_check",
        "CHUNK_LGIN_SEARCH_0009_002": "noise_self_check",
        "CHUNK_LGIN_SEARCH_0010_001": "noise_self_check",
        "CHUNK_LGIN_SEARCH_0021_001": "high_risk_refrigerant",
        "CHUNK_LGIN_SEARCH_0023_001": "no_cooling_self_check",
        "CHUNK_LGIN_SEARCH_0027_001": "water_leak_monsoon",
    }
    remove_low_signal_chunks = {"CHUNK_LGIN_SEARCH_0027_002"}

    removed_short_chunks = []
    removed_low_signal_chunks = []
    kept_chunks = []
    updated_chunks = 0
    for chunk in chunks:
        if str(chunk.get("chunk_id", "")).startswith("CHUNK_LGIN_SEARCH_"):
            text = chunk.get("chunk_text") or ""
            if len(text.strip()) < 80:
                removed_short_chunks.append(chunk.get("chunk_id"))
                continue
            if chunk.get("chunk_id") in remove_low_signal_chunks:
                removed_low_signal_chunks.append(chunk.get("chunk_id"))
                continue
            target_procedure = manual_procedure_override.get(chunk.get("chunk_id"))
            if not target_procedure and is_refrigerant_risk(f"{chunk.get('chunk_title')} {text}"):
                target_procedure = "high_risk_refrigerant"
            if target_procedure and chunk.get("procedure_type") != target_procedure:
                chunk["procedure_type"] = target_procedure
                updated_chunks += 1
        kept_chunks.append(chunk)

    updated_assets = 0
    asset_chunk_procedures: dict[str, set[str]] = {}
    for chunk in kept_chunks:
        if str(chunk.get("chunk_id", "")).startswith("CHUNK_LGIN_SEARCH_"):
            asset_chunk_procedures.setdefault(chunk.get("asset_id"), set()).add(chunk.get("procedure_type"))

    for asset in assets:
        if str(asset.get("asset_id", "")).startswith("OA_LGIN_SEARCH_"):
            procedures = sorted(p for p in asset_chunk_procedures.get(asset.get("asset_id"), set()) if p)
            if procedures and asset.get("available_procedures") != procedures:
                asset["available_procedures"] = procedures
                updated_assets += 1

    for row in manifest:
        if row.get("asset_id") in asset_chunk_procedures:
            procedures = sorted(p for p in asset_chunk_procedures[row.get("asset_id")] if p)
            if procedures:
                row["procedure_type"] = procedures[0] if len(procedures) == 1 else ",".join(procedures)
        if row.get("asset_id") == "OA_LGIN_SEARCH_0021":
            row["risk_note"] = "gas/refrigerant wording mapped to high_risk_refrigerant"

    summary["post_validation_removed_short_chunks"] = removed_short_chunks
    summary["post_validation_removed_low_signal_chunks"] = removed_low_signal_chunks
    summary["post_validation_updated_risk_chunks"] = updated_chunks

    write_json(assets_path, assets)
    write_json(chunks_path, kept_chunks)
    write_json(manifest_path, manifest)
    write_json(summary_path, summary)

    print(
        json.dumps(
            {
                "removed_short_chunks": removed_short_chunks,
                "removed_low_signal_chunks": removed_low_signal_chunks,
                "updated_chunks": updated_chunks,
                "updated_assets": updated_assets,
                "remaining_chunks": len(kept_chunks),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
