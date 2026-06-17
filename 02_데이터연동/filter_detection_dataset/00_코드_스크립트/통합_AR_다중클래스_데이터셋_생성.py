from __future__ import annotations

import argparse
import json
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
TARGET_NAMES = ["filter", "aircon", "aircon-top", "aircon-bottom"]


def bbox_line_from_values(class_id: int, values: list[float]) -> str | None:
    if len(values) == 4:
        x_center, y_center, width, height = values
    else:
        if len(values) < 6 or len(values) % 2 != 0:
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
    coords = [
        max(0.0, min(1.0, x_center)),
        max(0.0, min(1.0, y_center)),
        max(0.0, min(1.0, width)),
        max(0.0, min(1.0, height)),
    ]
    return f"{class_id} " + " ".join(f"{value:.6f}" for value in coords)


def remap_label(source_label: Path, class_map: dict[int, int]) -> tuple[str, int, int]:
    if not source_label.exists():
        return "", 0, 0
    lines: list[str] = []
    dropped = 0
    for raw_line in source_label.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        try:
            source_class = int(float(parts[0]))
            values = [float(part) for part in parts[1:]]
        except ValueError:
            dropped += 1
            continue
        target_class = class_map.get(source_class)
        if target_class is None:
            dropped += 1
            continue
        converted = bbox_line_from_values(target_class, values)
        if converted is None:
            dropped += 1
            continue
        lines.append(converted)
    return "\n".join(lines) + ("\n" if lines else ""), len(lines), dropped


def copy_labeled_source(
    source_dir: Path,
    target_dir: Path,
    slug: str,
    class_map: dict[int, int],
) -> dict[str, object]:
    summary: dict[str, object] = {
        "slug": slug,
        "source_dir": str(source_dir),
        "class_map": class_map,
        "splits": {},
        "images": 0,
        "labels": 0,
        "boxes": 0,
        "dropped_lines": 0,
    }
    for split in ["train", "valid", "test"]:
        source_images = source_dir / split / "images"
        source_labels = source_dir / split / "labels"
        if not source_images.exists():
            continue
        target_images = target_dir / split / "images"
        target_labels = target_dir / split / "labels"
        target_images.mkdir(parents=True, exist_ok=True)
        target_labels.mkdir(parents=True, exist_ok=True)
        split_counts = {"images": 0, "labels": 0, "boxes": 0, "dropped_lines": 0}
        for index, image_path in enumerate(
            sorted(path for path in source_images.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS),
            1,
        ):
            target_name = f"{slug}_{split}_{index:04d}{image_path.suffix.lower()}"
            target_image = target_images / target_name
            target_label = target_labels / f"{Path(target_name).stem}.txt"
            shutil.copy2(image_path, target_image)
            label_text, boxes, dropped = remap_label(source_labels / f"{image_path.stem}.txt", class_map)
            target_label.write_text(label_text, encoding="utf-8")
            split_counts["images"] += 1
            split_counts["labels"] += 1
            split_counts["boxes"] += boxes
            split_counts["dropped_lines"] += dropped
        summary["splits"][split] = split_counts
        for key in ["images", "labels", "boxes", "dropped_lines"]:
            summary[key] = int(summary[key]) + split_counts[key]
    return summary


def split_negative_images(images: list[Path]) -> dict[str, list[Path]]:
    shuffled = images[:]
    random.Random(20260616).shuffle(shuffled)
    total = len(shuffled)
    valid_count = max(1, round(total * 0.1)) if total >= 10 else 0
    test_count = max(1, round(total * 0.1)) if total >= 10 else 0
    train_count = total - valid_count - test_count
    return {
        "train": shuffled[:train_count],
        "valid": shuffled[train_count : train_count + valid_count],
        "test": shuffled[train_count + valid_count :],
    }


def copy_negative_sources(source_dirs: list[Path], target_dir: Path) -> dict[str, object]:
    images: list[Path] = []
    for source_dir in source_dirs:
        if not source_dir.exists():
            continue
        images.extend(sorted(path for path in source_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS))
    split_images = split_negative_images(images)
    summary: dict[str, object] = {
        "slug": "hard_negative",
        "source_dirs": [str(path) for path in source_dirs],
        "images": 0,
        "labels": 0,
        "boxes": 0,
        "splits": {},
    }
    for split, split_paths in split_images.items():
        target_images = target_dir / split / "images"
        target_labels = target_dir / split / "labels"
        target_images.mkdir(parents=True, exist_ok=True)
        target_labels.mkdir(parents=True, exist_ok=True)
        split_counts = {"images": 0, "labels": 0, "boxes": 0}
        for index, image_path in enumerate(split_paths, 1):
            target_name = f"hardneg_{split}_{index:04d}{image_path.suffix.lower()}"
            shutil.copy2(image_path, target_images / target_name)
            (target_labels / f"{Path(target_name).stem}.txt").write_text("", encoding="utf-8")
            split_counts["images"] += 1
            split_counts["labels"] += 1
        summary["splits"][split] = split_counts
        for key in ["images", "labels", "boxes"]:
            summary[key] = int(summary[key]) + split_counts[key]
    return summary


def write_data_yaml(target_dir: Path) -> None:
    lines = [
        "train: ../train/images",
        "val: ../valid/images",
        "test: ../test/images",
        f"nc: {len(TARGET_NAMES)}",
        "names:",
    ]
    lines.extend(f"  - {name}" for name in TARGET_NAMES)
    (target_dir / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    dataset_root = Path(__file__).resolve().parents[1]
    export_root = dataset_root / "30_Roboflow_내보내기_YOLO"
    raw_root = dataset_root / "10_원천이미지_raw"
    parser = argparse.ArgumentParser(description="Build multi-class AR YOLO dataset.")
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=export_root / "combined_ar_multiclass_filter_aircon_top_bottom_hardneg_yolov8_20260616",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    target_dir = args.target_dir.resolve()
    if target_dir.exists():
        if not args.force:
            raise FileExistsError(f"{target_dir} exists. Pass --force to rebuild.")
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    sources = [
        (
            export_root / "combined_filter_carevision099_testfilter066_bbox_yolov8_20260616",
            "filter",
            {0: 0},
        ),
        (
            export_root / "aircon_external_yolov8_20260616",
            "aircon",
            {0: 1},
        ),
        (
            export_root / "aircon_top_bottom_bbox_yolov8_20260616",
            "aircontopbottom",
            {0: 3, 1: 2},
        ),
    ]
    summary: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_dir": str(target_dir),
        "target_names": TARGET_NAMES,
        "sources": [],
        "splits": {
            "train": {"images": 0, "labels": 0, "boxes": 0},
            "valid": {"images": 0, "labels": 0, "boxes": 0},
            "test": {"images": 0, "labels": 0, "boxes": 0},
        },
    }
    for source_dir, slug, class_map in sources:
        source_summary = copy_labeled_source(source_dir, target_dir, slug, class_map)
        summary["sources"].append(source_summary)

    negative_summary = copy_negative_sources(
        [
            raw_root / "90_하드네거티브_공개이미지_20260616",
            raw_root / "91_하드네거티브_합성이미지_20260616",
        ],
        target_dir,
    )
    summary["sources"].append(negative_summary)

    for split in ["train", "valid", "test"]:
        images = len(list((target_dir / split / "images").glob("*")))
        labels = len(list((target_dir / split / "labels").glob("*.txt")))
        boxes = 0
        for label in (target_dir / split / "labels").glob("*.txt"):
            boxes += len([line for line in label.read_text(encoding="utf-8").splitlines() if line.strip()])
        summary["splits"][split] = {"images": images, "labels": labels, "boxes": boxes}

    write_data_yaml(target_dir)
    (target_dir / "combined_multiclass_metadata.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
