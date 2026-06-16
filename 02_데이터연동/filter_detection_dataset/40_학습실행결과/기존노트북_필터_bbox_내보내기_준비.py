from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def convert_segmentation_line_to_bbox(line: str) -> str | None:
    parts = line.split()
    if len(parts) < 5:
        return None
    class_id = int(float(parts[0]))
    values = [float(value) for value in parts[1:]]
    if len(values) == 4:
        x_center, y_center, width, height = values
    else:
        if len(values) % 2 != 0:
            return None
        xs = values[0::2]
        ys = values[1::2]
        x_min = max(0.0, min(xs))
        x_max = min(1.0, max(xs))
        y_min = max(0.0, min(ys))
        y_max = min(1.0, max(ys))
        width = x_max - x_min
        height = y_max - y_min
        x_center = x_min + width / 2
        y_center = y_min + height / 2
    if width <= 0 or height <= 0:
        return None
    return f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"


def prepare_export(source_dir: Path, target_dir: Path) -> dict[str, object]:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "class_name": "filter",
        "splits": {},
        "total_images": 0,
        "total_labels": 0,
        "total_boxes": 0,
        "dropped_label_lines": 0,
    }

    for split in ["train", "valid", "test"]:
        source_images = source_dir / split / "images"
        source_labels = source_dir / split / "labels"
        target_images = target_dir / split / "images"
        target_labels = target_dir / split / "labels"
        if not source_images.exists() or not source_labels.exists():
            continue
        target_images.mkdir(parents=True, exist_ok=True)
        target_labels.mkdir(parents=True, exist_ok=True)

        image_count = 0
        label_count = 0
        box_count = 0
        dropped_count = 0

        for image_path in sorted(source_images.iterdir()):
            if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            shutil.copy2(image_path, target_images / image_path.name)
            image_count += 1

        for label_path in sorted(source_labels.glob("*.txt")):
            converted: list[str] = []
            for raw_line in label_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                bbox_line = convert_segmentation_line_to_bbox(line)
                if bbox_line is None:
                    dropped_count += 1
                    continue
                converted.append(bbox_line)
            (target_labels / label_path.name).write_text(
                "\n".join(converted) + ("\n" if converted else ""),
                encoding="utf-8",
            )
            label_count += 1
            box_count += len(converted)

        summary["splits"][split] = {
            "images": image_count,
            "labels": label_count,
            "boxes": box_count,
            "dropped_label_lines": dropped_count,
        }
        summary["total_images"] = int(summary["total_images"]) + image_count
        summary["total_labels"] = int(summary["total_labels"]) + label_count
        summary["total_boxes"] = int(summary["total_boxes"]) + box_count
        summary["dropped_label_lines"] = int(summary["dropped_label_lines"]) + dropped_count

    data_yaml = "\n".join(
        [
            "train: ../train/images",
            "val: ../valid/images",
            "test: ../test/images",
            "nc: 1",
            "names:",
            "  - filter",
            "",
        ]
    )
    (target_dir / "data.yaml").write_text(data_yaml, encoding="utf-8")
    (target_dir / "conversion_metadata.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    dataset_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Convert the legacy Roboflow notebook segmentation export into bbox labels."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=dataset_root
        / "30_Roboflow_내보내기_YOLO"
        / "legacy_notebook_test_filter_v1_yolov8",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=dataset_root
        / "30_Roboflow_내보내기_YOLO"
        / "legacy_notebook_test_filter_v1_bbox_yolov8",
    )
    args = parser.parse_args()

    summary = prepare_export(args.source_dir.resolve(), args.target_dir.resolve())
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if int(summary["total_images"]) == 0 or int(summary["total_boxes"]) == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
