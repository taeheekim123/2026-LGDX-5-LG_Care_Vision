from __future__ import annotations

import argparse
import json
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
EXPECTED_CLASS_NAME = "filter"


def read_data_yaml(path: Path) -> dict[str, object]:
    data: dict[str, object] = {}
    names_inline: list[str] | None = None
    in_names_block = False
    block_names: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line:
            continue
        stripped = line.strip()
        if in_names_block and stripped.startswith("- "):
            block_names.append(stripped[2:].strip().strip("'\""))
            continue
        in_names_block = False
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "names":
            if value.startswith("[") and value.endswith("]"):
                names_inline = [
                    item.strip().strip("'\"")
                    for item in value[1:-1].split(",")
                    if item.strip()
                ]
            elif not value:
                in_names_block = True
            else:
                names_inline = [value.strip("'\"")]
        elif key in {"train", "val", "valid", "test"}:
            data[key] = value.strip("'\"")
        elif key == "nc":
            try:
                data[key] = int(value)
            except ValueError:
                data[key] = value
    if names_inline is not None:
        data["names"] = names_inline
    elif block_names:
        data["names"] = block_names
    return data


def split_dirs(root: Path) -> dict[str, tuple[Path, Path]]:
    result: dict[str, tuple[Path, Path]] = {}
    for split in ["train", "valid", "val", "test"]:
        split_root = root / split
        if split_root.exists():
            result["valid" if split == "val" else split] = (
                split_root / "images",
                split_root / "labels",
            )
    return result


def check_label_file(path: Path) -> list[str]:
    errors: list[str] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            errors.append(f"{path}:{line_no}: expected 5 YOLO columns, got {len(parts)}")
            continue
        try:
            class_id = int(float(parts[0]))
            coords = [float(value) for value in parts[1:]]
        except ValueError:
            errors.append(f"{path}:{line_no}: non-numeric YOLO value")
            continue
        if class_id != 0:
            errors.append(f"{path}:{line_no}: expected class id 0, got {class_id}")
        for value in coords:
            if value < 0 or value > 1:
                errors.append(f"{path}:{line_no}: bbox value outside 0..1: {value}")
        if coords[2] <= 0 or coords[3] <= 0:
            errors.append(f"{path}:{line_no}: bbox width/height must be positive")
    return errors


def verify_export(root: Path) -> tuple[dict[str, object], list[str]]:
    errors: list[str] = []
    data_yaml = root / "data.yaml"
    if not data_yaml.exists():
        errors.append(f"missing {data_yaml}")
        return {}, errors

    config = read_data_yaml(data_yaml)
    names = config.get("names")
    if names != [EXPECTED_CLASS_NAME]:
        errors.append(f"data.yaml names must be ['{EXPECTED_CLASS_NAME}'], got {names!r}")
    if config.get("nc") not in {1, "1", None}:
        errors.append(f"data.yaml nc must be 1, got {config.get('nc')!r}")

    summary: dict[str, object] = {
        "root": str(root),
        "data_yaml": str(data_yaml),
        "names": names,
        "splits": {},
        "total_images": 0,
        "total_labels": 0,
        "total_boxes": 0,
    }

    dirs = split_dirs(root)
    if not dirs:
        errors.append("no train/valid/test split directories found")
        return summary, errors

    for split, (images_dir, labels_dir) in dirs.items():
        split_summary = {
            "images_dir": str(images_dir),
            "labels_dir": str(labels_dir),
            "image_count": 0,
            "label_count": 0,
            "box_count": 0,
            "missing_labels": [],
        }
        if not images_dir.exists():
            errors.append(f"missing {images_dir}")
        if not labels_dir.exists():
            errors.append(f"missing {labels_dir}")
        images = sorted(
            path for path in images_dir.glob("*") if path.suffix.lower() in IMAGE_EXTENSIONS
        ) if images_dir.exists() else []
        labels = sorted(labels_dir.glob("*.txt")) if labels_dir.exists() else []
        split_summary["image_count"] = len(images)
        split_summary["label_count"] = len(labels)
        summary["total_images"] = int(summary["total_images"]) + len(images)
        summary["total_labels"] = int(summary["total_labels"]) + len(labels)

        label_stems = {path.stem for path in labels}
        for image_path in images:
            if image_path.stem not in label_stems:
                split_summary["missing_labels"].append(image_path.name)
        if split_summary["missing_labels"]:
            errors.append(
                f"{split}: missing labels for {len(split_summary['missing_labels'])} images"
            )

        for label_path in labels:
            label_errors = check_label_file(label_path)
            errors.extend(label_errors)
            if not label_errors:
                boxes = [
                    line for line in label_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                split_summary["box_count"] += len(boxes)
                summary["total_boxes"] = int(summary["total_boxes"]) + len(boxes)
        summary["splits"][split] = split_summary

    if int(summary["total_images"]) == 0:
        errors.append("export contains no images")
    if int(summary["total_boxes"]) == 0:
        errors.append("export contains no labeled boxes")
    return summary, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Roboflow YOLOv8 filter export.")
    parser.add_argument("export_dir", type=Path, help="Unzipped Roboflow YOLOv8 export root")
    parser.add_argument("--summary-json", type=Path, default=None)
    args = parser.parse_args()

    summary, errors = verify_export(args.export_dir.resolve())
    if args.summary_json:
        args.summary_json.write_text(
            json.dumps({"summary": summary, "errors": errors}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    print(json.dumps({"summary": summary, "errors": errors}, indent=2, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
