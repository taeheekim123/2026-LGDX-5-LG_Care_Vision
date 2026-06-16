from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
MOCK_DIR = DATA_DIR / "mock_data"
EXT_DIR = DATA_DIR / "source_data" / "official_lg_india" / "rag_corpus_extension"

BOILERPLATE_PATTERNS = [
    "skip to content",
    "we use cookies",
    "cookie settings",
    "lg signature",
    "about lg",
    "compliance energy consumption calculator",
    "service center locator",
    "email to ceo office",
    "environmental handing fee",
    "contact us chatbot whatsapp",
    "where to buy",
    "privacy portal",
]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def has_boilerplate(text: str) -> bool:
    lower = (text or "").lower()
    return any(pattern in lower for pattern in BOILERPLATE_PATTERNS)


def main() -> None:
    assets_path = MOCK_DIR / "official_assets_db.json"
    chunks_path = MOCK_DIR / "official_document_chunks.json"
    summary_path = EXT_DIR / "rag_corpus_extension_summary.json"

    assets = read_json(assets_path)
    chunks = read_json(chunks_path)
    summary = read_json(summary_path) if summary_path.exists() else {}

    removed_chunks = []
    kept_chunks = []
    for chunk in chunks:
        if str(chunk.get("chunk_id", "")).startswith("CHUNK_LGIN_RAG_"):
            text = chunk.get("chunk_text") or ""
            if len(text.strip()) < 80 or has_boilerplate(text):
                removed_chunks.append(chunk)
                continue
        kept_chunks.append(chunk)

    kept_asset_ids = {chunk.get("asset_id") for chunk in kept_chunks if chunk.get("asset_id")}
    removed_assets = []
    kept_assets = []
    for asset in assets:
        is_new_help_asset = (
            str(asset.get("asset_id", "")).startswith("OA_LGIN_RAG_")
            and asset.get("asset_type") == "help_library"
        )
        generic_title = str(asset.get("title") or "").strip().lower() in {"help library: | lg india", "| lg india"}
        if is_new_help_asset and (asset.get("asset_id") not in kept_asset_ids or generic_title):
            removed_assets.append(asset)
            continue
        kept_assets.append(asset)

    write_json(assets_path, kept_assets)
    write_json(chunks_path, kept_chunks)

    new_assets = [asset for asset in kept_assets if str(asset.get("asset_id", "")).startswith("OA_LGIN_RAG_")]
    new_chunks = [chunk for chunk in kept_chunks if str(chunk.get("chunk_id", "")).startswith("CHUNK_LGIN_RAG_")]
    summary.update(
        {
            "cleaned_at": datetime.now(timezone.utc).isoformat(),
            "new_assets": len(new_assets),
            "new_chunks": len(new_chunks),
            "combined_assets": len(kept_assets),
            "combined_chunks": len(kept_chunks),
            "new_assets_by_type": dict(Counter(asset.get("asset_type") for asset in new_assets)),
            "new_chunks_by_source_type": dict(Counter(chunk.get("source_type") for chunk in new_chunks)),
            "new_chunks_by_product_type": dict(Counter(chunk.get("product_type") for chunk in new_chunks)),
            "new_chunks_by_procedure_type": dict(Counter(chunk.get("procedure_type") for chunk in new_chunks)),
            "boilerplate_chunk_count": 0,
            "boilerplate_chunk_ids_sample": [],
            "post_validation_removed_assets": [
                {
                    "asset_id": asset.get("asset_id"),
                    "asset_type": asset.get("asset_type"),
                    "source_url": asset.get("source_url"),
                    "title": asset.get("title"),
                    "reason": "boilerplate_or_generic_help_library",
                }
                for asset in removed_assets
            ],
            "post_validation_removed_chunks": [
                {
                    "chunk_id": chunk.get("chunk_id"),
                    "asset_id": chunk.get("asset_id"),
                    "reason": "boilerplate_or_too_short",
                }
                for chunk in removed_chunks
            ],
        }
    )
    write_json(summary_path, summary)

    print(
        json.dumps(
            {
                "removed_assets": len(removed_assets),
                "removed_chunks": len(removed_chunks),
                "remaining_assets": len(kept_assets),
                "remaining_chunks": len(kept_chunks),
                "remaining_new_assets": len(new_assets),
                "remaining_new_chunks": len(new_chunks),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
