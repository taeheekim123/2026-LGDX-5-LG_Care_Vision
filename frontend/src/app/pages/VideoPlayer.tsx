import { useParams, useNavigate, useLocation } from "react-router";
import { ChevronLeft, Trash2, Star, Maximize, X } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import aiAlertVideo from "../../imports/AS-Q24ENXE_filter_cleaning_MVP_hyperframes.mp4";

const allVideos = {
  management: [
    {
      id: "1",
      title: "에어컨 필터 청소 방법",
      duration: "3:25",
      description: "에어컨 필터를 정기적으로 청소하면 냉방 효율이 향상됩니다.",
    },
    {
      id: "2",
      title: "실외기 관리 방법",
      duration: "2:45",
      description: "실외기 주변을 깨끗하게 유지하여 최적의 성능을 유지하세요.",
    },
    {
      id: "3",
      title: "겨울철 에어컨 보관 방법",
      duration: "4:10",
      description: "겨울철 에어컨을 올바르게 보관하는 방법을 알려드립니다.",
    },
  ],
  as: [
    {
      id: "1",
      title: "전원이 켜지지 않을 때",
      duration: "2:30",
      description: "전원 문제 해결 방법을 단계별로 안내합니다.",
    },
    {
      id: "2",
      title: "냉방이 안될 때",
      duration: "3:15",
      description: "냉방 불량 증상의 원인과 해결 방법입니다.",
    },
    {
      id: "3",
      title: "이상한 소음이 날 때",
      duration: "2:50",
      description: "에어컨에서 발생하는 소음의 원인을 파악하고 해결하세요.",
    },
  ],
};

export function VideoPlayer() {
  const { id, videoId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  // AI 알림 영상인지 확인
  const isAIAlertVideo = location.pathname === "/ai-alert-video";

  // 저장된 영상인지 확인
  const savedVideoId = (location.state as any)?.savedVideoId;
  const isSavedVideo = !!savedVideoId;

  // AI 알림 영상 정보
  const aiAlertVideoInfo = {
    title: "에어컨 필터 청소 방법",
    duration: "3:25",
    description: "오늘 대기질이 나쁩니다. 에어컨 필터를 정기적으로 청소하면 냉방 효율이 향상되고 실내 공기질을 개선할 수 있습니다.",
    videoSrc: aiAlertVideo,
  };

  // 현재 비디오 찾기
  const video = isAIAlertVideo
    ? aiAlertVideoInfo
    : allVideos.management.find((v) => v.id === videoId) ||
      allVideos.as.find((v) => v.id === videoId);

  if (!video) {
    return <div>비디오를 찾을 수 없습니다.</div>;
  }

  const handleDelete = () => {
    if (confirm(`"${video.title}" 영상을 삭제하시겠습니까?`)) {
      alert("영상이 삭제되었습니다.");
      navigate(`/device/${id}`);
    }
  };

  const handleDeleteSavedVideo = () => {
    if (confirm(`"${video.title}" 영상을 삭제하시겠습니까?`)) {
      // localStorage에서 저장된 영상 제거
      const savedVideos = JSON.parse(localStorage.getItem("savedVideos") || "[]");
      const updatedVideos = savedVideos.filter((v: any) => v.id !== savedVideoId);
      localStorage.setItem("savedVideos", JSON.stringify(updatedVideos));

      alert("저장된 영상이 삭제되었습니다.");
      navigate("/device/1");
    }
  };

  const handleBookmark = () => {
    setIsBookmarked(!isBookmarked);
  };

  const handleBack = () => {
    if (isAIAlertVideo) {
      navigate(isSavedVideo ? "/device/1" : "/");
    } else {
      navigate(`/device/${id}`);
    }
  };

  const handleFullscreen = () => {
    setIsFullscreen(true);
  };

  const closeFullscreen = () => {
    setIsFullscreen(false);
  };

  useEffect(() => {
    if (isFullscreen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isFullscreen]);

  return (
    <div className="bg-gradient-to-t from-[rgba(255,210,221,0.2)] to-[rgba(255,192,196,0.2)] via-[59.135%] via-[rgba(220,221,230,0.2)] min-h-full pb-8 w-full">
      <div className="px-[18px] pt-[39px] w-full max-w-[390px] mx-auto">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <button onClick={handleBack} className="p-1">
              <ChevronLeft size={24} className="text-[#606060]" />
            </button>
            <p className="font-['Pretendard:Medium',sans-serif] text-[20px] tracking-[-0.3px] text-black leading-[15px]">
              영상 재생
            </p>
          </div>
          <button
            onClick={handleBookmark}
            className="p-1 transition-transform hover:scale-110"
          >
            <Star
              size={24}
              className={isBookmarked ? "text-[#FFD700] fill-[#FFD700]" : "text-[#d0d0d0]"}
              strokeWidth={1.5}
            />
          </button>
        </div>

        {/* 비디오 플레이어 */}
        <div className="relative bg-gray-900 rounded-[15px] mb-6 aspect-video flex items-center justify-center overflow-hidden">
          {(isAIAlertVideo || videoId === "1") ? (
            <>
              <video
                ref={videoRef}
                controls
                className="w-full h-full"
                src={aiAlertVideo}
                controlsList="nodownload"
              >
                브라우저가 비디오 태그를 지원하지 않습니다.
              </video>
              <button
                onClick={handleFullscreen}
                className="absolute top-3 right-3 bg-black/50 hover:bg-black/70 p-2 rounded-[8px] transition-colors z-10"
                title="전체화면"
              >
                <Maximize size={20} className="text-white" />
              </button>
            </>
          ) : (
            <div className="text-white text-center">
              <p className="font-['Pretendard:Medium',sans-serif] text-[18px] mb-2">
                비디오 플레이어
              </p>
              <p className="font-['Pretendard:Regular',sans-serif] text-[14px] text-gray-400">
                {video.duration}
              </p>
            </div>
          )}
        </div>

        {/* 비디오 정보 */}
        <div className="bg-white rounded-[15px] p-6 mb-4">
          <h2 className="font-['Pretendard:SemiBold',sans-serif] text-[18px] text-black mb-3">
            {video.title}
          </h2>
          <p className="font-['Pretendard:Regular',sans-serif] text-[14px] text-[#606060] leading-relaxed mb-4">
            {video.description}
          </p>
          <div className="flex items-center gap-2 text-[#949ba5] text-[13px]">
            <span className="font-['Pretendard:Regular',sans-serif]">재생시간</span>
            <span>·</span>
            <span className="font-['Pretendard:Medium',sans-serif]">{video.duration}</span>
          </div>
        </div>

        {/* 삭제 버튼 */}
        {isSavedVideo ? (
          <button
            onClick={handleDeleteSavedVideo}
            className="w-full flex items-center justify-center gap-2 py-3 bg-[#fff0f0] hover:bg-[#ffe0e0] rounded-[15px] transition-colors"
          >
            <Trash2 size={18} className="text-[#ff4c49]" />
            <span className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#ff4c49]">
              저장된 영상 삭제
            </span>
          </button>
        ) : !isAIAlertVideo && (
          <button
            onClick={handleDelete}
            className="w-full flex items-center justify-center gap-2 py-3 bg-[#fff0f0] hover:bg-[#ffe0e0] rounded-[15px] transition-colors"
          >
            <Trash2 size={18} className="text-[#ff4c49]" />
            <span className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#ff4c49]">
              영상 삭제
            </span>
          </button>
        )}
      </div>

      {/* 전체화면 모달 - Portal을 사용해 body에 직접 렌더링 */}
      {isFullscreen && createPortal(
        <div className="fixed inset-0 bg-black z-[9999] flex items-center justify-center" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0 }}>
          <button
            onClick={closeFullscreen}
            className="absolute top-4 right-4 bg-white/20 hover:bg-white/30 p-2 rounded-full transition-colors z-10"
          >
            <X size={24} className="text-white" />
          </button>
          <video
            controls
            autoPlay
            className="w-full h-full"
            src={aiAlertVideo}
            controlsList="nodownload"
          >
            브라우저가 비디오 태그를 지원하지 않습니다.
          </video>
        </div>,
        document.body
      )}
    </div>
  );
}
