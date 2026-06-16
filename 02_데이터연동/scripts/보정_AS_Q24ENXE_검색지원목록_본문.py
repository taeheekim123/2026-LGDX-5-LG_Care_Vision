from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
MOCK_DIR = DATA_DIR / "mock_data"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_search_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"^(null|none)\s+", "", text, flags=re.I).strip()
    text = re.sub(r"\s*LG IN LG IN Home Support Product Support Troubleshoot\s*$", "", text).strip()
    return text


def main() -> None:
    path = MOCK_DIR / "official_document_chunks.json"
    chunks = read_json(path)
    updated = 0
    too_short = []
    for chunk in chunks:
        if str(chunk.get("chunk_id", "")).startswith("CHUNK_LGIN_SEARCH_"):
            before = chunk.get("chunk_text") or ""
            after = clean_search_text(before)
            if after != before:
                chunk["chunk_text"] = after
                extraction_quality = chunk.setdefault("extraction_quality", {})
                extraction_quality["char_count"] = len(after)
                updated += 1
            if len((chunk.get("chunk_text") or "").strip()) < 80:
                too_short.append(chunk.get("chunk_id"))
    write_json(path, chunks)
    print(json.dumps({"updated_chunks": updated, "too_short_after_cleaning": too_short}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
