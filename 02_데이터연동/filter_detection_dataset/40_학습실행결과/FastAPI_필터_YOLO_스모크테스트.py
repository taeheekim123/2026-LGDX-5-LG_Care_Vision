from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

from PIL import Image


def main() -> int:
    dataset_root = Path(__file__).resolve().parents[1]
    ar_root = dataset_root.parents[1]
    parser = argparse.ArgumentParser(
        description="Run an isolated FastAPI filter-detect smoke test with a supplied YOLO model."
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=dataset_root
        / "40_학습실행결과"
        / "filter_detection_yolo"
        / "smoke_review_only_no_deploy_test"
        / "weights"
        / "best.pt",
    )
    parser.add_argument(
        "--image-path",
        type=Path,
        default=dataset_root
        / "30_Roboflow_내보내기_YOLO"
        / "local_prelabel_yolov8_refined_v2_review_only"
        / "valid"
        / "images"
        / "user_primary_filter_027.jpg",
    )
    parser.add_argument(
        "--backend-dir",
        type=Path,
        default=ar_root / "04_백엔드",
    )
    parser.add_argument("--confidence-threshold", type=float, default=0.001)
    args = parser.parse_args()

    model_path = args.model_path.resolve()
    image_path = args.image_path.resolve()
    backend_dir = args.backend_dir.resolve()
    if not model_path.exists():
        print(f"missing model_path: {model_path}")
        return 1
    if not image_path.exists():
        print(f"missing image_path: {image_path}")
        return 1
    if not backend_dir.exists():
        print(f"missing backend_dir: {backend_dir}")
        return 1

    os.environ["CARESHOT_FILTER_YOLO_MODEL_PATH"] = str(model_path)
    sys.path.insert(0, str(backend_dir))

    from app.main import app
    from app.yolo_filter_service import get_filter_detection_service
    from fastapi.testclient import TestClient

    get_filter_detection_service.cache_clear()
    with Image.open(image_path) as image:
        width, height = image.size
    payload = "data:image/jpeg;base64," + base64.b64encode(image_path.read_bytes()).decode("ascii")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ar/filter-detect",
            json={
                "image_data_url": payload,
                "image_width": width,
                "image_height": height,
                "confidence_threshold": args.confidence_threshold,
                "mock_fallback": False,
            },
        )
    body = response.json()
    detections = body.get("detections", [])
    result = {
        "status_code": response.status_code,
        "mode": body.get("mode"),
        "model_loaded": body.get("model_loaded"),
        "detections_count": len(detections),
        "first_detection": detections[0] if detections else None,
        "message": body.get("message"),
        "model_path": str(model_path),
        "image_path": str(image_path),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if response.status_code != 200:
        return 1
    if body.get("mode") != "yolo" or body.get("model_loaded") is not True:
        return 1
    if not detections:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
