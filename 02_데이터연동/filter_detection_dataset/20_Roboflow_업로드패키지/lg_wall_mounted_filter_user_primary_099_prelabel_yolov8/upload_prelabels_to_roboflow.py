from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def mask_secret(value: str | None) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 8:
        return value[0] + "***"
    return f"{value[:4]}...{value[-4:]}"


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def collect_pairs(package_dir: Path) -> list[tuple[Path, Path]]:
    images_dir = package_dir / "images"
    labels_dir = package_dir / "labels"
    pairs: list[tuple[Path, Path]] = []
    for image_path in sorted(path for path in images_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS):
        label_path = labels_dir / f"{image_path.stem}.txt"
        if not label_path.exists():
            raise FileNotFoundError(f"Missing label for {image_path.name}: {label_path}")
        pairs.append((image_path, label_path))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload LG wall-mounted AC filter images with YOLO pre-labels to Roboflow."
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate files/config without uploading.")
    parser.add_argument("--limit", type=int, default=0, help="Upload only the first N images.")
    parser.add_argument("--split", default=os.getenv("ROBOFLOW_SPLIT", "train"))
    parser.add_argument(
        "--batch-name",
        default=os.getenv("ROBOFLOW_BATCH_NAME", "lg_wall_mounted_filter_user_primary_099_prelabel_yolov8"),
    )
    parser.add_argument(
        "--as-predictions",
        action=argparse.BooleanOptionalAction,
        default=env_bool("ROBOFLOW_UPLOAD_AS_PREDICTIONS", True),
        help="Upload labels as predictions for Roboflow review instead of final annotations.",
    )
    args = parser.parse_args()

    package_dir = Path(__file__).resolve().parent
    pairs = collect_pairs(package_dir)
    if args.limit > 0:
        pairs = pairs[: args.limit]

    labelmap_path = package_dir / "darknet.labels"
    labelmap_path.write_text("filter\n", encoding="utf-8")

    api_key = os.getenv("ROBOFLOW_API_KEY")
    workspace_slug = os.getenv("ROBOFLOW_WORKSPACE", "s-workspace-fmrs3")
    project_slug = os.getenv("ROBOFLOW_PROJECT", "carevision-ar")

    print("Roboflow pre-label upload config:")
    print(f"- ROBOFLOW_API_KEY={mask_secret(api_key)}")
    print(f"- ROBOFLOW_WORKSPACE={workspace_slug}")
    print(f"- ROBOFLOW_PROJECT={project_slug}")
    print(f"- split={args.split}")
    print(f"- batch_name={args.batch_name}")
    print(f"- as_predictions={args.as_predictions}")
    print(f"- image_label_pairs={len(pairs)}")
    print(f"- labelmap={labelmap_path}")

    results_csv = package_dir / "roboflow_prelabel_upload_results.csv"
    if args.dry_run:
        print("dry_run=true; no upload attempted")
        return 0

    if not api_key:
        print("Missing ROBOFLOW_API_KEY. Set it in the current shell before uploading.")
        return 1

    try:
        from roboflow import Roboflow
    except ModuleNotFoundError:
        print("roboflow SDK is not installed. Install it first: python -m pip install roboflow")
        return 1

    rf = Roboflow(api_key=api_key)
    try:
        project = rf.workspace(workspace_slug).project(project_slug)
    except Exception as exc:
        print(f"Failed to open Roboflow project {workspace_slug}/{project_slug}: {exc}")
        return 1

    uploaded = 0
    failed: list[tuple[str, str]] = []
    with results_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["filename", "label", "status", "split", "batch_name", "message"],
        )
        writer.writeheader()
        for image_path, label_path in pairs:
            try:
                result = project.single_upload(
                    image_path=str(image_path),
                    annotation_path=str(label_path),
                    annotation_labelmap=str(labelmap_path),
                    split=args.split,
                    batch_name=args.batch_name,
                    is_prediction=args.as_predictions,
                    num_retry_uploads=2,
                )
                uploaded += 1
                writer.writerow(
                    {
                        "filename": image_path.name,
                        "label": label_path.name,
                        "status": "uploaded",
                        "split": args.split,
                        "batch_name": args.batch_name,
                        "message": str(result)[:1000],
                    }
                )
                print(f"uploaded {uploaded}/{len(pairs)} {image_path.name}")
            except Exception as exc:
                failed.append((image_path.name, str(exc)))
                writer.writerow(
                    {
                        "filename": image_path.name,
                        "label": label_path.name,
                        "status": "failed",
                        "split": args.split,
                        "batch_name": args.batch_name,
                        "message": str(exc)[:1000],
                    }
                )
                print(f"failed {image_path.name}: {exc}")

    print(f"done uploaded={uploaded} failed={len(failed)} total={len(pairs)}")
    print(f"results_csv={results_csv}")
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
