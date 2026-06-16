from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def choose_split(name: str) -> str:
    bucket = int(hashlib.sha1(name.encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "valid"
    return "test"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a local YOLOv8 export from heuristic pre-labels for format verification only."
    )
    parser.add_argument("--source-slug", default="lg_wall_mounted_filter_user_primary_099_prelabel_yolov8")
    parser.add_argument("--out-slug", default="local_prelabel_yolov8_review_only")
    args = parser.parse_args()

    dataset_root = Path(__file__).resolve().parents[1]
    source_root = dataset_root / "20_Roboflow_업로드패키지" / args.source_slug
    out_root = dataset_root / "30_Roboflow_내보내기_YOLO" / args.out_slug
    images_dir = source_root / "images"
    labels_dir = source_root / "labels"

    if not images_dir.exists():
        raise FileNotFoundError(images_dir)
    if not labels_dir.exists():
        raise FileNotFoundError(labels_dir)

    if out_root.exists():
        shutil.rmtree(out_root)
    for split in ("train", "valid", "test"):
        (out_root / split / "images").mkdir(parents=True, exist_ok=True)
        (out_root / split / "labels").mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    counts = {"train": 0, "valid": 0, "test": 0}
    for image_path in sorted(path for path in images_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS):
        label_path = labels_dir / f"{image_path.stem}.txt"
        if not label_path.exists():
            raise FileNotFoundError(f"Missing label for {image_path.name}: {label_path}")
        split = choose_split(image_path.name)
        shutil.copy2(image_path, out_root / split / "images" / image_path.name)
        shutil.copy2(label_path, out_root / split / "labels" / label_path.name)
        counts[split] += 1
        rows.append(
            {
                "image_name": image_path.name,
                "label_name": label_path.name,
                "split": split,
                "source": args.source_slug,
                "review_status": "heuristic_prelabel_must_review_in_roboflow",
            }
        )

    (out_root / "data.yaml").write_text(
        "path: .\n"
        "train: train/images\n"
        "val: valid/images\n"
        "test: test/images\n"
        "nc: 1\n"
        "names:\n"
        "  - filter\n",
        encoding="utf-8",
    )

    with (out_root / "split_manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["image_name", "label_name", "split", "source", "review_status"],
        )
        writer.writeheader()
        writer.writerows(rows)

    (out_root / "README.md").write_text(
        "# local_prelabel_yolov8_review_only\n\n"
        "This export is generated from heuristic pre-labels for local format verification only.\n"
        "Do not treat it as Roboflow-reviewed ground truth and do not use it as the final training dataset.\n",
        encoding="utf-8",
    )

    print(json.dumps({"out_root": str(out_root), "counts": counts, "total": len(rows)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
