from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
MOCK_DIR = DATA_DIR / "mock_data"
OUTPUT_PATH = MOCK_DIR / "official_document_chunks.json"
NOW = "2026-06-03T12:00:00+05:30"


BOILERPLATE_PATTERNS = [
    "javascript appears to be disabled",
    "we use cookies",
    "cookie settings",
    "connect with your social channels",
    "share lg technology with friends",
    "add items to your wishlist",
    "the url has been copied",
    "was this information helpful",
    "your email has been successfully registered",
    "otp authentication failed",
    "all rights reserved",
    "lg electronics official website",
    "accessories all",
    "privacy and cookie policy",
    "get stock alert",
    "where to buy",
    "select region and language",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = text.replace("\\u0026", "&")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_title(source: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", source)
    if match:
        return norm_text(match.group(1))
    return ""


def extract_meta_description(source: str) -> str:
    patterns = [
        r'(?is)<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
        r'(?is)<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, source)
        if match:
            return norm_text(match.group(1))
    return ""


def extract_json_ld_nodes(source: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for match in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', source):
        raw = html.unescape(match.group(1)).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        nodes.extend(walk_json(data))
    return nodes


def walk_json(value: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if isinstance(value, dict):
        nodes.append(value)
        for child in value.values():
            nodes.extend(walk_json(child))
    elif isinstance(value, list):
        for item in value:
            nodes.extend(walk_json(item))
    return nodes


def unique_texts(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        value = clean_official_text(value)
        if len(value) < 30:
            continue
        key = value[:300].lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def extract_official_content(source: str) -> dict[str, Any]:
    title = extract_title(source)
    description = extract_meta_description(source)
    nodes = extract_json_ld_nodes(source)

    article_bodies = unique_texts([norm_text(node.get("articleBody")) for node in nodes if node.get("articleBody")])
    json_ld_descriptions = unique_texts(
        [
            norm_text(node.get(key))
            for node in nodes
            for key in ("headline", "name", "description")
            if node.get(key)
        ]
    )

    if article_bodies:
        body_parts = article_bodies
        source_section = "json_ld_articleBody"
    else:
        body_parts = json_ld_descriptions
        source_section = "json_ld_title_description"

    text = clean_official_text(" ".join([title, description, *body_parts]))
    if len(text) < 80:
        source_section = "meta_title_description"
        text = clean_official_text(" ".join([title, description]))

    return {
        "title": title,
        "description": description,
        "text": text,
        "source_section": source_section,
        "article_body_count": len(article_bodies),
        "json_ld_description_count": len(json_ld_descriptions),
    }


def clean_official_text(value: str) -> str:
    text = norm_text(value)
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+|(?<=\))\s+", text)
    cleaned = []
    for sentence in sentences:
        sentence = norm_text(sentence)
        if len(sentence) < 12:
            continue
        lower = sentence.lower()
        if any(pattern in lower for pattern in BOILERPLATE_PATTERNS):
            continue
        cleaned.append(sentence)
    return " ".join(cleaned)


def make_chunks(text: str) -> list[str]:
    if not text:
        return []
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if len(sentence.strip()) >= 20]
    chunks = []
    buffer: list[str] = []
    length = 0
    for sentence in sentences:
        buffer.append(sentence)
        length += len(sentence)
        if length >= 900:
            chunks.append(" ".join(buffer)[:1400])
            buffer = []
            length = 0
    if buffer:
        chunks.append(" ".join(buffer)[:1400])
    if not chunks and len(text) >= 80:
        chunks.append(text[:1400])
    return chunks[:20]


def has_boilerplate(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in BOILERPLATE_PATTERNS)


def main() -> None:
    assets = read_json(MOCK_DIR / "official_assets_db.json")
    chunks: list[dict[str, Any]] = []
    extraction_counter: Counter[str] = Counter()
    rejected_assets = []
    boilerplate_chunk_ids = []

    for asset_index, asset in enumerate(assets, start=1):
        raw_file = asset.get("raw_file")
        if not raw_file:
            rejected_assets.append({"asset_id": asset["asset_id"], "reason": "missing_raw_file"})
            continue
        raw_path = PROJECT_DIR / raw_file
        if not raw_path.exists():
            rejected_assets.append({"asset_id": asset["asset_id"], "reason": "raw_file_not_found", "raw_file": raw_file})
            continue
        source = raw_path.read_text(encoding="utf-8", errors="ignore")
        extracted = extract_official_content(source)
        extraction_counter[extracted["source_section"]] += 1
        asset_chunks = make_chunks(extracted["text"])
        if not asset_chunks:
            rejected_assets.append(
                {
                    "asset_id": asset["asset_id"],
                    "reason": "no_usable_title_description_or_article_body",
                    "source_url": asset.get("source_url"),
                }
            )
            continue
        for chunk_index, chunk_text in enumerate(asset_chunks, start=1):
            chunk_id = f"CHUNK_LGIN_{asset_index:03d}_{chunk_index:03d}"
            if has_boilerplate(chunk_text):
                boilerplate_chunk_ids.append(chunk_id)
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "asset_id": asset["asset_id"],
                    "product_type": asset["product_type"],
                    "model_name": asset.get("model_name"),
                    "series": asset.get("matched_series"),
                    "procedure_type": (asset.get("available_procedures") or [None])[0],
                    "language": "en",
                    "chunk_title": extracted["title"] or asset.get("title"),
                    "chunk_text": chunk_text,
                    "source_url": asset["source_url"],
                    "source_section": extracted["source_section"],
                    "source_raw_file": raw_file,
                    "applicability_scope": asset["applicability_scope"],
                    "forbidden_actions": asset.get("forbidden_actions", []),
                    "safety_tags": [],
                    "embedding_status": "not_embedded",
                    "verification_status": "collected_official_lg_india",
                    "last_checked_at": NOW,
                    "created_at": NOW,
                    "extraction_quality": {
                        "article_body_count": extracted["article_body_count"],
                        "json_ld_description_count": extracted["json_ld_description_count"],
                        "boilerplate_detected": has_boilerplate(chunk_text),
                    },
                }
            )

    write_json(OUTPUT_PATH, chunks)
    summary = {
        "assets_input": len(assets),
        "chunks_output": len(chunks),
        "rejected_assets": len(rejected_assets),
        "extraction_method_counts": dict(extraction_counter),
        "boilerplate_chunk_count": len(boilerplate_chunk_ids),
        "boilerplate_chunk_ids_sample": boilerplate_chunk_ids[:20],
        "rejected_assets_sample": rejected_assets[:20],
        "output_path": str(OUTPUT_PATH),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
