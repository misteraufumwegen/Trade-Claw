"use client";

import { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { AppDispatch, RootState } from "@/lib/store";
import { fetchQuotes, fetchPositions, fetchAccount } from "@/lib/thunks";
import styles from "./Dashboard.module.css";

export default function Dashboard() {
  const dispatch = useDispatch<AppDispatch>();
  const positions = useSelector((state: RootState) => state.positions);
  const quotes = useSelector((state: RootState) => state.quotes);
  const account = useSelector((state: RootState) => state.account);

  // Fetch data on mount
  useEffect(() => {
    dispatch(fetchQuotes(["EUR_USD", "GBP_USD", "SPY"]));
    dispatch(fetchPositions());
    dispatch(fetchAccount());
  }, [dispatch]);

  const calculateAccountMetrics = () => {
    const equity = 10000 + positions.totalPnl;
    const usedMargin = positions.positions.reduce((sum, p) => sum + (p.units * p.currentPrice) / 100, 0);
    const freeMargin = 100000 - usedMargin;
    const marginLevel = usedMargin > 0 ? (equity / usedMargin) * 100 : 100;
    return { equity, usedMargin, freeMargin, marginLevel };
  };

  const metrics = calculateAccountMetrics();

  return (
    <div className={styles.dashboard}>
      <h1 className={styles.title}>Dashboard</h1>

      {/* Key Metrics Grid */}
      <div className={styles.metricsGrid}>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Account Equity</div>
          <div className={styles.metricValue}>${metrics.equity.toFixed(2)}</div>
          <div className={styles.metricMeta}>Initial: $10,000.00</div>
        </div>

        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Total P&L</div>
          <div className={`${styles.metricValue} ${positions.totalPnl >= 0 ? styles.positive : styles.negative}`}>
            ${positions.totalPnl.toFixed(2)}
          </div>
          <div className={styles.metricMeta}>{((positions.totalPnl / 10000) * 100).toFixed(2)}% Return</div>
        </div>

        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Margin Level</div>
          <div className={styles.metricValue}>{metrics.marginLevel.toFixed(0)}%</div>
          <div className={styles.metricMeta}>Used: ${metrics.usedMargin.toFixed(2)}</div>
        </div>

        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Open Positions</div>
          <div className={styles.metricValue}>{positions.positions.length}</div>
          <div className={styles.metricMeta}>Active trades</div>
        </div>
      </div>

      {/* Positions Overview */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Open Positions</h2>
        <div className={styles.positionsTable}>
          <div className={styles.tableHeader}>
            <div className={styles.columnSymbol}>Symbol</div>
            <div className={styles.columnSide}>Side</div>
            <div className={styles.columnUnits}>Units</div>
            <div className={styles.columnPrice}>Entry Price</div>
            <div className={styles.columnPrice}>Current</div>
            <div className={styles.columnPnl}>P&L</div>
            <div className={styles.columnPnlPercent}>%</div>
          </div>
          {positions.positions.map((pos) => (
            <div key={pos.id} className={styles.tableRow}>
              <div className={styles.columnSymbol}>
                <strong>{pos.symbol}</strong>
              </div>
              <div className={styles.columnSide}>
                <span className={`${styles.badge} ${pos.side === "BUY" ? styles.buy : styles.sell}`}>
                  {pos.side}
                </span>
              </div>
              <div className={styles.columnUnits}>{pos.units.toLocaleString()}</div>
              <div className={styles.columnPrice}>{pos.entryPrice.toFixed(5)}</div>
              <div className={styles.columnPrice}>{pos.currentPrice.toFixed(5)}</div>
              <div className={`${styles.columnPnl} ${pos.pnl >= 0 ? styles.positive : styles.negative}`}>
                ${pos.pnl.toFixed(2)}
              </div>
              <div className={`${styles.columnPnlPercent} ${pos.pnlPercent >= 0 ? styles.positive : styles.negative}`}>
                {pos.pnlPercent >= 0 ? "+" : ""}{pos.pnlPercent.toFixed(2)}%
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Live Quotes */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Market Quotes</h2>
        <div className={styles.quotesGrid}>
          {Object.entries(quotes.quotes).map(([symbol, quote]) => (
            <div key={symbol} className={styles.quoteCard}>
              <div className={styles.quoteSymbol}>{symbol}</div>
              <div className={styles.quoteBidAsk}>
                <span>Bid: {quote.bid.toFixed(5)}</span>
                <span>Ask: {quote.ask.toFixed(5)}</span>
              </div>
              <div className={`${styles.quoteChange} ${quote.changePercent! >= 0 ? styles.positive : styles.negative}`}>
                {quote.changePercent! >= 0 ? "+" : ""}{quote.changePercent?.toFixed(2)}%
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
