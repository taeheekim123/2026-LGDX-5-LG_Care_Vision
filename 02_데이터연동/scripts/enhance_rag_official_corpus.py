from __future__ import annotations

import html
import json
import re
import shutil
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from pypdf import PdfReader


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
MOCK_DIR = DATA_DIR / "mock_data"
SOURCE_DIR = DATA_DIR / "source_data" / "official_lg_india"
RAW_DIR = SOURCE_DIR / "raw"
EXT_DIR = SOURCE_DIR / "rag_corpus_extension"
PDF_DIR = EXT_DIR / "manual_pdfs"
ONLINE_DIR = EXT_DIR / "online_manual_html"
HELP_DIR = EXT_DIR / "help_library_html"
API_DIR = EXT_DIR / "api_responses"
REPORT_DIR = PROJECT_DIR / "06_산출물"

NOW = datetime.now(timezone.utc).isoformat()
LG_API_BASE = "https://www.lg.com/ncms/api/v1/support/proxy"
MODEL_LIST_API = f"{LG_API_BASE}/retrieveManualSoftwareModelList?locale=IN"
MANUAL_LIST_API = f"{LG_API_BASE}/retrieveManualSoftwareList?locale=IN"
LG_MANUAL_PAGE = "https://www.lg.com/in/support/product-support/manuals-software/"
GSCS_DOWNLOAD_PREFIX = "https://gscs-b2c.lge.com/downloadFile?fileId="

MODEL_LIMIT_BY_PRODUCT = {
    "air_conditioner": 16,
    "washing_machine": 16,
    "water_purifier": 12,
    "air_purifier": 8,
}

ADDITIONAL_HELP_LIBRARY_URLS = [
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006833-20154844425291/",
        "product_type": "air_conditioner",
        "procedure_type": "filter_cleaning",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006627-20153341509108/",
        "product_type": "air_conditioner",
        "procedure_type": "filter_cleaning",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006833-20154615810632/",
        "product_type": "air_conditioner",
        "procedure_type": "filter_cleaning",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT00022939-20153142007439/",
        "product_type": "air_conditioner",
        "procedure_type": "filter_cleaning_error",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006833-20153181971685/",
        "product_type": "air_conditioner",
        "procedure_type": "filter_cleaning",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006833-20153301479025/",
        "product_type": "air_conditioner",
        "procedure_type": "filter_cleaning",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006584-20154700752682/",
        "product_type": "air_conditioner",
        "procedure_type": "water_leak_monsoon",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006584-20153300327000LST/",
        "product_type": "air_conditioner",
        "procedure_type": "water_leak_monsoon",
        "asset_type": "help_library",
    },
]

BOILERPLATE_PATTERNS = [
    "javascript appears to be disabled",
    "we use cookies",
    "cookie settings",
    "connect with your social channels",
    "share lg technology with friends",
    "add items to your wishlist",
    "the url has been copied",
    "your email has been successfully registered",
    "otp authentication failed",
    "all rights reserved",
    "lg electronics official website",
    "privacy and cookie policy",
    "get stock alert",
    "where to buy",
    "shop menu toggle",
    "close menu",
    "installment calculator",
    "sign in to create your wishlist",
    "lg signature",
    "about lg",
    "compliance energy consumption calculator",
    "service center locator",
    "email to ceo office",
    "environmental handing fee",
]

PROCEDURE_KEYWORDS = {
    "filter_cleaning": ["filter", "clean filter", "dust", "wash the filter"],
    "tub_clean": ["tub clean", "tub cleaning", "scalgo", "drum clean"],
    "filter_replacement": ["replace filter", "filter replacement", "cartridge"],
    "limescale_care": ["scale", "limescale", "hard water", "tds", "mineral"],
    "odor_mold_care": ["odor", "smell", "mold", "dry", "auto cleaning"],
    "water_leak_monsoon": ["leak", "drain", "monsoon", "water drops", "moisture"],
    "no_cooling_self_check": ["not cooling", "low cooling", "cooling mode", "18"],
    "high_risk_electrical": ["electric", "spark", "smoke", "burning", "fire", "shock"],
    "spec_dimension": ["dimension", "weight", "indoor", "outdoor", "net dimension", "size"],
}


def ensure_dirs() -> None:
    for path in [PDF_DIR, ONLINE_DIR, HELP_DIR, API_DIR, REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def request_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")
    return json.loads(body)


def request_bytes(url: str, accept: str = "*/*") -> tuple[bytes, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": accept})
    resp = urllib.request.urlopen(req, timeout=45)
    return resp.read(), dict(resp.headers.items())


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = text.replace("\\u0026", "&")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_text(value: str) -> str:
    text = normalize_text(value)
    sentences = re.split(r"(?<=[.!?])\s+|(?<=\))\s+|(?<=:)\s+", text)
    cleaned: list[str] = []
    for sentence in sentences:
        sentence = normalize_text(sentence)
        if len(sentence) < 12:
            continue
        lower = sentence.lower()
        if any(pattern in lower for pattern in BOILERPLATE_PATTERNS):
            continue
        cleaned.append(sentence)
    return " ".join(cleaned)


def make_chunks(text: str, max_chunks: int = 18) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) >= 18]
    chunks: list[str] = []
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
    return chunks[:max_chunks]


def infer_procedure(product_type: str, text: str, fallback: str) -> str:
    lower = text.lower()
    scores = {
        procedure: sum(1 for keyword in keywords if keyword in lower)
        for procedure, keywords in PROCEDURE_KEYWORDS.items()
    }
    best, score = max(scores.items(), key=lambda item: item[1])
    if score > 0:
        return best
    if product_type == "washing_machine":
        return "tub_clean" if "clean" in lower else fallback
    if product_type == "air_conditioner":
        return "filter_cleaning" if "filter" in lower else fallback
    if product_type == "water_purifier":
        return "filter_replacement" if "filter" in lower else fallback
    if product_type == "air_purifier":
        return "filter_replacement" if "filter" in lower else fallback
    return fallback


def forbidden_actions_for(product_type: str) -> list[str]:
    base = ["electrical_repair", "pcb_repair", "internal_disassembly"]
    if product_type == "air_conditioner":
        return base + ["refrigerant_repair", "compressor_repair"]
    if product_type == "washing_machine":
        return base + ["motor_repair", "drain_pump_disassembly"]
    if product_type == "water_purifier":
        return base + ["pump_disassembly", "internal_pipe_disassembly"]
    return base


def applicability_for(model_name: str | None, source_type: str) -> str:
    if model_name and source_type in {"owners_manual_pdf", "online_manual"}:
        return "exact_model"
    return "product_type_common"


def select_models(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen = set()
    for asset in assets:
        model = asset.get("model_name")
        product = asset.get("product_type")
        if not model or product not in MODEL_LIMIT_BY_PRODUCT:
            continue
        if model.startswith(("ALL-", "SPLIT-", "FRONT-", "TOP-", "SEMI-", "WASHER-", "DRYERS", "WATER-PURIFIERS")):
            continue
        key = (product, model)
        if key in seen:
            continue
        seen.add(key)
        buckets[product].append(
            {
                "product_type": product,
                "model_name": model,
                "product_page_url": asset.get("source_url"),
                "existing_asset_id": asset.get("asset_id"),
            }
        )
    selected = []
    for product, limit in MODEL_LIMIT_BY_PRODUCT.items():
        selected.extend(buckets[product][:limit])
    return selected


def resolve_model_manuals(model_row: dict[str, Any]) -> dict[str, Any]:
    model = model_row["model_name"]
    result = {
        **model_row,
        "model_search_status": "not_requested",
        "manual_search_status": "not_requested",
        "model_data": {},
        "manual_items": [],
        "errors": [],
    }
    try:
        model_data = request_json(MODEL_LIST_API, {"tabType": "K", "keyword": model})
        result["model_search_status"] = "found" if model_data.get("csSalesCode") else "not_found"
        result["model_data"] = model_data
        (API_DIR / f"model_search_{safe_name(model)}.json").write_text(
            json.dumps(model_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        cs_sales_code = model_data.get("csSalesCode")
        if not cs_sales_code:
            return result
        manual_data = request_json(MANUAL_LIST_API, {"csSalesCode": cs_sales_code})
        result["manual_search_status"] = "found"
        (API_DIR / f"manual_list_{safe_name(model)}.json").write_text(
            json.dumps(manual_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manual_root = manual_data.get("retrieveManualSoftwareList", {}).get("manualList", {})
        result["manual_items"] = manual_root.get("manualList") or []
        result["cs_sales_code"] = cs_sales_code
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    return result


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)[:80]


def download_pdf(item: dict[str, Any], model: str) -> dict[str, Any]:
    file_id = item.get("fileName")
    original = item.get("originalFileName") or f"{model}_{file_id}.pdf"
    url = GSCS_DOWNLOAD_PREFIX + urllib.parse.quote(file_id)
    target = PDF_DIR / f"{safe_name(model)}__{safe_name(original)}"
    result = {
        "download_url": url,
        "raw_file": relative(target),
        "status": "not_downloaded",
        "content_type": "",
        "byte_size": 0,
        "pdf_header_verified": False,
        "text": "",
        "page_count": 0,
    }
    try:
        data, headers = request_bytes(url, "application/pdf,*/*")
        result["content_type"] = headers.get("Content-Type", "")
        result["byte_size"] = len(data)
        result["pdf_header_verified"] = data.startswith(b"%PDF")
        if result["pdf_header_verified"]:
            target.write_bytes(data)
            result["status"] = "downloaded"
            text, page_count = extract_pdf_text(target)
            result["text"] = text
            result["page_count"] = page_count
        else:
            error_target = target.with_suffix(target.suffix + ".html")
            error_target.write_bytes(data)
            result["raw_file"] = relative(error_target)
            result["status"] = "rejected_not_pdf"
    except Exception as exc:
        result["status"] = "download_failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def extract_pdf_text(path: Path) -> tuple[str, int]:
    reader = PdfReader(str(path))
    page_texts = []
    for index, page in enumerate(reader.pages[:24], start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = clean_text(text)
        if text:
            page_texts.append(f"[page {index}] {text}")
    return "\n".join(page_texts), len(reader.pages)


def fetch_online_manual(item: dict[str, Any], model: str) -> dict[str, Any]:
    file_url = item.get("fileUrl")
    file_id = item.get("fileName")
    result = {
        "online_url": file_url,
        "download_url": GSCS_DOWNLOAD_PREFIX + urllib.parse.quote(file_id or ""),
        "raw_file": None,
        "status": "not_fetched",
        "text": "",
    }
    if file_url and file_url.startswith("http://gscs-manual.lge.com/"):
        url = file_url.replace("http://", "https://", 1)
        result["online_url"] = url
        target = ONLINE_DIR / f"{safe_name(model)}__online_manual_main.html"
        try:
            data, _headers = request_bytes(url, "text/html,*/*")
            target.write_bytes(data)
            result["raw_file"] = relative(target)
            result["status"] = "fetched_main_html"
            result["text"] = extract_html_text(data.decode("utf-8", errors="ignore"))
        except Exception as exc:
            result["status"] = "fetch_failed"
            result["error"] = f"{type(exc).__name__}: {exc}"
    elif file_id:
        target_zip = ONLINE_DIR / f"{safe_name(model)}__online_manual.zip"
        try:
            data, _headers = request_bytes(result["download_url"], "application/zip,*/*")
            if data.startswith(b"PK"):
                target_zip.write_bytes(data)
                result["raw_file"] = relative(target_zip)
                result["status"] = "downloaded_zip"
                result["text"] = extract_online_zip_text(target_zip, model)
            else:
                result["status"] = "rejected_not_zip"
        except Exception as exc:
            result["status"] = "download_failed"
            result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def extract_online_zip_text(path: Path, model: str) -> str:
    extract_dir = ONLINE_DIR / f"{safe_name(model)}__online_manual"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    texts = []
    with zipfile.ZipFile(path) as zf:
        html_members = [m for m in zf.namelist() if m.lower().endswith((".html", ".htm"))][:12]
        for member in html_members:
            zf.extract(member, extract_dir)
            source = (extract_dir / member).read_text(encoding="utf-8", errors="ignore")
            text = extract_html_text(source)
            if text:
                texts.append(text)
    return "\n".join(texts)


def extract_html_text(source: str) -> str:
    soup = BeautifulSoup(source, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return clean_text(soup.get_text(" "))


def fetch_help_library() -> list[dict[str, Any]]:
    rows = []
    for index, entry in enumerate(ADDITIONAL_HELP_LIBRARY_URLS, start=1):
        url = entry["url"]
        target = HELP_DIR / f"help_library_extra_{index:03d}.html"
        row = {**entry, "raw_file": relative(target), "status": "not_fetched", "text": ""}
        try:
            if not url.startswith("https://www.lg.com/in/"):
                row["status"] = "rejected_non_lg_in"
                rows.append(row)
                continue
            data, _headers = request_bytes(url, "text/html,*/*")
            target.write_bytes(data)
            source = data.decode("utf-8", errors="ignore")
            row["status"] = "fetched"
            row["text"] = extract_json_ld_or_html_text(source)
            row["title"] = extract_title(source)
            if not is_help_library_text_usable(row["title"], row["text"], entry["procedure_type"]):
                row["status"] = "rejected_boilerplate_or_mismatch"
        except Exception as exc:
            row["status"] = "fetch_failed"
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    return rows


def is_help_library_text_usable(title: str, text: str, procedure_type: str) -> bool:
    normalized_title = normalize_text(title).lower()
    normalized_text = normalize_text(text).lower()
    if not normalized_text or len(normalized_text) < 120:
        return False
    if normalized_title in {"help library: | lg india", "| lg india"}:
        return False
    if has_boilerplate(normalized_text):
        return False
    expected_terms = PROCEDURE_KEYWORDS.get(procedure_type, [])
    return not expected_terms or any(term.lower() in normalized_text for term in expected_terms)


def extract_title(source: str) -> str:
    soup = BeautifulSoup(source, "html.parser")
    if soup.title and soup.title.string:
        return normalize_text(soup.title.string)
    return ""


def extract_json_ld_or_html_text(source: str) -> str:
    parts = []
    for match in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', source):
        raw = html.unescape(match.group(1)).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in walk_json(data):
            if isinstance(node, dict):
                for key in ("headline", "name", "description", "articleBody"):
                    if node.get(key):
                        parts.append(normalize_text(node[key]))
    text = clean_text(" ".join(parts))
    if len(text) >= 80:
        return text
    return extract_html_text(source)


def walk_json(value: Any) -> list[Any]:
    if isinstance(value, dict):
        rows = [value]
        for child in value.values():
            rows.extend(walk_json(child))
        return rows
    if isinstance(value, list):
        rows = []
        for child in value:
            rows.extend(walk_json(child))
        return rows
    return []


def extract_spec_chunks_from_product_pages(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for asset in assets:
        if asset.get("asset_type") != "product_page" or not asset.get("model_name"):
            continue
        raw_file = asset.get("raw_file")
        if not raw_file:
            continue
        raw_path = PROJECT_DIR / raw_file
        if not raw_path.exists():
            continue
        source = raw_path.read_text(encoding="utf-8", errors="ignore")
        text = extract_product_spec_text(source, asset.get("model_name"))
        if len(text) < 80:
            continue
        rows.append({**asset, "spec_text": text, "source_raw_file": raw_file})
    return rows


def extract_product_spec_text(source: str, model_name: str | None) -> str:
    snippets = []
    decoded = html.unescape(source)
    for term in ["modelName", "salesModelCode", "userFriendlyName", "imageAltText", "dimension", "Dimension", "Indoor", "Outdoor", "Net Weight", "Product WxHxD"]:
        for match in re.finditer(re.escape(term), decoded, re.I):
            start = max(0, match.start() - 350)
            end = min(len(decoded), match.end() + 800)
            snippets.append(decoded[start:end])
            break
    text = re.sub(r"\\[nr]", " ", " ".join(snippets))
    text = re.sub(r"[{}\\\"$]+", " ", text)
    text = clean_text(text)
    if model_name and model_name.lower() not in text.lower():
        text = f"{model_name}. {text}"
    return text


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_DIR.resolve()))


def source_is_official(row: dict[str, Any]) -> bool:
    candidates = [
        row.get("source_url", ""),
        row.get("download_url", ""),
        row.get("online_url", ""),
    ]
    return any(
        url.startswith("https://www.lg.com/in/")
        or url.startswith("https://gscs-b2c.lge.com/")
        or url.startswith("https://gscs-manual.lge.com/")
        for url in candidates
        if url
    )


def next_asset_id(index: int) -> str:
    return f"OA_LGIN_RAG_{index:04d}"


def create_asset(asset_id: str, source_type: str, product_type: str, model_name: str | None, title: str, source_url: str, procedure_type: str, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_type": source_type,
        "product_type": product_type,
        "model_name": model_name,
        "title": title,
        "source_url": source_url,
        "source_date": NOW[:10],
        "applicability_scope": applicability_for(model_name, source_type),
        "matched_model_names": [model_name] if model_name else [],
        "matched_aliases": [],
        "matched_series": None,
        "available_procedures": [procedure_type],
        "forbidden_actions": forbidden_actions_for(product_type),
        "verification_status": "official_source_verified",
        "last_checked_at": NOW,
        **({"raw_file": raw.get("raw_file")} if raw.get("raw_file") else {}),
        "source_origin": raw.get("source_origin"),
        "download_url": raw.get("download_url"),
        "online_url": raw.get("online_url"),
    }


def add_chunks(chunks: list[dict[str, Any]], asset: dict[str, Any], text: str, source_section: str, start_index: int) -> int:
    chunk_texts = make_chunks(text)
    added = 0
    for idx, chunk_text in enumerate(chunk_texts, start=1):
        if len(chunk_text.strip()) < 80 or has_boilerplate(chunk_text):
            continue
        procedure_type = infer_procedure(asset["product_type"], chunk_text, asset["available_procedures"][0])
        chunks.append(
            {
                "chunk_id": f"CHUNK_LGIN_RAG_{start_index:04d}_{idx:03d}",
                "asset_id": asset["asset_id"],
                "product_type": asset["product_type"],
                "model_name": asset.get("model_name"),
                "series": asset.get("matched_series"),
                "procedure_type": procedure_type,
                "language": "en",
                "chunk_title": asset["title"],
                "chunk_text": chunk_text,
                "source_url": asset["source_url"],
                "source_section": source_section,
                "source_type": asset["asset_type"],
                "source_raw_file": asset.get("raw_file"),
                "download_url": asset.get("download_url"),
                "online_url": asset.get("online_url"),
                "applicability_scope": asset["applicability_scope"],
                "forbidden_actions": asset.get("forbidden_actions", []),
                "safety_tags": [],
                "embedding_status": "not_embedded",
                "verification_status": "official_source_verified",
                "last_checked_at": NOW,
                "created_at": NOW,
                "extraction_quality": {
                    "boilerplate_detected": has_boilerplate(chunk_text),
                    "char_count": len(chunk_text),
                },
            }
        )
        added += 1
    return added


def has_boilerplate(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in BOILERPLATE_PATTERNS)


def main() -> None:
    ensure_dirs()
    existing_assets = read_json(MOCK_DIR / "official_assets_db.json")
    existing_chunks = read_json(MOCK_DIR / "official_document_chunks.json")
    selected_models = select_models(existing_assets)
    model_results = [resolve_model_manuals(row) for row in selected_models]
    help_rows = fetch_help_library()
    spec_rows = extract_spec_chunks_from_product_pages(existing_assets)

    new_assets: list[dict[str, Any]] = []
    new_chunks: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    asset_index = 1
    chunk_asset_index = 1

    for result in model_results:
        product_type = result["product_type"]
        model = result["model_name"]
        for item in result.get("manual_items", []):
            manual_type = item.get("manualType") or ""
            file_type = item.get("fileType") or ""
            if file_type == "PDF" and manual_type == "Owner’s Manual":
                pdf = download_pdf(item, model)
                source_url = LG_MANUAL_PAGE
                row = {
                    "source_url": source_url,
                    "download_url": pdf.get("download_url"),
                    "source_origin": "LG India manual API + gscs-b2c official download host",
                    **pdf,
                }
                if pdf["status"] == "downloaded" and pdf["pdf_header_verified"] and len(pdf["text"]) >= 120 and source_is_official(row):
                    asset = create_asset(
                        next_asset_id(asset_index),
                        "owners_manual_pdf",
                        product_type,
                        model,
                        f"{model} Owner's Manual",
                        source_url,
                        infer_procedure(product_type, pdf["text"], "owner_manual"),
                        row,
                    )
                    new_assets.append(asset)
                    add_chunks(new_chunks, asset, pdf["text"], "pdf_text", chunk_asset_index)
                    manifest_rows.append({**row, "asset_id": asset["asset_id"], "model_name": model, "product_type": product_type, "manual_item": item})
                    asset_index += 1
                    chunk_asset_index += 1
                else:
                    manifest_rows.append({**row, "asset_id": None, "model_name": model, "product_type": product_type, "manual_item": item})
            elif file_type in {"HTML2", "HTML"} or manual_type == "Online Manual":
                online = fetch_online_manual(item, model)
                source_url = online.get("online_url") or LG_MANUAL_PAGE
                row = {
                    "source_url": source_url,
                    "source_origin": "LG India manual API + gscs-manual official host",
                    **online,
                }
                if online["status"] in {"fetched_main_html", "downloaded_zip"} and len(online["text"]) >= 120 and source_is_official(row):
                    asset = create_asset(
                        next_asset_id(asset_index),
                        "online_manual",
                        product_type,
                        model,
                        f"{model} Online Manual",
                        source_url,
                        infer_procedure(product_type, online["text"], "online_manual"),
                        row,
                    )
                    new_assets.append(asset)
                    add_chunks(new_chunks, asset, online["text"], "online_manual_html", chunk_asset_index)
                    manifest_rows.append({**row, "asset_id": asset["asset_id"], "model_name": model, "product_type": product_type, "manual_item": item})
                    asset_index += 1
                    chunk_asset_index += 1
                else:
                    manifest_rows.append({**row, "asset_id": None, "model_name": model, "product_type": product_type, "manual_item": item})

    for help_row in help_rows:
        if help_row["status"] == "fetched" and len(help_row["text"]) >= 120 and source_is_official({"source_url": help_row["url"]}):
            asset = create_asset(
                next_asset_id(asset_index),
                "help_library",
                help_row["product_type"],
                None,
                help_row.get("title") or "LG Help Library",
                help_row["url"],
                help_row["procedure_type"],
                {
                    "raw_file": help_row.get("raw_file"),
                    "source_origin": "LG India help-library official page",
                },
            )
            new_assets.append(asset)
            add_chunks(new_chunks, asset, help_row["text"], "json_ld_or_html", chunk_asset_index)
            manifest_rows.append({**help_row, "asset_id": asset["asset_id"], "source_url": help_row["url"]})
            asset_index += 1
            chunk_asset_index += 1
        else:
            manifest_rows.append({**help_row, "asset_id": None, "source_url": help_row["url"]})

    for spec_row in spec_rows[:50]:
        product_type = spec_row["product_type"]
        model = spec_row.get("model_name")
        asset = create_asset(
            next_asset_id(asset_index),
            "product_spec_dimension",
            product_type,
            model,
            f"{model} Product Page Spec/Dimension Evidence",
            spec_row["source_url"],
            "spec_dimension",
            {
                "raw_file": spec_row.get("source_raw_file"),
                "source_origin": "LG India product page structured text",
            },
        )
        new_assets.append(asset)
        add_chunks(new_chunks, asset, spec_row["spec_text"], "product_page_spec_text", chunk_asset_index)
        manifest_rows.append({"asset_id": asset["asset_id"], "model_name": model, "product_type": product_type, "source_url": spec_row["source_url"], "raw_file": spec_row.get("source_raw_file"), "status": "spec_extracted"})
        asset_index += 1
        chunk_asset_index += 1

    existing_asset_ids = {asset["asset_id"] for asset in existing_assets}
    combined_assets = existing_assets + [asset for asset in new_assets if asset["asset_id"] not in existing_asset_ids]
    existing_chunk_ids = {chunk["chunk_id"] for chunk in existing_chunks}
    combined_chunks = existing_chunks + [chunk for chunk in new_chunks if chunk["chunk_id"] not in existing_chunk_ids]

    write_json(MOCK_DIR / "official_assets_db.json", combined_assets)
    write_json(MOCK_DIR / "official_document_chunks.json", combined_chunks)
    write_json(EXT_DIR / "rag_corpus_extension_manifest.json", manifest_rows)

    summary = build_summary(existing_assets, existing_chunks, new_assets, new_chunks, manifest_rows, model_results)
    write_json(EXT_DIR / "rag_corpus_extension_summary.json", summary)
    report_path = REPORT_DIR / "RAG데이터구축고도화_검증리포트_2026-06-03.md"
    report_path.write_text(render_report(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def build_summary(existing_assets: list[dict[str, Any]], existing_chunks: list[dict[str, Any]], new_assets: list[dict[str, Any]], new_chunks: list[dict[str, Any]], manifest_rows: list[dict[str, Any]], model_results: list[dict[str, Any]]) -> dict[str, Any]:
    combined_asset_count = len(existing_assets) + len(new_assets)
    combined_chunk_count = len(existing_chunks) + len(new_chunks)
    boilerplate = [chunk["chunk_id"] for chunk in new_chunks if has_boilerplate(chunk["chunk_text"])]
    official_rejected = [
        row
        for row in manifest_rows
        if row.get("asset_id") is None
        and row.get("status") not in {"not_fetched"}
    ]
    return {
        "created_at": NOW,
        "existing_assets": len(existing_assets),
        "existing_chunks": len(existing_chunks),
        "new_assets": len(new_assets),
        "new_chunks": len(new_chunks),
        "combined_assets": combined_asset_count,
        "combined_chunks": combined_chunk_count,
        "new_assets_by_type": dict(Counter(asset["asset_type"] for asset in new_assets)),
        "new_chunks_by_source_type": dict(Counter(chunk.get("source_type") for chunk in new_chunks)),
        "new_chunks_by_product_type": dict(Counter(chunk.get("product_type") for chunk in new_chunks)),
        "new_chunks_by_procedure_type": dict(Counter(chunk.get("procedure_type") for chunk in new_chunks)),
        "manual_model_search": {
            "requested_models": len(model_results),
            "found_models": sum(1 for row in model_results if row.get("model_search_status") == "found"),
            "models_with_manual_items": sum(1 for row in model_results if row.get("manual_items")),
        },
        "official_source_policy": [
            "https://www.lg.com/in/",
            "https://gscs-b2c.lge.com/ official download host returned by LG India manual API",
            "https://gscs-manual.lge.com/ official online manual host returned by LG India manual API",
        ],
        "boilerplate_chunk_count": len(boilerplate),
        "boilerplate_chunk_ids_sample": boilerplate[:20],
        "rejected_or_unusable_source_count": len(official_rejected),
        "rejected_or_unusable_source_sample": official_rejected[:20],
        "output_files": {
            "official_assets_db": relative(MOCK_DIR / "official_assets_db.json"),
            "official_document_chunks": relative(MOCK_DIR / "official_document_chunks.json"),
            "extension_manifest": relative(EXT_DIR / "rag_corpus_extension_manifest.json"),
            "extension_summary": relative(EXT_DIR / "rag_corpus_extension_summary.json"),
            "report": relative(REPORT_DIR / "RAG데이터구축고도화_검증리포트_2026-06-03.md"),
        },
    }


def render_report(summary: dict[str, Any]) -> str:
    def table(counter: dict[str, int]) -> str:
        if not counter:
            return "| 항목 | 건수 |\n|---|---:|\n| 없음 | 0 |\n"
        lines = ["| 항목 | 건수 |", "|---|---:|"]
        for key, value in sorted(counter.items()):
            lines.append(f"| `{key}` | {value} |")
        return "\n".join(lines) + "\n"

    return f"""# RAG 데이터 구축 고도화 검증 리포트

작성일: 2026-06-03

## 1. 결론

이번 작업은 RAGService 고도화가 아니라 RAG 데이터 구축 고도화다.

기존 `official_document_chunks` {summary['existing_chunks']}건에 LG India 공식 매뉴얼 PDF, Online Manual, 추가 Help Library, 제품 페이지 spec/dimension 근거를 확장했다.

## 2. 수집 정책

허용한 공식 출처:

```text
https://www.lg.com/in/
https://gscs-b2c.lge.com/        LG India manual API가 반환한 공식 다운로드 호스트
https://gscs-manual.lge.com/     LG India manual API가 반환한 공식 Online Manual 호스트
```

비공식 리뷰, 블로그, 커뮤니티, LG USA/AU 등 India 외 국가 URL은 이번 RAG DB에 넣지 않았다.

## 3. 수량 검증

| 항목 | 건수 |
|---|---:|
| 기존 official_assets | {summary['existing_assets']} |
| 기존 official_document_chunks | {summary['existing_chunks']} |
| 신규 official_assets | {summary['new_assets']} |
| 신규 official_document_chunks | {summary['new_chunks']} |
| 합산 official_assets | {summary['combined_assets']} |
| 합산 official_document_chunks | {summary['combined_chunks']} |
| boilerplate 검출 chunk | {summary['boilerplate_chunk_count']} |

## 4. 신규 asset 유형

{table(summary['new_assets_by_type'])}

## 5. 신규 chunk source_type

{table(summary['new_chunks_by_source_type'])}

## 6. 신규 chunk 제품군

{table(summary['new_chunks_by_product_type'])}

## 7. 신규 chunk procedure_type

{table(summary['new_chunks_by_procedure_type'])}

## 8. 매뉴얼 API 검증

| 항목 | 건수 |
|---|---:|
| 모델 검색 요청 | {summary['manual_model_search']['requested_models']} |
| LG 공식 API에서 모델 확인 | {summary['manual_model_search']['found_models']} |
| manual item 보유 모델 | {summary['manual_model_search']['models_with_manual_items']} |

## 9. 산출 파일

```text
{summary['output_files']['official_assets_db']}
{summary['output_files']['official_document_chunks']}
{summary['output_files']['extension_manifest']}
{summary['output_files']['extension_summary']}
{summary['output_files']['report']}
```

## 10. 다음 단계

```text
1. SQLite 재시드
2. DB count 검증
3. RAGService 검색 검증
4. Embedding/Vector DB 구축 단계로 이동
```
"""


if __name__ == "__main__":
    main()
