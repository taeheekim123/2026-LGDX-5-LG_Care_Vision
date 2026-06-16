from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests


CATEGORIES = [
    ("keyboard", "Category:Computer keyboards"),
    ("mobile_phone", "Category:Mobile phones"),
    ("laptop", "Category:Laptop computers"),
    ("remote_control", "Category:Remote controls"),
    ("window_blinds", "Category:Window blinds"),
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "CareShotARHardNegativeCollector/1.0 (local research dataset)"


def safe_suffix(url: str) -> str:
    path = url.split("?", 1)[0].lower()
    for suffix in IMAGE_EXTENSIONS:
        if path.endswith(suffix):
            return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


def commons_category_files(category: str, limit: int) -> list[str]:
    titles: list[str] = []
    cmcontinue: str | None = None
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    while len(titles) < limit:
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "file",
            "cmlimit": min(50, limit - len(titles)),
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        data = session.get(COMMONS_API, params=params, timeout=30).json()
        members = data.get("query", {}).get("categorymembers", [])
        titles.extend(member["title"] for member in members if member.get("title", "").startswith("File:"))
        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break
    return titles[:limit]


def image_info(titles: list[str]) -> list[dict[str, str]]:
    if not titles:
        return []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    results: list[dict[str, str]] = []
    for index in range(0, len(titles), 50):
        chunk = titles[index : index + 50]
        params = {
            "action": "query",
            "format": "json",
            "titles": "|".join(chunk),
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": "960",
        }
        data = session.get(COMMONS_API, params=params, timeout=30).json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            infos = page.get("imageinfo") or []
            if not infos:
                continue
            info = infos[0]
            mime = info.get("mime", "")
            if not mime.startswith("image/"):
                continue
            url = info.get("thumburl") or info.get("url")
            if not url:
                continue
            results.append(
                {
                    "title": page.get("title", ""),
                    "url": url,
                    "description_url": info.get("descriptionurl", ""),
                    "mime": mime,
                    "license": (
                        info.get("extmetadata", {})
                        .get("LicenseShortName", {})
                        .get("value", "")
                    ),
                }
            )
    return results


def download_image(url: str, target: Path) -> tuple[bool, str]:
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            return False, f"not_image:{content_type}"
        target.write_bytes(response.content)
        return True, hashlib.sha256(response.content).hexdigest()
    except Exception as exc:  # pragma: no cover - network guard
        return False, f"{type(exc).__name__}:{exc}"


def main() -> int:
    dataset_root = Path(__file__).resolve().parents[1]
    default_output = dataset_root / "10_원천이미지_raw" / "90_하드네거티브_공개이미지_20260616"
    default_manifest = dataset_root / "02_매니페스트_CSV" / "hard_negative_public_images_20260616_manifest.csv"
    parser = argparse.ArgumentParser(description="Collect public hard-negative images from Wikimedia Commons.")
    parser.add_argument("--output-dir", type=Path, default=default_output)
    parser.add_argument("--manifest", type=Path, default=default_manifest)
    parser.add_argument("--target-count", type=int, default=80)
    parser.add_argument("--per-category", type=int, default=35)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    manifest_path = args.manifest.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    if args.force:
        for existing in output_dir.iterdir():
            if existing.is_file() and existing.suffix.lower() in IMAGE_EXTENSIONS:
                existing.unlink()

    rows: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    category_index = 0
    for category_slug, category in CATEGORIES:
        if len(rows) >= args.target_count:
            break
        titles = commons_category_files(category, args.per_category)
        for info in image_info(titles):
            if len(rows) >= args.target_count:
                break
            url = info["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            category_index += 1
            suffix = safe_suffix(url)
            filename = f"hardneg_{category_slug}_{category_index:04d}{suffix}"
            target = output_dir / filename
            if target.exists() and not args.force:
                continue
            ok, status = download_image(url, target)
            rows.append(
                {
                    "filename": filename,
                    "category": category_slug,
                    "source_category": category,
                    "source_title": info["title"],
                    "source_url": info["description_url"],
                    "download_url": url,
                    "license": info.get("license", ""),
                    "status": "downloaded" if ok else "failed",
                    "sha256_or_error": status,
                    "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            )
            time.sleep(0.1)

    with manifest_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[
                "filename",
                "category",
                "source_category",
                "source_title",
                "source_url",
                "download_url",
                "license",
                "status",
                "sha256_or_error",
                "collected_at_utc",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "target_count": args.target_count,
        "downloaded": len([row for row in rows if row["status"] == "downloaded"]),
        "failed": len([row for row in rows if row["status"] == "failed"]),
        "categories": [slug for slug, _ in CATEGORIES],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["downloaded"] >= min(args.target_count, 50) else 1


if __name__ == "__main__":
    raise SystemExit(main())
