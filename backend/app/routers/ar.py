from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_service
from ..schemas import (
    ARCameraReviewCaptureRequest,
    ARCameraReviewCaptureResponse,
    ARFilterDetectionRequest,
    ARFilterDetectionResponse,
    ARPlanRequest,
    ARSessionCreateRequest,
    ARSessionUpdateRequest,
)
from ..services import CareShotBackendService
from ..ar_camera_review_service import save_camera_review_capture
from ..yolo_filter_service import get_filter_detection_service_for_profile


router = APIRouter(prefix="/ar", tags=["ar"])


@router.post("/plans")
def create_ar_plan(
    request: ARPlanRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    payload = request.model_dump()
    analysis = payload.get("analysis") or service.analyze(payload)
    return service.plan_from_analysis(analysis)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_ar_session(
    request: ARSessionCreateRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    return service.create_session(request.model_dump())


@router.get("/sessions/{session_id}")
def get_ar_session(
    session_id: str,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {session_id}")
    return session


@router.patch("/sessions/{session_id}")
def update_ar_session(
    session_id: str,
    request: ARSessionUpdateRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    session = service.update_session(session_id, request.model_dump(exclude_unset=True))
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {session_id}")
    return session


@router.post("/filter-detect", response_model=ARFilterDetectionResponse)
def detect_filter_bbox(request: ARFilterDetectionRequest) -> dict:
    image_payload = request.image_data_url or request.image_base64
    detector = get_filter_detection_service_for_profile(
        request.model_profile or "",
        request.procedure_type or "",
    )
    return detector.detect(
        image_payload=image_payload,
        image_width=request.image_width,
        image_height=request.image_height,
        confidence_threshold=request.confidence_threshold,
        target_classes=request.target_classes,
        require_context_classes=request.require_context_classes,
        mock_fallback=request.mock_fallback,
        debug_detections=request.debug_detections,
    )


@router.post("/camera-review-capture", response_model=ARCameraReviewCaptureResponse)
def create_camera_review_capture(request: ARCameraReviewCaptureRequest) -> dict:
    result = save_camera_review_capture(request.model_dump())
    if not result["saved"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
    return result
