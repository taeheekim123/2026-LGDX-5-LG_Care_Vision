from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def dataset_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def default_deploy_path(dataset_root: Path) -> Path:
    return (
        dataset_root.parents[1]
        / "03_AI로직"
        / "models"
        / "filter_detection"
        / "best.pt"
    )


def load_verifier(dataset_root: Path):
    import sys

    verifier_dir = dataset_root / "30_Roboflow_내보내기_YOLO"
    if str(verifier_dir) not in sys.path:
        sys.path.insert(0, str(verifier_dir))
    from Roboflow_YOLOv8_내보내기_검증 import verify_export

    return verify_export


def write_ultralytics_data_yaml(export_dir: Path) -> Path:
    valid_split = "valid" if (export_dir / "valid").exists() else "val"
    lines = [
        f"path: {export_dir.as_posix()}",
        "train: train/images",
        f"val: {valid_split}/images",
        "test: test/images",
        "nc: 1",
        "names:",
        "  - filter",
    ]
    training_data_yaml = export_dir / "_ultralytics_data.yaml"
    training_data_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return training_data_yaml


def backup_existing_model(path: Path) -> Path | None:
    if not path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.stem}_{timestamp}_backup{path.suffix}")
    shutil.copy2(path, backup_path)
    return backup_path


def main() -> int:
    dataset_root = dataset_root_from_script()
    parser = argparse.ArgumentParser(
        description="Verify Roboflow YOLOv8 export, train YOLO, and stage best.pt for FastAPI."
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        required=True,
        help="Unzipped Roboflow YOLOv8 export root containing data.yaml and train/valid/test folders.",
    )
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument(
        "--project",
        type=Path,
        default=dataset_root / "40_학습실행결과" / "filter_detection_yolo",
    )
    parser.add_argument("--name", default="yolov8n_filter_wall_primary_099")
    parser.add_argument("--deploy-path", type=Path, default=default_deploy_path(dataset_root))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-review-only-training",
        action="store_true",
        help="Allow training from local *_review_only exports. Do not use for final best.pt.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacing an existing deployed best.pt after backing it up.",
    )
    parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="Train and verify best.pt but do not copy it to the FastAPI model path.",
    )
    args = parser.parse_args()

    export_dir = args.export_dir.resolve()
    verify_export = load_verifier(dataset_root)
    summary, errors = verify_export(export_dir)
    training_data_yaml = write_ultralytics_data_yaml(export_dir)
    planned_best_pt = args.project / args.name / "weights" / "best.pt"
    deploy_path = args.deploy_path.resolve()
    metadata_path = deploy_path.with_name("best_pt_deployment_metadata.json")
    is_review_only = "review_only" in export_dir.name.lower()

    plan = {
        "export_dir": str(export_dir),
        "verify_errors": errors,
        "summary": summary,
        "is_review_only_export": is_review_only,
        "training": {
            "model": args.model,
            "epochs": args.epochs,
            "imgsz": args.imgsz,
            "batch": args.batch,
            "project": str(args.project),
            "name": args.name,
            "planned_best_pt": str(planned_best_pt),
            "data_yaml": str(training_data_yaml),
        },
        "deploy_path": str(deploy_path),
        "metadata_path": str(metadata_path),
        "dry_run": args.dry_run,
        "no_deploy": args.no_deploy,
    }
    print(json.dumps(plan, indent=2, ensure_ascii=False))

    if errors:
        print("Export verification failed; training is blocked.")
        return 1
    if is_review_only and not args.allow_review_only_training:
        print("Review-only export detected; pass --allow-review-only-training only for non-final smoke tests.")
        return 1
    if args.dry_run:
        print("dry_run=true; no training or model deployment attempted.")
        return 0
    if deploy_path.exists() and not args.force:
        print(f"Deployment target already exists; use --force to replace after backup: {deploy_path}")
        return 1

    try:
        from ultralytics import YOLO
    except ModuleNotFoundError:
        print("ultralytics is not installed. Run: python -m pip install ultralytics")
        return 1

    model = YOLO(args.model)
    result = model.train(
        data=str(training_data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=str(args.project),
        name=args.name,
        patience=20,
        plots=True,
        exist_ok=True,
    )
    print(result)
    if not planned_best_pt.exists():
        print(f"Training finished but best.pt was not found: {planned_best_pt}")
        return 1
    if args.no_deploy:
        print(f"no_deploy=true; trained best.pt kept at {planned_best_pt}")
        return 0

    deploy_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = backup_existing_model(deploy_path)
    shutil.copy2(planned_best_pt, deploy_path)
    metadata = {
        "deployed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_export_dir": str(export_dir),
        "source_best_pt": str(planned_best_pt),
        "deploy_path": str(deploy_path),
        "backup_path": str(backup_path) if backup_path else None,
        "training_args": plan["training"],
        "export_summary": summary,
        "review_only_export": is_review_only,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"deployed_best_pt={deploy_path}")
    print(f"metadata={metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
