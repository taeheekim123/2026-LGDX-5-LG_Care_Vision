from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def copy_split(source_dir: Path, target_dir: Path, source_slug: str, split: str) -> dict[str, int]:
    source_images = source_dir / split / "images"
    source_labels = source_dir / split / "labels"
    target_images = target_dir / split / "images"
    target_labels = target_dir / split / "labels"
    target_images.mkdir(parents=True, exist_ok=True)
    target_labels.mkdir(parents=True, exist_ok=True)
    image_count = 0
    label_count = 0
    box_count = 0

    if not source_images.exists():
        return {"images": 0, "labels": 0, "boxes": 0}

    for index, image_path in enumerate(
        sorted(path for path in source_images.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS),
        1,
    ):
        target_name = f"{source_slug}_{split}_{index:04d}{image_path.suffix.lower()}"
        target_image = target_images / target_name
        target_label = target_labels / f"{Path(target_name).stem}.txt"
        shutil.copy2(image_path, target_image)
        label_path = source_labels / f"{image_path.stem}.txt"
        if label_path.exists():
            text = label_path.read_text(encoding="utf-8")
        else:
            text = ""
        target_label.write_text(text, encoding="utf-8")
        image_count += 1
        label_count += 1
        box_count += len([line for line in text.splitlines() if line.strip()])
    return {"images": image_count, "labels": label_count, "boxes": box_count}


def write_data_yaml(target_dir: Path) -> None:
    (target_dir / "data.yaml").write_text(
        "\n".join(
            [
                "train: ../train/images",
                "val: ../valid/images",
                "test: ../test/images",
                "nc: 1",
                "names:",
                "  - filter",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    dataset_root = Path(__file__).resolve().parents[1]
    export_root = dataset_root / "30_Roboflow_내보내기_YOLO"
    parser = argparse.ArgumentParser(description="Build combined filter bbox dataset.")
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=export_root / "combined_filter_carevision099_testfilter066_bbox_yolov8_20260616",
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
        {
            "slug": "carevision099",
            "path": export_root / "carevision_ar_reviewed_099_bbox_yolov8_20260616",
            "split_map": {"train": "train"},
        },
        {
            "slug": "testfilter066",
            "path": export_root / "test_filter_v1_bbox_yolov8_20260616",
            "split_map": {"train": "train", "valid": "valid", "test": "test"},
        },
    ]
    summary: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_dir": str(target_dir),
        "sources": [],
        "splits": {
            "train": {"images": 0, "labels": 0, "boxes": 0},
            "valid": {"images": 0, "labels": 0, "boxes": 0},
            "test": {"images": 0, "labels": 0, "boxes": 0},
        },
    }
    for source in sources:
        source_summary = {"slug": source["slug"], "path": str(source["path"]), "splits": {}}
        for source_split, target_split in source["split_map"].items():
            counts = copy_split(source["path"], target_dir, source["slug"], source_split)
            source_summary["splits"][f"{source_split}->{target_split}"] = counts
            for key in ["images", "labels", "boxes"]:
                summary["splits"][target_split][key] += counts[key]
        summary["sources"].append(source_summary)

    write_data_yaml(target_dir)
    (target_dir / "combined_dataset_metadata.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
