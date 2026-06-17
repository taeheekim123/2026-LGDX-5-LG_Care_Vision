from __future__ import annotations

import csv
import hashlib
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw


DATASET_SLUG = "lg_wall_mounted_filter_real_photo_candidates"

SOURCE_PAGES = [
    {
        "source_id": "lg_official_kr_wall_filter_support",
        "url": "https://www.lge.co.kr/support/solutions-20150297260085",
        "source_type": "lg_official_support_public_page",
        "license_status": "official_public_support_candidate_not_explicit_training_license",
    },
    {
        "source_id": "lg_official_us_wall_filter_support",
        "url": "https://www.lg.com/us/support/help-library/lg-airconditioner-filter-how-to-clean-and-replace-airconditioner-filter--20154844424480",
        "source_type": "lg_official_support_public_page",
        "license_status": "official_public_support_candidate_not_explicit_training_license",
    },
    {
        "source_id": "fooland_lg_dual_inverter_wall_disassembly",
        "url": "https://fooland.tistory.com/entry/LG-%EB%B2%BD%EA%B1%B8%EC%9D%B4%EC%97%90%EC%96%B4%EC%BB%A8-%EC%B2%AD%EC%86%8C",
        "source_type": "public_blog_wall_mounted_lg_photo_candidate",
        "license_status": "unknown_verify_before_training",
    },
    {
        "source_id": "fooland_lg_2013_wall_disassembly",
        "url": "https://fooland.tistory.com/entry/%EC%97%98%EC%A7%80-%EC%97%90%EC%96%B4%EC%BB%A8-%EC%B2%AD%EC%86%8C",
        "source_type": "public_blog_wall_mounted_lg_photo_candidate",
        "license_status": "unknown_verify_before_training",
    },
    {
        "source_id": "lgesy_wall_filter_faq",
        "url": "https://lgesy.com/article/%EC%9E%90%EC%A3%BC%EB%AC%BB%EB%8A%94%EC%A7%88%EB%AC%B8-faq/3/73/",
        "source_type": "public_support_partner_page_candidate",
        "license_status": "unknown_verify_before_training",
    },
    {
        "source_id": "kingtip_lg_filter_cleaning",
        "url": "https://kingtip0206.tistory.com/entry/LG-%EC%97%98%EC%A7%80-%EC%97%90%EC%96%B4%EC%BB%A8-%ED%95%84%ED%84%B0%EC%B2%AD%EC%86%8C-thinQ-%ED%95%84%ED%84%B0%EA%B4%80%EB%A6%AC-%EC%8A%A4%EB%A7%88%ED%8A%B8%EC%A7%84%EB%8B%A8-%EC%85%80%ED%94%84%EC%A7%84%EB%8B%A8-%EC%96%B4%ED%94%8C-%EC%82%AC%EC%9A%A9%EB%B2%95",
        "source_type": "public_blog_wall_mounted_lg_photo_candidate",
        "license_status": "unknown_verify_before_training",
    },
    {
        "source_id": "lg_eastafrica_filter_blog",
        "url": "https://www.lg.com/eastafrica/b2c/blog-list/how-to-clean-your-air-conditioner-filter",
        "source_type": "lg_official_blog_public_page",
        "license_status": "official_public_support_candidate_not_explicit_training_license",
    },
    {
        "source_id": "lg_sa_clean_air_conditioner",
        "url": "https://www.lg.com/sa_en/lg-story/helpful-guide/how-to-clean-your-air-conditioner/",
        "source_type": "lg_official_blog_public_page",
        "license_status": "official_public_support_candidate_not_explicit_training_license",
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_urls_from_page(html: str, base_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[tuple[str, str]] = []

    for tag in soup.find_all(["img", "source"]):
        alt = tag.get("alt") or tag.get("title") or ""
        attrs = ["src", "data-src", "data-original", "data-lazy-src", "content"]
        for attr in attrs:
            value = tag.get(attr)
            if value:
                urls.append((urljoin(base_url, value.strip()), alt))
        srcset = tag.get("srcset") or tag.get("data-srcset")
        if srcset:
            for item in srcset.split(","):
                candidate = item.strip().split(" ")[0]
                if candidate:
                    urls.append((urljoin(base_url, candidate), alt))

    for tag in soup.find_all("meta"):
        if tag.get("property") in {"og:image", "twitter:image"} and tag.get("content"):
            urls.append((urljoin(base_url, tag["content"].strip()), tag.get("property") or ""))

    seen = set()
    deduped = []
    for url, alt in urls:
        if not url.lower().startswith(("http://", "https://")):
            continue
        if url in seen:
            continue
        seen.add(url)
        deduped.append((url, alt))
    return deduped


def clean_suffix(url: str, content_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    return ".jpg"


def save_contact_sheet(files: list[Path], out_path: Path) -> None:
    thumb_w, thumb_h, label_h, cols = 180, 135, 34, 5
    rows = max(1, (len(files) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(files):
        row, col = divmod(i, cols)
        x, y = col * thumb_w, row * (thumb_h + label_h)
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((thumb_w, thumb_h))
            sheet.paste(img, (x + (thumb_w - img.width) // 2, y + (thumb_h - img.height) // 2))
        except Exception as exc:
            draw.text((x + 4, y + 4), f"ERR {exc}"[:40], fill=(255, 0, 0))
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + label_h), outline=(180, 180, 180), fill=(245, 245, 245))
        draw.text((x + 4, y + thumb_h + 4), f"{i + 1:03d} {path.name[:28]}", fill=(0, 0, 0))
    sheet.save(out_path, quality=90)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python collect_wall_mounted_filter_candidates.py <dataset_root>")
        return 2

    dataset_root = Path(sys.argv[1]).resolve()
    raw_out = dataset_root / "10_원천이미지_raw" / "10_웹크롤링후보" / DATASET_SLUG
    candidate_out = dataset_root / "10_원천이미지_raw" / "20_학습후보" / DATASET_SLUG
    raw_out.mkdir(parents=True, exist_ok=True)
    candidate_out.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }
    )

    rows: list[dict[str, str]] = []
    seen_hashes: set[str] = set()
    idx = 1

    existing_manifest = dataset_root / "lg_filter_round3_product_and_guides_manifest.csv"
    if existing_manifest.exists():
        with existing_manifest.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rel = row.get("relative_path") or row.get("path") or row.get("source_rel_to_copy") or ""
                source_path = dataset_root / rel
                if not source_path.exists() and row.get("local_path"):
                    source_path = Path(row["local_path"])
                name = source_path.name.lower()
                # Contact-sheet reviewed range: old wall-mounted actual photos start at round3_102.
                if not source_path.exists() or not name.startswith("round3_"):
                    continue
                try:
                    num = int(name.split("_")[1])
                except Exception:
                    continue
                if not (102 <= num <= 145):
                    continue
                try:
                    digest = sha256_file(source_path)
                    if digest in seen_hashes:
                        continue
                    seen_hashes.add(digest)
                    suffix = source_path.suffix.lower()
                    dest = candidate_out / f"wall_filter_candidate_{idx:03d}{suffix}"
                    shutil.copy2(source_path, dest)
                    rows.append(
                        {
                            "candidate_relative_path": str(dest.relative_to(dataset_root)).replace("\\", "/"),
                            "candidate_index": str(idx),
                            "source_page": row.get("source_page", ""),
                            "url": row.get("url", ""),
                            "alt": row.get("alt", ""),
                            "sha256": digest,
                            "bytes": str(dest.stat().st_size),
                            "source_type": "existing_round3_wall_mounted_actual_photo_candidate",
                            "license_status": row.get("license_status", "unknown_verify_before_training"),
                            "appliance_form": "wall_mounted",
                            "target_class": "filter",
                            "label_status": "needs_human_filter_bbox_labeling",
                            "visual_review_status": "candidate_wall_mounted_photo_review_needed",
                            "notes": "Copied from prior round3 contact-sheet wall-mounted actual-photo range; remove if filter is not visible.",
                        }
                    )
                    idx += 1
                except Exception as exc:
                    print(f"existing copy failed {source_path}: {exc}")

    for source in SOURCE_PAGES:
        try:
            page = session.get(source["url"], timeout=25)
            page.raise_for_status()
            urls = image_urls_from_page(page.text, source["url"])
        except Exception as exc:
            print(f"page failed {source['source_id']}: {exc}")
            continue

        for image_url, alt in urls:
            if any(skip in image_url.lower() for skip in ["logo", "favicon", "sprite", "icon", "banner"]):
                continue
            try:
                resp = session.get(image_url, timeout=25)
                if resp.status_code >= 400:
                    continue
                content_type = resp.headers.get("Content-Type", "")
                if "image" not in content_type and not Path(urlparse(image_url).path).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    continue
                suffix = clean_suffix(image_url, content_type)
                temp = raw_out / f"{source['source_id']}_{idx:03d}{suffix}"
                temp.write_bytes(resp.content)
                try:
                    with Image.open(temp) as img:
                        width, height = img.size
                        if width < 180 or height < 120:
                            temp.unlink(missing_ok=True)
                            continue
                        img.verify()
                except Exception:
                    temp.unlink(missing_ok=True)
                    continue
                digest = sha256_file(temp)
                if digest in seen_hashes:
                    temp.unlink(missing_ok=True)
                    continue
                seen_hashes.add(digest)
                dest = candidate_out / f"wall_filter_candidate_{idx:03d}{suffix}"
                shutil.copy2(temp, dest)
                rows.append(
                    {
                        "candidate_relative_path": str(dest.relative_to(dataset_root)).replace("\\", "/"),
                        "candidate_index": str(idx),
                        "source_page": source["url"],
                        "url": image_url,
                        "alt": alt,
                        "sha256": digest,
                        "bytes": str(dest.stat().st_size),
                        "source_type": source["source_type"],
                        "license_status": source["license_status"],
                        "appliance_form": "wall_mounted_candidate",
                        "target_class": "filter",
                        "label_status": "needs_human_filter_bbox_labeling",
                        "visual_review_status": "candidate_review_needed",
                        "notes": "Crawled candidate; keep only if actual wall-mounted LG indoor unit and filter/filter slot is visible.",
                    }
                )
                idx += 1
                time.sleep(0.15)
            except Exception as exc:
                print(f"image failed {image_url}: {exc}")

    manifest_path = dataset_root / f"{DATASET_SLUG}_manifest.csv"
    fieldnames = [
        "candidate_relative_path",
        "candidate_index",
        "source_page",
        "url",
        "alt",
        "sha256",
        "bytes",
        "source_type",
        "license_status",
        "appliance_form",
        "target_class",
        "label_status",
        "visual_review_status",
        "notes",
    ]
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    files = sorted(candidate_out.iterdir())
    save_contact_sheet(files, dataset_root / f"{DATASET_SLUG}_contact_sheet.jpg")
    print(f"candidate_count={len(files)}")
    print(f"manifest={manifest_path}")
    print(f"candidate_dir={candidate_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
