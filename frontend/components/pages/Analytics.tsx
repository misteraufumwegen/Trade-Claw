"use client";

import { useSelector } from "react-redux";
import { RootState } from "@/lib/store";
import styles from "./Analytics.module.css";

export default function Analytics() {
  const backtest = useSelector((state: RootState) => state.backtest);
  const result = backtest.currentResult;

  if (!result) {
    return (
      <div className={styles.analytics}>
        <h1 className={styles.title}>Analytics</h1>
        <div className={styles.empty}>No backtest results available</div>
      </div>
    );
  }

  return (
    <div className={styles.analytics}>
      <h1 className={styles.title}>Analytics - {result.strategyName}</h1>

      {/* Summary Stats */}
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Total Return</div>
          <div className={`${styles.statValue} ${result.totalReturnPercent >= 0 ? styles.positive : styles.negative}`}>
            {result.totalReturnPercent >= 0 ? "+" : ""}{result.totalReturnPercent.toFixed(2)}%
          </div>
          <div className={styles.statMeta}>${result.totalReturn.toFixed(2)}</div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statLabel}>Sharpe Ratio</div>
          <div className={styles.statValue}>{result.sharpeRatio.toFixed(2)}</div>
          <div className={styles.statMeta}>Risk-adjusted returns</div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statLabel}>Profit Factor</div>
          <div className={styles.statValue}>{result.profitFactor.toFixed(2)}</div>
          <div className={styles.statMeta}>Gross profit / loss</div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statLabel}>Max Drawdown</div>
          <div className={`${styles.statValue} ${styles.negative}`}>
            -{result.maxDrawdownPercent.toFixed(2)}%
          </div>
          <div className={styles.statMeta}>${result.maxDrawdown.toFixed(2)}</div>
        </div>
      </div>

      {/* Equity Curve (ASCII visualization) */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Equity Curve</h2>
        <div className={styles.equityCurveChart}>
          {/* Simple ASCII bar chart representation */}
          <div className={styles.chartContainer}>
            {result.equityCurve.map((point, idx) => {
              const minBalance = Math.min(...result.equityCurve.map((p) => p.balance));
              const maxBalance = Math.max(...result.equityCurve.map((p) => p.balance));
              const range = maxBalance - minBalance || 1;
              const normalized = ((point.balance - minBalance) / range) * 100;

              return (
                <div key={idx} className={styles.chartBar}>
                  <div
                    className={styles.chartBarFill}
                    style={{
                      height: `${normalized}%`,
                      backgroundColor:
                        point.balance > result.initialBalance
                          ? "#10B981"
                          : "#EF4444",
                    }}
                    title={`$${point.balance.toFixed(2)}`}
                  />
                </div>
              );
            })}
          </div>
          <div className={styles.chartLabel}>
            <span>Initial: ${result.initialBalance.toFixed(2)}</span>
            <span>Final: ${result.finalBalance.toFixed(2)}</span>
          </div>
        </div>
      </section>

      {/* Trade Stats */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Trade Statistics</h2>
        <div className={styles.statsTable}>
          <div className={styles.tableRow}>
            <span className={styles.label}>Total Trades</span>
            <span className={styles.value}>{result.totalTrades}</span>
          </div>
          <div className={styles.tableRow}>
            <span className={styles.label}>Winning Trades</span>
            <span className={`${styles.value} ${styles.positive}`}>{result.winningTrades}</span>
          </div>
          <div className={styles.tableRow}>
            <span className={styles.label}>Losing Trades</span>
            <span className={`${styles.value} ${styles.negative}`}>{result.losingTrades}</span>
          </div>
          <div className={styles.tableRow}>
            <span className={styles.label}>Win Rate</span>
            <span className={styles.value}>
              {((result.winningTrades / result.totalTrades) * 100).toFixed(1)}%
            </span>
          </div>
          <div className={styles.tableRow}>
            <span className={styles.label}>Avg Win</span>
            <span className={`${styles.value} ${styles.positive}`}>${result.avgWin.toFixed(2)}</span>
          </div>
          <div className={styles.tableRow}>
            <span className={styles.label}>Avg Loss</span>
            <span className={`${styles.value} ${styles.negative}`}>-${result.avgLoss.toFixed(2)}</span>
          </div>
        </div>
      </section>

      {/* Recent Trades */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Trade History ({result.trades.length})</h2>
        <div className={styles.tradesTable}>
          <div className={styles.tableHeader}>
            <div>Entry Time</div>
            <div>Exit Time</div>
            <div>Side</div>
            <div>Entry</div>
            <div>Exit</div>
            <div>P&L</div>
            <div>Return %</div>
          </div>
          {result.trades.map((trade, idx) => (
            <div key={idx} className={styles.tableRow}>
              <div className={styles.time}>
                {new Date(trade.entryTime).toLocaleString()}
              </div>
              <div className={styles.time}>
                {new Date(trade.exitTime).toLocaleString()}
              </div>
              <div>
                <span className={`${styles.badge} ${trade.side === "BUY" ? styles.buy : styles.sell}`}>
                  {trade.side}
                </span>
              </div>
              <div className={styles.price}>{trade.entryPrice.toFixed(5)}</div>
              <div className={styles.price}>{trade.exitPrice.toFixed(5)}</div>
              <div className={`${styles.price} ${trade.pnl >= 0 ? styles.positive : styles.negative}`}>
                ${trade.pnl.toFixed(2)}
              </div>
              <div className={`${styles.price} ${trade.pnlPercent >= 0 ? styles.positive : styles.negative}`}>
                {trade.pnlPercent >= 0 ? "+" : ""}{trade.pnlPercent.toFixed(2)}%
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
