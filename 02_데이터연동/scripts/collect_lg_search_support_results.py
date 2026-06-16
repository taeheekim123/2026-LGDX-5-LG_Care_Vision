from __future__ import annotations

import html
import json
import re
import urllib.parse
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
EXT_DIR = DATA_DIR / "source_data" / "official_lg_india" / "rag_corpus_extension"
SEARCH_DIR = EXT_DIR / "search_support_html"
REPORT_DIR = PROJECT_DIR / "06_산출물"

SEARCH_QUERY = "AS-Q24ENXE"
SEARCH_PAGE_URL = f"https://www.lg.com/in/search/?search={urllib.parse.quote(SEARCH_QUERY)}&tab=support"
COVEO_TOKEN_URL = "https://www.lg.com/ncms/api/v1/coveo/token"
COVEO_SEARCH_URL = "https://platform-eu.cloud.coveo.com/rest/search/v2?organizationId=lgcorporationproduction0fxcu0qx"
NOW = datetime.now(timezone.utc).isoformat()

BOILERPLATE_PATTERNS = [
    "javascript appears to be disabled",
    "we use cookies",
    "cookie settings",
    "lg signature",
    "about lg",
    "service center locator",
    "email to ceo office",
    "environmental handing fee",
    "contact us chatbot whatsapp",
    "privacy portal",
    "all rights reserved",
]

PROCEDURE_KEYWORDS = {
    "high_risk_refrigerant": ["gas", "refrigerant", "leak", "service technician"],
    "filter_cleaning": ["filter", "clean", "dust"],
    "water_leak_monsoon": ["water", "leak", "drip", "humidity", "dew"],
    "no_cooling_self_check": ["cooling", "cold", "temperature", "outdoor unit"],
    "noise_self_check": ["noise", "sound", "hissing", "swishing", "gulping"],
    "remote_operation": ["remote", "fan speed", "operate"],
    "high_risk_electrical": ["electric", "shock", "fire", "burning", "spark"],
}


def request_bytes(url: str, headers: dict[str, str] | None = None, data: bytes | None = None) -> tuple[bytes, dict[str, str]]:
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0 CareShotOfficialCorpusBot/1.0",
            "Accept": "application/json,text/html,*/*",
            "Referer": SEARCH_PAGE_URL,
            **(headers or {}),
        },
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read(), dict(response.headers)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(null|none)\s+", "", text, flags=re.I).strip()
    text = re.sub(r"\s*LG IN LG IN Home Support Product Support Troubleshoot\s*$", "", text).strip()
    return text


def clean_text(value: str) -> str:
    soup = BeautifulSoup(value, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return normalize_text(soup.get_text(" "))


def extract_json_ld_or_html_text(source: str) -> tuple[str, str]:
    title = ""
    parts: list[str] = []
    soup = BeautifulSoup(source, "html.parser")
    if soup.title and soup.title.string:
        title = normalize_text(soup.title.string)
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(html.unescape(tag.get_text()).strip())
        except json.JSONDecodeError:
            continue
        for node in walk_json(data):
            if isinstance(node, dict):
                for key in ("headline", "name", "description", "articleBody"):
                    value = node.get(key)
                    if value:
                        parts.append(normalize_text(value))
    text = normalize_text(" ".join(parts))
    if len(text) < 100:
        text = clean_text(source)
    return title, text


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


def make_chunks(text: str, max_chars: int = 1100) -> list[str]:
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
    return [chunk for chunk in chunks if len(chunk) >= 80 and not has_boilerplate(chunk)]


def get_coveo_token() -> str:
    data, _headers = request_bytes(COVEO_TOKEN_URL)
    payload = json.loads(data.decode("utf-8"))
    return payload["token"]


def search_support_results(token: str) -> dict[str, Any]:
    body = {
        "q": SEARCH_QUERY,
        "searchHub": "IN-B2C-Search",
        "aq": '@commonsource=="Support"',
        "numberOfResults": 30,
        "firstResult": 0,
        "fieldsToInclude": [
            "title",
            "clickUri",
            "uri",
            "printableUri",
            "excerpt",
            "commonsource",
            "ec_super_category_id",
            "ec_doc_id",
            "source",
        ],
    }
    data, _headers = request_bytes(
        COVEO_SEARCH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        data=json.dumps(body).encode("utf-8"),
    )
    return json.loads(data.decode("utf-8"))


def support_url_from_result(result: dict[str, Any]) -> str | None:
    raw = result.get("raw") or {}
    uri = str(result.get("uri") or raw.get("uri") or raw.get("sysuri") or "")
    match = re.search(r"support://(\d+)\.in\.(CT\d+)", uri, re.I)
    if not match:
        return None
    doc_id, super_cat_id = match.group(1), match.group(2)
    return f"https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-{super_cat_id}-{doc_id}/"


def choose_listing_title(coveo_title: str, page_title: str) -> str:
    generic_titles = {
        "lg help library - support & help | lg india",
        "lg help library - support & help | lg in",
        "support & help | lg india",
    }
    if page_title.strip().lower() in generic_titles and coveo_title:
        return coveo_title
    return page_title or coveo_title


def next_numeric_id(existing: list[dict[str, Any]], prefix: str) -> int:
    max_id = 0
    pattern = re.compile(re.escape(prefix) + r"(\d+)")
    for row in existing:
        match = pattern.match(str(row.get("asset_id") or row.get("chunk_id") or ""))
        if match:
            max_id = max(max_id, int(match.group(1)))
    return max_id + 1


def official_asset_exists(assets: list[dict[str, Any]], source_url: str) -> bool:
    return any(asset.get("source_url") == source_url for asset in assets)


def chunk_exists(chunks: list[dict[str, Any]], source_url: str, title: str) -> bool:
    return any(chunk.get("source_url") == source_url and chunk.get("chunk_title") == title for chunk in chunks)


def main() -> None:
    SEARCH_DIR.mkdir(parents=True, exist_ok=True)
    search_html, search_headers = request_bytes(SEARCH_PAGE_URL, headers={"Accept": "text/html,*/*"})
    search_page_file = SEARCH_DIR / "AS-Q24ENXE_support_search.html"
    search_page_file.write_bytes(search_html)

    token = get_coveo_token()
    coveo_results = search_support_results(token)
    write_json(SEARCH_DIR / "AS-Q24ENXE_coveo_support_filtered_raw.json", coveo_results)

    assets_path = MOCK_DIR / "official_assets_db.json"
    chunks_path = MOCK_DIR / "official_document_chunks.json"
    assets = read_json(assets_path)
    chunks = read_json(chunks_path)

    asset_index = next_numeric_id(assets, "OA_LGIN_SEARCH_")
    chunk_index = next_numeric_id(chunks, "CHUNK_LGIN_SEARCH_")
    new_assets: list[dict[str, Any]] = []
    new_chunks: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []

    results = coveo_results.get("results") or []
    for rank, result in enumerate(results, start=1):
        raw = result.get("raw") or {}
        commonsource = raw.get("commonsource")
        source = raw.get("source") or raw.get("syssource")
        source_url = support_url_from_result(result)
        title = normalize_text(result.get("title") or raw.get("title"))
        excerpt = normalize_text(result.get("excerpt"))
        row = {
            "rank": rank,
            "title": title,
            "excerpt": excerpt,
            "source_url": source_url,
            "uri": result.get("uri"),
            "commonsource": commonsource,
            "source": source,
            "status": "candidate",
        }
        if commonsource != "Support" or not source_url or not source_url.startswith("https://www.lg.com/in/"):
            row["status"] = "rejected_non_support_or_non_official"
            manifest.append(row)
            continue
        if official_asset_exists(assets + new_assets, source_url):
            row["status"] = "skipped_duplicate_source_url"
            manifest.append(row)
            continue

        raw_file = SEARCH_DIR / f"AS-Q24ENXE_support_result_{rank:03d}.html"
        try:
            page_bytes, headers = request_bytes(source_url, headers={"Accept": "text/html,*/*"})
            raw_file.write_bytes(page_bytes)
            page_source = page_bytes.decode("utf-8", errors="ignore")
            page_title, text = extract_json_ld_or_html_text(page_source)
            page_title = choose_listing_title(title, page_title)
            if len(text) < 120 or has_boilerplate(text):
                row.update({"status": "rejected_boilerplate_or_short_text", "raw_file": relative(raw_file), "title": page_title})
                manifest.append(row)
                continue
            procedure_type = infer_procedure(page_title, excerpt, text)
            asset_id = f"OA_LGIN_SEARCH_{asset_index:04d}"
            asset = {
                "asset_id": asset_id,
                "asset_type": "search_support_result",
                "product_type": "air_conditioner",
                "model_name": SEARCH_QUERY,
                "title": page_title,
                "source_url": source_url,
                "raw_file": relative(raw_file),
                "source_origin": "LG India search support tab via Coveo + Help Library official page",
                "source_date": NOW[:10],
                "applicability_scope": "model_search_support_result",
                "matched_model_names": [SEARCH_QUERY],
                "matched_aliases": [],
                "matched_series": None,
                "available_procedures": [procedure_type],
                "forbidden_actions": [
                    "electrical_repair",
                    "pcb_repair",
                    "internal_disassembly",
                    "refrigerant_repair",
                    "compressor_repair",
                ],
                "verification_status": "official_source_verified",
                "last_checked_at": NOW,
            }
            if chunk_exists(chunks + new_chunks, source_url, page_title):
                row["status"] = "skipped_duplicate_chunk"
                manifest.append(row)
                continue
            made_chunks = make_chunks(text)
            if not made_chunks:
                row.update({"status": "rejected_no_usable_chunks", "raw_file": relative(raw_file), "title": page_title})
                manifest.append(row)
                continue
            for idx, chunk_text in enumerate(made_chunks, start=1):
                new_chunks.append(
                    {
                        "chunk_id": f"CHUNK_LGIN_SEARCH_{chunk_index:04d}_{idx:03d}",
                        "asset_id": asset_id,
                        "product_type": "air_conditioner",
                        "model_name": SEARCH_QUERY,
                        "series": None,
                        "procedure_type": infer_procedure(page_title, excerpt, chunk_text),
                        "language": "en",
                        "chunk_title": page_title,
                        "chunk_text": chunk_text,
                        "source_url": source_url,
                        "source_section": "search_support_json_ld_or_html",
                        "source_type": "search_support_result",
                        "source_raw_file": relative(raw_file),
                        "download_url": None,
                        "online_url": None,
                        "applicability_scope": "model_search_support_result",
                        "forbidden_actions": asset["forbidden_actions"],
                        "safety_tags": [],
                        "embedding_status": "not_embedded",
                        "verification_status": "official_source_verified",
                        "created_at": NOW,
                        "last_checked_at": NOW,
                        "extraction_quality": {
                            "boilerplate_detected": False,
                            "char_count": len(chunk_text),
                        },
                    }
                )
            new_assets.append(asset)
            row.update(
                {
                    "status": "added",
                    "asset_id": asset_id,
                    "raw_file": relative(raw_file),
                    "chunk_count": len(made_chunks),
                    "procedure_type": procedure_type,
                    "title": page_title,
                }
            )
            manifest.append(row)
            asset_index += 1
            chunk_index += 1
        except Exception as exc:
            row["status"] = f"fetch_failed:{type(exc).__name__}:{exc}"
            manifest.append(row)

    if new_assets or new_chunks:
        write_json(assets_path, assets + new_assets)
        write_json(chunks_path, chunks + new_chunks)

    summary = {
        "created_at": NOW,
        "search_page_url": SEARCH_PAGE_URL,
        "search_page_raw_file": relative(search_page_file),
        "search_page_status_code_inferred": "downloaded",
        "search_page_bytes": len(search_html),
        "coveo_total_count": coveo_results.get("totalCount"),
        "coveo_result_count": len(results),
        "new_assets": len(new_assets),
        "new_chunks": len(new_chunks),
        "manifest_count": len(manifest),
        "manifest_status_counts": dict(Counter(row["status"] for row in manifest)),
        "new_chunks_by_procedure_type": dict(Counter(chunk["procedure_type"] for chunk in new_chunks)),
        "official_source_policy": [
            "https://www.lg.com/in/search/?search=AS-Q24ENXE&tab=support",
            "https://platform-eu.cloud.coveo.com/rest/search/v2 organization lgcorporationproduction0fxcu0qx via LG coveo token",
            "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-{super_cat_id}-{doc_id}/",
        ],
        "output_files": {
            "search_page_raw": relative(search_page_file),
            "coveo_raw": relative(SEARCH_DIR / "AS-Q24ENXE_coveo_support_filtered_raw.json"),
            "manifest": relative(SEARCH_DIR / "AS-Q24ENXE_search_support_manifest.json"),
            "summary": relative(SEARCH_DIR / "AS-Q24ENXE_search_support_summary.json"),
        },
    }
    write_json(SEARCH_DIR / "AS-Q24ENXE_search_support_manifest.json", manifest)
    write_json(SEARCH_DIR / "AS-Q24ENXE_search_support_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_DIR.resolve()))


if __name__ == "__main__":
    main()
