from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def parse_names(data_yaml: Path) -> list[str]:
    names: list[str] = []
    in_names = False
    for raw_line in data_yaml.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("names:"):
            value = stripped.split(":", 1)[1].strip()
            if value.startswith("[") and value.endswith("]"):
                return [
                    item.strip().strip("'\"")
                    for item in value.strip("[]").split(",")
                    if item.strip()
                ]
            in_names = True
            continue
        if not in_names:
            continue
        if stripped.startswith("- "):
            names.append(stripped[2:].strip().strip("'\""))
        elif ":" in stripped and stripped.split(":", 1)[0].strip().isdigit():
            names.append(stripped.split(":", 1)[1].strip().strip("'\""))
        else:
            break
    return names


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


def convert_label_file(source: Path, target: Path, class_map: dict[int, int]) -> tuple[int, int]:
    converted: list[str] = []
    dropped = 0
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        try:
            source_class_id = int(float(parts[0]))
            values = [float(value) for value in parts[1:]]
        except (ValueError, IndexError):
            dropped += 1
            continue
        target_class_id = class_map.get(source_class_id)
        if target_class_id is None:
            dropped += 1
            continue
        converted_line = bbox_line_from_values(target_class_id, values)
        if converted_line is None:
            dropped += 1
            continue
        converted.append(converted_line)
    target.write_text("\n".join(converted) + ("\n" if converted else ""), encoding="utf-8")
    return len(converted), dropped


def write_data_yaml(target_dir: Path, names: list[str]) -> None:
    lines = [
        "train: ../train/images",
        "val: ../valid/images",
        "test: ../test/images",
        f"nc: {len(names)}",
        "names:",
    ]
    lines.extend(f"  - {name}" for name in names)
    (target_dir / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_export(
    source_dir: Path,
    target_dir: Path,
    target_names: list[str],
    source_to_target: dict[int, int],
    force: bool,
) -> dict[str, object]:
    if target_dir.exists():
        if not force:
            raise FileExistsError(f"{target_dir} exists. Pass --force to rebuild.")
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "source_names": parse_names(source_dir / "data.yaml") if (source_dir / "data.yaml").exists() else [],
        "target_names": target_names,
        "source_to_target": source_to_target,
        "splits": {},
        "total_images": 0,
        "total_labels": 0,
        "total_boxes": 0,
        "total_dropped_lines": 0,
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

        images = sorted(path for path in source_images.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)
        image_count = 0
        label_count = 0
        box_count = 0
        dropped_count = 0
        missing_labels: list[str] = []
        for image in images:
            shutil.copy2(image, target_images / image.name)
            image_count += 1
            source_label = source_labels / f"{image.stem}.txt"
            target_label = target_labels / f"{image.stem}.txt"
            if not source_label.exists():
                target_label.write_text("", encoding="utf-8")
                missing_labels.append(image.name)
                label_count += 1
                continue
            boxes, dropped = convert_label_file(source_label, target_label, source_to_target)
            label_count += 1
            box_count += boxes
            dropped_count += dropped

        split_summary = {
            "images": image_count,
            "labels": label_count,
            "boxes": box_count,
            "dropped_lines": dropped_count,
            "missing_labels": missing_labels,
        }
        summary["splits"][split] = split_summary
        summary["total_images"] = int(summary["total_images"]) + image_count
        summary["total_labels"] = int(summary["total_labels"]) + label_count
        summary["total_boxes"] = int(summary["total_boxes"]) + box_count
        summary["total_dropped_lines"] = int(summary["total_dropped_lines"]) + dropped_count

    write_data_yaml(target_dir, target_names)
    (target_dir / "bbox_conversion_metadata.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def parse_class_map(value: str) -> dict[int, int]:
    result: dict[int, int] = {}
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        left, right = item.split(":", 1)
        result[int(left)] = int(right)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert YOLO polygon/segmentation labels to bbox labels.")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--target-dir", type=Path, required=True)
    parser.add_argument("--target-names", required=True, help="Comma-separated target class names.")
    parser.add_argument("--class-map", default="0:0", help="Comma-separated source:target class id map.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    summary = prepare_export(
        source_dir=args.source_dir.resolve(),
        target_dir=args.target_dir.resolve(),
        target_names=[name.strip() for name in args.target_names.split(",") if name.strip()],
        source_to_target=parse_class_map(args.class_map),
        force=args.force,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if int(summary["total_images"]) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
