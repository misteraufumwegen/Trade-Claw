"use client";

import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import MainContent from "@/components/MainContent";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.app}>
      <Header />
      <div className={styles.container}>
        <Sidebar />
        <MainContent />
      </div>
    </div>
  );
}
