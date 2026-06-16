from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def dataset_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def ar_root_from_dataset_root(dataset_root: Path) -> Path:
    return dataset_root.parents[1]


def default_model_path(dataset_root: Path) -> Path:
    return ar_root_from_dataset_root(dataset_root) / "03_AI로직" / "models" / "filter_detection" / "best.pt"


def yolo_line_from_xyxy(xyxy: list[float], image_width: int, image_height: int) -> str:
    x1, y1, x2, y2 = xyxy
    x1 = max(0.0, min(float(image_width), x1))
    x2 = max(0.0, min(float(image_width), x2))
    y1 = max(0.0, min(float(image_height), y1))
    y2 = max(0.0, min(float(image_height), y2))
    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)
    x_center = x1 + width / 2
    y_center = y1 + height / 2
    return (
        "0 "
        f"{x_center / image_width:.6f} "
        f"{y_center / image_height:.6f} "
        f"{width / image_width:.6f} "
        f"{height / image_height:.6f}"
    )


def draw_contact_sheet(rows: list[dict[str, object]], output_path: Path, max_items: int = 24) -> None:
    selected = rows[:max_items]
    thumb_w, thumb_h = 280, 220
    cols = 4
    sheet_h = ((len(selected) + cols - 1) // cols) * thumb_h
    sheet = Image.new("RGB", (cols * thumb_w, max(thumb_h, sheet_h)), (245, 245, 245))

    for index, row in enumerate(selected):
        image_path = Path(str(row["target_image_path"]))
        boxes = row.get("boxes", [])
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        scale = min(thumb_w / width, (thumb_h - 30) / height)
        resized = image.resize((int(width * scale), int(height * scale)))
        tile = Image.new("RGB", (thumb_w, thumb_h), (255, 255, 255))
        offset_x = (thumb_w - resized.width) // 2
        offset_y = 0
        tile.paste(resized, (offset_x, offset_y))
        draw = ImageDraw.Draw(tile)

        for box in boxes[:3]:
            x1, y1, x2, y2 = [float(value) * scale for value in box["xyxy"]]
            x1 += offset_x
            x2 += offset_x
            y1 += offset_y
            y2 += offset_y
            draw.rectangle([x1, y1, x2, y2], outline=(0, 170, 90), width=3)
            draw.text((x1 + 4, max(0, y1 - 14)), f"{float(box['confidence']):.2f}", fill=(0, 120, 60))

        label = f"{image_path.stem} det={row['detections']} max={row['max_confidence']}"
        draw.rectangle([0, thumb_h - 30, thumb_w, thumb_h], fill=(30, 30, 30))
        draw.text((6, thumb_h - 22), label[:44], fill=(255, 255, 255))
        sheet.paste(tile, ((index % cols) * thumb_w, (index // cols) * thumb_h))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def main() -> int:
    dataset_root = dataset_root_from_script()
    parser = argparse.ArgumentParser(
        description="Generate Roboflow-ready YOLO prelabels by running the deployed filter best.pt on user primary images."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=dataset_root / "20_Roboflow_업로드패키지" / "lg_wall_mounted_filter_user_primary_099" / "images",
    )
    parser.add_argument(
        "--output-slug",
        default="lg_wall_mounted_filter_user_primary_099_model_prelabel_yolov8",
    )
    parser.add_argument("--model-path", type=Path, default=default_model_path(dataset_root))
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.4)
    parser.add_argument("--max-detections", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    output_dir = dataset_root / "20_Roboflow_업로드패키지" / args.output_slug
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    model_path = args.model_path.resolve()

    if not source_dir.exists():
        raise FileNotFoundError(source_dir)
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    if output_dir.exists():
        if not args.force:
            raise FileExistsError(f"{output_dir} exists. Pass --force to rebuild it.")
        shutil.rmtree(output_dir)

    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    try:
        from ultralytics import YOLO
    except ModuleNotFoundError as exc:
        raise RuntimeError("ultralytics is required. Run: python -m pip install ultralytics") from exc

    model = YOLO(str(model_path))
    source_images = sorted(
        path for path in source_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS
    )
    rows: list[dict[str, object]] = []

    for source_image in source_images:
        target_image = images_dir / source_image.name
        shutil.copy2(source_image, target_image)
        with Image.open(target_image) as image:
            image_width, image_height = image.size

        result = model.predict(
            str(target_image),
            conf=args.conf,
            iou=args.iou,
            max_det=args.max_detections,
            verbose=False,
        )[0]

        boxes: list[dict[str, object]] = []
        yolo_lines: list[str] = []
        if result.boxes is not None:
            xyxy_values = result.boxes.xyxy.tolist()
            confidences = result.boxes.conf.tolist()
            pairs = sorted(
                zip(xyxy_values, confidences, strict=False),
                key=lambda item: float(item[1]),
                reverse=True,
            )[: args.max_detections]
            for xyxy, confidence in pairs:
                line = yolo_line_from_xyxy(xyxy, image_width, image_height)
                yolo_lines.append(line)
                boxes.append(
                    {
                        "xyxy": [round(float(value), 3) for value in xyxy],
                        "confidence": round(float(confidence), 6),
                    }
                )

        label_path = labels_dir / f"{target_image.stem}.txt"
        label_path.write_text("\n".join(yolo_lines) + ("\n" if yolo_lines else ""), encoding="utf-8")
        max_confidence = max([float(box["confidence"]) for box in boxes], default=None)
        rows.append(
            {
                "image": target_image.name,
                "target_image_path": str(target_image),
                "label": label_path.name,
                "image_width": image_width,
                "image_height": image_height,
                "detections": len(boxes),
                "max_confidence": round(max_confidence, 6) if max_confidence is not None else "",
                "boxes": boxes,
                "review_status": "model_prelabel_review_required"
                if boxes
                else "manual_label_required_no_model_detection",
            }
        )

    (output_dir / "darknet.labels").write_text("filter\n", encoding="utf-8")
    (output_dir / "data.yaml").write_text(
        "\n".join(
            [
                "path: .",
                "train: images",
                "val: images",
                "test: images",
                "names:",
                "  0: filter",
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest_path = output_dir / "model_prelabel_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "image",
                "label",
                "image_width",
                "image_height",
                "detections",
                "max_confidence",
                "review_status",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "model_path": str(model_path),
        "confidence_threshold": args.conf,
        "iou_threshold": args.iou,
        "max_detections": args.max_detections,
        "images": len(rows),
        "labels": len(rows),
        "images_with_detection": sum(1 for row in rows if int(row["detections"]) > 0),
        "images_without_detection": sum(1 for row in rows if int(row["detections"]) == 0),
        "total_boxes": sum(int(row["detections"]) for row in rows),
    }
    (output_dir / "model_prelabel_summary.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# Model prelabel package",
                "",
                "This package contains user primary wall-mounted LG AC filter images plus YOLO txt labels generated by the deployed filter best.pt.",
                "Labels are predictions, not ground truth. Review every box in Roboflow before final training.",
                "",
                f"- model: {model_path}",
                f"- conf: {args.conf}",
                f"- iou: {args.iou}",
                f"- images: {summary['images']}",
                f"- images_with_detection: {summary['images_with_detection']}",
                f"- images_without_detection: {summary['images_without_detection']}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    contact_sheet = output_dir / "model_prelabel_contact_sheet.jpg"
    draw_contact_sheet(rows, contact_sheet)
    archive_base = output_dir / args.output_slug
    archive_path = shutil.make_archive(str(archive_base), "zip", root_dir=output_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"manifest={manifest_path}")
    print(f"contact_sheet={contact_sheet}")
    print(f"zip={archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
