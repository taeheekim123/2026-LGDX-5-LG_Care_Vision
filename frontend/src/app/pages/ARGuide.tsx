import { useNavigate, useLocation } from "react-router";
import { useState } from "react";
import { ChevronLeft, Camera } from "lucide-react";

const CHAT_STORAGE_KEY = "chat_messages_v20260612";

const steps = [
  { title: "전원 차단", desc: "전원을 끄고 플러그를 뽑으세요." },
  { title: "커버 열기", desc: "필터 커버를 천천히 들어 올리세요." },
  { title: "필터 분리", desc: "양쪽 잠금을 풀고 필터를 분리하세요." },
  { title: "세척 및 건조", desc: "흐르는 물로 헹군 후 그늘에 말리세요." },
  { title: "재장착", desc: "필터를 다시 끼우고 커버를 닫으세요." },
];

export function ARGuide() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/self-care";
  const [current, setCurrent] = useState(0);

  const goBack = () => navigate(from);
  const handlePrev = () => {
    if (current > 0) setCurrent(current - 1);
  };
  const handleNext = () => {
    if (current < steps.length - 1) {
      setCurrent(current + 1);
    } else {
      // AR 가이드 완료 시 채팅으로 돌아가면서 완료 확인 메시지 추가
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
        {/* 상단 헤더 */}
        <div className="flex items-center gap-3 px-4 pt-10 pb-4 bg-gradient-to-b from-black/60 to-transparent">
          <button onClick={goBack} className="p-1">
            <ChevronLeft size={22} className="text-white" />
          </button>

          {/* 프로세스 바 */}
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
                  <div
                    className={`flex-1 h-[2px] ${
                      idx < current ? "bg-white" : "bg-white/30"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 카메라 / AR 미리보기 영역 */}
        <div className="flex-1 relative flex items-center justify-center bg-gradient-to-b from-[#1a1a1a] to-[#2a2a2a] overflow-hidden">
          <div className="flex flex-col items-center gap-3 text-white/60">
            <Camera size={48} />
            <p className="font-['Pretendard:Medium',sans-serif] text-[13px]">
              카메라로 제품을 비춰주세요
            </p>
          </div>

          {/* AR 오버레이 박스 */}
          <div className="absolute top-[28%] left-[20%] w-[60%] h-[40%] border-2 border-[#F77B50] rounded-[12px]">
            <div className="absolute -top-7 left-0 bg-[#F77B50] text-white px-2 py-0.5 rounded-md font-['Pretendard:SemiBold',sans-serif] text-[11px]">
              {steps[current].title}
            </div>
          </div>
        </div>

        {/* 단계 설명 */}
        <div className="bg-white px-6 py-5">
          <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#F77B50] mb-1">
            STEP {current + 1} / {steps.length}
          </p>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[16px] text-black mb-1">
            {steps[current].title}
          </p>
          <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#666] mb-4">
            {steps[current].desc}
          </p>

          {/* 이전/다음 버튼 */}
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
