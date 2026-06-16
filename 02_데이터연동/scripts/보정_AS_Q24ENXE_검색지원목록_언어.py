from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
MOCK_DIR = DATA_DIR / "mock_data"
SEARCH_DIR = DATA_DIR / "source_data" / "official_lg_india" / "rag_corpus_extension" / "search_support_html"


DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    chunks_path = MOCK_DIR / "official_document_chunks.json"
    summary_path = SEARCH_DIR / "AS-Q24ENXE_search_support_summary.json"
    chunks = read_json(chunks_path)
    summary = read_json(summary_path)

    updated = []
    for chunk in chunks:
        if str(chunk.get("chunk_id", "")).startswith("CHUNK_LGIN_SEARCH_"):
            text = f"{chunk.get('chunk_title') or ''} {chunk.get('chunk_text') or ''}"
            if DEVANAGARI_RE.search(text) and chunk.get("language") != "hi":
                chunk["language"] = "hi"
                updated.append(chunk.get("chunk_id"))

    summary["post_validation_language_updates"] = {
        "hi_chunks": updated,
        "reason": "Devanagari text detected in LG India support search result",
    }

    write_json(chunks_path, chunks)
    write_json(summary_path, summary)
    print(json.dumps(summary["post_validation_language_updates"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
