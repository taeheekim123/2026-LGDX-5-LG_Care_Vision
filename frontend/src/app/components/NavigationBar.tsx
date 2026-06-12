import { Link, useLocation } from "react-router";
import { Home, Users, MessageCircle, Menu } from "lucide-react";

export function NavigationBar() {
  const location = useLocation();

  const navItems = [
    { path: "/", label: "Home", icon: Home },
    { path: "/device", label: "Device", icon: Users },
    { path: "/chat", label: "Chat", icon: MessageCircle },
    { path: "/settings", label: "Menu", icon: Menu },
  ];

  return (
    <div className="absolute bottom-0 left-0 right-0 h-[72px] z-50 flex items-end justify-center pb-[8px] px-[14px]">
      <div
        className="w-full flex items-center justify-around rounded-[28px] py-[10px] px-[4px]"
        style={{
          background: "rgba(255,255,255,0.72)",
          backdropFilter: "blur(28px)",
          WebkitBackdropFilter: "blur(28px)",
          border: "1px solid rgba(255,255,255,0.85)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.10), inset 0 1px 0 rgba(255,255,255,0.95)",
        }}
      >
      {navItems.map((item) => {
        const isActive =
          location.pathname === item.path ||
          (item.path === "/device" && location.pathname.startsWith("/device"));
        const Icon = item.icon;

        return (
          <Link
            key={item.path}
            to={item.path}
            className="flex flex-col gap-[3px] items-center justify-center p-[5px] w-[74px]"
          >
            <Icon
              size={22}
              strokeWidth={isActive ? 2 : 1.5}
              color={isActive ? "#1DB87A" : "#b0b8b4"}
            />
            <p
              className="font-['Pretendard:Medium',sans-serif] text-[11px] leading-[14px] tracking-[-0.18px] whitespace-nowrap"
              style={{ color: isActive ? "#1DB87A" : "#b0b8b4" }}
            >
              {item.label}
            </p>
          </Link>
        );
      })}
      </div>
    </div>
  );
}
