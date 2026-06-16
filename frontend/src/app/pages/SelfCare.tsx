import { useNavigate } from "react-router";
import { ChevronLeft, Maximize2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import acImage from "../../imports/제품페이지관리/47f735f974d0900368394246ff236d4a45df2a58.png";
import { completeGuide, getGuideOptions } from "../api/care";
import type { ChatGuideOptions, ChatManualGuide } from "../types/chat";
import { getCurrentUserEmail } from "../utils/authSession";

const glass = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
} as React.CSSProperties;

const FILTER_CLEANING_STEPS = [
  "전원을 끄고 플러그를 뽑습니다",
  "필터 커버를 천천히 열어 올립니다",
  "잠금을 풀고 필터를 분리합니다",
  "흐르는 물로 세척 후 그늘에 말립니다",
  "필터를 다시 장착하고 커버를 닫습니다",
];

const AR_GUIDE_STEP_TITLES: Record<string, string[]> = {
  filter_cleaning: ["전원 차단", "커버 열기", "필터 분리", "세척 및 건조", "재장착"],
};

const youtubeEmbedUrl = (url?: string | null, videoId?: string) => {
  if (videoId) return `https://www.youtube.com/embed/${videoId}`;
  if (!url) return null;
  const watchMatch = url.match(/[?&]v=([^&]+)/);
  if (watchMatch?.[1]) return `https://www.youtube.com/embed/${watchMatch[1]}`;
  const shortMatch = url.match(/youtu\.be\/([^?&]+)/);
  if (shortMatch?.[1]) return `https://www.youtube.com/embed/${shortMatch[1]}`;
  return null;
};

const extractGuideSteps = (guide?: ChatManualGuide, procedureType?: string) => {
  if (procedureType === "filter_cleaning") return FILTER_CLEANING_STEPS;
  const text = guide?.guide_text || guide?.summary || "";
  const steps = text
    .split(/\n+/)
    .map((line) => line.replace(/^\s*(?:\d+[\).\s-]*|[①-⑳]\s*)/, "").trim())
    .filter((line) => line.length > 0);
  return steps.length > 0 ? steps : FILTER_CLEANING_STEPS;
};

const arGuideStepsFromOptions = (guideOptions?: ChatGuideOptions) => {
  const procedureType = guideOptions?.procedure_type || "filter_cleaning";
  const manual = guideOptions?.manual_guides?.[0];
  const titles = AR_GUIDE_STEP_TITLES[procedureType] ?? AR_GUIDE_STEP_TITLES.filter_cleaning;
  return extractGuideSteps(manual, procedureType).map((desc, index) => ({
    title: titles[index] || `STEP ${index + 1}`,
    desc,
  }));
};

const guideVideo = (guideOptions?: ChatGuideOptions) => {
  const youtube = guideOptions?.youtube_recommendations?.[0];
  const manual = guideOptions?.manual_guides?.[0];
  const embedUrl = youtubeEmbedUrl(youtube?.source_url, youtube?.video_id) || youtubeEmbedUrl(manual?.video_url);
  return {
    title: youtube?.title || manual?.title || "LG 공식 영상 가이드",
    embedUrl,
  };
};

export function SelfCare() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"manual" | "ar">("manual");
  const [guideOptions, setGuideOptions] = useState<ChatGuideOptions | null>(null);
  const [isGuideLoading, setIsGuideLoading] = useState(true);
  const [guideError, setGuideError] = useState("");
  const [isCompleting, setIsCompleting] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadGuideOptions() {
      try {
        const options = await getGuideOptions({
          userId: getCurrentUserEmail(),
          deviceId: "D001",
          procedureType: "filter_cleaning",
          serviceFlowType: "self_care",
          languageCode: "en",
        });
        if (!cancelled) {
          setGuideOptions(options);
          setGuideError("");
        }
      } catch {
        if (!cancelled) {
          setGuideOptions(null);
          setGuideError("공식 가이드 API 연결을 확인하지 못했어요.");
        }
      } finally {
        if (!cancelled) setIsGuideLoading(false);
      }
    }

    loadGuideOptions();
    return () => {
      cancelled = true;
    };
  }, []);

  const manualGuide = guideOptions?.manual_guides?.[0];
  const steps = useMemo(
    () => extractGuideSteps(manualGuide, guideOptions?.procedure_type || "filter_cleaning"),
    [guideOptions?.procedure_type, manualGuide],
  );
  const video = guideVideo(guideOptions ?? undefined);

  const handleDone = async () => {
    setIsCompleting(true);
    try {
      const guideId = (manualGuide as { guide_id?: string | number } | undefined)?.guide_id ?? 1;
      await completeGuide({
        userId: getCurrentUserEmail(),
        deviceId: "D001",
        guideId,
        procedureType: guideOptions?.procedure_type || "filter_cleaning",
        serviceFlowType: "self_care",
      });
    } catch {
      // 로컬 시연 기록은 유지하되, 백엔드 실패는 화면 흐름을 막지 않는다.
    }
    const history = JSON.parse(localStorage.getItem("careHistory") || "[]");
    history.push({
      id: Date.now().toString(),
      type: "Self Care",
      title: "에어컨 필터 청소",
      date: new Date().toISOString(),
    });
    localStorage.setItem("careHistory", JSON.stringify(history));
    setIsCompleting(false);
    navigate("/", { state: { aiDismissed: true } });
  };

  const handleSkip = () => navigate("/");
  const handleStartArGuide = () => {
    navigate("/ar-guide", {
      state: {
        from: "/self-care",
        procedureType: guideOptions?.procedure_type || "filter_cleaning",
        guideTitle: "필터 청소",
        guideSteps: arGuideStepsFromOptions(guideOptions ?? undefined),
      },
    });
  };

  const cardCls = "rounded-[20px] p-5";

  const DoneSection = () => (
    <div className={cardCls} style={glass}>
      <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-4 text-center">관리를 완료하셨나요?</p>
      <div className="flex gap-3">
        <button
          onClick={handleDone}
          disabled={isCompleting}
          className="flex-1 rounded-2xl py-3 text-[14px] font-semibold text-white bg-gradient-to-r from-[#F77B50] to-[#F05C5C] hover:opacity-90 transition-opacity"
        >
          {isCompleting ? "저장 중" : "예"}
        </button>
        <button
          onClick={handleSkip}
          className="flex-1 rounded-2xl py-3 text-[14px] font-semibold text-[#F77B50] bg-white border border-[#F77B50] hover:bg-orange-50 transition-colors"
        >
          아니요
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen w-full bg-gradient-to-b from-[#F3FFF7] via-[#FAF3E3] to-[#FEECD7]">
      <div className="w-full max-w-[390px] mx-auto pb-10">

        {/* 헤더 */}
        <div className="flex items-center gap-1 px-4 pt-10 pb-5">
          <button onClick={() => navigate("/")} className="p-1">
            <ChevronLeft size={22} className="text-[#555]" />
          </button>
          <p className="font-['Pretendard:Medium',sans-serif] text-[20px] tracking-[-0.3px] text-black leading-[15px]">
            셀프 케어
          </p>
        </div>

        {/* 제품 카드 — DeviceDetail 동일 구조 */}
        <div className="mx-6 mb-5">
          <div className="rounded-[20px] p-5" style={glass}>
            <div className="flex justify-center mb-4">
              <img src={acImage} alt="에어컨" className="w-[200px] h-[100px] object-contain" />
            </div>
            <p className="font-['Pretendard:SemiBold',sans-serif] text-[18px] text-[#111] text-center mb-1">거실 에어컨</p>
            <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] text-center mb-4">
              LG 휘센 벽걸이
            </p>
            <div className="grid grid-cols-2 gap-2 pt-4" style={{ borderTop: "1px solid rgba(200,200,200,0.3)" }}>
              <div className="flex justify-between">
                <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">제품군</p>
                <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#111]">에어컨</p>
              </div>
              <div className="flex justify-between">
                <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">등록일</p>
                <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#111]">2024.01.15</p>
              </div>
            </div>
          </div>
        </div>

        {/* 탭 */}
        <div className="flex mx-6 mb-5 border-b border-[#e0e0e0]">
          {(["manual", "ar"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2.5 text-[14px] font-semibold border-b-2 -mb-px transition-colors ${
                activeTab === tab
                  ? "text-[#F05C5C] border-[#F05C5C]"
                  : "text-[#b0b0b0] border-transparent"
              }`}
            >
              {tab === "manual" ? "매뉴얼" : "AR"}
            </button>
          ))}
        </div>

        {/* 메뉴얼 탭 */}
        {activeTab === "manual" && (
          <div className="mx-6 flex flex-col gap-4">
            {/* 영상 플레이어 */}
            <div className="rounded-[20px] overflow-hidden" style={glass}>
              <div className="w-full aspect-video bg-[#e8ecef] flex items-center justify-center relative">
                <button className="absolute top-3 right-3 w-8 h-8 bg-white/80 rounded-lg flex items-center justify-center">
                  <Maximize2 size={16} className="text-[#555]" />
                </button>
                {video.embedUrl ? (
                  <iframe
                    className="w-full h-full"
                    src={video.embedUrl}
                    title={video.title}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowFullScreen
                  />
                ) : (
                  <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#999]">
                    {isGuideLoading ? "공식 영상을 불러오는 중" : "공식 영상 준비 중"}
                  </p>
                )}
              </div>
            </div>

            {/* 단계 카드 */}
            <div className={cardCls} style={glass}>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-4">진행 순서</p>
              {guideError && (
                <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#F05C5C] mb-3">{guideError}</p>
              )}
              <div className="flex flex-col gap-3">
                {steps.map((step, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="w-[22px] h-[22px] rounded-full bg-gradient-to-r from-[#F77B50] to-[#F05C5C] flex items-center justify-center flex-shrink-0 mt-[1px]">
                      <span className="text-[11px] font-bold text-white">{i + 1}</span>
                    </span>
                    <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#555] leading-snug pt-[2px]">{step}</p>
                  </div>
                ))}
              </div>
            </div>

            <DoneSection />
          </div>
        )}

        {/* AR 탭 */}
        {activeTab === "ar" && (
          <div className="mx-6 flex flex-col gap-4">
            {/* 단계 카드 */}
            <div className={cardCls} style={glass}>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-4">진행 순서</p>
              <div className="flex flex-col gap-3">
                {steps.map((step, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="w-[22px] h-[22px] rounded-full bg-gradient-to-r from-[#F77B50] to-[#F05C5C] flex items-center justify-center flex-shrink-0 mt-[1px]">
                      <span className="text-[11px] font-bold text-white">{i + 1}</span>
                    </span>
                    <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#555] leading-snug pt-[2px]">{step}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* AR 가이드 버튼 */}
            <button
              onClick={handleStartArGuide}
              className="w-full rounded-2xl py-4 text-[15px] font-semibold text-white bg-gradient-to-r from-[#F77B50] to-[#F05C5C] hover:opacity-90 transition-opacity"
            >
              AR 가이드 시작하기
            </button>

            <DoneSection />
          </div>
        )}
      </div>
    </div>
  );
}
