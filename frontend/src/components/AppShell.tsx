import { Outlet, useLocation } from "react-router-dom";
import { Header } from "./foundation/Header";
import { MobileBottomTabBar } from "./foundation/MobileBottomTabBar";
import { useEffect, useRef } from "react";
import { auditMark } from "@/perf/audit";

export function AppShell() {
  const location = useLocation();
  const previousPath = useRef<string | null>(null);

  useEffect(() => {
    auditMark("navigation", `${previousPath.current ?? "initial"} -> ${location.pathname}`, {
      from: previousPath.current,
      to: location.pathname,
    });
    previousPath.current = location.pathname;
  }, [location.pathname]);

  return (
    <div className="min-h-full bg-bg text-text">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <Header />
      <main
        id="main"
        role="main"
        className="mx-auto w-full max-w-page px-4 pb-24 pt-6 md:px-6 md:pb-12 md:pt-8"
      >
        <Outlet />
      </main>
      <MobileBottomTabBar />
    </div>
  );
}
