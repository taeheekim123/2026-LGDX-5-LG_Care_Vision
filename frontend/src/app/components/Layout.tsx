import { Outlet, Navigate } from "react-router";
import { NavigationBar } from "./NavigationBar";

export function Layout() {
  const isLoggedIn = localStorage.getItem("isLoggedIn");
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="relative h-screen w-full max-w-[390px] overflow-hidden bg-[#f7f9f8]">
        <div className="h-[calc(100vh-67px)] overflow-y-auto">
          <Outlet />
        </div>
        <NavigationBar />
      </div>
    </div>
  );
}
