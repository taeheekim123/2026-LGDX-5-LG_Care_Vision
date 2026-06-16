export interface DetectionBox {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  class_name: string;
}

export interface FilterDetectionResponse {
  model_loaded: boolean;
  mode: "yolo" | "mock" | "none";
  image_width: number;
  image_height: number;
  detections: DetectionBox[];
  message?: string | null;
}

export type CameraState = "loading" | "ready" | "denied";
export type DetectionMode = "yolo" | "mock" | "none";

export const CAPTURE_WIDTH = 416;

export const smoothBox = (previous: DetectionBox | null, next: DetectionBox, alpha = 0.35): DetectionBox => {
  if (!previous) return next;
  return {
    ...next,
    x: previous.x + (next.x - previous.x) * alpha,
    y: previous.y + (next.y - previous.y) * alpha,
    width: previous.width + (next.width - previous.width) * alpha,
    height: previous.height + (next.height - previous.height) * alpha,
  };
};

export const getCaptureSizeFromDimensions = (videoWidth: number, videoHeight: number) => {
  const sourceRatio = videoHeight ? videoWidth / videoHeight : 4 / 3;
  return {
    width: CAPTURE_WIDTH,
    height: Math.max(1, Math.round(CAPTURE_WIDTH / sourceRatio)),
  };
};

export const getObjectCoverTransform = (
  containerWidth: number,
  containerHeight: number,
  sourceWidth: number,
  sourceHeight: number,
) => {
  const sourceRatio = sourceWidth / Math.max(1, sourceHeight);
  const containerRatio = containerWidth / Math.max(1, containerHeight);
  if (sourceRatio > containerRatio) {
    const renderedWidth = containerHeight * sourceRatio;
    return {
      offsetX: (containerWidth - renderedWidth) / 2,
      offsetY: 0,
      scaleX: renderedWidth / sourceWidth,
      scaleY: containerHeight / sourceHeight,
    };
  }

  const renderedHeight = containerWidth / sourceRatio;
  return {
    offsetX: 0,
    offsetY: (containerHeight - renderedHeight) / 2,
    scaleX: containerWidth / sourceWidth,
    scaleY: renderedHeight / sourceHeight,
  };
};

export const getDetectionGuideText = (
  cameraState: CameraState,
  detectionMode: DetectionMode,
  lastDetection: DetectionBox | null,
) => {
  if (cameraState === "denied") return "카메라 권한을 허용하면 필터 위치 안내가 표시됩니다.";
  if (cameraState === "loading") return "카메라 화면을 준비하고 있습니다.";
  if (!lastDetection) return "필터가 화면 중앙에 보이도록 에어컨을 비춰주세요.";
  if (detectionMode === "mock") return "예비 위치 표시 중입니다. best.pt 연결 후 실제 탐지로 전환됩니다.";
  if (detectionMode === "yolo") return "탐지된 필터 위치를 기준으로 현재 단계를 진행하세요.";
  return "탐지 서버 연결을 확인하고 있습니다.";
};
