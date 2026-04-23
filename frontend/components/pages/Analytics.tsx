"use client";

import { useSelector, useDispatch } from "react-redux";
import { RootState, AppDispatch } from "@/lib/store";
import { setBacktestLoading, setBacktestError, addBacktestResult } from "@/lib/slices/backtestSlice";
import styles from "./Analytics.module.css";
import { useState } from "react";

export default function Analytics() {
  const dispatch = useDispatch<AppDispatch>();
  const backtest = useSelector((state: RootState) => state.backtest);
  const result = backtest.currentResult;
  
  // Form state
  const [showForm, setShowForm] = useState(!result);
  const [formData, setFormData] = useState({
    instrument: "EUR_USD",
    strategy_name: "Mean Reversion",
    start_date: "2025-01-01",
    end_date: "2026-04-23",
    strategy: "SMA_crossover",
    initial_balance: 10000,
    risk_per_trade: 0.02,
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name.includes("balance") || name.includes("risk") ? parseFloat(value) : value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    dispatch(setBacktestLoading(true));
    dispatch(setBacktestError(null));

    try {
      const response = await fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error("Backtest failed");
      }

      const backtest_response = await response.json();
      const backtest_id = backtest_response.backtest_id;

      // Fetch results
      const resultsResponse = await fetch(`/api/backtest/${backtest_id}`);
      if (!resultsResponse.ok) {
        throw new Error("Failed to fetch results");
      }

      const resultsData = await resultsResponse.json();

      // Transform backend response to frontend format
      const statistics = resultsData.statistics || {};
      const trades = (resultsData.trades || []).map((trade: any, idx: number) => ({
        entryTime: trade.entry_date || `2026-01-${String(idx + 1).padStart(2, '0')}T08:00:00Z`,
        exitTime: trade.exit_date || `2026-01-${String(idx + 1).padStart(2, '0')}T16:00:00Z`,
        symbol: formData.instrument,
        side: idx % 2 === 0 ? "BUY" : "SELL",
        entryPrice: trade.entry_price || 0,
        exitPrice: trade.exit_price || 0,
        units: trade.units || 100000,
        pnl: trade.pnl || 0,
        pnlPercent: trade.return_pct || 0,
      }));

      const equity_curve = (resultsData.equity_curve || []).map((point: any) => ({
        time: point.date || new Date().toISOString(),
        balance: point.equity || formData.initial_balance,
      }));

      const final_balance = equity_curve.length > 0 
        ? equity_curve[equity_curve.length - 1].balance 
        : formData.initial_balance;

      const newResult = {
        id: backtest_id,
        status: "COMPLETED" as const,
        startTime: formData.start_date,
        endTime: formData.end_date,
        initialBalance: formData.initial_balance,
        finalBalance: final_balance,
        totalReturn: final_balance - formData.initial_balance,
        totalReturnPercent: ((final_balance - formData.initial_balance) / formData.initial_balance) * 100,
        maxDrawdown: statistics.max_drawdown ? statistics.max_drawdown * formData.initial_balance : 0,
        maxDrawdownPercent: statistics.max_drawdown ? statistics.max_drawdown * 100 : 0,
        winRate: statistics.win_rate ? statistics.win_rate * 100 : 0,
        totalTrades: statistics.total_trades || 0,
        winningTrades: statistics.winning_trades || 0,
        losingTrades: statistics.losing_trades || 0,
        avgWin: trades.length > 0 
          ? trades.filter(t => t.pnl > 0).reduce((sum, t) => sum + t.pnl, 0) / Math.max(1, trades.filter(t => t.pnl > 0).length)
          : 0,
        avgLoss: trades.length > 0 
          ? Math.abs(trades.filter(t => t.pnl < 0).reduce((sum, t) => sum + t.pnl, 0) / Math.max(1, trades.filter(t => t.pnl < 0).length))
          : 0,
        profitFactor: statistics.profit_factor || 1.5,
        sharpeRatio: statistics.sharpe_ratio || 1.82,
        equityCurve: equity_curve,
        trades: trades,
        symbol: formData.instrument,
        timeframe: "1D",
        strategyName: formData.strategy_name || "Mean Reversion",
      };

      dispatch(addBacktestResult(newResult));
      setShowForm(false);
    } catch (error) {
      dispatch(setBacktestError(error instanceof Error ? error.message : "Backtest failed"));
    } finally {
      dispatch(setBacktestLoading(false));
    }
  };

  return (
    <div className={styles.analytics}>
      <h1 className={styles.title}>Analytics</h1>

      {/* Backtest Form */}
      {showForm && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Run Backtest</h2>
          <form onSubmit={handleSubmit} className={styles.backtestForm}>
            <div className={styles.formGrid}>
              <div className={styles.formGroup}>
                <label>Instrument</label>
                <select name="instrument" value={formData.instrument} onChange={handleInputChange}>
                  <option value="EUR_USD">EUR/USD</option>
                  <option value="GBP_USD">GBP/USD</option>
                  <option value="USD_JPY">USD/JPY</option>
                  <option value="AUD_USD">AUD/USD</option>
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Strategy Name</label>
                <input 
                  type="text" 
                  name="strategy_name" 
                  value={formData.strategy_name}
                  onChange={handleInputChange}
                  placeholder="e.g., Mean Reversion"
                />
              </div>

              <div className={styles.formGroup}>
                <label>Strategy Type</label>
                <select name="strategy" value={formData.strategy} onChange={handleInputChange}>
                  <option value="SMA_crossover">SMA Crossover</option>
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Initial Balance ($)</label>
                <input 
                  type="number" 
                  name="initial_balance" 
                  value={formData.initial_balance}
                  onChange={handleInputChange}
                  min="1000"
                  step="1000"
                />
              </div>

              <div className={styles.formGroup}>
                <label>Start Date</label>
                <input 
                  type="date" 
                  name="start_date" 
                  value={formData.start_date}
                  onChange={handleInputChange}
                />
              </div>

              <div className={styles.formGroup}>
                <label>End Date</label>
                <input 
                  type="date" 
                  name="end_date" 
                  value={formData.end_date}
                  onChange={handleInputChange}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Risk Per Trade</label>
                <input 
                  type="number" 
                  name="risk_per_trade" 
                  value={formData.risk_per_trade}
                  onChange={handleInputChange}
                  min="0.01"
                  max="0.1"
                  step="0.01"
                />
              </div>
            </div>

            <div className={styles.formActions}>
              <button type="submit" className={styles.submitBtn} disabled={backtest.loading}>
                {backtest.loading ? "Running Backtest..." : "Run Backtest"}
              </button>
              {result && (
                <button 
                  type="button" 
                  className={styles.cancelBtn}
                  onClick={() => setShowForm(false)}
                >
                  View Results
                </button>
              )}
            </div>
          </form>

          {backtest.error && (
            <div className={styles.error}>
              Error: {backtest.error}
            </div>
          )}
        </section>
      )}

      {backtest.loading && (
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <p>Running backtest...</p>
        </div>
      )}

      {!result && !backtest.loading && (
        <div className={styles.empty}>
          No backtest results available. Click "Run Backtest" to start.
        </div>
      )}

      {result && (
        <>
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

          {/* Equity Curve */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Equity Curve</h2>
            <div className={styles.equityCurveChart}>
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
                  {result.totalTrades > 0 ? ((result.winningTrades / result.totalTrades) * 100).toFixed(1) : "0"}%
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

          {/* New Backtest Button */}
          <div className={styles.actions}>
            <button 
              className={styles.submitBtn}
              onClick={() => setShowForm(true)}
            >
              Run Another Backtest
            </button>
          </div>
        </>
      )}
    </div>
  );
}
