from __future__ import annotations

import csv
import shutil
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def propose_filter_bbox(image_path: Path) -> tuple[int, int, int, int, str]:
    # cv2.imread can fail on Korean/Unicode Windows paths. np.fromfile keeps the
    # filesystem access in Python and lets OpenCV decode the image bytes only.
    image_bytes = np.fromfile(str(image_path), dtype=np.uint8)
    image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 45, 140)

    # The visible filter is usually a dense horizontal grid in the upper/middle body.
    y_min_roi = int(height * 0.04)
    y_max_roi = int(height * 0.78)
    roi = edges[y_min_roi:y_max_roi, :]
    kernel_close = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(15, width // 18), max(3, height // 90)),
    )
    closed = cv2.morphologyEx(roi, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    dilated = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3)), iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[tuple[float, tuple[int, int, int, int]]] = []
    image_area = width * height
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        y += y_min_roi
        area = w * h
        if area < image_area * 0.015:
            continue
        if w < width * 0.18 or h < height * 0.06:
            continue
        aspect = w / max(1, h)
        if aspect < 1.2:
            continue
        edge_density = cv2.countNonZero(edges[y : y + h, x : x + w]) / max(1, area)
        # Prefer wide, grid-dense regions around the opened front panel.
        center_y = (y + h / 2) / height
        center_penalty = abs(center_y - 0.38)
        score = (area / image_area) * 2.0 + edge_density * 4.0 + min(aspect, 6) * 0.08 - center_penalty
        candidates.append((score, (x, y, w, h)))

    if candidates:
        _, (x, y, w, h) = max(candidates, key=lambda item: item[0])
        pad_x = int(w * 0.04)
        pad_y = int(h * 0.10)
        x1 = clamp(x - pad_x, 0, width - 1)
        y1 = clamp(y - pad_y, 0, height - 1)
        x2 = clamp(x + w + pad_x, 1, width)
        y2 = clamp(y + h + pad_y, 1, height)
        return x1, y1, x2, y2, "edge_grid_candidate"

    # Fallback: broad central filter area for manual correction in Roboflow.
    x1 = int(width * 0.12)
    y1 = int(height * 0.18)
    x2 = int(width * 0.88)
    y2 = int(height * 0.58)
    return x1, y1, x2, y2, "fallback_broad_center"


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
            original_w, original_h = image.size
            image.thumbnail((thumb_w, thumb_h))
            paste_x = x0 + (thumb_w - image.width) // 2
            paste_y = y0 + (thumb_h - image.height) // 2
            sheet.paste(image, (paste_x, paste_y))

            bx1, by1, bx2, by2 = bboxes[path.name]
            sx = image.width / original_w
            sy = image.height / original_h
            draw.rectangle(
                (
                    paste_x + bx1 * sx,
                    paste_y + by1 * sy,
                    paste_x + bx2 * sx,
                    paste_y + by2 * sy,
                ),
                outline=(255, 0, 0),
                width=3,
            )
        except Exception as exc:
            draw.text((x0 + 4, y0 + 4), f"ERR {exc}"[:40], fill=(255, 0, 0))

        draw.rectangle((x0, y0 + thumb_h, x0 + thumb_w, y0 + thumb_h + label_h), outline=(180, 180, 180), fill=(245, 245, 245))
        draw.text((x0 + 4, y0 + thumb_h + 4), f"{index + 1:03d} {path.name[:32]}", fill=(0, 0, 0))

    sheet.save(out_path, quality=92)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python generate_filter_bbox_prelabels.py <dataset_root> <source_slug>")
        return 2

    dataset_root = Path(sys.argv[1]).resolve()
    source_slug = sys.argv[2]
    source_dir = dataset_root / "20_Roboflow_업로드패키지" / source_slug / "images"
    out_slug = f"{source_slug}_prelabel_yolov8"
    out_root = dataset_root / "20_Roboflow_업로드패키지" / out_slug
    out_images = out_root / "images"
    out_labels = out_root / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    for folder in (out_images, out_labels):
        for path in folder.iterdir():
            if path.is_file():
                path.unlink()

    rows: list[dict[str, str]] = []
    bboxes: dict[str, tuple[int, int, int, int]] = {}
    image_paths = sorted([p for p in source_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}])

    for image_path in image_paths:
        target_image = out_images / image_path.name
        shutil.copy2(image_path, target_image)
        x1, y1, x2, y2, method = propose_filter_bbox(image_path)
        with Image.open(image_path) as image:
            width, height = image.size

        cx = ((x1 + x2) / 2) / width
        cy = ((y1 + y2) / 2) / height
        bw = (x2 - x1) / width
        bh = (y2 - y1) / height
        label_path = out_labels / f"{image_path.stem}.txt"
        label_path.write_text(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding="utf-8")
        bboxes[image_path.name] = (x1, y1, x2, y2)
        rows.append(
            {
                "image_name": image_path.name,
                "label_name": label_path.name,
                "width": str(width),
                "height": str(height),
                "x1": str(x1),
                "y1": str(y1),
                "x2": str(x2),
                "y2": str(y2),
                "yolo_class_id": "0",
                "class_name": "filter",
                "method": method,
                "review_status": "must_review_in_roboflow",
                "notes": "Heuristic pre-label only; correct or delete in Roboflow before training.",
            }
        )

    manifest_path = out_root / "prelabel_manifest.csv"
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = list(rows[0].keys()) if rows else ["image_name"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    data_yaml = out_root / "data.yaml"
    data_yaml.write_text(
        "path: .\n"
        "train: images\n"
        "val: images\n"
        "test: images\n"
        "names:\n"
        "  0: filter\n",
        encoding="utf-8",
    )

    contact_sheet_path = out_root / "prelabel_overlay_contact_sheet.jpg"
    save_contact_sheet([out_images / p.name for p in image_paths], bboxes, contact_sheet_path)

    zip_path = out_root / f"{out_slug}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in (out_images, out_labels):
            for path in sorted(folder.iterdir()):
                archive.write(path, arcname=f"{folder.name}/{path.name}")
        archive.write(data_yaml, arcname="data.yaml")
        archive.write(manifest_path, arcname="prelabel_manifest.csv")

    readme = out_root / "README.md"
    readme.write_text(
        f"# {out_slug}\n\n"
        f"- Source package: `{source_slug}`\n"
        f"- Images: {len(image_paths)}\n"
        "- Label class: `filter`\n"
        "- This is a heuristic pre-label package, not final ground truth.\n"
        "- Import into Roboflow only as an annotation starting point, then review every bbox before training.\n",
        encoding="utf-8",
    )

    print(f"source_slug={source_slug}")
    print(f"prelabel_slug={out_slug}")
    print(f"images={len(image_paths)}")
    print(f"labels={len(list(out_labels.glob('*.txt')))}")
    print(f"zip={zip_path}")
    print(f"contact_sheet={contact_sheet_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
