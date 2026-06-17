from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], cwd: Path, allow_fail: bool = False) -> subprocess.CompletedProcess[str]:
    print(json.dumps({"cmd": command, "cwd": str(cwd)}, ensure_ascii=False))
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0 and not allow_fail:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def dataset_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def ar_root_from_dataset(dataset_root: Path) -> Path:
    return dataset_root.parents[1]


def table_count(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "select count(*) from sqlite_master where type='table' and name not like 'sqlite_%'"
        ).fetchone()
        return int(row[0])
    finally:
        conn.close()


def main() -> int:
    dataset_root = dataset_root_from_script()
    ar_root = ar_root_from_dataset(dataset_root)
    parser = argparse.ArgumentParser(
        description="Finalize a reviewed Roboflow YOLO export into the CareShot AR filter detector runtime."
    )
    parser.add_argument("--export-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--name", default="yolov8n_filter_wall_primary_099")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-review-only-smoke",
        action="store_true",
        help="Only for validating this wrapper with local *_review_only exports. Never use for final runtime deployment.",
    )
    args = parser.parse_args()

    export_dir = args.export_dir.resolve()
    deploy_path = ar_root / "03_AI로직" / "models" / "filter_detection" / "best.pt"
    backend_dir = ar_root / "04_백엔드"
    frontend_dir = ar_root / "05_프론트엔드" / "react-vite"
    db_path = ar_root / "02_데이터연동" / "db" / "careshot_ar_mock.db"

    is_review_only = "review_only" in export_dir.name.lower()
    if is_review_only and not args.allow_review_only_smoke:
        print(
            json.dumps(
                {
                    "blocked": True,
                    "reason": "review-only export detected; complete Roboflow bbox review and export a final YOLOv8 dataset first",
                    "export_dir": str(export_dir),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    if is_review_only and not args.dry_run:
        print("review-only smoke is allowed only with --dry-run")
        return 1

    train_command = [
        sys.executable,
        str(dataset_root / "40_학습실행결과" / "필터검출기_학습및배포스테이징.py"),
        "--export-dir",
        str(export_dir),
        "--epochs",
        str(args.epochs),
        "--imgsz",
        str(args.imgsz),
        "--batch",
        str(args.batch),
        "--name",
        args.name,
    ]
    if args.force:
        train_command.append("--force")
    if args.dry_run:
        train_command.append("--dry-run")
    if args.allow_review_only_smoke:
        train_command.append("--allow-review-only-training")
        train_command.append("--no-deploy")

    run_command(train_command, cwd=dataset_root)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "deploy_path": str(deploy_path)}, ensure_ascii=False, indent=2))
        return 0

    if not deploy_path.exists():
        print(f"deployed best.pt missing after training: {deploy_path}")
        return 1

    run_command(
        [
            sys.executable,
            str(dataset_root / "40_학습실행결과" / "FastAPI_필터_YOLO_스모크테스트.py"),
            "--model-path",
            str(deploy_path),
        ],
        cwd=dataset_root,
    )
    run_command([sys.executable, "-m", "pytest", "-q", "tests/test_ar_filter_detection.py"], cwd=backend_dir)
    run_command(["npm", "run", "smoke:ar-guide"], cwd=frontend_dir)
    run_command(["npm", "run", "build"], cwd=frontend_dir)

    count = table_count(db_path)
    print(json.dumps({"db_path": str(db_path), "table_count": count}, ensure_ascii=False, indent=2))
    if count != 21:
        print(f"unexpected DB table_count={count}; expected 21")
        return 1
    print(
        json.dumps(
            {
                "finalized": True,
                "deploy_path": str(deploy_path),
                "backend_smoke": "passed",
                "frontend_smoke": "passed",
                "db_table_count": count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
