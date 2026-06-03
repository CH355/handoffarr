import { Outlet } from "react-router-dom";
import { Header } from "./foundation/Header";
import { MobileBottomTabBar } from "./foundation/MobileBottomTabBar";

export function AppShell() {
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
