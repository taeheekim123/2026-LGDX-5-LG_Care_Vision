import { useNavigate, useLocation } from "react-router";
import { useEffect, useRef, useState } from "react";
import { ChevronLeft, Camera, ScanSearch, ShieldCheck } from "lucide-react";
import { API_BASE_URL } from "../api/client";
import {
  getCaptureSizeFromDimensions,
  getDetectionGuideText,
  getObjectCoverTransform,
  smoothBox,
  type DetectionBox,
  type DetectionMode,
  type FilterDetectionResponse,
  type CameraState,
} from "./arGuideDetection";

const CHAT_STORAGE_KEY = "chat_messages_v20260612";

interface ARGuideStep {
  title: string;
  desc: string;
  safety?: string;
  targetHint?: string;
}

interface ARGuideLocationState {
  from?: string;
  procedureType?: string;
  guideTitle?: string;
  guideSteps?: ARGuideStep[];
}

const defaultSteps: ARGuideStep[] = [
  {
    title: "전원 차단",
    desc: "전원을 끄고 플러그를 뽑으세요.",
    safety: "전원이 완전히 꺼진 상태에서만 다음 단계로 이동하세요.",
    targetHint: "전원 버튼 / 플러그",
  },
  {
    title: "커버 열기",
    desc: "필터 커버를 천천히 들어 올리세요.",
    safety: "커버가 걸리면 억지로 당기지 말고 여닫힘 방향을 다시 확인하세요.",
    targetHint: "전면 커버 상단",
  },
  {
    title: "필터 분리",
    desc: "양쪽 잠금을 풀고 필터를 분리하세요.",
    safety: "표시된 필터 위치와 실제 손 위치가 맞는지 확인한 뒤 분리하세요.",
    targetHint: "필터 그물망",
  },
  {
    title: "세척 및 건조",
    desc: "흐르는 물로 헹군 후 그늘에 말리세요.",
    safety: "젖은 필터는 완전히 건조한 뒤 재장착하세요.",
    targetHint: "분리한 필터",
  },
  {
    title: "재장착",
    desc: "필터를 다시 끼우고 커버를 닫으세요.",
    safety: "필터 방향이 맞는지 확인하고 커버를 천천히 닫으세요.",
    targetHint: "필터 삽입부",
  },
];

const getCaptureSize = (video: HTMLVideoElement) => {
  return getCaptureSizeFromDimensions(video.videoWidth, video.videoHeight);
};

const getStepSafetyText = (step: ARGuideStep) =>
  step.safety ?? "무리하게 분해하지 말고 이상하면 작업을 중단하세요.";

const getStepTargetText = (step: ARGuideStep) => step.targetHint ?? "필터 위치";

export function ARGuide() {
  const navigate = useNavigate();
  const location = useLocation();
  const routeState = (location.state as ARGuideLocationState | null) ?? {};
  const from = routeState.from ?? "/self-care";
  const steps = routeState.guideSteps?.length ? routeState.guideSteps : defaultSteps;
  const [current, setCurrent] = useState(0);
  const [cameraState, setCameraState] = useState<CameraState>("loading");
  const [detectionMode, setDetectionMode] = useState<DetectionMode>("none");
  const [lastDetection, setLastDetection] = useState<DetectionBox | null>(null);
  const [statusText, setStatusText] = useState("카메라 준비 중");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayRef = useRef<HTMLCanvasElement | null>(null);
  const captureRef = useRef<HTMLCanvasElement | null>(null);
  const smoothedBoxRef = useRef<DetectionBox | null>(null);
  const currentStep = steps[current];
  const stepSafetyText = getStepSafetyText(currentStep);
  const stepTargetText = getStepTargetText(currentStep);
  const detectionGuideText = getDetectionGuideText(cameraState, detectionMode, lastDetection);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment", width: { ideal: 640 }, height: { ideal: 480 } },
          audio: false,
        });
        if (cancelled) return;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        setCameraState("ready");
        setStatusText("필터 위치 탐지 중");
      } catch {
        setCameraState("denied");
        setStatusText("카메라 권한을 확인해주세요");
      }
    }

    startCamera();
    return () => {
      cancelled = true;
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (cameraState !== "ready") return;

    let busy = false;
    const interval = window.setInterval(async () => {
      const video = videoRef.current;
      const canvas = captureRef.current;
      if (!video || !canvas || video.readyState < 2 || busy) return;

      const { width, height } = getCaptureSize(video);
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(video, 0, 0, width, height);
      const imageDataUrl = canvas.toDataURL("image/jpeg", 0.72);

      busy = true;
      try {
        const response = await fetch(`${API_BASE_URL}/v1/ar/filter-detect`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image_data_url: imageDataUrl,
            image_width: width,
            image_height: height,
            confidence_threshold: 0.25,
            mock_fallback: false,
          }),
        });
        if (!response.ok) throw new Error(`filter detect failed: ${response.status}`);
        const result = (await response.json()) as FilterDetectionResponse;
        setDetectionMode(result.mode);
        const detection = result.detections[0] ?? null;
        if (detection) {
          const smoothed = smoothBox(smoothedBoxRef.current, detection);
          smoothedBoxRef.current = smoothed;
          setLastDetection(smoothed);
          setStatusText(result.mode === "mock" ? "필터 위치 예비 표시" : "필터 위치 탐지됨");
        } else {
          setLastDetection(null);
          smoothedBoxRef.current = null;
          setStatusText("필터를 찾는 중");
        }
      } catch {
        setDetectionMode("none");
        setStatusText("탐지 서버 연결 대기");
      } finally {
        busy = false;
      }
    }, 700);

    return () => window.clearInterval(interval);
  }, [cameraState]);

  useEffect(() => {
    const canvas = overlayRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const draw = () => {
      const rect = video.getBoundingClientRect();
      const width = Math.max(1, Math.round(rect.width));
      const height = Math.max(1, Math.round(rect.height));
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);
      if (!lastDetection) return;

      const captureSize = getCaptureSize(video);
      const transform = getObjectCoverTransform(width, height, captureSize.width, captureSize.height);
      const x = transform.offsetX + lastDetection.x * transform.scaleX;
      const y = transform.offsetY + lastDetection.y * transform.scaleY;
      const boxWidth = lastDetection.width * transform.scaleX;
      const boxHeight = lastDetection.height * transform.scaleY;

      if (x + boxWidth < 0 || y + boxHeight < 0 || x > width || y > height) return;
      const visibleX = Math.max(0, x);
      const visibleY = Math.max(0, y);
      const visibleWidth = Math.min(width - visibleX, boxWidth - Math.max(0, -x));
      const visibleHeight = Math.min(height - visibleY, boxHeight - Math.max(0, -y));
      if (visibleWidth <= 0 || visibleHeight <= 0) return;

      ctx.strokeStyle = "#F77B50";
      ctx.lineWidth = 3;
      ctx.shadowColor = "rgba(247, 123, 80, 0.45)";
      ctx.shadowBlur = 12;
      ctx.strokeRect(visibleX, visibleY, visibleWidth, visibleHeight);
      ctx.shadowBlur = 0;
      ctx.fillStyle = "#F77B50";
      ctx.fillRect(visibleX, Math.max(0, visibleY - 28), 118, 24);
      ctx.fillStyle = "#fff";
      ctx.font = "12px sans-serif";
      ctx.fillText(
        `필터 ${(lastDetection.confidence * 100).toFixed(0)}%`,
        visibleX + 8,
        Math.max(16, visibleY - 11),
      );
    };

    draw();
  }, [lastDetection]);

  const goBack = () => navigate(from);
  const handlePrev = () => {
    if (current > 0) setCurrent(current - 1);
  };
  const handleNext = () => {
    if (current < steps.length - 1) {
      setCurrent(current + 1);
    } else {
      if (from === "/chat") {
        const saved = localStorage.getItem(CHAT_STORAGE_KEY);
        const messages = saved ? JSON.parse(saved) : [];
        const doneMsg = {
          id: Date.now().toString(),
          type: "bot",
          content: "AR 가이드를 완료하셨나요?\n관리 내용을 기록해드릴게요.",
          time: new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }),
          showDoneAsk: true,
        };
        localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify([...messages, doneMsg]));
      }
      navigate(from);
    }
  };

  return (
    <div className="min-h-screen w-full bg-black">
      <div className="w-full max-w-[390px] mx-auto min-h-screen relative flex flex-col">
        <div className="flex items-center gap-3 px-4 pt-10 pb-4 bg-gradient-to-b from-black/60 to-transparent z-10">
          <button onClick={goBack} className="p-1">
            <ChevronLeft size={22} className="text-white" />
          </button>

          <div className="flex-1 flex items-center">
            {steps.map((_, idx) => (
              <div key={idx} className="flex items-center flex-1 last:flex-none">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold transition-colors ${
                    idx === current
                      ? "bg-[#F77B50] text-white scale-110"
                      : idx < current
                      ? "bg-white text-black"
                      : "bg-white/30 text-white"
                  }`}
                >
                  {idx + 1}
                </div>
                {idx < steps.length - 1 && (
                  <div className={`flex-1 h-[2px] ${idx < current ? "bg-white" : "bg-white/30"}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="flex-1 relative flex items-center justify-center bg-[#111] overflow-hidden">
          <video ref={videoRef} className="absolute inset-0 h-full w-full object-cover" muted playsInline />
          <canvas ref={overlayRef} className="absolute inset-0 h-full w-full" />
          <canvas ref={captureRef} className="hidden" />

          {cameraState !== "ready" && (
            <div className="relative z-10 flex flex-col items-center gap-3 text-white/70">
              <Camera size={48} />
              <p className="font-['Pretendard:Medium',sans-serif] text-[13px]">{statusText}</p>
            </div>
          )}

          <div className="absolute left-4 right-4 top-4 rounded-lg bg-black/45 px-3 py-2 text-white backdrop-blur-sm">
            <p className="font-['Pretendard:SemiBold',sans-serif] text-[12px]">{statusText}</p>
            <p className="font-['Pretendard:Medium',sans-serif] text-[10px] text-white/65">
              {detectionGuideText}
            </p>
          </div>
        </div>

        <div className="bg-white px-6 py-5">
          <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#F77B50] mb-1">
            STEP {current + 1} / {steps.length}
          </p>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[16px] text-black mb-1">
            {currentStep.title}
          </p>
          <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#666] mb-4">
            {currentStep.desc}
          </p>

          <div className="mb-4 space-y-2 rounded-lg border border-[#f0e0d8] bg-[#fff8f4] px-3 py-3">
            <div className="flex items-start gap-2">
              <ScanSearch size={16} className="mt-[1px] shrink-0 text-[#F77B50]" />
              <div>
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[12px] text-black">
                  확인 위치: {stepTargetText}
                </p>
                <p className="font-['Pretendard:Medium',sans-serif] text-[11px] leading-[1.45] text-[#777]">
                  {detectionGuideText}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <ShieldCheck size={16} className="mt-[1px] shrink-0 text-[#2f8f5b]" />
              <p className="font-['Pretendard:Medium',sans-serif] text-[11px] leading-[1.45] text-[#555]">
                {stepSafetyText}
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handlePrev}
              disabled={current === 0}
              className={`flex-1 rounded-2xl py-3 font-['Pretendard:SemiBold',sans-serif] text-[14px] border transition-colors ${
                current === 0
                  ? "border-[#e0e0e0] text-[#c0c0c0] bg-[#f8f8f8]"
                  : "border-[#F77B50] text-[#F77B50] bg-white hover:bg-[#fff4ef]"
              }`}
            >
              이전으로
            </button>
            <button
              onClick={handleNext}
              className="flex-1 rounded-2xl py-3 font-['Pretendard:SemiBold',sans-serif] text-[14px] text-white bg-gradient-to-r from-[#F77B50] to-[#F05C5C]"
            >
              {current === steps.length - 1 ? "완료" : "다음으로"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
