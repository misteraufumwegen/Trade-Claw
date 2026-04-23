"use client";

import { useSelector } from "react-redux";
import { RootState } from "@/lib/store";
import styles from "./Risk.module.css";

export default function Risk() {
  const positions = useSelector((state: RootState) => state.positions);
  const backtest = useSelector((state: RootState) => state.backtest);

  const riskMetrics = () => {
    const result = backtest.currentResult;
    if (!result) return { dd: 0, ddPercent: 0, winRate: 0, trades: 0 };
    return {
      dd: result.maxDrawdown,
      ddPercent: result.maxDrawdownPercent,
      winRate: result.winRate,
      trades: result.totalTrades,
    };
  };

  const metrics = riskMetrics();
  const maxExposure = positions.positions.reduce((sum, p) => sum + p.units * p.currentPrice / 100, 0);
  const leverage = maxExposure > 0 ? maxExposure / 10000 : 0;

  return (
    <div className={styles.risk}>
      <h1 className={styles.title}>Risk Management</h1>

      {/* Risk Metrics Cards */}
      <div className={styles.metricsGrid}>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Max Drawdown</div>
          <div className={`${styles.metricValue} ${metrics.ddPercent > 15 ? styles.warning : ""}`}>
            {metrics.ddPercent.toFixed(2)}%
          </div>
          <div className={styles.metricMeta}>Peak to trough loss</div>
        </div>

        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Current Leverage</div>
          <div className={`${styles.metricValue} ${leverage > 10 ? styles.warning : ""}`}>
            {leverage.toFixed(2)}x
          </div>
          <div className={styles.metricMeta}>Exposure: ${maxExposure.toFixed(2)}</div>
        </div>

        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Win Rate (Backtest)</div>
          <div className={styles.metricValue}>{metrics.winRate.toFixed(1)}%</div>
          <div className={styles.metricMeta}>{Math.round((metrics.trades * metrics.winRate) / 100)} wins</div>
        </div>

        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Total Trades</div>
          <div className={styles.metricValue}>{metrics.trades}</div>
          <div className={styles.metricMeta}>Historical sample</div>
        </div>
      </div>

      {/* Risk Heatmap */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Position Risk Heatmap</h2>
        <div className={styles.heatmap}>
          {positions.positions.map((pos) => {
            const riskScore = Math.abs(pos.pnlPercent);
            const color =
              riskScore < 1
                ? "#10B981"
                : riskScore < 3
                ? "#FFB700"
                : "#EF4444";
            return (
              <div
                key={pos.id}
                className={styles.heatmapCell}
                style={{
                  backgroundColor: color,
                  opacity: 0.3 + (riskScore / 10) * 0.7,
                }}
              >
                <div className={styles.cellLabel}>{pos.symbol}</div>
                <div className={styles.cellValue}>{pos.pnlPercent.toFixed(2)}%</div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Account Health */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Account Health</h2>
        <div className={styles.healthCards}>
          <div className={styles.healthCard}>
            <div className={styles.healthLabel}>Equity</div>
            <div className={styles.healthValue}>${(10000 + positions.totalPnl).toFixed(2)}</div>
            <div className={styles.healthBar}>
              <div
                className={styles.healthBarFill}
                style={{
                  width: Math.min(100, Math.max(0, ((10000 + positions.totalPnl) / 15000) * 100)),
                  backgroundColor: (10000 + positions.totalPnl) >= 10000 ? "#10B981" : "#EF4444",
                }}
              />
            </div>
          </div>

          <div className={styles.healthCard}>
            <div className={styles.healthLabel}>Margin Level</div>
            <div className={styles.healthValue}>
              {(((10000 + positions.totalPnl) / maxExposure) * 100).toFixed(0)}%
            </div>
            <div className={styles.healthBar}>
              <div
                className={styles.healthBarFill}
                style={{
                  width: Math.min(100, (((10000 + positions.totalPnl) / maxExposure) * 100) / 2),
                  backgroundColor:
                    ((10000 + positions.totalPnl) / maxExposure) * 100 > 100
                      ? "#10B981"
                      : ((10000 + positions.totalPnl) / maxExposure) * 100 > 50
                      ? "#FFB700"
                      : "#EF4444",
                }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Risk Settings */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Risk Limits</h2>
        <div className={styles.settingsGrid}>
          <div className={styles.setting}>
            <label className={styles.settingLabel}>Max Leverage</label>
            <input type="range" min="1" max="50" defaultValue="10" className={styles.slider} />
            <span className={styles.settingValue}>10x</span>
          </div>
          <div className={styles.setting}>
            <label className={styles.settingLabel}>Max Drawdown %</label>
            <input type="range" min="1" max="50" defaultValue="20" className={styles.slider} />
            <span className={styles.settingValue}>20%</span>
          </div>
          <div className={styles.setting}>
            <label className={styles.settingLabel}>Risk per Trade</label>
            <input type="range" min="0.1" max="5" step="0.1" defaultValue="2" className={styles.slider} />
            <span className={styles.settingValue}>2%</span>
          </div>
        </div>
      </section>
    </div>
  );
}
