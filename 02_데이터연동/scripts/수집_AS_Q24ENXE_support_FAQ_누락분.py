from __future__ import annotations

import html
import json
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
MOCK_DIR = DATA_DIR / "mock_data"
SOURCE_DIR = DATA_DIR / "source_data" / "official_lg_india"
GAP_DIR = SOURCE_DIR / "support_faq_gap_validation"
RAW_DIR = GAP_DIR / "missing_support_html"
OUTPUT_DIR = PROJECT_DIR / "06_산출물"

SEARCH_QUERY = "AS-Q24ENXE"
TODAY = datetime.now(timezone.utc).date().isoformat()
NOW = datetime.now(timezone.utc).isoformat()
SEARCH_PAGE_URL = "https://www.lg.com/in/search/?search=AS-Q24ENXE&tab=support"

BOILERPLATE_PATTERNS = [
    "javascript appears to be disabled",
    "we use cookies",
    "cookie settings",
    "lg signature",
    "about lg",
    "service center locator",
    "email to ceo office",
    "environmental handing fee",
    "privacy portal",
    "all rights reserved",
]

PROCEDURE_KEYWORDS = {
    "filter_cleaning": ["filter", "clean", "dust", "mesh", "odor", "smell"],
    "no_cooling_self_check": ["cooling", "cold", "temperature", "not cool", "outdoor unit", "indoor unit"],
    "water_leak_monsoon": ["water", "leak", "drip", "dew", "condensation", "humidity", "drain"],
    "noise_self_check": ["noise", "sound", "hissing", "swishing", "gulping", "vibration"],
    "remote_operation": ["remote", "fan speed", "mode", "operate", "display", "button"],
    "power_error_self_check": ["power", "turn on", "turn off", "error code", "display", "sp/cp/po"],
    "high_risk_refrigerant": ["gas", "refrigerant", "compressor", "service technician"],
    "high_risk_electrical": ["electric", "shock", "fire", "burning", "spark", "smoke"],
}

FORBIDDEN_ACTIONS = [
    "electrical_repair",
    "pcb_repair",
    "internal_disassembly",
    "refrigerant_repair",
    "compressor_repair",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def request_html(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 CareShotOfficialCorpusCollector/1.0",
            "Accept": "text/html,*/*",
            "Referer": SEARCH_PAGE_URL,
        },
    )
    with urllib.request.urlopen(req, timeout=40) as response:
        return response.read()


def normalize_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(null|none)\s+", "", text, flags=re.I).strip()
    text = re.sub(r"\s*LG IN LG IN Home Support Product Support Troubleshoot\s*$", "", text).strip()
    return text


def walk_json(value: Any) -> list[Any]:
    if isinstance(value, dict):
        rows = [value]
        for child in value.values():
            rows.extend(walk_json(child))
        return rows
    if isinstance(value, list):
        rows: list[Any] = []
        for child in value:
            rows.extend(walk_json(child))
        return rows
    return []


def clean_text(source: str) -> str:
    soup = BeautifulSoup(source, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    return normalize_text(soup.get_text(" "))


def extract_json_ld_or_html_text(source: str) -> tuple[str, str, dict[str, Any]]:
    title = ""
    parts: list[str] = []
    json_ld_nodes = 0
    article_body_count = 0
    description_count = 0
    soup = BeautifulSoup(source, "html.parser")
    if soup.title and soup.title.string:
        title = normalize_text(soup.title.string)
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(html.unescape(tag.get_text()).strip())
        except json.JSONDecodeError:
            continue
        json_ld_nodes += 1
        for node in walk_json(data):
            if isinstance(node, dict):
                for key in ("headline", "name", "description", "articleBody", "text"):
                    value = node.get(key)
                    if value:
                        if key == "articleBody":
                            article_body_count += 1
                        if key == "description":
                            description_count += 1
                        parts.append(normalize_text(value))
    text = normalize_text(" ".join(parts))
    if len(text) < 160:
        text = clean_text(source)
    quality = {
        "json_ld_nodes": json_ld_nodes,
        "article_body_count": article_body_count,
        "json_ld_description_count": description_count,
        "char_count": len(text),
        "boilerplate_detected": has_boilerplate(text),
    }
    return title, text, quality


def has_boilerplate(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in BOILERPLATE_PATTERNS)


def infer_procedure(title: str, excerpt: str, text: str) -> str:
    corpus = f"{title} {excerpt} {text}".lower()
    scores = {
        procedure: sum(1 for keyword in keywords if keyword in corpus)
        for procedure, keywords in PROCEDURE_KEYWORDS.items()
    }
    best, score = max(scores.items(), key=lambda item: item[1])
    return best if score > 0 else "support_search_result"


def detect_language(text: str) -> str:
    return "hi" if re.search(r"[\u0900-\u097F]", text) else "en"


def make_chunks(text: str, max_chars: int = 1200) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = normalize_text(sentence)
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 > max_chars and current:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if len(chunk) >= 100 and not has_boilerplate(chunk)]


def next_numeric_id(rows: list[dict[str, Any]], key: str, prefix: str) -> int:
    max_id = 0
    pattern = re.compile(re.escape(prefix) + r"(\d+)")
    for row in rows:
        match = pattern.match(str(row.get(key) or ""))
        if match:
            max_id = max(max_id, int(match.group(1)))
    return max_id + 1


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_DIR.resolve()))


def title_from_candidate(candidate: dict[str, Any], page_title: str) -> str:
    generic_titles = {
        "lg help library - support & help | lg india",
        "lg help library - support & help | lg in",
        "support & help | lg india",
    }
    candidate_title = normalize_text(candidate.get("title"))
    if page_title.strip().lower() in generic_titles and candidate_title:
        return candidate_title
    return page_title or candidate_title or "LG India support document"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = GAP_DIR / f"AS-Q24ENXE_support_FAQ_candidate_manifest_{TODAY}.json"
    missing_path = GAP_DIR / f"AS-Q24ENXE_support_FAQ_missing_urls_{TODAY}.json"
    if not manifest_path.exists() or not missing_path.exists():
        raise FileNotFoundError("간극 검증 manifest/missing URL 파일이 없습니다. 먼저 검증 스크립트를 실행하세요.")

    candidates = read_json(manifest_path)
    missing_urls = set(read_json(missing_path))
    candidate_by_url = {
        row["source_url"]: row
        for row in candidates
        if row.get("source_url") in missing_urls
    }

    assets_path = MOCK_DIR / "official_assets_db.json"
    chunks_path = MOCK_DIR / "official_document_chunks.json"
    assets = read_json(assets_path)
    chunks = read_json(chunks_path)
    existing_asset_urls = {row.get("source_url") for row in assets}
    existing_chunk_urls = {row.get("source_url") for row in chunks}

    asset_index = next_numeric_id(assets, "asset_id", "OA_LGIN_SUPPORT_FAQ_")
    chunk_index = next_numeric_id(chunks, "chunk_id", "CHUNK_LGIN_SUPPORT_FAQ_")
    new_assets: list[dict[str, Any]] = []
    new_chunks: list[dict[str, Any]] = []
    collection_manifest: list[dict[str, Any]] = []

    for ordinal, url in enumerate(sorted(missing_urls), start=1):
        candidate = candidate_by_url.get(url, {"source_url": url, "rank": None})
        row = {
            "ordinal": ordinal,
            "source_url": url,
            "candidate_rank": candidate.get("rank"),
            "candidate_title": candidate.get("title"),
            "status": "candidate",
        }
        if not url.startswith("https://www.lg.com/in/support/product-support/troubleshoot/help-library/"):
            row["status"] = "rejected_non_help_library_url"
            collection_manifest.append(row)
            continue
        if url in existing_asset_urls or url in existing_chunk_urls:
            row["status"] = "skipped_already_collected"
            collection_manifest.append(row)
            continue

        raw_file = RAW_DIR / f"AS-Q24ENXE_support_missing_{ordinal:03d}.html"
        try:
            if raw_file.exists() and raw_file.stat().st_size > 10_000:
                page_bytes = raw_file.read_bytes()
                row["raw_fetch_mode"] = "reused_existing_raw_html"
            else:
                page_bytes = request_html(url)
                raw_file.write_bytes(page_bytes)
                row["raw_fetch_mode"] = "downloaded"
            source = page_bytes.decode("utf-8", errors="ignore")
            page_title, text, quality = extract_json_ld_or_html_text(source)
            title = title_from_candidate(candidate, page_title)
            if len(text) < 140 or quality["boilerplate_detected"]:
                row.update(
                    {
                        "status": "rejected_short_or_boilerplate_text",
                        "raw_file": relative(raw_file),
                        "title": title,
                        "char_count": len(text),
                    }
                )
                collection_manifest.append(row)
                continue

            excerpt = normalize_text(candidate.get("excerpt"))
            procedure_type = infer_procedure(title, excerpt, text)
            made_chunks = make_chunks(text)
            if not made_chunks:
                row.update(
                    {
                        "status": "rejected_no_usable_chunks",
                        "raw_file": relative(raw_file),
                        "title": title,
                        "char_count": len(text),
                    }
                )
                collection_manifest.append(row)
                continue

            asset_id = f"OA_LGIN_SUPPORT_FAQ_{asset_index:04d}"
            asset = {
                "asset_id": asset_id,
                "asset_type": "help_library",
                "product_type": "air_conditioner",
                "model_name": SEARCH_QUERY,
                "title": title,
                "source_url": url,
                "raw_file": relative(raw_file),
                "source_origin": "LG India search support tab via Coveo missing support/FAQ gap collection",
                "source_date": TODAY,
                "applicability_scope": "model_search_support_result",
                "matched_model_names": [SEARCH_QUERY],
                "matched_aliases": [],
                "matched_series": None,
                "available_procedures": [procedure_type],
                "forbidden_actions": FORBIDDEN_ACTIONS,
                "verification_status": "official_source_verified",
                "last_checked_at": NOW,
            }
            for idx, chunk_text in enumerate(made_chunks, start=1):
                chunk_procedure_type = infer_procedure(title, excerpt, chunk_text)
                new_chunks.append(
                    {
                        "chunk_id": f"CHUNK_LGIN_SUPPORT_FAQ_{chunk_index:04d}_{idx:03d}",
                        "asset_id": asset_id,
                        "product_type": "air_conditioner",
                        "model_name": SEARCH_QUERY,
                        "series": None,
                        "procedure_type": chunk_procedure_type,
                        "language": detect_language(chunk_text),
                        "chunk_title": title,
                        "chunk_text": chunk_text,
                        "source_url": url,
                        "source_section": "missing_support_json_ld_or_html",
                        "source_type": "help_library",
                        "source_raw_file": relative(raw_file),
                        "download_url": None,
                        "online_url": None,
                        "applicability_scope": "model_search_support_result",
                        "forbidden_actions": FORBIDDEN_ACTIONS,
                        "safety_tags": [],
                        "embedding_status": "not_embedded",
                        "verification_status": "official_source_verified",
                        "created_at": NOW,
                        "last_checked_at": NOW,
                        "extraction_quality": {
                            **quality,
                            "chunk_char_count": len(chunk_text),
                        },
                    }
                )
            new_assets.append(asset)
            row.update(
                {
                    "status": "added",
                    "asset_id": asset_id,
                    "raw_file": relative(raw_file),
                    "title": title,
                    "procedure_type": procedure_type,
                    "chunk_count": len(made_chunks),
                    "char_count": len(text),
                }
            )
            collection_manifest.append(row)
            existing_asset_urls.add(url)
            existing_chunk_urls.add(url)
            asset_index += 1
            chunk_index += 1
        except Exception as exc:
            row["status"] = f"fetch_failed:{type(exc).__name__}:{exc}"
            collection_manifest.append(row)

    if new_assets or new_chunks:
        write_json(assets_path, assets + new_assets)
        write_json(chunks_path, chunks + new_chunks)

    summary = {
        "created_at": NOW,
        "source_missing_url_file": relative(missing_path),
        "candidate_manifest_file": relative(manifest_path),
        "target_missing_url_count": len(missing_urls),
        "processed_url_count": len(collection_manifest),
        "new_assets": len(new_assets),
        "new_chunks": len(new_chunks),
        "status_counts": dict(Counter(row["status"] for row in collection_manifest)),
        "new_chunks_by_procedure_type": dict(Counter(chunk["procedure_type"] for chunk in new_chunks)),
        "new_chunks_by_language": dict(Counter(chunk["language"] for chunk in new_chunks)),
        "raw_html_dir": relative(RAW_DIR),
        "updated_files": {
            "official_assets_db": relative(assets_path),
            "official_document_chunks": relative(chunks_path),
            "collection_manifest": relative(GAP_DIR / f"AS-Q24ENXE_support_FAQ_missing_collection_manifest_{TODAY}.json"),
            "summary": relative(GAP_DIR / f"AS-Q24ENXE_support_FAQ_missing_collection_summary_{TODAY}.json"),
            "report": relative(OUTPUT_DIR / f"AS-Q24ENXE_support_FAQ_누락분_수집리포트_{TODAY}.md"),
        },
    }
    write_json(GAP_DIR / f"AS-Q24ENXE_support_FAQ_missing_collection_manifest_{TODAY}.json", collection_manifest)
    write_json(GAP_DIR / f"AS-Q24ENXE_support_FAQ_missing_collection_summary_{TODAY}.json", summary)
    write_report(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def write_report(summary: dict[str, Any]) -> None:
    report_path = OUTPUT_DIR / f"AS-Q24ENXE_support_FAQ_누락분_수집리포트_{TODAY}.md"
    status_rows = "\n".join(f"| {key} | {value} |" for key, value in summary["status_counts"].items())
    procedure_rows = "\n".join(
        f"| {key} | {value} |" for key, value in summary["new_chunks_by_procedure_type"].items()
    )
    language_rows = "\n".join(f"| {key} | {value} |" for key, value in summary["new_chunks_by_language"].items())
    text = f"""# AS-Q24ENXE support/FAQ 누락분 수집 리포트

## 1. 작업 목적

간극 검증에서 확인된 AS-Q24ENXE support/FAQ 후보 누락 URL을 공식 LG India 원본 HTML로 저장하고, RAG용 official asset/chunk로 확장한다.

## 2. 수집 결과

| 항목 | 수량 |
|---|---:|
| 대상 누락 URL | {summary['target_missing_url_count']} |
| 처리 URL | {summary['processed_url_count']} |
| 신규 official asset | {summary['new_assets']} |
| 신규 official chunk | {summary['new_chunks']} |

## 3. 처리 상태

| status | count |
|---|---:|
{status_rows}

## 4. 신규 chunk procedure_type 분포

| procedure_type | count |
|---|---:|
{procedure_rows}

## 5. 신규 chunk language 분포

| language | count |
|---|---:|
{language_rows}

## 6. 저장 위치

```text
{summary['raw_html_dir']}
{summary['updated_files']['official_assets_db']}
{summary['updated_files']['official_document_chunks']}
{summary['updated_files']['collection_manifest']}
{summary['updated_files']['summary']}
```

## 7. 다음 작업

1. SQLite DB를 mock JSON 기준으로 재적재한다.
2. 신규 chunk를 포함해 embedding/vector index를 재생성한다.
3. chunk 수와 embedding 수가 일치하는지 검증한다.
4. 그 다음 RAGService v2 검색 품질 검증을 수행한다.
"""
    report_path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
