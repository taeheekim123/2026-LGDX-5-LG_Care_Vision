from __future__ import annotations

import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
MOCK_DIR = DATA_DIR / "mock_data"
SUMMARY_PATH = DATA_DIR / "source_data" / "official_lg_india" / "rag_corpus_extension" / "rag_corpus_extension_summary.json"


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_DIR.resolve()))


def main() -> None:
    assets = json.loads((MOCK_DIR / "official_assets_db.json").read_text(encoding="utf-8"))
    chunks = json.loads((MOCK_DIR / "official_document_chunks.json").read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    manifest_path = DATA_DIR / "source_data" / "official_lg_india" / "rag_corpus_extension" / "search_support_html" / "AS-Q24ENXE_search_support_manifest.json"
    search_summary_path = DATA_DIR / "source_data" / "official_lg_india" / "rag_corpus_extension" / "search_support_html" / "AS-Q24ENXE_search_support_summary.json"

    summary["current_total_assets_after_search_support"] = len(assets)
    summary["current_total_chunks_after_search_support"] = len(chunks)
    summary["search_support_extension"] = {
        "asset_type": "search_support_result",
        "assets": sum(1 for asset in assets if asset.get("asset_type") == "search_support_result"),
        "chunks": sum(1 for chunk in chunks if chunk.get("source_type") == "search_support_result"),
        "model_name": "AS-Q24ENXE",
        "source_page": "https://www.lg.com/in/search/?search=AS-Q24ENXE&tab=support",
        "manifest": relative(manifest_path),
        "summary": relative(search_summary_path),
    }

    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary["search_support_extension"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
