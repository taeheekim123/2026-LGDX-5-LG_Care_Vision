from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
MOCK_DIR = DATA_DIR / "mock_data"
SEARCH_DIR = DATA_DIR / "source_data" / "official_lg_india" / "rag_corpus_extension" / "search_support_html"


def read_json(path: Path) -> Any:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, str):
        data = json.loads(data)
    return data


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def support_url_from_result(result: dict[str, Any]) -> str | None:
    raw = result.get("raw") or {}
    uri = str(result.get("uri") or raw.get("uri") or raw.get("sysuri") or "")
    match = re.search(r"support://(\d+)\.in\.(CT\d+)", uri, re.I)
    if not match:
        return None
    doc_id, super_cat_id = match.group(1), match.group(2)
    return f"https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-{super_cat_id}-{doc_id}/"


def main() -> None:
    coveo = read_json(SEARCH_DIR / "AS-Q24ENXE_coveo_support_filtered_raw.json")
    manifest = read_json(SEARCH_DIR / "AS-Q24ENXE_search_support_manifest.json")
    assets = read_json(MOCK_DIR / "official_assets_db.json")
    chunks = read_json(MOCK_DIR / "official_document_chunks.json")

    title_by_url = {}
    for result in coveo.get("results") or []:
        url = support_url_from_result(result)
        title = result.get("title")
        if url and title:
            title_by_url[url] = title

    updated_assets = 0
    updated_chunks = 0
    updated_manifest = 0

    for asset in assets:
        if str(asset.get("asset_id", "")).startswith("OA_LGIN_SEARCH_"):
            title = title_by_url.get(asset.get("source_url"))
            if title and asset.get("title") != title:
                asset["title"] = title
                updated_assets += 1

    for chunk in chunks:
        if str(chunk.get("chunk_id", "")).startswith("CHUNK_LGIN_SEARCH_"):
            title = title_by_url.get(chunk.get("source_url"))
            if title and chunk.get("chunk_title") != title:
                chunk["chunk_title"] = title
                updated_chunks += 1

    for row in manifest:
        title = title_by_url.get(row.get("source_url"))
        if title and row.get("title") != title:
            row["title"] = title
            updated_manifest += 1

    write_json(MOCK_DIR / "official_assets_db.json", assets)
    write_json(MOCK_DIR / "official_document_chunks.json", chunks)
    write_json(SEARCH_DIR / "AS-Q24ENXE_search_support_manifest.json", manifest)

    print(
        json.dumps(
            {
                "updated_assets": updated_assets,
                "updated_chunks": updated_chunks,
                "updated_manifest": updated_manifest,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
