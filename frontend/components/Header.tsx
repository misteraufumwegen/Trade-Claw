"use client";

import { useDispatch, useSelector } from "react-redux";
import { toggleSidebar } from "@/lib/slices/appSlice";
import { RootState } from "@/lib/store";
import styles from "./Header.module.css";

export default function Header() {
  const dispatch = useDispatch();
  const positions = useSelector((state: RootState) => state.positions);
  const quotes = useSelector((state: RootState) => state.quotes);

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <button
          className={styles.menuButton}
          onClick={() => dispatch(toggleSidebar())}
          aria-label="Toggle sidebar"
        >
          ☰
        </button>
        <h1 className={styles.title}>Trade-Claw</h1>
      </div>

      <div className={styles.center}>
        <div className={styles.quoteWidget}>
          <span className={styles.symbol}>EUR/USD</span>
          <span className={styles.price}>{quotes.quotes["EUR/USD"]?.bid || 1.0845}</span>
          <span
            className={`${styles.change} ${positions.totalPnl >= 0 ? styles.positive : styles.negative}`}
          >
            +{quotes.quotes["EUR/USD"]?.changePercent?.toFixed(2) || 0.14}%
          </span>
        </div>
      </div>

      <div className={styles.right}>
        <div className={styles.accountInfo}>
          <div className={styles.pnl}>
            <span className={styles.label}>P&L</span>
            <span
              className={`${styles.value} ${positions.totalPnl >= 0 ? styles.positive : styles.negative}`}
            >
              ${positions.totalPnl.toFixed(2)}
            </span>
          </div>
        </div>
        <div className={styles.userMenu}>
          <button className={styles.userButton} aria-label="User menu">
            👤
          </button>
        </div>
      </div>
    </header>
  );
}
