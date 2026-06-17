from __future__ import annotations

import csv
import shutil
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def read_image(path: Path) -> np.ndarray:
    image_bytes = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Cannot read image: {path}")
    return image


def trim_projection(mask: np.ndarray, axis: int, lo: int, hi: int) -> tuple[int, int] | None:
    projection = mask.mean(axis=axis)
    if projection.size == 0:
        return None
    peak = float(projection.max())
    if peak <= 0:
        return None
    threshold = max(peak * 0.22, float(np.percentile(projection, 78)))
    indices = np.where(projection >= threshold)[0]
    if len(indices) < 2:
        return None
    return lo + int(indices[0]), lo + int(indices[-1])


def refine_bbox(image_path: Path, original: tuple[int, int, int, int]) -> tuple[int, int, int, int, str]:
    image = read_image(image_path)
    height, width = image.shape[:2]
    ox1, oy1, ox2, oy2 = original
    ox1 = clamp(ox1, 0, width - 2)
    oy1 = clamp(oy1, 0, height - 2)
    ox2 = clamp(ox2, ox1 + 1, width)
    oy2 = clamp(oy2, oy1 + 1, height)

    roi = image[oy1:oy2, ox1:ox2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 35, 120)

    # Filter mesh is usually darker and more line-dense than the surrounding white body.
    dark_limit = max(80, min(185, int(np.percentile(gray, 48))))
    dark = cv2.inRange(gray, 0, dark_limit)
    line_mask = cv2.bitwise_or(edges, dark)
    line_mask = cv2.morphologyEx(
        line_mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(7, width // 140), 3)),
        iterations=1,
    )
    line_mask = cv2.dilate(line_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3)), iterations=1)

    x_range = trim_projection(line_mask, axis=0, lo=ox1, hi=ox2)
    y_range = trim_projection(line_mask, axis=1, lo=oy1, hi=oy2)
    if not x_range or not y_range:
        return ox1, oy1, ox2, oy2, "keep_original_projection_failed"

    x1, x2 = x_range
    y1, y2 = y_range
    bbox_w = x2 - x1
    bbox_h = y2 - y1
    if bbox_w < width * 0.12 or bbox_h < height * 0.04:
        return ox1, oy1, ox2, oy2, "keep_original_too_small"

    pad_x = int(bbox_w * 0.05)
    pad_y = int(bbox_h * 0.10)
    x1 = clamp(x1 - pad_x, 0, width - 1)
    y1 = clamp(y1 - pad_y, 0, height - 1)
    x2 = clamp(x2 + pad_x, x1 + 1, width)
    y2 = clamp(y2 + pad_y, y1 + 1, height)

    original_area = (ox2 - ox1) * (oy2 - oy1)
    refined_area = (x2 - x1) * (y2 - y1)
    if refined_area > original_area * 0.98:
        return ox1, oy1, ox2, oy2, "keep_original_no_tightening"
    return x1, y1, x2, y2, "projection_tightened"


def risk_score(width: int, height: int, x1: int, y1: int, x2: int, y2: int, method: str) -> tuple[int, str]:
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
    if method.startswith("keep_original"):
        score += 2
        reasons.append(method)
    if not reasons:
        reasons.append("normal_review")
    return score, "|".join(reasons)


def save_contact_sheet(image_paths: list[Path], bboxes: dict[str, tuple[int, int, int, int]], out_path: Path) -> None:
    thumb_w, thumb_h, label_h, cols = 220, 165, 34, 4
    rows = max(1, (len(image_paths) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(image_paths):
        row, col = divmod(index, cols)
        x0, y0 = col * thumb_w, row * (thumb_h + label_h)
        try:
            image = Image.open(path).convert("RGB")
            ow, oh = image.size
            image.thumbnail((thumb_w, thumb_h))
            px = x0 + (thumb_w - image.width) // 2
            py = y0 + (thumb_h - image.height) // 2
            sheet.paste(image, (px, py))
            sx = image.width / ow
            sy = image.height / oh
            bx1, by1, bx2, by2 = bboxes[path.name]
            draw.rectangle((px + bx1 * sx, py + by1 * sy, px + bx2 * sx, py + by2 * sy), outline=(255, 0, 0), width=3)
        except Exception as exc:
            draw.text((x0 + 4, y0 + 4), f"ERR {exc}"[:40], fill=(255, 0, 0))
        draw.rectangle((x0, y0 + thumb_h, x0 + thumb_w, y0 + thumb_h + label_h), fill=(245, 245, 245), outline=(180, 180, 180))
        draw.text((x0 + 4, y0 + thumb_h + 4), f"{index + 1:03d} {path.name[:32]}", fill=(0, 0, 0))
    sheet.save(out_path, quality=92)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python refine_filter_bbox_prelabels.py <dataset_root>")
        return 2

    dataset_root = Path(sys.argv[1]).resolve()
    source_slug = "lg_wall_mounted_filter_user_primary_099_prelabel_yolov8"
    out_slug = "lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2"
    source_root = dataset_root / "20_Roboflow_업로드패키지" / source_slug
    source_images = source_root / "images"
    manifest_path = source_root / "prelabel_manifest.csv"
    out_root = dataset_root / "20_Roboflow_업로드패키지" / out_slug
    out_images = out_root / "images"
    out_labels = out_root / "labels"
    if out_root.exists():
        shutil.rmtree(out_root)
    out_images.mkdir(parents=True)
    out_labels.mkdir(parents=True)

    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    out_rows: list[dict[str, str]] = []
    bboxes: dict[str, tuple[int, int, int, int]] = {}
    tightened = 0
    high_priority = 0
    for row in rows:
        image_name = row["image_name"]
        image_path = source_images / image_name
        shutil.copy2(image_path, out_images / image_name)
        width = int(row["width"])
        height = int(row["height"])
        original = (int(row["x1"]), int(row["y1"]), int(row["x2"]), int(row["y2"]))
        x1, y1, x2, y2, method = refine_bbox(image_path, original)
        if method == "projection_tightened":
            tightened += 1
        score, reasons = risk_score(width, height, x1, y1, x2, y2, method)
        if score >= 5:
            high_priority += 1
        cx = ((x1 + x2) / 2) / width
        cy = ((y1 + y2) / 2) / height
        bw = (x2 - x1) / width
        bh = (y2 - y1) / height
        label_path = out_labels / f"{Path(image_name).stem}.txt"
        label_path.write_text(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding="utf-8")
        bboxes[image_name] = (x1, y1, x2, y2)
        out_row = dict(row)
        out_row.update(
            {
                "x1": str(x1),
                "y1": str(y1),
                "x2": str(x2),
                "y2": str(y2),
                "method": method,
                "bbox_area_ratio": f"{((x2 - x1) * (y2 - y1)) / max(1, width * height):.4f}",
                "review_priority": str(score),
                "review_reasons": reasons,
                "review_status": "must_review_in_roboflow_refined_v2",
            }
        )
        out_rows.append(out_row)

    manifest_out = out_root / "prelabel_manifest.csv"
    with manifest_out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    (out_root / "data.yaml").write_text(
        "path: .\ntrain: images\nval: images\ntest: images\nnames:\n  0: filter\n",
        encoding="utf-8",
    )
    (out_root / "darknet.labels").write_text("filter\n", encoding="utf-8")

    contact_sheet = out_root / "prelabel_overlay_contact_sheet.jpg"
    save_contact_sheet([out_images / row["image_name"] for row in out_rows], bboxes, contact_sheet)

    zip_path = out_root / f"{out_slug}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in (out_images, out_labels):
            for path in sorted(folder.iterdir()):
                archive.write(path, arcname=f"{folder.name}/{path.name}")
        archive.write(out_root / "data.yaml", arcname="data.yaml")
        archive.write(out_root / "darknet.labels", arcname="darknet.labels")
        archive.write(manifest_out, arcname="prelabel_manifest.csv")

    (out_root / "README.md").write_text(
        "# lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2\n\n"
        "Refined heuristic pre-labels for Roboflow review. These are not final ground truth.\n"
        "Use this package instead of v1 when uploading pre-labels, then review every bbox manually.\n",
        encoding="utf-8",
    )

    print(f"images={len(out_rows)}")
    print(f"labels={len(list(out_labels.glob('*.txt')))}")
    print(f"tightened={tightened}")
    print(f"high_priority_review={high_priority}")
    print(f"zip={zip_path}")
    print(f"contact_sheet={contact_sheet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
