import { useParams, useNavigate } from "react-router";
import { ChevronLeft, Snowflake, Thermometer, Wind } from "lucide-react";
import imgImage6 from "../../imports/제품페이지관리/47f735f974d0900368394246ff236d4a45df2a58.png";

const recentHistory = [
  { id: "r1", type: "Self Care", title: "에어컨 필터 청소", date: "2일 전" },
  { id: "r2", type: "Self A/S", title: "리모컨 페어링", date: "1주 전" },
  { id: "r3", type: "Self Care", title: "실외기 외관 점검", date: "2주 전" },
];

const glass = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

const innerCard = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(16px)",
  WebkitBackdropFilter: "blur(16px)",
  border: "1px solid rgba(255,255,255,0.85)",
  boxShadow: "0 2px 12px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)",
};

export function DeviceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const careCount = 5;
  const asCount = 2;

  return (
    <div className="relative min-h-full w-full bg-[#f7f9f8]">
      <div className="pointer-events-none absolute -top-20 -left-16 w-72 h-72 rounded-full"
        style={{ background: "rgba(61,220,151,0.09)", filter: "blur(90px)" }} />
      <div className="pointer-events-none absolute top-[300px] -right-12 w-56 h-56 rounded-full"
        style={{ background: "rgba(100,210,190,0.08)", filter: "blur(80px)" }} />

      <div className="relative z-10 px-[18px] pt-[39px] pb-[20px] w-full max-w-[390px] mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => navigate("/device")} className="p-1">
            <ChevronLeft size={24} className="text-[#555]" />
          </button>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[20px] tracking-[-0.3px] text-[#111]">
            제품 상세
          </p>
        </div>

        {/* 제품 이미지 + 기본 정보 */}
        <div className="rounded-[20px] p-5 mb-4" style={glass}>
          <div className="flex justify-center mb-4">
            <img src={imgImage6} alt="에어컨" className="w-[200px] h-[100px] object-contain" />
          </div>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[18px] text-[#111] text-center mb-1">거실 에어컨</p>
          <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] text-center mb-4">
            LG 휘센 벽걸이 · 제품 #{id}
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

        {/* 제품 상태 */}
        <div className="rounded-[20px] p-5 mb-4" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-4">제품 상태</p>
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-[14px] p-3 flex flex-col items-center gap-1" style={innerCard}>
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center"
                style={{ background: "rgba(145,205,255,0.18)" }}>
                <Snowflake size={16} className="text-[#2060b0]" />
              </div>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[14px] text-[#111]">냉방</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">모드</p>
            </div>
            <div className="rounded-[14px] p-3 flex flex-col items-center gap-1" style={innerCard}>
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center"
                style={{ background: "rgba(251,191,36,0.12)" }}>
                <Thermometer size={16} className="text-[#d97706]" />
              </div>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[14px] text-[#111]">23°</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">설정 온도</p>
            </div>
            <div className="rounded-[14px] p-3 flex flex-col items-center gap-1" style={innerCard}>
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center"
                style={{ background: "rgba(61,220,151,0.10)" }}>
                <Wind size={16} className="text-[#1DB87A]" />
              </div>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[14px] text-[#111]">자동</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">바람 세기</p>
            </div>
          </div>
        </div>

        {/* 관리 요약 */}
        <div className="rounded-[20px] p-5 mb-4" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-4">관리 요약</p>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="rounded-[14px] p-4 text-center"
              style={{ background: "rgba(61,220,151,0.12)", border: "1px solid rgba(29,184,122,0.22)" }}>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[24px] text-[#0f8a58] mb-1">{careCount}</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#0f8a58]">Self Care 횟수</p>
            </div>
            <div className="rounded-[14px] p-4 text-center"
              style={{ background: "rgba(255,160,70,0.12)", border: "1px solid rgba(217,107,58,0.22)" }}>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[24px] text-[#d96b3a] mb-1">{asCount}</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#d96b3a]">Self A/S 횟수</p>
            </div>
          </div>
          <div className="pt-3" style={{ borderTop: "1px solid rgba(200,200,200,0.3)" }}>
            <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#888] mb-1">최근 관리 내용</p>
            <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-[#111]">
              {recentHistory[0].title} · {recentHistory[0].date}
            </p>
          </div>
        </div>

        {/* 최근 관리 이력 */}
        <div className="rounded-[20px] p-5" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-3">최근 관리 이력</p>
          <div className="space-y-3">
            {recentHistory.map((item) => (
              <div key={item.id} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span
                    className="py-0.5 rounded-[6px] font-['Pretendard:Medium',sans-serif] text-[11px] text-center inline-block"
                    style={{
                      minWidth: "64px",
                      ...(item.type === "Self Care"
                        ? { background: "rgba(61,220,151,0.12)", color: "#0f8a58", border: "1px solid rgba(29,184,122,0.22)" }
                        : { background: "rgba(255,160,70,0.12)", color: "#d96b3a", border: "1px solid rgba(217,107,58,0.22)" })
                    }}
                  >
                    {item.type}
                  </span>
                  <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-[#111]">{item.title}</p>
                </div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#888]">{item.date}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
