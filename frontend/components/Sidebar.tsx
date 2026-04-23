"use client";

import { useDispatch, useSelector } from "react-redux";
import { setCurrentPage } from "@/lib/slices/appSlice";
import { RootState } from "@/lib/store";
import styles from "./Sidebar.module.css";

interface NavItem {
  id: string;
  label: string;
  icon: string;
  page: "dashboard" | "trading" | "risk" | "analytics" | "settings";
}

const navItems: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: "📊", page: "dashboard" },
  { id: "trading", label: "Trading", icon: "💱", page: "trading" },
  { id: "risk", label: "Risk", icon: "⚠️", page: "risk" },
  { id: "analytics", label: "Analytics", icon: "📈", page: "analytics" },
  { id: "settings", label: "Settings", icon: "⚙️", page: "settings" },
];

export default function Sidebar() {
  const dispatch = useDispatch();
  const currentPage = useSelector((state: RootState) => state.app.currentPage);
  const sidebarOpen = useSelector((state: RootState) => state.app.sidebarOpen);

  return (
    <aside className={`${styles.sidebar} ${sidebarOpen ? styles.open : styles.collapsed}`}>
      <nav className={styles.nav}>
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`${styles.navItem} ${currentPage === item.page ? styles.active : ""}`}
            onClick={() => dispatch(setCurrentPage(item.page))}
            title={item.label}
          >
            <span className={styles.icon}>{item.icon}</span>
            {sidebarOpen && <span className={styles.label}>{item.label}</span>}
          </button>
        ))}
      </nav>

      <div className={styles.footer}>
        <div className={styles.version}>{sidebarOpen && <span>v0.1.0</span>}</div>
      </div>
    </aside>
  );
}
