from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def project_child(parent: Path, prefix: str) -> Path:
    return next(path for path in parent.iterdir() if path.name.startswith(prefix))


DEV_DIR = project_child(PROJECT_ROOT, "07_")
AR_DIR = project_child(DEV_DIR, "06_AR")
DATA_DIR = project_child(AR_DIR, "02_")
AI_DIR = project_child(AR_DIR, "03_")
OUTPUT_BASE_DIR = project_child(AR_DIR, "06_")

DB_PATH = DATA_DIR / "db" / "careshot_ar_mock.db"
RAG_PATH = AI_DIR / "rag"
OUTPUT_DIR = OUTPUT_BASE_DIR / "official_youtube"

sys.path.insert(0, str(RAG_PATH))
from careshot_embedding_model import DEFAULT_CONFIG, embed_text  # noqa: E402


OFFICIAL_CHANNEL_WHITELIST = {
    "LG India": "https://www.youtube.com/@LGIndia",
    "LG Global": "https://www.youtube.com/@LGGlobal",
    "LG DIY Service": "https://www.youtube.com/@LGService4u",
}


@dataclass(frozen=True)
class YouTubeCandidate:
    video_id: str
    procedure_type: str
    language_code: str
    query_terms: tuple[str, ...]
    curated_summary: str
    official_scope: str = "air_conditioner_common"
    product_code: str | None = None
    model_name: str | None = None
    risk_policy: str = "self_care_allowed"

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


AIRCON_YOUTUBE_CANDIDATES = [
    YouTubeCandidate(
        video_id="tR91lFD0yIo",
        product_code="AS-Q24ENXE",
        model_name="AS-Q24ENXE",
        procedure_type="filter_cleaning",
        language_code="en",
        official_scope="mvp_exact_model_support",
        query_terms=("split ac filter cleaning", "air conditioner filter cleaning", "ac filter clean"),
        curated_summary="Official LG India split AC filter-cleaning guide for safe customer filter maintenance.",
    ),
    YouTubeCandidate(
        video_id="gp8CqK-uP5M",
        procedure_type="filter_cleaning",
        language_code="en",
        query_terms=("air conditioner air filter clean", "clean your air filter", "ac filter maintenance"),
        curated_summary="Official LG India guide explaining how to clean an air-conditioner air filter.",
    ),
    YouTubeCandidate(
        video_id="--LTtMx6ST8",
        procedure_type="filter_cleaning",
        language_code="en",
        query_terms=("window ac filter cleaning", "window air conditioner filter clean", "ac care"),
        curated_summary="Official LG India window AC filter-cleaning guide.",
    ),
    YouTubeCandidate(
        video_id="Sm-9WJ5Kdtg",
        procedure_type="filter_cleaning",
        language_code="en",
        query_terms=("window air conditioner air filter cleaning process", "window ac filter clean"),
        curated_summary="Official LG India step guide for the window air-conditioner air-filter cleaning process.",
    ),
    YouTubeCandidate(
        video_id="6kN4D7ZiswY",
        procedure_type="clean_filter_indicator_reset",
        language_code="en",
        query_terms=("filter clean indication reset", "clean filter light reset", "window ac filter indicator"),
        curated_summary="Official LG India guide for resetting the filter-clean indication after safe filter care.",
    ),
    YouTubeCandidate(
        video_id="Qn14cE3nhrA",
        procedure_type="clean_filter_indicator_reset",
        language_code="hi",
        query_terms=("clean filter indicator reset hindi", "window ac clean filter light", "filter indicator reset"),
        curated_summary="Official LG India Hindi guide for resetting the clean-filter indicator in a window AC.",
    ),
    YouTubeCandidate(
        video_id="WtWgW5iWJxc",
        procedure_type="filter_cleaning",
        language_code="en",
        query_terms=("window ac care", "keep it cool keep it clean", "ac filter care"),
        curated_summary="Official LG India window AC care video for filter-related customer maintenance.",
    ),
    YouTubeCandidate(
        video_id="mEh9jV1dVvE",
        procedure_type="filter_cleaning",
        language_code="hi",
        query_terms=("window ac care hindi", "clean filter means cooler home", "ac filter care"),
        curated_summary="Official LG India Hindi window AC care video focused on clean-filter maintenance.",
    ),
    YouTubeCandidate(
        video_id="0gMM6_J56dg",
        procedure_type="filter_cleaning",
        language_code="en",
        query_terms=("easy to clean and maintain", "dualcool ac maintenance", "filter cleaning easily"),
        curated_summary="Official LG India DUALCOOL AC video emphasizing easy filter cleaning and maintenance.",
    ),
    YouTubeCandidate(
        video_id="V7lRsemCvxw",
        procedure_type="air_quality_filter",
        language_code="en",
        query_terms=("hd filter", "dualcool hd filter", "air conditioner filter"),
        curated_summary="Official LG India DUALCOOL HD filter video for air-quality filter evidence.",
    ),
    YouTubeCandidate(
        video_id="345lp8r0T6w",
        procedure_type="air_quality_filter",
        language_code="en",
        query_terms=("anti allergy filter", "ac filter", "air quality filter"),
        curated_summary="Official LG India AC anti-allergy filter video for air-quality filter evidence.",
    ),
    YouTubeCandidate(
        video_id="GdF3tQELIUk",
        procedure_type="air_quality_filter",
        language_code="en",
        query_terms=("double filtration", "pure hygienic air", "ac filter system"),
        curated_summary="Official LG India DUALCOOL AC double-filtration video for air-quality filter evidence.",
    ),
    YouTubeCandidate(
        video_id="JeGM__LAklc",
        procedure_type="air_quality_filter",
        language_code="en",
        query_terms=("multi protection filter", "3m filter", "dualcool filter"),
        curated_summary="Official LG Global DUALCOOL multi-protection filter video.",
    ),
    YouTubeCandidate(
        video_id="2W-vjLGobzQ",
        procedure_type="air_quality_filter",
        language_code="en",
        query_terms=("comfortable healthy", "multi protection filter", "dual inverter"),
        curated_summary="Official LG Global DUALCOOL feature video referencing healthy air and multi-protection filtering.",
    ),
    YouTubeCandidate(
        video_id="s8QWYZGHU9M",
        procedure_type="air_quality_filter",
        language_code="en",
        query_terms=("duct air conditioner uvnano filter box", "uvnano filter", "duct ac filter"),
        curated_summary="Official LG Global duct air-conditioner UVnano filter-box video.",
    ),
    YouTubeCandidate(
        video_id="gUr0_jYWfnE",
        procedure_type="auto_clean",
        language_code="en",
        query_terms=("himclean", "ac self cleaning", "air conditioner hygiene"),
        curated_summary="Official LG India HIMClean video for AC hygiene and automatic cleaning evidence.",
    ),
    YouTubeCandidate(
        video_id="e5yXc2_0kas",
        procedure_type="auto_clean",
        language_code="en",
        query_terms=("auto cleaning function", "split air conditioner auto clean", "mold odor prevention"),
        curated_summary="Official LG India split AC auto-cleaning function guide.",
    ),
    YouTubeCandidate(
        video_id="5tPv8Nc0rzU",
        procedure_type="auto_clean",
        language_code="en",
        query_terms=("protect yourself with auto clean", "dualcool auto clean", "ac hygiene"),
        curated_summary="Official LG India DUALCOOL auto-clean video for hygiene and odor-prevention evidence.",
    ),
    YouTubeCandidate(
        video_id="zC74wMD1AkA",
        procedure_type="auto_clean",
        language_code="en",
        query_terms=("artcool uvnano", "uvnano clean fan", "air conditioner hygiene"),
        curated_summary="Official LG Global ARTCOOL UVnano video related to air-conditioner hygiene.",
    ),
    YouTubeCandidate(
        video_id="KvAdsmQMLOc",
        procedure_type="pm_sensor_cleaning",
        language_code="en",
        query_terms=("clean pm sensor", "lg ac pm sensor", "air conditioner sensor clean"),
        curated_summary="Official LG India DIY guide for cleaning the AC PM sensor.",
    ),
    YouTubeCandidate(
        video_id="t0WbXQnqlK4",
        procedure_type="pm_sensor_check",
        language_code="en",
        query_terms=("check pm sensor", "ac pm sensor", "smart ac sensor"),
        curated_summary="Official LG India DIY guide for checking the AC PM sensor.",
    ),
    YouTubeCandidate(
        video_id="wqNftUymDhs",
        procedure_type="air_purifier_function",
        language_code="en",
        query_terms=("built in air purifier", "lg ac air purifier", "fresh air"),
        curated_summary="Official LG India DIY guide for the built-in air purifier function in LG AC.",
    ),
    YouTubeCandidate(
        video_id="CGFhqqwzPLk",
        procedure_type="remote_operation",
        language_code="en",
        query_terms=("inverter split ac remote basic functions", "ac remote guide", "basic functions"),
        curated_summary="Official LG India remote guide for basic inverter split AC functions.",
    ),
    YouTubeCandidate(
        video_id="QkkFdobWAzU",
        procedure_type="remote_operation",
        language_code="en",
        query_terms=("inverter split ac remote special functions", "ac remote guide", "special functions"),
        curated_summary="Official LG India remote guide for special inverter split AC functions.",
    ),
    YouTubeCandidate(
        video_id="UVwbCuwfPsA",
        procedure_type="remote_operation",
        language_code="en",
        query_terms=("split ac remote special functions", "remote special functions", "lg ac remote"),
        curated_summary="Official LG India remote guide variant for split AC special functions.",
    ),
    YouTubeCandidate(
        video_id="5H2oDs7xc2Y",
        procedure_type="remote_operation",
        language_code="en",
        query_terms=("inverter split ac remote additional functions", "ac remote additional functions"),
        curated_summary="Official LG India remote guide for additional inverter split AC functions.",
    ),
    YouTubeCandidate(
        video_id="GwWC-0sxE_k",
        procedure_type="remote_operation",
        language_code="hi",
        query_terms=("set time in lg ac remote hindi", "ac remote clock", "timer setup"),
        curated_summary="Official LG India Hindi guide for setting time on the LG AC remote.",
    ),
    YouTubeCandidate(
        video_id="S_9nKa1pBXE",
        procedure_type="remote_operation",
        language_code="hi",
        query_terms=("set sleep timer", "lg ac remote sleep timer", "hindi"),
        curated_summary="Official LG India guide for setting the AC sleep timer.",
    ),
    YouTubeCandidate(
        video_id="JJUNsTxx_Gw",
        procedure_type="convertible_cooling",
        language_code="en",
        query_terms=("5 in one convertible", "super convertible feature", "lg ac cooling mode"),
        curated_summary="Official LG India DIY guide for the 5-in-1 super convertible AC feature.",
    ),
    YouTubeCandidate(
        video_id="zirjvsBEMik",
        procedure_type="smart_connectivity",
        language_code="en",
        query_terms=("connect air conditioner alexa", "smart ac alexa", "lg ac connectivity"),
        curated_summary="Official LG India DIY guide for connecting an LG air conditioner with Amazon Alexa.",
    ),
    YouTubeCandidate(
        video_id="prcKg6dnFVg",
        procedure_type="quiet_mode",
        language_code="en",
        query_terms=("experience peace with mute", "dualcool mute", "quiet mode"),
        curated_summary="Official LG India DUALCOOL video for mute/quiet operation guidance.",
    ),
    YouTubeCandidate(
        video_id="oP3P0Z5TArE",
        procedure_type="high_risk_refrigerant",
        language_code="hi",
        query_terms=("ch38 error code", "low refrigerant", "ac error code"),
        curated_summary=(
            "Official LG India Hindi guide explaining CH38 error code. Because it relates to low refrigerant, "
            "use only as evidence for expert-AS routing, not self-care or AR guidance."
        ),
        risk_policy="expert_as_only",
    ),
]


DISCOVERED_AIRCON_VIDEO_IDS = (
    # LG India playlist: "LG DIY Service - Air Conditioner"
    "mEh9jV1dVvE",
    "WtWgW5iWJxc",
    "XqXSN0_qBOI",
    "IMBionT2lbI",
    "YTlRZDhC3Ng",
    "gh66UZW-upM",
    "NND7jVpEid0",
    "nWf2GZQd7ko",
    "vp5q7r-aYtY",
    "RXHA5wDUvfc",
    "5H2oDs7xc2Y",
    "QkkFdobWAzU",
    "CGFhqqwzPLk",
    "UVwbCuwfPsA",
    "wqNftUymDhs",
    "KvAdsmQMLOc",
    "t0WbXQnqlK4",
    "zirjvsBEMik",
    "JJUNsTxx_Gw",
    "1fT2F9LQ-14",
    "AwC7HcfZ2Ug",
    "qFcsCY03EVk",
    "Sm-9WJ5Kdtg",
    "2Oz1wsPDN2w",
    "YXj-wKKzWA0",
    "I-06GlrB_pY",
    "QQ3YP01ms7g",
    "OskLCxO7mp4",
    "zC3W9uGNto8",
    "tm7nX1zu2JU",
    "6kN4D7ZiswY",
    "r138oB3OaeE",
    "5znrxw-XqxE",
    "e5yXc2_0kas",
    "ieAzY8TTyIE",
    "eqEm2qIvkDk",
    "r-_Q7vWIxNM",
    "TCLuliWE0Is",
    "D_qzY4Y7dws",
    "CqyVy2uR5M0",
    "O0Q3_NoIfTQ",
    "lIJW1qsPFrw",
    "4XPOMMTDXgA",
    "phLqLRRiZQE",
    "OTpAPncMWT0",
    "mB4sBuXo1TI",
    "--LTtMx6ST8",
    "l8l6BzFjPsk",
    "L6UaOG3ps_Y",
    "PTfUMFYigx0",
    "Ipw80tGm_M0",
    "AYRRNehb_Sk",
    "U1aU722eKO0",
    "MR2uCLqp_XE",
    "tR91lFD0yIo",
    # LG DIY Service channel searches: "Air Conditioner" and "AC"
    "s0VvjQCak3g",
    "UV7E8Ccs4nw",
    "6rRQ4JZqbuU",
    "vNoKUDHZZp8",
    "vA8NPbY1kKI",
    "7o4FOHGIfVI",
    "uik6iu2QXf4",
    "gZJNXPVbcx0",
    "Ykq6eIvQgzE",
    "9HUHaUAKMHE",
    "xjb-ZrKl7Mk",
    "7u2oEgw5Qjg",
    "1p4JYMsqgwM",
    "NB7CuY6bOoE",
    "dLXDFJikZ3M",
    "qIoBLIbEol8",
    "kgFaqnYhxW0",
    "MHY-cUHeM2U",
    "kWskYFC5yN0",
    "H9wDiaopVZM",
    "rvn_nt8YAzE",
    "dsOW94Uc4_c",
    "DAeHEf5xlmQ",
    "qGUjCBMisa4",
    "VO9AwQJwYfs",
    "tiO_ilFCcu4",
    "LPRwVkU36fQ",
    "KM3vm9-tjMY",
    "BrAlK8ddIWA",
    "FyxirqCWIRI",
    "-6FzcR0metA",
    "2xx6u_tQLf4",
    "KHoetMNNZN0",
    "GDBwJwqFBNQ",
    "A4hvCEOpJXU",
    "BZhqI13QugM",
)


def build_discovered_candidate(video_id: str) -> YouTubeCandidate:
    return YouTubeCandidate(
        video_id=video_id,
        procedure_type="auto_aircon_support",
        language_code="en",
        query_terms=("lg ac", "lg air conditioner", "lg diy service air conditioner"),
        curated_summary=(
            "Official LG air-conditioner support video discovered from the LG DIY Service "
            "Air Conditioner playlist or LG DIY Service channel search results."
        ),
        risk_policy="title_classified",
    )


def classify_candidate_from_title(candidate: YouTubeCandidate, oembed: dict[str, Any]) -> YouTubeCandidate:
    if candidate.procedure_type != "auto_aircon_support":
        return candidate

    title = str(oembed.get("title") or "")
    lower = title.lower()
    language_code = "hi" if "hindi" in lower or "_hindi" in lower else "en"
    procedure_type = "air_conditioner_support"
    risk_policy = "self_care_allowed"
    query_terms = ["lg air conditioner", "lg ac", title]

    if "filter" in lower or "filer" in lower:
        procedure_type = "filter_cleaning"
        query_terms.extend(["filter cleaning", "ac filter"])
    elif "auto clean" in lower or "auto cleaning" in lower or "freeze cleaning" in lower:
        procedure_type = "auto_clean"
        query_terms.extend(["auto clean", "freeze cleaning", "ac hygiene"])
    elif "pm" in lower or "sensor" in lower or "dust" in lower:
        procedure_type = "pm_sensor_cleaning"
        query_terms.extend(["pm sensor", "dust sensor", "sensor cleaning"])
    elif "remote" in lower or "timer" in lower or "sleep" in lower or "temperature" in lower:
        procedure_type = "remote_operation"
        query_terms.extend(["remote control", "timer", "temperature setting"])
    elif "thinq" in lower or "alexa" in lower or "google" in lower or "iphone" in lower or "wi-fi" in lower:
        procedure_type = "smart_connectivity"
        query_terms.extend(["thinq", "smart connectivity", "wifi"])
    elif "cooling" in lower or "cool" in lower:
        procedure_type = "no_cooling_self_check"
        query_terms.extend(["cooling", "not cooling", "cooling performance"])
        risk_policy = "self_as_allowed"
    elif "energy saving" in lower:
        procedure_type = "energy_saving"
        query_terms.extend(["energy saving", "power saving"])
    elif "swing" in lower or "flap" in lower or "fan speed" in lower or "mode" in lower:
        procedure_type = "remote_operation"
        query_terms.extend(["air distribution", "fan speed", "mode setting"])
    elif "plasma" in lower or "ionizer" in lower or "air purifier" in lower:
        procedure_type = "air_quality_filter"
        query_terms.extend(["plasma", "ionizer", "air purifier"])
    elif "outdoor unit" in lower:
        procedure_type = "outdoor_unit_care"
        query_terms.extend(["outdoor unit", "unit cleaning"])

    if any(term in lower for term in ("no power", "power off", "turning off", "turns off", "turned off")):
        procedure_type = "power_troubleshooting"
        risk_policy = "expert_as_only" if "no power" in lower else "self_as_allowed"
        query_terms.extend(["no power", "power troubleshooting", "turning off", "self check"])
    elif any(term in lower for term in ("burn", "burning", "ch38", "error code")):
        procedure_type = "high_risk_troubleshooting"
        risk_policy = "expert_as_only"
        query_terms.extend(["expert as", "safety issue"])
    elif any(term in lower for term in ("ice build", "noise", "vibration", "not working")):
        procedure_type = "troubleshooting_self_check"
        risk_policy = "self_as_allowed"
        query_terms.extend(["self check", "troubleshooting"])

    return replace(
        candidate,
        procedure_type=procedure_type,
        language_code=language_code,
        query_terms=tuple(dict.fromkeys(query_terms)),
        curated_summary=f"Official LG air-conditioner video: {title}",
        risk_policy=risk_policy,
    )


def dedupe_candidates(candidates: list[YouTubeCandidate]) -> list[YouTubeCandidate]:
    seen: set[str] = set()
    unique: list[YouTubeCandidate] = []
    for candidate in candidates:
        if candidate.video_id in seen:
            continue
        seen.add(candidate.video_id)
        unique.append(candidate)
    return unique


AIRCON_YOUTUBE_CANDIDATES = dedupe_candidates(
    [*AIRCON_YOUTUBE_CANDIDATES, *(build_discovered_candidate(video_id) for video_id in DISCOVERED_AIRCON_VIDEO_IDS)]
)


def fetch_json(url: str, timeout: int = 12) -> tuple[int, dict[str, Any]]:
    req = Request(url, headers={"User-Agent": "CareShot-BrowserYouTubeCollector/2.0"})
    with urlopen(req, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def check_url_accessible(url: str, timeout: int = 12) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "CareShot-BrowserYouTubeCollector/2.0"}, method="GET")
    try:
        with urlopen(req, timeout=timeout) as response:
            response.read(1024)
            return {"ok": 200 <= response.status < 400, "status": response.status, "error": None}
    except HTTPError as exc:
        return {"ok": 200 <= exc.code < 400, "status": exc.code, "error": str(exc)}
    except URLError as exc:
        return {"ok": False, "status": None, "error": str(exc)}


def is_direct_access_acceptable(direct_access: dict[str, Any]) -> bool:
    # YouTube can rate-limit repeated watch-page checks during batch reruns.
    # A 429 is treated as non-fatal when oEmbed already confirms the official video.
    return bool(direct_access.get("ok")) or direct_access.get("status") == 429


def fetch_oembed(url: str) -> dict[str, Any]:
    endpoint = "https://www.youtube.com/oembed?" + urlencode({"url": url, "format": "json"})
    try:
        status, payload = fetch_json(endpoint)
    except Exception as exc:
        return {"ok": False, "status": None, "error": str(exc)}
    author_name = payload.get("author_name")
    author_url = payload.get("author_url")
    return {
        "ok": status == 200
        and author_name in OFFICIAL_CHANNEL_WHITELIST
        and author_url == OFFICIAL_CHANNEL_WHITELIST.get(author_name),
        "status": status,
        "title": payload.get("title"),
        "author_name": author_name,
        "author_url": author_url,
        "error": None,
    }


def next_int_id(con: sqlite3.Connection, table_name: str, id_column: str) -> int:
    row = con.execute(f'SELECT COALESCE(MAX("{id_column}"), 0) + 1 FROM "{table_name}"').fetchone()
    return int(row[0])


def chunk_text(candidate: YouTubeCandidate, oembed: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Official YouTube video title: {oembed['title']}",
            f"Official channel: {oembed['author_name']} ({oembed['author_url']})",
            "Collection method: browser/search discovery + YouTube oEmbed official-channel validation + watch URL access check.",
            "Product type: air_conditioner",
            f"Model scope: {candidate.model_name or candidate.official_scope}",
            f"Procedure type: {candidate.procedure_type}",
            f"Risk policy: {candidate.risk_policy}",
            f"Official video summary: {candidate.curated_summary}",
            f"Customer query phrases: {', '.join(candidate.query_terms)}",
            "Safety boundary: self-care videos are for customer-safe care/settings only; refrigerant, electrical, smoke, burning smell, or internal disassembly issues must route to expert AS.",
        ]
    )


def purge_non_aircon_official_youtube(con: sqlite3.Connection) -> dict[str, int]:
    asset_ids = [
        int(row["asset_id"])
        for row in con.execute(
            """
            SELECT asset_id
            FROM "OFFICIAL_ASSET"
            WHERE source_type = 'official_youtube'
              AND product_type <> 'air_conditioner'
            """
        ).fetchall()
    ]
    if not asset_ids:
        return {"deleted_embeddings": 0, "deleted_chunks": 0, "deleted_assets": 0}
    placeholders = ",".join("?" for _ in asset_ids)
    chunk_ids = [
        int(row["chunk_id"])
        for row in con.execute(
            f'SELECT chunk_id FROM "OFFICIAL_DOCUMENT_CHUNK" WHERE asset_id IN ({placeholders})',
            asset_ids,
        ).fetchall()
    ]
    deleted_embeddings = 0
    if chunk_ids:
        chunk_placeholders = ",".join("?" for _ in chunk_ids)
        deleted_embeddings = con.execute(
            f'DELETE FROM "OFFICIAL_DOCUMENT_EMBEDDING" WHERE chunk_id IN ({chunk_placeholders})',
            chunk_ids,
        ).rowcount
    deleted_chunks = con.execute(
        f'DELETE FROM "OFFICIAL_DOCUMENT_CHUNK" WHERE asset_id IN ({placeholders})',
        asset_ids,
    ).rowcount
    deleted_assets = con.execute(
        f'DELETE FROM "OFFICIAL_ASSET" WHERE asset_id IN ({placeholders})',
        asset_ids,
    ).rowcount
    return {
        "deleted_embeddings": deleted_embeddings,
        "deleted_chunks": deleted_chunks,
        "deleted_assets": deleted_assets,
    }


def upsert_candidate(con: sqlite3.Connection, candidate: YouTubeCandidate, oembed: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    url = candidate.url
    asset_row = con.execute('SELECT asset_id FROM "OFFICIAL_ASSET" WHERE source_url = ?', (url,)).fetchone()
    inserted_asset = False
    if asset_row:
        asset_id = int(asset_row["asset_id"])
        con.execute(
            """
            UPDATE "OFFICIAL_ASSET"
            SET product_code = ?, product_type = 'air_conditioner', model_name = ?, procedure_type = ?,
                source_type = 'official_youtube', source_title = ?, language_code = ?, verified_yn = 'Y'
            WHERE asset_id = ?
            """,
            (
                candidate.product_code,
                candidate.model_name,
                candidate.procedure_type,
                oembed["title"],
                candidate.language_code,
                asset_id,
            ),
        )
    else:
        asset_id = next_int_id(con, "OFFICIAL_ASSET", "asset_id")
        inserted_asset = True
        con.execute(
            """
            INSERT INTO "OFFICIAL_ASSET"
              (asset_id, product_code, product_type, model_name, procedure_type, source_type,
               source_title, source_url, language_code, verified_yn, created_at)
            VALUES (?, ?, 'air_conditioner', ?, ?, 'official_youtube', ?, ?, ?, 'Y', ?)
            """,
            (
                asset_id,
                candidate.product_code,
                candidate.model_name,
                candidate.procedure_type,
                oembed["title"],
                url,
                candidate.language_code,
                now,
            ),
        )

    text = chunk_text(candidate, oembed)
    chunk_row = con.execute(
        'SELECT chunk_id FROM "OFFICIAL_DOCUMENT_CHUNK" WHERE asset_id = ? AND source_url = ?',
        (asset_id, url),
    ).fetchone()
    inserted_chunk = False
    if chunk_row:
        chunk_id = int(chunk_row["chunk_id"])
        con.execute(
            """
            UPDATE "OFFICIAL_DOCUMENT_CHUNK"
            SET product_code = ?, procedure_type = ?, chunk_text = ?,
                source_section = 'youtube_browser_oembed_metadata',
                language_code = ?, embedding_status = 'embedded'
            WHERE chunk_id = ?
            """,
            (candidate.product_code, candidate.procedure_type, text, candidate.language_code, chunk_id),
        )
    else:
        chunk_id = next_int_id(con, "OFFICIAL_DOCUMENT_CHUNK", "chunk_id")
        inserted_chunk = True
        con.execute(
            """
            INSERT INTO "OFFICIAL_DOCUMENT_CHUNK"
              (chunk_id, asset_id, product_code, procedure_type, chunk_text, source_url,
               source_section, language_code, embedding_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'youtube_browser_oembed_metadata', ?, 'embedded', ?)
            """,
            (
                chunk_id,
                asset_id,
                candidate.product_code,
                candidate.procedure_type,
                text,
                url,
                candidate.language_code,
                now,
            ),
        )

    embedding_vector = json.dumps(embed_text(text), ensure_ascii=True, sort_keys=True)
    embedding_row = con.execute(
        """
        SELECT embedding_id
        FROM "OFFICIAL_DOCUMENT_EMBEDDING"
        WHERE chunk_id = ? AND embedding_model = ?
        """,
        (chunk_id, DEFAULT_CONFIG.model_name),
    ).fetchone()
    inserted_embedding = False
    if embedding_row:
        con.execute(
            """
            UPDATE "OFFICIAL_DOCUMENT_EMBEDDING"
            SET embedding_vector = ?, embedding_status = 'embedded', created_at = ?
            WHERE embedding_id = ?
            """,
            (embedding_vector, now, embedding_row["embedding_id"]),
        )
    else:
        embedding_id = next_int_id(con, "OFFICIAL_DOCUMENT_EMBEDDING", "embedding_id")
        inserted_embedding = True
        con.execute(
            """
            INSERT INTO "OFFICIAL_DOCUMENT_EMBEDDING"
              (embedding_id, chunk_id, embedding_model, embedding_vector, embedding_status, created_at)
            VALUES (?, ?, ?, ?, 'embedded', ?)
            """,
            (embedding_id, chunk_id, DEFAULT_CONFIG.model_name, embedding_vector, now),
        )

    return {
        "asset_id": asset_id,
        "chunk_id": chunk_id,
        "inserted_asset": inserted_asset,
        "inserted_chunk": inserted_chunk,
        "inserted_embedding": inserted_embedding,
    }


def update_mvp_guide_video(con: sqlite3.Connection, video_url: str, chunk_id: int, asset_id: int) -> dict[str, Any]:
    row = con.execute(
        """
        SELECT guide_id, source_chunk_ids
        FROM "GUIDE"
        WHERE product_code = 'AS-Q24ENXE'
          AND guide_type = 'manual'
          AND guide_category = 'filter_cleaning'
        ORDER BY guide_id ASC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return {"updated": False, "reason": "mvp_manual_guide_not_found"}
    try:
        source_chunk_ids = json.loads(row["source_chunk_ids"] or "[]")
    except json.JSONDecodeError:
        source_chunk_ids = []
    if chunk_id not in source_chunk_ids:
        source_chunk_ids.append(chunk_id)
    con.execute(
        """
        UPDATE "GUIDE"
        SET video_url = ?,
            source_asset_id = COALESCE(source_asset_id, ?),
            source_chunk_ids = ?
        WHERE guide_id = ?
        """,
        (video_url, asset_id, json.dumps(source_chunk_ids, ensure_ascii=True), row["guide_id"]),
    )
    return {"updated": True, "guide_id": row["guide_id"], "source_chunk_ids": source_chunk_ids}


def run() -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    stored: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    guide_update: dict[str, Any] | None = None

    with con:
        purge_result = purge_non_aircon_official_youtube(con)
        for candidate in AIRCON_YOUTUBE_CANDIDATES:
            oembed = fetch_oembed(candidate.url)
            direct_access = check_url_accessible(candidate.url)
            candidate = classify_candidate_from_title(candidate, oembed)
            validation = {
                "video_id": candidate.video_id,
                "url": candidate.url,
                "oembed": oembed,
                "direct_access": direct_access,
            }
            if not oembed["ok"] or not is_direct_access_acceptable(direct_access):
                skipped.append({**validation, "reason": "official_channel_or_access_check_failed"})
                continue
            db_result = upsert_candidate(con, candidate, oembed)
            item = {
                **validation,
                **db_result,
                "product_type": "air_conditioner",
                "procedure_type": candidate.procedure_type,
                "language_code": candidate.language_code,
                "risk_policy": candidate.risk_policy,
                "query_terms": candidate.query_terms,
            }
            stored.append(item)
            if candidate.video_id == "tR91lFD0yIo":
                guide_update = update_mvp_guide_video(con, candidate.url, db_result["chunk_id"], db_result["asset_id"])

    counts = {
        "official_youtube_total": con.execute(
            'SELECT COUNT(*) FROM "OFFICIAL_ASSET" WHERE source_type = "official_youtube"'
        ).fetchone()[0],
        "official_youtube_aircon": con.execute(
            'SELECT COUNT(*) FROM "OFFICIAL_ASSET" WHERE source_type = "official_youtube" AND product_type = "air_conditioner"'
        ).fetchone()[0],
        "official_youtube_non_aircon": con.execute(
            'SELECT COUNT(*) FROM "OFFICIAL_ASSET" WHERE source_type = "official_youtube" AND product_type <> "air_conditioner"'
        ).fetchone()[0],
        "youtube_aircon_chunks": con.execute(
            """
            SELECT COUNT(*)
            FROM "OFFICIAL_DOCUMENT_CHUNK" c
            JOIN "OFFICIAL_ASSET" a ON a.asset_id = c.asset_id
            WHERE a.source_type = 'official_youtube'
              AND a.product_type = 'air_conditioner'
            """
        ).fetchone()[0],
        "youtube_aircon_embeddings": con.execute(
            """
            SELECT COUNT(*)
            FROM "OFFICIAL_DOCUMENT_EMBEDDING" e
            JOIN "OFFICIAL_DOCUMENT_CHUNK" c ON c.chunk_id = e.chunk_id
            JOIN "OFFICIAL_ASSET" a ON a.asset_id = c.asset_id
            WHERE a.source_type = 'official_youtube'
              AND a.product_type = 'air_conditioner'
            """
        ).fetchone()[0],
    }
    guide_row = con.execute(
        'SELECT guide_id, video_url, source_asset_id, source_chunk_ids FROM "GUIDE" WHERE guide_id = 1'
    ).fetchone()
    summary = {
        "collection_method": "browser_search_candidates_plus_oembed_official_channel_validation",
        "db_path": str(DB_PATH),
        "attempted": len(AIRCON_YOUTUBE_CANDIDATES),
        "stored": len(stored),
        "skipped": len(skipped),
        "direct_access_rate_limited": sum(1 for item in stored if item["direct_access"].get("status") == 429),
        "inserted_assets": sum(1 for item in stored if item["inserted_asset"]),
        "inserted_chunks": sum(1 for item in stored if item["inserted_chunk"]),
        "inserted_embeddings": sum(1 for item in stored if item["inserted_embedding"]),
        "purge_non_aircon_result": purge_result,
        "counts": counts,
        "mvp_guide_update": guide_update,
        "mvp_guide": dict(guide_row) if guide_row else None,
        "stored_items": stored,
        "skipped_items": skipped,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    report_path = OUTPUT_DIR / "official_youtube_aircon_collection_report.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return summary


if __name__ == "__main__":
    run()
