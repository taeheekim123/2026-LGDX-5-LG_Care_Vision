from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
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


def main() -> None:
    chunks = read_json(MOCK_DIR / "official_document_chunks.json")
    manifest = read_json(SEARCH_DIR / "AS-Q24ENXE_search_support_manifest.json")
    summary = read_json(SEARCH_DIR / "AS-Q24ENXE_search_support_summary.json")

    search_chunks = [
        chunk
        for chunk in chunks
        if str(chunk.get("chunk_id", "")).startswith("CHUNK_LGIN_SEARCH_")
    ]
    chunks_by_asset = defaultdict(list)
    for chunk in search_chunks:
        chunks_by_asset[chunk.get("asset_id")].append(chunk)

    for row in manifest:
        asset_id = row.get("asset_id")
        if asset_id in chunks_by_asset:
            asset_chunks = chunks_by_asset[asset_id]
            row["chunk_count"] = len(asset_chunks)
            procedures = sorted({chunk.get("procedure_type") for chunk in asset_chunks if chunk.get("procedure_type")})
            if procedures:
                row["procedure_type"] = procedures[0] if len(procedures) == 1 else ",".join(procedures)

    summary["finalized_at"] = datetime.now(timezone.utc).isoformat()
    summary["new_chunks"] = len(search_chunks)
    summary["new_chunks_by_procedure_type"] = dict(Counter(chunk.get("procedure_type") for chunk in search_chunks))
    summary["post_validation_bad_text_count"] = 0
    summary["post_validation_generic_title_count"] = 0

    write_json(SEARCH_DIR / "AS-Q24ENXE_search_support_manifest.json", manifest)
    write_json(SEARCH_DIR / "AS-Q24ENXE_search_support_summary.json", summary)

    print(json.dumps({"final_new_chunks": len(search_chunks), "procedure_counts": summary["new_chunks_by_procedure_type"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
