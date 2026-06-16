from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PROJECT_DIR = Path(__file__).resolve().parents[2]
CRAWL_DIR = ROOT / "02_자료조사" / "02_크롤링"
MOCK_DIR = PROJECT_DIR / "02_데이터연동" / "mock_data"
SOURCE_DIR = PROJECT_DIR / "02_데이터연동" / "source_data"
VOC_DIR = SOURCE_DIR / "voc"
ENV_DIR = SOURCE_DIR / "environment"
OFFICIAL_DIR = SOURCE_DIR / "official_lg_india"
OFFICIAL_RAW_DIR = OFFICIAL_DIR / "raw"

NOW = "2026-06-03T12:00:00+05:30"

PRODUCT_TYPES = ["air_conditioner", "washing_machine", "air_purifier", "water_purifier"]

LG_INDIA_OFFICIAL_URLS = [
    {
        "url": "https://www.lg.com/in/support/order-support/frequently-asked-questions-1/",
        "product_type": "common",
        "procedure_type": "faq_care_and_service",
        "asset_type": "official_faq",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT20150063-20152544608551/",
        "product_type": "air_conditioner",
        "procedure_type": "filter_cleaning",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006627-20153905536408TWW/",
        "product_type": "washing_machine",
        "procedure_type": "tub_clean",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006627-20155073290419/",
        "product_type": "washing_machine",
        "procedure_type": "tub_clean",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006833-20154844249465/",
        "product_type": "air_purifier",
        "procedure_type": "filter_replacement_lamp",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/support/product-support/troubleshoot/help-library/cs-CT52006627-20153753013272/",
        "product_type": "water_purifier",
        "procedure_type": "filter_replacement",
        "asset_type": "help_library",
    },
    {
        "url": "https://www.lg.com/in/air-conditioners/split-air-conditioners/as-q24enxe/",
        "product_type": "air_conditioner",
        "procedure_type": "product_page",
        "asset_type": "product_page",
        "model_name": "AS-Q24ENXE",
    },
    {
        "url": "https://www.lg.com/in/care-accessories/air-purifiers/filter/adq75153435/",
        "product_type": "air_purifier",
        "procedure_type": "filter_replacement",
        "asset_type": "product_page",
        "model_name": "ADQ75153435",
    },
]

INDIA_CITIES = [
    ("Ahmedabad", "Gujarat", 23.0225, 72.5714),
    ("Bengaluru", "Karnataka", 12.9716, 77.5946),
    ("Bhopal", "Madhya Pradesh", 23.2599, 77.4126),
    ("Bhubaneswar", "Odisha", 20.2961, 85.8245),
    ("Chandigarh", "Chandigarh", 30.7333, 76.7794),
    ("Chennai", "Tamil Nadu", 13.0827, 80.2707),
    ("Coimbatore", "Tamil Nadu", 11.0168, 76.9558),
    ("Delhi", "Delhi", 28.6139, 77.2090),
    ("Faridabad", "Haryana", 28.4089, 77.3178),
    ("Ghaziabad", "Uttar Pradesh", 28.6692, 77.4538),
    ("Gurugram", "Haryana", 28.4595, 77.0266),
    ("Guwahati", "Assam", 26.1445, 91.7362),
    ("Hyderabad", "Telangana", 17.3850, 78.4867),
    ("Indore", "Madhya Pradesh", 22.7196, 75.8577),
    ("Jaipur", "Rajasthan", 26.9124, 75.7873),
    ("Jodhpur", "Rajasthan", 26.2389, 73.0243),
    ("Kanpur", "Uttar Pradesh", 26.4499, 80.3319),
    ("Kochi", "Kerala", 9.9312, 76.2673),
    ("Kolkata", "West Bengal", 22.5726, 88.3639),
    ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462),
    ("Ludhiana", "Punjab", 30.9010, 75.8573),
    ("Madurai", "Tamil Nadu", 9.9252, 78.1198),
    ("Meerut", "Uttar Pradesh", 28.9845, 77.7064),
    ("Mumbai", "Maharashtra", 19.0760, 72.8777),
    ("Mysuru", "Karnataka", 12.2958, 76.6394),
    ("Nagpur", "Maharashtra", 21.1458, 79.0882),
    ("Nashik", "Maharashtra", 19.9975, 73.7898),
    ("Noida", "Uttar Pradesh", 28.5355, 77.3910),
    ("Patna", "Bihar", 25.5941, 85.1376),
    ("Pune", "Maharashtra", 18.5204, 73.8567),
    ("Raipur", "Chhattisgarh", 21.2514, 81.6296),
    ("Rajkot", "Gujarat", 22.3039, 70.8022),
    ("Ranchi", "Jharkhand", 23.3441, 85.3096),
    ("Surat", "Gujarat", 21.1702, 72.8311),
    ("Thane", "Maharashtra", 19.2183, 72.9781),
    ("Thiruvananthapuram", "Kerala", 8.5241, 76.9366),
    ("Vadodara", "Gujarat", 22.3072, 73.1812),
    ("Varanasi", "Uttar Pradesh", 25.3176, 82.9739),
    ("Vijayawada", "Andhra Pradesh", 16.5062, 80.6480),
    ("Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185),
    ("Agra", "Uttar Pradesh", 27.1767, 78.0081),
    ("Amritsar", "Punjab", 31.6340, 74.8723),
    ("Aurangabad", "Maharashtra", 19.8762, 75.3433),
    ("Dehradun", "Uttarakhand", 30.3165, 78.0322),
    ("Jalandhar", "Punjab", 31.3260, 75.5762),
    ("Kota", "Rajasthan", 25.2138, 75.8648),
    ("Mangalore", "Karnataka", 12.9141, 74.8560),
    ("Puducherry", "Puducherry", 11.9416, 79.8083),
    ("Srinagar", "Jammu and Kashmir", 34.0837, 74.7973),
    ("Tiruchirappalli", "Tamil Nadu", 10.7905, 78.7047),
]


def ensure_dirs() -> None:
    for path in [MOCK_DIR, VOC_DIR, ENV_DIR, OFFICIAL_RAW_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    return []


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def stable_id(prefix: str, value: str, width: int = 12) -> str:
    digest = hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:width].upper()
    return f"{prefix}_{digest}"


def norm_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(str(value))
    value = re.sub(r"\s+", " ", value).strip()
    return value


def infer_product_type(path: Path, row: dict[str, str], text: str) -> str | None:
    path_text = str(path).lower()
    if "정수기" in str(path) or "water-purifier" in path_text or "water_purifier" in path_text:
        return "water_purifier"
    if "공기청정" in str(path) or "air-purifier" in path_text or "air_purifier" in path_text:
        return "air_purifier"
    if "세탁기" in str(path) or "washing" in path_text or "washer" in path_text:
        return "washing_machine"
    if "에어컨" in str(path) or "air-conditioner" in path_text or "air_conditioner" in path_text:
        return "air_conditioner"
    hay = " ".join([str(path), row.get("query", ""), row.get("title", ""), text]).lower()
    if any(k in hay for k in ["air purifier", "purifier", "공기청정"]):
        return "air_purifier"
    if any(k in hay for k in ["water purifier", "정수기"]):
        return "water_purifier"
    if any(k in hay for k in ["washing", "washer", "세탁기", "laundry"]):
        return "washing_machine"
    if any(k in hay for k in [" air conditioner", "split ac", " ac ", "에어컨", "cooling", "ch38"]):
        return "air_conditioner"
    if re.search(r"\bac\b", hay):
        return "air_conditioner"
    return None


PAIN_KEYWORDS = {
    "cooling_not_working": ["not cooling", "cooling", "hot air", "cool air", "ch38", "gas refill"],
    "water_leak": ["water leak", "leaking", "water coming", "drain", "leakage"],
    "burning_smell_smoke": ["burning", "smoke", "fire", "short circuit", "spark"],
    "odor_mold": ["smell", "odor", "mold", "fungus", "bad smell", "stink"],
    "filter_dirty": ["filter", "dust", "clean filter", "pm2.5", "pollution"],
    "service_delay": ["service", "technician", "customer care", "repair", "warranty", "complaint"],
    "noise_vibration": ["noise", "vibration", "sound"],
    "hard_water_limescale": ["hard water", "limescale", "scale", "tds", "scalgo"],
}


HIGH_RISK_TAGS = {"burning_smell_smoke"}
MEDIUM_RISK_TAGS = {"water_leak", "cooling_not_working", "noise_vibration"}
CARE_TAGS = {"odor_mold", "filter_dirty", "hard_water_limescale"}


def pain_tags(text: str) -> list[str]:
    lower = text.lower()
    tags = []
    for tag, words in PAIN_KEYWORDS.items():
        if any(word in lower for word in words):
            tags.append(tag)
    return tags


def sampling_bucket(tags: list[str], text: str) -> str:
    lower = text.lower()
    if any(tag in HIGH_RISK_TAGS for tag in tags) or any(k in lower for k in ["pcb", "wiring", "electric", "shock"]):
        return "high_signal_candidate"
    if any(tag in MEDIUM_RISK_TAGS for tag in tags):
        return "medium_signal_candidate"
    if any(tag in CARE_TAGS for tag in tags):
        return "care_signal_candidate"
    if len(text.split()) < 5:
        return "ambiguous_candidate"
    if "general_customer_voice" in tags:
        return "ambiguous_candidate"
    return "general_issue_candidate"


def source_type_from_path(path: Path) -> str:
    s = str(path)
    if "레딧" in s:
        return "reddit"
    if "희진" in s and "유튜브" in s:
        return "youtube_comment"
    if "mouthshut" in s.lower() or "가전 커뮤니티" in s:
        return "mouthshut_review"
    return "crawled_csv"


def collect_voc_cases() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    inventory = []
    for path in CRAWL_DIR.rglob("*.csv"):
        if "facebook_login_profile" in str(path) or "environment_sample" in path.name:
            continue
        rows = read_csv(path)
        if not rows:
            continue
        used = 0
        for idx, row in enumerate(rows):
            text = norm_text(
                row.get("english_translation")
                or row.get("comments")
                or row.get("review_text")
                or row.get("original")
                or row.get("title")
            )
            if len(text) < 20:
                continue
            product_type = infer_product_type(path, row, text)
            if not product_type:
                continue
            tags = pain_tags(text)
            if not tags:
                if source_type_from_path(path) in {"youtube_comment", "mouthshut_review"}:
                    tags = ["general_customer_voice"]
                else:
                    continue
            source_url = row.get("url") or row.get("review_url") or ""
            case_key = f"{path}|{idx}|{text[:120]}"
            bucket = sampling_bucket(tags, text)
            candidates.append(
                {
                    "voc_case_id": stable_id("VOC", case_key),
                    "source_type": source_type_from_path(path),
                    "source_path": str(path.relative_to(ROOT)),
                    "source_url": source_url,
                    "source_row_index": idx,
                    "product_type": product_type,
                    "raw_text": norm_text(row.get("original") or row.get("comments") or row.get("review_text") or text),
                    "english_text": text,
                    "korean_translation": norm_text(row.get("korean_translation")),
                    "language_hint": "mixed_or_unknown",
                    "pain_tags": tags,
                    "selection_bucket": bucket,
                    "evidence_level": "crawled_user_voc",
                    "collected_at": NOW,
                }
            )
            used += 1
        inventory.append(
            {
                "source_path": str(path.relative_to(ROOT)),
                "rows_total": len(rows),
                "rows_used": used,
                "source_type": source_type_from_path(path),
            }
        )

    seen = set()
    deduped = []
    for row in sorted(candidates, key=lambda x: (x["product_type"], x["selection_bucket"], x["voc_case_id"])):
        key = re.sub(r"\W+", "", row["english_text"].lower())[:180]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    by_bucket: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in deduped:
        by_bucket[(row["product_type"], row["selection_bucket"])].append(row)

    selected = []
    for product in PRODUCT_TYPES:
        product_selected = []
        for bucket in [
            "high_signal_candidate",
            "medium_signal_candidate",
            "care_signal_candidate",
            "ambiguous_candidate",
            "general_issue_candidate",
        ]:
            product_selected.extend(by_bucket.get((product, bucket), [])[:30])
        if len(product_selected) < 125:
            product_pool = [row for row in deduped if row["product_type"] == product and row not in product_selected]
            product_selected.extend(product_pool[: 125 - len(product_selected)])
        selected.extend(product_selected[:125])
    if len(selected) < 300:
        selected = deduped[:500]
    else:
        selected = selected[:500]

    summary = {
        "csv_files_scanned": len(inventory),
        "candidate_voc_cases": len(candidates),
        "deduped_voc_cases": len(deduped),
        "selected_voc_cases": len(selected),
        "selected_by_product_type": Counter(row["product_type"] for row in selected),
        "selected_by_sampling_bucket": Counter(row["selection_bucket"] for row in selected),
        "inventory": inventory,
    }
    public_selected = [
        {key: value for key, value in row.items() if key != "selection_bucket"}
        for row in selected
    ]
    return public_selected, summary


def build_intent_cases(voc_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return []


def build_environment_contexts() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    api_contexts, api_observations = fetch_open_meteo_environment()
    if len(api_contexts) >= 50 and len(api_observations) >= 300:
        summary = {
            "source_api": "Open-Meteo Historical Weather API; Open-Meteo Air Quality API; water-risk lookup based on CGWB/NWDP references",
            "observations_available": len(api_observations),
            "observations_exported": len(api_observations),
            "contexts_exported": len(api_contexts),
            "cities": len(api_contexts),
            "api_collection_status": "collected_live",
        }
        return api_contexts, api_observations, summary

    env_csv = CRAWL_DIR / "환경문제" / "environment_sample.csv"
    rows = read_csv(env_csv)
    observations = []
    for idx, row in enumerate(rows[:1000]):
        observations.append(
            {
                "observation_id": f"ENV_OBS_{idx+1:05d}",
                "date": row.get("date"),
                "city": row.get("city"),
                "state": row.get("state"),
                "temperature_max": row.get("temperature_max"),
                "temperature_avg": row.get("temperature_avg"),
                "humidity": row.get("humidity"),
                "rainfall": row.get("rainfall"),
                "monsoon_flag": row.get("monsoon_flag"),
                "heatwave_flag": row.get("heatwave_flag"),
                "aqi": row.get("aqi"),
                "pm25": row.get("pm25"),
                "pm10": row.get("pm10"),
                "water_hardness": row.get("water_hardness"),
                "tds": row.get("tds"),
                "environmental_risk_type": row.get("environmental_risk_type"),
                "source": row.get("source"),
                "source_path": str(env_csv.relative_to(ROOT)),
            }
        )

    by_city: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_city[(row.get("state", ""), row.get("city", ""))].append(row)

    contexts = []
    for idx, ((state, city), city_rows) in enumerate(sorted(by_city.items())[:50], start=1):
        risk_counter = Counter()
        humidity_values = []
        temp_values = []
        aqi_values = []
        hardness_values = []
        tds_values = []
        for row in city_rows:
            for risk in str(row.get("environmental_risk_type", "")).split("|"):
                if risk:
                    risk_counter[risk] += 1
            for target, values in [
                ("humidity", humidity_values),
                ("temperature_avg", temp_values),
                ("aqi", aqi_values),
                ("water_hardness", hardness_values),
                ("tds", tds_values),
            ]:
                try:
                    values.append(float(row.get(target, "")))
                except ValueError:
                    pass
        top_risks = [risk for risk, _ in risk_counter.most_common(4)]
        contexts.append(
            {
                "environment_id": f"ENV_REAL_{idx:03d}",
                "source": "Open-Meteo Historical Weather API; Open-Meteo Air Quality API; CGWB/NWDP referenced water-risk lookup",
                "source_path": str(env_csv.relative_to(ROOT)),
                "source_summary_path": str((CRAWL_DIR / "환경문제" / "environment_sources_summary.md").relative_to(ROOT)),
                "country": "India",
                "region": state,
                "city": city,
                "climate_zone": infer_climate_zone(top_risks),
                "season": "multi_period_2023_2026",
                "temperature_c": round(sum(temp_values) / len(temp_values), 2) if temp_values else None,
                "humidity_percent": round(sum(humidity_values) / len(humidity_values), 2) if humidity_values else None,
                "aqi": round(sum(aqi_values) / len(aqi_values), 2) if aqi_values else None,
                "water_hardness_level": water_hardness_level(sum(hardness_values) / len(hardness_values)) if hardness_values else None,
                "care_triggers": top_risks,
                "observed_at": NOW,
                "evidence_level": "api_statistical_context",
            }
        )
    if api_contexts:
        combined_contexts = list(api_contexts)
        seen_cities = {(row["region"], row["city"]) for row in combined_contexts}
        for row in contexts:
            key = (row["region"], row["city"])
            if key in seen_cities:
                continue
            row = dict(row)
            row["environment_id"] = f"ENV_REAL_{len(combined_contexts)+1:03d}"
            combined_contexts.append(row)
            seen_cities.add(key)
            if len(combined_contexts) >= 50:
                break
        combined_observations = api_observations + observations
        summary = {
            "source_api": "Open-Meteo Historical Weather API; Open-Meteo Air Quality API; CSV fallback based on same source family",
            "observations_available": len(rows),
            "observations_exported": len(combined_observations),
            "contexts_exported": len(combined_contexts),
            "cities": len(combined_contexts),
            "api_contexts_collected": len(api_contexts),
            "api_observations_collected": len(api_observations),
            "csv_contexts_used_for_gap_fill": len(combined_contexts) - len(api_contexts),
            "api_collection_status": "partial_live_plus_csv_gap_fill",
        }
        return combined_contexts, combined_observations, summary

    summary = {
        "source_csv": str(env_csv.relative_to(ROOT)),
        "observations_available": len(rows),
        "observations_exported": len(observations),
        "contexts_exported": len(contexts),
        "cities": len(by_city),
    }
    return contexts, observations, summary


def fetch_open_meteo_environment() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contexts = []
    observations = []
    water_lookup = load_water_lookup()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(fetch_city_environment, idx, city_data, water_lookup): idx
            for idx, city_data in enumerate(INDIA_CITIES, start=1)
        }
        for future in as_completed(futures):
            result = future.result()
            if not result:
                continue
            context, city_observations = result
            contexts.append(context)
            observations.extend(city_observations)
    contexts.sort(key=lambda row: row["environment_id"])
    observations.sort(key=lambda row: row["observation_id"])
    return contexts, observations


def fetch_city_environment(
    idx: int, city_data: tuple[str, str, float, float], water_lookup: dict[tuple[str, str], tuple[float, float]]
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    start_date = "2026-05-12"
    end_date = "2026-05-18"
    city, state, lat, lon = city_data
    archive_url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
        "&daily=temperature_2m_max,temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum"
        "&timezone=Asia%2FKolkata"
    )
    air_url = (
        "https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
        "&hourly=pm10,pm2_5&timezone=Asia%2FKolkata"
    )
    try:
        weather = fetch_json(archive_url)
        air = fetch_json(air_url)
    except Exception:
        return None
    daily = weather.get("daily", {})
    dates = daily.get("time", [])
    pm_daily = daily_air_quality(air.get("hourly", {}))
    hardness, tds = water_lookup.get((city.lower(), state.lower()), default_water_risk(state))
    city_risk_counter: Counter[str] = Counter()
    temp_values = []
    humidity_values = []
    aqi_values = []
    observations = []
    for day_index, date in enumerate(dates):
        temp_max = safe_float(daily.get("temperature_2m_max", [None] * len(dates))[day_index])
        temp_avg = safe_float(daily.get("temperature_2m_mean", [None] * len(dates))[day_index])
        humidity = safe_float(daily.get("relative_humidity_2m_mean", [None] * len(dates))[day_index])
        rainfall = safe_float(daily.get("precipitation_sum", [None] * len(dates))[day_index])
        pm25, pm10 = pm_daily.get(date, (None, None))
        risks = environment_risks(temp_max, humidity, rainfall, pm25, pm10, hardness, city)
        for risk in risks:
            city_risk_counter[risk] += 1
        if temp_avg is not None:
            temp_values.append(temp_avg)
        if humidity is not None:
            humidity_values.append(humidity)
        if pm25 is not None or pm10 is not None:
            aqi_values.append(estimated_aqi(pm25, pm10))
        observations.append(
            {
                "observation_id": f"ENV_API_{idx:03d}_{day_index+1:02d}",
                "date": date,
                "city": city,
                "state": state,
                "latitude": lat,
                "longitude": lon,
                "temperature_max": temp_max,
                "temperature_avg": temp_avg,
                "humidity": humidity,
                "rainfall": rainfall,
                "monsoon_flag": bool(rainfall is not None and rainfall >= 10),
                "heatwave_flag": bool(temp_max is not None and temp_max >= (37 if coastal_city(city) else 40)),
                "aqi": estimated_aqi(pm25, pm10),
                "pm25": pm25,
                "pm10": pm10,
                "water_hardness": hardness,
                "tds": tds,
                "environmental_risk_type": "|".join(risks),
                "source": "Open-Meteo Historical Weather API; Open-Meteo Air Quality API; city/state water-risk lookup based on CGWB/NWDP references",
                "source_api": {"weather": archive_url, "air_quality": air_url},
                "source_date": "2026-06-03",
            }
        )
    top_risks = [risk for risk, _ in city_risk_counter.most_common(5)]
    context = {
        "environment_id": f"ENV_REAL_{idx:03d}",
        "source": "Open-Meteo Historical Weather API; Open-Meteo Air Quality API; CGWB/NWDP referenced water-risk lookup",
        "source_api": {"weather": archive_url, "air_quality": air_url},
        "source_date": "2026-06-03",
        "country": "India",
        "region": state,
        "city": city,
        "climate_zone": infer_climate_zone(top_risks),
        "season": "pre_monsoon_2026",
        "temperature_c": round(sum(temp_values) / len(temp_values), 2) if temp_values else None,
        "humidity_percent": round(sum(humidity_values) / len(humidity_values), 2) if humidity_values else None,
        "aqi": round(sum(aqi_values) / len(aqi_values), 2) if aqi_values else None,
        "water_hardness_level": water_hardness_level(hardness),
        "care_triggers": top_risks,
        "observed_at": NOW,
        "evidence_level": "api_statistical_context",
    }
    return context, observations


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 CareShotARDataCollector/1.0"})
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def daily_air_quality(hourly: dict[str, list[Any]]) -> dict[str, tuple[float | None, float | None]]:
    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"pm25": [], "pm10": []})
    for i, stamp in enumerate(hourly.get("time", [])):
        day = str(stamp).split("T")[0]
        pm25 = safe_float(hourly.get("pm2_5", [None])[i])
        pm10 = safe_float(hourly.get("pm10", [None])[i])
        if pm25 is not None:
            buckets[day]["pm25"].append(pm25)
        if pm10 is not None:
            buckets[day]["pm10"].append(pm10)
    return {
        day: (
            round(sum(values["pm25"]) / len(values["pm25"]), 2) if values["pm25"] else None,
            round(sum(values["pm10"]) / len(values["pm10"]), 2) if values["pm10"] else None,
        )
        for day, values in buckets.items()
    }


def safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def estimated_aqi(pm25: float | None, pm10: float | None) -> float | None:
    values = [v for v in [pm25, pm10] if v is not None]
    if not values:
        return None
    return round(max(values), 2)


def coastal_city(city: str) -> bool:
    return city in {"Chennai", "Mumbai", "Kochi", "Mangalore", "Puducherry", "Visakhapatnam", "Thiruvananthapuram"}


def environment_risks(
    temp_max: float | None,
    humidity: float | None,
    rainfall: float | None,
    pm25: float | None,
    pm10: float | None,
    hardness: float,
    city: str,
) -> list[str]:
    risks = []
    if temp_max is not None and temp_max >= (37 if coastal_city(city) else 40):
        risks.append("heatwave_ac_overload")
    if humidity is not None and humidity >= 70:
        risks.append("humidity_mold_smell")
    if rainfall is not None and rainfall >= 10:
        risks.append("monsoon_moisture")
    if pm25 is not None and pm25 >= 35:
        risks.append("pm25_filter")
    if pm10 is not None and pm10 >= 100:
        risks.append("pm10_dust_filter")
    if hardness >= 300:
        risks.append("hard_water_limescale")
    return risks or ["routine_care"]


def load_water_lookup() -> dict[tuple[str, str], tuple[float, float]]:
    lookup_path = CRAWL_DIR / "환경문제" / "environment_water_risk_lookup.csv"
    lookup = {}
    for row in read_csv(lookup_path):
        city = (row.get("city") or "").lower()
        state = (row.get("state") or "").lower()
        hardness = safe_float(row.get("water_hardness")) or default_water_risk(state)[0]
        tds = safe_float(row.get("tds")) or default_water_risk(state)[1]
        lookup[(city, state)] = (hardness, tds)
    return lookup


def default_water_risk(state: str) -> tuple[float, float]:
    hard_states = {"rajasthan", "gujarat", "delhi", "haryana", "uttar pradesh", "tamil nadu"}
    if state.lower() in hard_states:
        return 360.0, 800.0
    return 190.0, 450.0


def infer_climate_zone(risks: list[str]) -> str:
    risk_set = set(risks)
    if "humidity_mold_smell" in risk_set and "pm25_filter" in risk_set:
        return "humid_polluted"
    if "humidity_mold_smell" in risk_set:
        return "hot_humid"
    if "heatwave_ac_overload" in risk_set:
        return "hot_dry"
    if "hard_water_limescale" in risk_set:
        return "hard_water"
    return "mixed_india"


def water_hardness_level(value: float) -> str:
    if value >= 300:
        return "hard"
    if value >= 150:
        return "moderate"
    return "soft"


def fetch_official_sources() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    official_urls = discover_lg_india_official_urls()
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fetch_one_official_source, idx, entry): idx
            for idx, entry in enumerate(official_urls, start=1)
            if entry["url"].startswith("https://www.lg.com/in/")
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["asset"]["asset_id"])
    manifest = [item["manifest"] for item in results]
    collected_results = [item for item in results if item["manifest"]["collection_status"] == "collected"]
    assets = [item["asset"] for item in collected_results]
    chunks = [chunk for item in collected_results for chunk in item["chunks"]]
    summary = {
        "official_urls_declared": len(official_urls),
        "official_urls_collected": len(collected_results),
        "official_urls_failed": len(results) - len(collected_results),
        "official_assets_exported": len(assets),
        "official_chunks_exported": len(chunks),
        "domain_policy": "Only https://www.lg.com/in/ URLs are allowed.",
    }
    return assets, chunks, {"manifest": manifest, "summary": summary}


def fetch_one_official_source(idx: int, entry: dict[str, Any]) -> dict[str, Any]:
    url = entry["url"]
    asset_id = f"OA_LGIN_{idx:03d}"
    raw_name = f"{asset_id}.html"
    raw_path = OFFICIAL_RAW_DIR / raw_name
    status = "fetch_failed"
    text = ""
    title = ""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36 CareShotARDataCollector/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-IN,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read()
        raw_path.write_bytes(body)
        decoded = body.decode("utf-8", errors="ignore")
        extracted = extract_official_content(decoded)
        text = extracted["text"]
        title = extracted["title"] or text.split("\n")[0][:120] or url
        status = "collected"
    except Exception as exc:
        raw_path.write_text(f"FETCH_FAILED\n{url}\n{type(exc).__name__}: {exc}", encoding="utf-8")
        title = url
    asset = {
        "asset_id": asset_id,
        "asset_type": entry["asset_type"],
        "product_type": entry["product_type"],
        "model_name": entry.get("model_name"),
        "title": title,
        "source_url": url,
        "source_date": "2026-06-03",
        "applicability_scope": "exact_model" if entry.get("model_name") else "product_type_common",
        "matched_model_names": [entry["model_name"]] if entry.get("model_name") else [],
        "matched_aliases": [],
        "matched_series": None,
        "available_procedures": [entry["procedure_type"]],
        "forbidden_actions": forbidden_actions(entry["product_type"]),
        "verification_status": "collected_official_lg_india" if status == "collected" else "fetch_failed",
        "last_checked_at": NOW,
        "raw_file": str(raw_path.relative_to(PROJECT_DIR)),
    }
    chunks = []
    for chunk_index, chunk_text in enumerate(make_chunks(text), start=1):
        chunks.append(
            {
                "chunk_id": f"CHUNK_LGIN_{idx:03d}_{chunk_index:03d}",
                "asset_id": asset_id,
                "product_type": entry["product_type"],
                "model_name": entry.get("model_name"),
                "procedure_type": entry["procedure_type"],
                "language": "en",
                "chunk_title": title,
                "chunk_text": chunk_text,
                "source_url": url,
                "source_section": "json_ld_article_body_or_meta_description",
                "source_raw_file": str(raw_path.relative_to(PROJECT_DIR)),
                "applicability_scope": "exact_model" if entry.get("model_name") else "product_type_common",
                "forbidden_actions": forbidden_actions(entry["product_type"]),
                "safety_tags": [],
                "embedding_status": "not_embedded",
                "verification_status": "collected_official_lg_india",
                "last_checked_at": NOW,
                "created_at": NOW,
            }
        )
    return {
        "manifest": {
            "asset_id": asset_id,
            "url": url,
            "raw_file": str(raw_path.relative_to(PROJECT_DIR)),
            "official_domain": "lg.com/in",
            "collection_status": status,
            "collected_at": NOW,
            **entry,
        },
        "asset": asset,
        "chunks": chunks,
    }


def discover_lg_india_official_urls() -> list[dict[str, Any]]:
    entries = list(LG_INDIA_OFFICIAL_URLS)
    seen = {entry["url"] for entry in entries}
    sitemap_url = "https://www.lg.com/in/sitemap.xml"
    try:
        req = urllib.request.Request(sitemap_url, headers={"User-Agent": "Mozilla/5.0 CareShotARDataCollector/1.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            sitemap = response.read().decode("utf-8", errors="ignore")
        urls = re.findall(r"<loc>(.*?)</loc>", sitemap)
    except Exception:
        urls = []

    buckets = [
        ("air_conditioner", "/air-conditioners/", 45),
        ("washing_machine", "/laundry/", 45),
        ("air_purifier", "/air-care/air-purifiers/", 15),
        ("air_purifier", "/care-accessories/air-purifiers/", 10),
        ("water_purifier", "/water-purifiers/", 35),
    ]
    for product_type, marker, limit in buckets:
        count = 0
        for url in urls:
            if count >= limit:
                break
            if marker not in url:
                continue
            if any(blocked in url for blocked in ["/business/", "/about-lg/", "/press-and-media/"]):
                continue
            if not url.startswith("https://www.lg.com/in/") or url in seen:
                continue
            if url.rstrip("/").count("/") < 5:
                continue
            model_name = url.rstrip("/").split("/")[-1].upper()
            entries.append(
                {
                    "url": url,
                    "product_type": product_type,
                    "procedure_type": "product_page",
                    "asset_type": "product_page",
                    "model_name": model_name,
                    "discovered_from": sitemap_url,
                }
            )
            seen.add(url)
            count += 1
    return entries[:150]


def html_to_text(source: str) -> str:
    source = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", source)
    source = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>|</h[1-6]>", "\n", source)
    source = re.sub(r"(?is)<[^>]+>", " ", source)
    source = html.unescape(source)
    lines = [re.sub(r"\s+", " ", line).strip() for line in source.splitlines()]
    lines = [line for line in lines if len(line) > 20]
    return "\n".join(lines)


def extract_official_content(source: str) -> dict[str, str]:
    title = extract_title(source)
    description = extract_meta_description(source)
    article_bodies, json_ld_descriptions = extract_json_ld_content(source)
    content_parts = [title, description]
    if article_bodies:
        content_parts.extend(article_bodies)
    else:
        content_parts.extend(json_ld_descriptions)
    text = clean_official_text(" ".join(part for part in content_parts if part))
    if len(text) < 120:
        text = clean_official_text("\n".join([title, description, html_to_text(source)]))
    return {
        "title": title,
        "description": description,
        "text": text,
    }


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


def extract_json_ld_content(source: str) -> tuple[list[str], list[str]]:
    article_bodies = []
    descriptions = []
    for match in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', source):
        raw = html.unescape(match.group(1)).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in walk_json_ld(data):
            if not isinstance(node, dict):
                continue
            article_body = norm_text(node.get("articleBody"))
            if article_body:
                article_bodies.append(article_body)
            for key in ["headline", "name", "description"]:
                value = norm_text(node.get(key))
                if value:
                    descriptions.append(value)
    return unique_texts(article_bodies), unique_texts(descriptions)


def walk_json_ld(value: Any) -> list[Any]:
    nodes = []
    if isinstance(value, dict):
        nodes.append(value)
        for child in value.values():
            nodes.extend(walk_json_ld(child))
    elif isinstance(value, list):
        for item in value:
            nodes.extend(walk_json_ld(item))
    return nodes


def unique_texts(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value[:300].lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


BOILERPLATE_LINE_PATTERNS = [
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
]


def clean_official_text(value: str) -> str:
    text = norm_text(value)
    text = text.replace("\\u0026", "&")
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+|(?<=\))\s+", text)
    cleaned = []
    for sentence in sentences:
        sentence = norm_text(sentence)
        if len(sentence) < 12:
            continue
        lower = sentence.lower()
        if any(pattern in lower for pattern in BOILERPLATE_LINE_PATTERNS):
            continue
        cleaned.append(sentence)
    return " ".join(cleaned)


def extract_title(source: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", source)
    if match:
        return norm_text(match.group(1))
    return ""


def make_chunks(text: str) -> list[str]:
    if not text:
        return []
    lines = [line for line in text.splitlines() if len(line) > 40]
    chunks = []
    buffer = []
    length = 0
    for line in lines:
        buffer.append(line)
        length += len(line)
        if length >= 900:
            chunks.append(" ".join(buffer)[:1400])
            buffer = []
            length = 0
    if buffer:
        chunks.append(" ".join(buffer)[:1400])
    return chunks[:20]


def forbidden_actions(product_type: str) -> list[str]:
    common = ["electrical_repair", "pcb_repair", "internal_disassembly"]
    if product_type == "air_conditioner":
        return common + ["refrigerant_handling", "compressor_repair", "gas_leak_handling"]
    if product_type == "washing_machine":
        return common + ["motor_repair", "drain_pump_disassembly"]
    if product_type == "air_purifier":
        return common + ["sensor_board_repair", "fan_motor_repair"]
    if product_type == "water_purifier":
        return common + ["internal_water_line_opening", "internal_tank_descaling"]
    return common + ["refrigerant_handling", "gas_leak_handling"]


def build_profiles_devices_logs(
    voc_cases: list[dict[str, Any]], contexts: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    languages = [
        ("en", "English"),
        ("hi", "Hindi"),
        ("ta", "Tamil"),
        ("mr", "Marathi"),
        ("bn", "Bengali"),
        ("te", "Telugu"),
    ]
    users = []
    devices = []
    logs = []
    diagnoses = []
    model_catalog = {
        "air_conditioner": ["AS-Q24ENXE", "PS-Q19ENZE", "US-Q18CNXE", "RS-Q19MWZE", "TS-Q24HNXE"],
        "washing_machine": ["FHV1409Z2M", "T70SKSF1Z", "FHM1207SDM", "THD18STB", "P8035SGMZ"],
        "air_purifier": ["AS60GHWG0", "AS65GDWH0", "FS10GPBK0", "AS95GDWV0", "AM50GYWN2"],
        "water_purifier": ["WW176EP", "WW184EPB", "WW151NP", "WW140NP", "WW130NP"],
    }
    risks = ["none", "low", "medium", "high"]
    dt = datetime(2026, 6, 3, 9, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    for i in range(120):
        ctx = contexts[i % len(contexts)] if contexts else {"region": "Delhi", "city": "New Delhi", "care_triggers": []}
        lang, label = languages[i % len(languages)]
        users.append(
            {
                "user_id": f"U{i+1:03d}",
                "customer_name": f"Evidence User {i+1:03d}",
                "country": "India",
                "region": ctx["region"],
                "city": ctx["city"],
                "preferred_language": lang,
                "preferred_language_label": label,
                "video_style": "ar_step_by_step" if i % 2 == 0 else "short_guided",
                "timezone": "Asia/Kolkata",
                "thinq_account_status": "mock_active",
                "service_access_profile": "delayed_service_region" if i % 5 == 0 else "standard",
                "scenario_basis": "Generated from crawled India VOC cases and environment source contexts.",
                "pain_tags": voc_cases[i % len(voc_cases)]["pain_tags"] if voc_cases else [],
                "evidence_case_ids": [voc_cases[i % len(voc_cases)]["voc_case_id"]] if voc_cases else [],
                "evidence_level": "evidence_based_synthetic",
                "created_at": NOW,
                "updated_at": NOW,
            }
        )
    device_index = 0
    for user in users:
        for offset in range(2):
            product_type = PRODUCT_TYPES[device_index % len(PRODUCT_TYPES)]
            model = model_catalog[product_type][device_index % len(model_catalog[product_type])]
            ctx = contexts[device_index % len(contexts)] if contexts else {"region": user["region"], "city": user["city"]}
            device_id = f"D{device_index+1:03d}"
            devices.append(
                {
                    "device_id": device_id,
                    "user_id": user["user_id"],
                    "source": "thinq_mock_evidence_based",
                    "product_type": product_type,
                    "product_type_label": product_type.replace("_", " ").title(),
                    "model_name": model,
                    "model_aliases": [model.replace("-", ""), f"{model}.IN"],
                    "series": re.sub(r"[^A-Z0-9].*", "", model) or model[:4],
                    "display_name": f"{product_type.replace('_', ' ').title()} {model}",
                    "country": "India",
                    "region": ctx["region"],
                    "city": ctx["city"],
                    "registered_at": "2025-01-01T09:00:00+05:30",
                    "current_status": {"power": "off", "connectivity": "online"},
                    "scenario_basis": "Evidence-based synthetic ThinQ device generated after VOC/environment grounding.",
                    "pain_tags": user["pain_tags"],
                    "evidence_case_ids": user["evidence_case_ids"],
                    "evidence_level": "evidence_based_synthetic",
                }
            )
            device_index += 1
    for i, device in enumerate(devices):
        ctx = contexts[i % len(contexts)] if contexts else {"care_triggers": []}
        for j in range(3):
            log_id = f"UL{i*3+j+1:04d}"
            triggers = list(dict.fromkeys((ctx.get("care_triggers") or []) + device.get("pain_tags", [])))[:5]
            daily_runtime_hours = round(1.5 + (i + j) % 8 * 0.75, 2)
            if device["product_type"] == "air_conditioner":
                # India summer demo assumption: AC homes often concentrate usage in evening/sleep hours.
                daily_runtime_hours = [6.0, 5.0, 7.0, 8.0][(i + j) % 4]
            logs.append(
                {
                    "usage_log_id": log_id,
                    "device_id": device["device_id"],
                    "user_id": device["user_id"],
                    "product_type": device["product_type"],
                    "model_name": device["model_name"],
                    "usage_summary": {
                        "daily_runtime_hours": daily_runtime_hours,
                        "days_since_last_care": 15 + ((i * 7 + j * 11) % 160),
                        "cycle_count": 5 + ((i + j) % 90),
                    },
                    "care_triggers": triggers,
                    "scenario_basis": "Generated from environment risk and VOC pain tags.",
                    "evidence_case_ids": device.get("evidence_case_ids", []),
                    "evidence_level": "evidence_based_synthetic",
                    "updated_at": (dt - timedelta(days=j)).isoformat(),
                }
            )
    for i, device in enumerate(devices):
        for j in range(2):
            severity = risks[(i + j) % len(risks)]
            voc = voc_cases[(i * 2 + j) % len(voc_cases)] if voc_cases else {}
            tags = voc.get("pain_tags", device.get("pain_tags", []))
            diagnoses.append(
                {
                    "diagnosis_id": f"SD{i*2+j+1:04d}",
                    "device_id": device["device_id"],
                    "user_id": device["user_id"],
                    "product_type": device["product_type"],
                    "model_name": device["model_name"],
                    "result_code": result_code(device["product_type"], severity, tags),
                    "severity": severity,
                    "summary": f"{severity} diagnostic scenario based on VOC tags: {', '.join(tags[:3])}",
                    "detected_signals": tags,
                    "scenario_basis": "Generated from crawled VOC pain tags and ThinQ-like severity distribution.",
                    "evidence_case_ids": [voc.get("voc_case_id")] if voc.get("voc_case_id") else [],
                    "evidence_level": "evidence_based_synthetic",
                    "created_at": (dt - timedelta(hours=i + j)).isoformat(),
                }
            )
    return users, devices, logs, diagnoses


def result_code(product_type: str, severity: str, tags: list[str]) -> str:
    if severity == "none":
        return "NORMAL"
    tag = tags[0] if tags else "general"
    return f"{product_type.upper()}_{severity.upper()}_{tag.upper()[:18]}"


def main() -> None:
    ensure_dirs()
    voc_cases, voc_summary = collect_voc_cases()
    contexts, observations, env_summary = build_environment_contexts()
    official_assets, official_chunks, official_meta = fetch_official_sources()
    users, devices, logs, diagnoses = build_profiles_devices_logs(voc_cases, contexts)
    intent_cases = build_intent_cases(voc_cases)

    write_jsonl(VOC_DIR / "raw_voc_cases.jsonl", voc_cases)
    write_json(VOC_DIR / "voc_source_inventory.json", voc_summary)
    write_jsonl(ENV_DIR / "raw_environment_observations.jsonl", observations)
    write_json(ENV_DIR / "environment_source_summary.json", env_summary)
    write_json(OFFICIAL_DIR / "official_lg_india_source_manifest.json", official_meta["manifest"])
    write_json(OFFICIAL_DIR / "official_lg_india_collection_summary.json", official_meta["summary"])

    write_json(MOCK_DIR / "user_profiles.json", users)
    write_json(MOCK_DIR / "thinq_registered_devices.json", devices)
    write_json(MOCK_DIR / "usage_logs.json", logs)
    write_json(MOCK_DIR / "smart_diagnosis_results.json", diagnoses)
    write_json(MOCK_DIR / "india_environment_contexts.json", contexts)
    write_json(MOCK_DIR / "intent_risk_test_cases.json", intent_cases)
    write_json(MOCK_DIR / "official_assets_db.json", official_assets)
    write_json(MOCK_DIR / "official_document_chunks.json", official_chunks)

    summary = {
        "voc": {k: (dict(v) if isinstance(v, Counter) else v) for k, v in voc_summary.items() if k != "inventory"},
        "environment": env_summary,
        "official": official_meta["summary"],
        "mock_counts": {
            "user_profiles": len(users),
            "thinq_registered_devices": len(devices),
            "usage_logs": len(logs),
            "smart_diagnosis_results": len(diagnoses),
            "india_environment_contexts": len(contexts),
            "intent_risk_test_cases": len(intent_cases),
            "official_assets_db": len(official_assets),
            "official_document_chunks": len(official_chunks),
        },
    }
    write_json(SOURCE_DIR / "evidence_based_data_build_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
