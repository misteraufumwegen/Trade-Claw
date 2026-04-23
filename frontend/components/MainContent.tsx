"use client";

import { useSelector } from "react-redux";
import { RootState } from "@/lib/store";
import Dashboard from "@/components/pages/Dashboard";
import Trading from "@/components/pages/Trading";
import Risk from "@/components/pages/Risk";
import Analytics from "@/components/pages/Analytics";
import Settings from "@/components/pages/Settings";
import styles from "./MainContent.module.css";

export default function MainContent() {
  const currentPage = useSelector((state: RootState) => state.app.currentPage);
  const sidebarOpen = useSelector((state: RootState) => state.app.sidebarOpen);

  const renderPage = () => {
    switch (currentPage) {
      case "dashboard":
        return <Dashboard />;
      case "trading":
        return <Trading />;
      case "risk":
        return <Risk />;
      case "analytics":
        return <Analytics />;
      case "settings":
        return <Settings />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <main className={`${styles.mainContent} ${sidebarOpen ? styles.withSidebar : styles.collapsedSidebar}`}>
      {renderPage()}
    </main>
  );
}
