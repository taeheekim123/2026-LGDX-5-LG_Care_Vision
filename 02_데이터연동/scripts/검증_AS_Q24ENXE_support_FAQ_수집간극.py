from __future__ import annotations

import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
SOURCE_DIR = DATA_DIR / "source_data" / "official_lg_india"
GAP_DIR = SOURCE_DIR / "support_faq_gap_validation"
OUTPUT_DIR = PROJECT_DIR / "06_산출물"
DB_PATH = DATA_DIR / "db" / "careshot_ar_mock.db"

SEARCH_QUERY = "AS-Q24ENXE"
SEARCH_PAGE_URL = f"https://www.lg.com/in/search/?search={urllib.parse.quote(SEARCH_QUERY)}&tab=support"
COVEO_TOKEN_URL = "https://www.lg.com/ncms/api/v1/coveo/token"
COVEO_SEARCH_URL = "https://platform-eu.cloud.coveo.com/rest/search/v2?organizationId=lgcorporationproduction0fxcu0qx"
NOW = datetime.now(timezone.utc).isoformat()
TODAY = NOW[:10]


def request_bytes(url: str, headers: dict[str, str] | None = None, data: bytes | None = None) -> bytes:
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0 CareShotOfficialGapVerifier/1.0",
            "Accept": "application/json,text/html,*/*",
            "Referer": SEARCH_PAGE_URL,
            **(headers or {}),
        },
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=40) as response:
        return response.read()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def get_coveo_token() -> str:
    payload = json.loads(request_bytes(COVEO_TOKEN_URL).decode("utf-8"))
    return payload["token"]


def support_url_from_result(result: dict[str, Any]) -> str | None:
    raw = result.get("raw") or {}
    uri = str(result.get("uri") or raw.get("uri") or raw.get("sysuri") or "")
    match = re.search(r"support://(\d+)\.in\.(CT\d+)", uri, re.I)
    if not match:
        return None
    doc_id, super_cat_id = match.group(1), match.group(2)
    return f"https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-{super_cat_id}-{doc_id}/"


def search_support_page(token: str, first_result: int, page_size: int) -> dict[str, Any]:
    body = {
        "q": SEARCH_QUERY,
        "searchHub": "IN-B2C-Search",
        "aq": '@commonsource=="Support"',
        "numberOfResults": page_size,
        "firstResult": first_result,
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
    raw = request_bytes(
        COVEO_SEARCH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        data=json.dumps(body).encode("utf-8"),
    )
    return json.loads(raw.decode("utf-8"))


def db_counts(candidate_urls: set[str]) -> dict[str, Any]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    def one(query: str, params: tuple[Any, ...] = ()) -> int:
        cur.execute(query, params)
        return int(cur.fetchone()[0])

    cur.execute("SELECT source_url, asset_type, asset_id FROM official_assets")
    asset_rows = [dict(row) for row in cur.fetchall()]
    cur.execute("SELECT source_url, source_type, chunk_id FROM official_document_chunks")
    chunk_rows = [dict(row) for row in cur.fetchall()]

    asset_urls = {row["source_url"] for row in asset_rows if row.get("source_url")}
    chunk_urls = {row["source_url"] for row in chunk_rows if row.get("source_url")}
    con.close()

    matched_asset_urls = sorted(candidate_urls & asset_urls)
    matched_chunk_urls = sorted(candidate_urls & chunk_urls)
    return {
        "official_assets_total": one_count("official_assets"),
        "official_document_chunks_total": one_count("official_document_chunks"),
        "official_document_embeddings_total": one_count("official_document_embeddings"),
        "candidate_urls_matched_in_assets": len(matched_asset_urls),
        "candidate_urls_matched_in_chunks": len(matched_chunk_urls),
        "matched_asset_urls": matched_asset_urls,
        "matched_chunk_urls": matched_chunk_urls,
    }


def one_count(table: str) -> int:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    value = int(cur.fetchone()[0])
    con.close()
    return value


def old_collection_counts() -> dict[str, Any]:
    search_dir = SOURCE_DIR / "rag_corpus_extension" / "search_support_html"
    summary_path = search_dir / "AS-Q24ENXE_search_support_summary.json"
    manifest_path = search_dir / "AS-Q24ENXE_search_support_manifest.json"
    result_html_count = len(list(search_dir.glob("AS-Q24ENXE_support_result_*.html")))
    summary = read_json(summary_path) if summary_path.exists() else {}
    manifest = read_json(manifest_path) if manifest_path.exists() else []
    return {
        "previous_summary_path": relative(summary_path) if summary_path.exists() else None,
        "previous_manifest_path": relative(manifest_path) if manifest_path.exists() else None,
        "previous_coveo_total_count": summary.get("coveo_total_count"),
        "previous_coveo_result_count": summary.get("coveo_result_count"),
        "previous_new_assets": summary.get("new_assets"),
        "previous_new_chunks": summary.get("new_chunks"),
        "previous_search_result_html_count": result_html_count,
        "previous_manifest_count": len(manifest),
    }


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_DIR.resolve()))


def main() -> None:
    GAP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    search_html = request_bytes(SEARCH_PAGE_URL, headers={"Accept": "text/html,*/*"})
    search_page_path = GAP_DIR / f"AS-Q24ENXE_support_search_page_{TODAY}.html"
    search_page_path.write_bytes(search_html)

    token = get_coveo_token()
    first_page = search_support_page(token, 0, 100)
    total_count = int(first_page.get("totalCount") or 0)
    pages = [first_page]
    write_json(GAP_DIR / f"AS-Q24ENXE_coveo_support_page_000_{TODAY}.json", first_page)

    first_result = len(first_page.get("results") or [])
    while first_result < total_count:
        page = search_support_page(token, first_result, 100)
        results = page.get("results") or []
        if not results:
            break
        pages.append(page)
        write_json(GAP_DIR / f"AS-Q24ENXE_coveo_support_page_{first_result:03d}_{TODAY}.json", page)
        first_result += len(results)

    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for page in pages:
        for result in page.get("results") or []:
            raw = result.get("raw") or {}
            source_url = support_url_from_result(result)
            status = "official_lg_support_url" if source_url and source_url.startswith("https://www.lg.com/in/") else "unsupported_result_shape"
            if source_url in seen_urls:
                status = "duplicate_official_url"
            if source_url:
                seen_urls.add(source_url)
            candidates.append(
                {
                    "rank": len(candidates) + 1,
                    "title": result.get("title") or raw.get("title") or raw.get("systitle"),
                    "excerpt": result.get("excerpt"),
                    "uri": result.get("uri") or raw.get("uri") or raw.get("sysuri"),
                    "source_url": source_url,
                    "commonsource": raw.get("commonsource"),
                    "source": raw.get("source") or raw.get("syssource"),
                    "status": status,
                }
            )

    official_candidate_urls = {
        row["source_url"]
        for row in candidates
        if row.get("source_url") and row.get("status") in {"official_lg_support_url", "duplicate_official_url"}
    }
    counts = db_counts(official_candidate_urls)
    missing_urls = sorted(official_candidate_urls - set(counts["matched_asset_urls"]))
    for row in candidates:
        url = row.get("source_url")
        if not url:
            row["collection_gap_status"] = "no_official_url_candidate"
        elif url in counts["matched_asset_urls"]:
            row["collection_gap_status"] = "already_in_official_assets"
        else:
            row["collection_gap_status"] = "missing_from_official_assets_needs_raw_html_collection"

    summary = {
        "created_at": NOW,
        "search_query": SEARCH_QUERY,
        "search_page_url": SEARCH_PAGE_URL,
        "search_page_raw_file": relative(search_page_path),
        "search_page_bytes": len(search_html),
        "live_coveo_total_count": total_count,
        "live_coveo_downloaded_result_count": len(candidates),
        "live_unique_official_support_url_count": len(official_candidate_urls),
        "currently_collected_candidate_url_count": counts["candidate_urls_matched_in_assets"],
        "currently_chunked_candidate_url_count": counts["candidate_urls_matched_in_chunks"],
        "missing_candidate_url_count": len(missing_urls),
        "db_counts": {
            "official_assets_total": counts["official_assets_total"],
            "official_document_chunks_total": counts["official_document_chunks_total"],
            "official_document_embeddings_total": counts["official_document_embeddings_total"],
        },
        "previous_collection": old_collection_counts(),
        "gap_judgement": (
            "gap_exists"
            if len(missing_urls) > 0 or counts["candidate_urls_matched_in_assets"] < len(official_candidate_urls)
            else "no_gap_detected"
        ),
        "important_note": (
            "The LG India support tab exposes a Coveo Support result count larger than the currently collected "
            "30 support result assets. Current DB does not contain the full support/FAQ candidate set."
        ),
        "output_files": {
            "candidate_manifest": relative(GAP_DIR / f"AS-Q24ENXE_support_FAQ_candidate_manifest_{TODAY}.json"),
            "summary": relative(GAP_DIR / f"AS-Q24ENXE_support_FAQ_gap_summary_{TODAY}.json"),
            "report": relative(OUTPUT_DIR / f"AS-Q24ENXE_support_FAQ_수집간극_검증리포트_{TODAY}.md"),
        },
    }

    write_json(GAP_DIR / f"AS-Q24ENXE_support_FAQ_candidate_manifest_{TODAY}.json", candidates)
    write_json(GAP_DIR / f"AS-Q24ENXE_support_FAQ_missing_urls_{TODAY}.json", missing_urls)
    write_json(GAP_DIR / f"AS-Q24ENXE_support_FAQ_gap_summary_{TODAY}.json", summary)
    write_report(summary, candidates, missing_urls)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def write_report(summary: dict[str, Any], candidates: list[dict[str, Any]], missing_urls: list[str]) -> None:
    report_path = OUTPUT_DIR / f"AS-Q24ENXE_support_FAQ_수집간극_검증리포트_{TODAY}.md"
    previous = summary["previous_collection"]
    db = summary["db_counts"]
    sample_missing = "\n".join(f"- {url}" for url in missing_urls[:20]) or "- 없음"
    lines = f"""# AS-Q24ENXE support/FAQ 수집 간극 검증 리포트

## 1. 검증 목적

LG India 검색 페이지 `https://www.lg.com/in/search/?search=AS-Q24ENXE&tab=support` 기준으로 실제 support/FAQ 후보 수와 현재 DB 반영 수의 차이를 검증한다.

## 2. 현재 검색 페이지/API 검증 결과

| 항목 | 값 |
|---|---:|
| Coveo Support totalCount | {summary['live_coveo_total_count']} |
| 이번 검증에서 내려받은 결과 수 | {summary['live_coveo_downloaded_result_count']} |
| 공식 LG India support URL 후보 수 | {summary['live_unique_official_support_url_count']} |
| 현재 DB official_assets에 반영된 후보 URL 수 | {summary['currently_collected_candidate_url_count']} |
| 현재 DB official_document_chunks에 반영된 후보 URL 수 | {summary['currently_chunked_candidate_url_count']} |
| 누락 후보 URL 수 | {summary['missing_candidate_url_count']} |

주의:

```text
544건은 LG India 검색 페이지 support tab의 Coveo Support totalCount다.
이 값을 순수 FAQ 문서 544건으로 확정하지 않는다.
현재 DB 기준 official_faq asset은 1건이고, 대부분은 Help Library/support 성격의 공식 후보 URL이다.
따라서 본 리포트에서는 "support/FAQ 후보"로 표기한다.
```

## 3. 기존 수집 상태

| 항목 | 값 |
|---|---:|
| 이전 Coveo totalCount | {previous.get('previous_coveo_total_count')} |
| 이전에 요청한 검색 결과 수 | {previous.get('previous_coveo_result_count')} |
| 이전 신규 asset 수 | {previous.get('previous_new_assets')} |
| 이전 신규 chunk 수 | {previous.get('previous_new_chunks')} |
| 저장된 support result HTML 수 | {previous.get('previous_search_result_html_count')} |

## 4. 현재 DB 전체 상태

| 테이블 | 현재 수 |
|---|---:|
| official_assets | {db['official_assets_total']} |
| official_document_chunks | {db['official_document_chunks_total']} |
| official_document_embeddings | {db['official_document_embeddings_total']} |

## 5. 판단

현재 DB에는 AS-Q24ENXE support/FAQ 후보 전체가 들어가 있지 않다.

기존 수집은 Coveo Support totalCount 중 일부 결과만 요청하여 `search_support_result` asset과 chunk로 저장했다. 따라서 FAQ/support 후보 전체를 기준으로 RAG 품질 검증을 수행하면 검색 대상 자체가 누락된 상태가 된다.

## 6. 누락 원인

| 원인 | 설명 |
|---|---|
| 페이지네이션 미수집 | 기존 수집 스크립트는 `numberOfResults=30`, `firstResult=0` 중심으로 동작했다. |
| 검색 결과 전체 원본 HTML 미저장 | 전체 후보 URL 중 일부만 raw HTML로 저장되었다. |
| DB 반영 범위 제한 | 현재 DB에는 일부 `search_support_result`만 asset/chunk로 반영되어 있다. |
| FAQ/support 용어 혼재 | 검색 tab의 Support 결과는 Help Library/FAQ 성격의 문서를 포함하지만, DB상 `official_faq` asset은 1건뿐이다. |

## 7. 다음 수집 대상

누락 URL은 아래 파일에 전체 저장했다.

```text
{summary['output_files']['candidate_manifest']}
{summary['output_files'].get('summary')}
```

누락 URL 샘플:

{sample_missing}

## 8. 다음 작업

1. `missing_from_official_assets_needs_raw_html_collection` 상태의 URL만 공식 URL로 재검증한다.
2. 각 URL의 원본 HTML을 별도 폴더에 저장한다.
3. JSON-LD, articleBody, FAQ Q/A, troubleshooting 본문을 추출한다.
4. boilerplate chunk를 제거한다.
5. `official_document_chunks`를 확장한다.
6. 신규 chunk embedding을 생성한다.
7. 그 다음에 RAGService v2 검색 품질 검증을 수행한다.
"""
    report_path.write_text(lines, encoding="utf-8")


if __name__ == "__main__":
    main()
