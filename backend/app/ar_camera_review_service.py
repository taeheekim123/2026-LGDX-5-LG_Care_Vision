from __future__ import annotations

import base64
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def _strip_data_url(value: str) -> tuple[str, str]:
    if "," not in value or not value.lstrip().startswith("data:"):
        return value, ".jpg"

    header, payload = value.split(",", 1)
    if "image/png" in header:
        return payload, ".png"
    if "image/webp" in header:
        return payload, ".webp"
    return payload, ".jpg"


def _decode_image(payload: str | None) -> tuple[bytes | None, str]:
    if not payload:
        return None, ".jpg"
    raw_payload, suffix = _strip_data_url(payload)
    try:
        return base64.b64decode(raw_payload, validate=False), suffix
    except Exception:
        return None, suffix


def default_review_root() -> Path:
    configured = os.getenv("CARESHOT_AR_CAMERA_REVIEW_ROOT")
    if configured:
        return Path(configured)
    return (
        Path(__file__).resolve().parents[2]
        / "02_데이터연동"
        / "filter_detection_dataset"
    )


def _safe_token(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return cleaned.strip("_") or "review"


def save_camera_review_capture(payload: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    image_value = payload.get("image_data_url") or payload.get("image_base64")
    image_bytes, suffix = _decode_image(image_value)
    if not image_bytes:
        return {
            "saved": False,
            "message": "image payload is missing or invalid",
            "paths": {},
        }

    review_root = root or default_review_root()
    session = _safe_token(payload.get("session") or datetime.now().strftime("%Y%m%d_demo"))
    issue_type = _safe_token(payload.get("issue_type") or "review")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"camera_{timestamp}_{issue_type}{suffix}"
    stem = Path(filename).stem

    raw_dir = review_root / "10_원천이미지_raw" / f"92_카메라_시연_오탐미탐_{session}"
    manifest_dir = review_root / "02_매니페스트_CSV"
    yolo_dir = review_root / "30_Roboflow_내보내기_YOLO" / f"camera_review_hardneg_{session}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    image_path = raw_dir / filename
    image_path.write_bytes(image_bytes)

    yolo_label_path = ""
    yolo_image_path = ""
    if issue_type == "false_positive":
        yolo_images_dir = yolo_dir / "train" / "images"
        yolo_labels_dir = yolo_dir / "train" / "labels"
        yolo_images_dir.mkdir(parents=True, exist_ok=True)
        yolo_labels_dir.mkdir(parents=True, exist_ok=True)
        yolo_image_path = str(yolo_images_dir / filename)
        yolo_label_path = str(yolo_labels_dir / f"{stem}.txt")
        (yolo_images_dir / filename).write_bytes(image_bytes)
        (yolo_labels_dir / f"{stem}.txt").write_text("", encoding="utf-8")

    record = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "image_path": str(image_path),
        "issue_type": issue_type,
        "expected_class": payload.get("expected_class") or "",
        "predicted_class": payload.get("predicted_class") or "",
        "confidence": payload.get("confidence") if payload.get("confidence") is not None else "",
        "step_index": payload.get("step_index") if payload.get("step_index") is not None else "",
        "step_title": payload.get("step_title") or "",
        "target_classes": "|".join(payload.get("target_classes") or []),
        "context_classes": "|".join(payload.get("context_classes") or []),
        "notes": payload.get("notes") or "",
        "yolo_image_path": yolo_image_path,
        "yolo_label_path": yolo_label_path,
    }

    csv_path = manifest_dir / f"camera_review_issues_{session}_manifest.csv"
    write_header = not csv_path.exists()
    with csv_path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(record.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(record)

    jsonl_path = manifest_dir / f"camera_review_issues_{session}_manifest.jsonl"
    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "saved": True,
        "message": "camera review capture saved",
        "paths": {
            "image_path": str(image_path),
            "csv_manifest": str(csv_path),
            "jsonl_manifest": str(jsonl_path),
            "yolo_image_path": yolo_image_path,
            "yolo_label_path": yolo_label_path,
        },
    }
