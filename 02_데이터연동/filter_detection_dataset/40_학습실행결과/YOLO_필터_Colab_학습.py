from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Train YOLO filter detector from Roboflow export.")
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to Roboflow YOLOv8 data.yaml",
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="Base YOLO model. Use yolov8n.pt for fast Colab T4 POC.",
    )
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument(
        "--project",
        type=Path,
        default=Path("40_학습실행결과") / "filter_detection_yolo",
    )
    parser.add_argument("--name", default="yolov8n_filter_wall_primary_099")
    args = parser.parse_args()

    if not args.data.exists():
        raise FileNotFoundError(f"data.yaml not found: {args.data}")

    try:
        from ultralytics import YOLO
    except ModuleNotFoundError as exc:
        raise SystemExit("ultralytics is not installed. Run: pip install ultralytics") from exc

    model = YOLO(args.model)
    result = model.train(
        data=str(args.data),
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
    print("Expected best.pt path:")
    print(args.project / args.name / "weights" / "best.pt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
