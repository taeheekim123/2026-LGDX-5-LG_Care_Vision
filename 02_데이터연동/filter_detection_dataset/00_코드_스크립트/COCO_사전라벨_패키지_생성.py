from __future__ import annotations

import csv
import json
import argparse
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw


DEFAULT_SOURCE_SLUG = "lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2"
DEFAULT_OUT_SLUG = "lg_wall_mounted_filter_user_primary_099_prelabel_refined_v2_coco"


def risk_score(row: dict[str, str]) -> tuple[int, list[str]]:
    width = int(row["width"])
    height = int(row["height"])
    x1 = int(row["x1"])
    y1 = int(row["y1"])
    x2 = int(row["x2"])
    y2 = int(row["y2"])
    bbox_w = max(1, x2 - x1)
    bbox_h = max(1, y2 - y1)
    area_ratio = (bbox_w * bbox_h) / max(1, width * height)
    aspect = bbox_w / bbox_h

    score = 0
    reasons: list[str] = []
    if x1 <= 2 or y1 <= 2 or x2 >= width - 2 or y2 >= height - 2:
        score += 3
        reasons.append("touches_image_edge")
    if area_ratio > 0.45:
        score += 4
        reasons.append("bbox_too_large")
    elif area_ratio > 0.30:
        score += 2
        reasons.append("bbox_large")
    if area_ratio < 0.03:
        score += 3
        reasons.append("bbox_too_small")
    if aspect > 8 or aspect < 1.1:
        score += 2
        reasons.append("odd_aspect_ratio")
    if row.get("method") == "fallback_broad_center":
        score += 3
        reasons.append("fallback_bbox")
    if y1 < height * 0.02:
        score += 1
        reasons.append("starts_near_top")
    if not reasons:
        reasons.append("normal_review")
    return score, reasons


def save_priority_contact_sheet(rows: list[dict[str, str]], images_dir: Path, out_path: Path) -> None:
    selected = rows[:40]
    thumb_w, thumb_h, label_h, cols = 240, 170, 44, 4
    rows_count = max(1, (len(selected) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows_count * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)

    for index, row in enumerate(selected):
        image_path = images_dir / row["image_name"]
        grid_y, grid_x = divmod(index, cols)
        x0 = grid_x * thumb_w
        y0 = grid_y * (thumb_h + label_h)
        try:
            image = Image.open(image_path).convert("RGB")
            original_w, original_h = image.size
            image.thumbnail((thumb_w, thumb_h))
            paste_x = x0 + (thumb_w - image.width) // 2
            paste_y = y0 + (thumb_h - image.height) // 2
            sheet.paste(image, (paste_x, paste_y))
            sx = image.width / original_w
            sy = image.height / original_h
            bx1 = int(row["x1"]) * sx
            by1 = int(row["y1"]) * sy
            bx2 = int(row["x2"]) * sx
            by2 = int(row["y2"]) * sy
            draw.rectangle((paste_x + bx1, paste_y + by1, paste_x + bx2, paste_y + by2), outline=(255, 0, 0), width=3)
        except Exception as exc:
            draw.text((x0 + 4, y0 + 4), f"ERR {exc}"[:45], fill=(255, 0, 0))

        draw.rectangle((x0, y0 + thumb_h, x0 + thumb_w, y0 + thumb_h + label_h), fill=(245, 245, 245), outline=(180, 180, 180))
        label = f"{int(row['review_priority']):02d} {row['image_name'][:24]}"
        reason = row["review_reasons"][:32]
        draw.text((x0 + 4, y0 + thumb_h + 4), label, fill=(0, 0, 0))
        draw.text((x0 + 4, y0 + thumb_h + 22), reason, fill=(120, 0, 0))

    sheet.save(out_path, quality=92)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a COCO Roboflow fallback package from pre-labels.")
    parser.add_argument("--source-slug", default=DEFAULT_SOURCE_SLUG)
    parser.add_argument("--out-slug", default=DEFAULT_OUT_SLUG)
    args = parser.parse_args()

    dataset_root = Path(__file__).resolve().parents[1]
    source_root = dataset_root / "20_Roboflow_업로드패키지" / args.source_slug
    out_root = dataset_root / "20_Roboflow_업로드패키지" / args.out_slug
    out_images = out_root / "images"
    images_dir = source_root / "images"
    manifest_path = source_root / "prelabel_manifest.csv"

    if out_root.exists():
        shutil.rmtree(out_root)
    out_images.mkdir(parents=True, exist_ok=True)

    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    images = []
    annotations = []
    review_rows: list[dict[str, str]] = []
    for image_id, row in enumerate(rows, 1):
        image_name = row["image_name"]
        width = int(row["width"])
        height = int(row["height"])
        x1 = int(row["x1"])
        y1 = int(row["y1"])
        x2 = int(row["x2"])
        y2 = int(row["y2"])
        bbox_w = max(1, x2 - x1)
        bbox_h = max(1, y2 - y1)

        shutil.copy2(images_dir / image_name, out_images / image_name)
        images.append({"id": image_id, "file_name": image_name, "width": width, "height": height})
        annotations.append(
            {
                "id": image_id,
                "image_id": image_id,
                "category_id": 1,
                "bbox": [x1, y1, bbox_w, bbox_h],
                "area": bbox_w * bbox_h,
                "iscrowd": 0,
            }
        )

        score, reasons = risk_score(row)
        review_row = dict(row)
        review_row["bbox_area_ratio"] = f"{(bbox_w * bbox_h) / max(1, width * height):.4f}"
        review_row["bbox_aspect_ratio"] = f"{bbox_w / bbox_h:.3f}"
        review_row["review_priority"] = str(score)
        review_row["review_reasons"] = "|".join(reasons)
        review_rows.append(review_row)

    coco = {
        "info": {
            "description": f"LG wall-mounted AC filter heuristic pre-labels from {args.source_slug}; must be reviewed before training.",
            "version": "2026-06-15-review-only",
        },
        "licenses": [],
        "categories": [{"id": 1, "name": "filter", "supercategory": "air_conditioner_part"}],
        "images": images,
        "annotations": annotations,
    }
    annotations_path = out_root / "_annotations.coco.json"
    annotations_path.write_text(json.dumps(coco, indent=2, ensure_ascii=False), encoding="utf-8")

    review_rows.sort(key=lambda item: int(item["review_priority"]), reverse=True)
    priority_csv = out_root / "bbox_review_priority.csv"
    with priority_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = list(review_rows[0].keys()) if review_rows else ["image_name"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(review_rows)

    contact_sheet = out_root / "bbox_review_priority_top40.jpg"
    save_priority_contact_sheet(review_rows, images_dir, contact_sheet)

    readme = out_root / "README.md"
    readme.write_text(
        f"# {args.out_slug}\n\n"
        "COCO-format Roboflow import fallback for the same heuristic pre-labels.\n"
        "These annotations are not final ground truth. Review every bbox in Roboflow before training.\n\n"
        "Files:\n"
        "- images/: 99 images\n"
        "- _annotations.coco.json: COCO annotations for class filter\n"
        "- bbox_review_priority.csv: suspicious bbox review order\n"
        "- bbox_review_priority_top40.jpg: visual review sheet for high-priority fixes\n",
        encoding="utf-8",
    )

    zip_path = out_root / f"{args.out_slug}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out_images.iterdir()):
            archive.write(path, arcname=f"images/{path.name}")
        archive.write(annotations_path, arcname="_annotations.coco.json")

    high_priority = sum(1 for row in review_rows if int(row["review_priority"]) >= 5)
    print(f"images={len(images)}")
    print(f"annotations={len(annotations)}")
    print(f"high_priority_review={high_priority}")
    print(f"zip={zip_path}")
    print(f"priority_csv={priority_csv}")
    print(f"contact_sheet={contact_sheet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
