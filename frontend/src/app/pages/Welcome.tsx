import { useState } from "react";
import { useNavigate } from "react-router";
import { motion } from "motion/react";
import careVisionLogo from "../../imports/care-vision-logo.svg";
import careVisionLogoIcon from "../../imports/care_vision_logo_icon.png";

const pageBackground =
  "linear-gradient(160deg, #d6f2e8 0%, #f0f8e8 30%, #fce8f0 65%, #ede8f8 100%)";

const primaryButtonStyle = {
  background: "linear-gradient(135deg, #3DDC97 0%, #14B989 100%)",
  boxShadow: "0 8px 24px rgba(29,184,122,0.32), inset 0 1px 0 rgba(255,255,255,0.25)",
};

const secondaryButtonStyle = {
  background: "rgba(255,255,255,0.65)",
  backdropFilter: "blur(16px)",
  WebkitBackdropFilter: "blur(16px)",
  border: "1px solid rgba(255,255,255,0.9)",
  boxShadow: "0 4px 16px rgba(0,0,0,0.06)",
  color: "#14B989",
};

export function Welcome() {
  const navigate = useNavigate();
  const [isLeaving, setIsLeaving] = useState(false);

  const handleRouteChange = (path: string) => {
    if (isLeaving) return;
    setIsLeaving(true);
    window.setTimeout(() => navigate(path), 360);
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <motion.div
        className="relative h-screen w-full max-w-[390px] overflow-hidden flex flex-col items-center justify-center px-[28px]"
        style={{ background: pageBackground }}
        animate={isLeaving ? { opacity: 0, scale: 0.985, y: -10, filter: "blur(6px)" } : { opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
        transition={{ duration: isLeaving ? 0.36 : 0.42, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="flex flex-col items-center gap-4" style={{ transform: "translateY(-20px)" }}>
          <motion.img
            src={careVisionLogoIcon}
            alt="Care Vision app icon"
            className="h-[104px] w-[104px] rounded-[26px] object-cover"
            initial={{ scale: 0.82, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.55, ease: [0.34, 1.15, 0.64, 1] }}
            style={{
              boxShadow: "0 16px 42px rgba(29,184,122,0.22), 0 4px 16px rgba(255,255,255,0.55)",
            }}
          />

          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5, ease: [0.34, 1.15, 0.64, 1] }}
          >
            <img src={careVisionLogo} alt="Care Vision" className="w-[190px] h-auto" />
          </motion.div>

          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.36, duration: 0.42, ease: [0.34, 1.1, 0.64, 1] }}
            className="font-['Pretendard:Medium',sans-serif] text-[14px] text-[#777] leading-[1.5] text-center"
          >
            India Home Appliance Slef Care and A/S
            <br />
            AR Guide Service.
          </motion.p>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.75, duration: 0.45, ease: [0.34, 1.1, 0.64, 1] }}
          className="absolute bottom-[52px] w-full px-[28px] flex flex-col gap-3"
        >
          <button
            onClick={() => handleRouteChange("/login")}
            disabled={isLeaving}
            className="w-full text-white rounded-[18px] py-[15px] font-['Pretendard:SemiBold',sans-serif] text-[15px] transition-opacity hover:opacity-90"
            style={primaryButtonStyle}
          >
            Log In
          </button>
          <button
            onClick={() => handleRouteChange("/signup")}
            disabled={isLeaving}
            className="w-full rounded-[18px] py-[15px] font-['Pretendard:SemiBold',sans-serif] text-[15px] transition-opacity hover:opacity-90"
            style={secondaryButtonStyle}
          >
            Sign Up
          </button>
        </motion.div>
      </motion.div>
    </div>
  );
}
