"use client";

import { useSelector, useDispatch } from "react-redux";
import { RootState } from "@/lib/store";
import { addOrder } from "@/lib/slices/ordersSlice";
import { useState } from "react";
import styles from "./Trading.module.css";

export default function Trading() {
  const dispatch = useDispatch();
  const orders = useSelector((state: RootState) => state.orders);
  const positions = useSelector((state: RootState) => state.positions);
  const quotes = useSelector((state: RootState) => state.quotes);

  const [formData, setFormData] = useState({
    symbol: "EUR/USD",
    side: "BUY" as const,
    type: "MARKET" as const,
    units: 100000,
    price: 1.0845,
  });

  const handlePlaceOrder = (e: React.FormEvent) => {
    e.preventDefault();
    const newOrder = {
      id: `ord-${Date.now()}`,
      symbol: formData.symbol,
      side: formData.side,
      type: formData.type,
      units: formData.units,
      price: formData.price,
      status: "PENDING" as const,
      createdAt: new Date().toISOString(),
    };
    dispatch(addOrder(newOrder));
    setFormData({ ...formData, units: 100000 });
  };

  return (
    <div className={styles.trading}>
      <h1 className={styles.title}>Trading</h1>

      <div className={styles.container}>
        {/* Order Form */}
        <section className={styles.formSection}>
          <h2 className={styles.sectionTitle}>New Order</h2>
          <form className={styles.form} onSubmit={handlePlaceOrder}>
            <div className={styles.formGroup}>
              <label className={styles.label}>Symbol</label>
              <select
                className={styles.select}
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
              >
                <option>EUR/USD</option>
                <option>GBP/USD</option>
                <option>SPY</option>
              </select>
            </div>

            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label className={styles.label}>Side</label>
                <div className={styles.buttonGroup}>
                  <button
                    type="button"
                    className={`${styles.sideButton} ${formData.side === "BUY" ? styles.active : ""} ${styles.buy}`}
                    onClick={() => setFormData({ ...formData, side: "BUY" })}
                  >
                    BUY
                  </button>
                  <button
                    type="button"
                    className={`${styles.sideButton} ${formData.side === "SELL" ? styles.active : ""} ${styles.sell}`}
                    onClick={() => setFormData({ ...formData, side: "SELL" })}
                  >
                    SELL
                  </button>
                </div>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>Type</label>
                <select
                  className={styles.select}
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value as any })}
                >
                  <option>MARKET</option>
                  <option>LIMIT</option>
                  <option>STOP</option>
                </select>
              </div>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label}>Units</label>
              <input
                type="number"
                className={styles.input}
                value={formData.units}
                onChange={(e) => setFormData({ ...formData, units: parseInt(e.target.value) })}
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label}>Price (if Limit/Stop)</label>
              <input
                type="number"
                step="0.0001"
                className={styles.input}
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) })}
              />
            </div>

            <button type="submit" className={`${styles.button} ${styles.primary}`}>
              Place Order
            </button>
          </form>
        </section>

        {/* Active Orders */}
        <section className={styles.ordersSection}>
          <h2 className={styles.sectionTitle}>Active Orders ({orders.orders.filter((o) => o.status === "PENDING").length})</h2>
          <div className={styles.table}>
            <div className={styles.tableHeader}>
              <div>Symbol</div>
              <div>Type</div>
              <div>Side</div>
              <div>Units</div>
              <div>Price</div>
              <div>Status</div>
              <div>Time</div>
            </div>
            {orders.orders
              .filter((o) => o.status === "PENDING")
              .map((order) => (
                <div key={order.id} className={styles.tableRow}>
                  <div>{order.symbol}</div>
                  <div>{order.type}</div>
                  <div>
                    <span className={`${styles.badge} ${order.side === "BUY" ? styles.buy : styles.sell}`}>
                      {order.side}
                    </span>
                  </div>
                  <div>{order.units.toLocaleString()}</div>
                  <div className={styles.price}>{order.price.toFixed(5)}</div>
                  <div>
                    <span className={`${styles.statusBadge} ${styles.pending}`}>{order.status}</span>
                  </div>
                  <div className={styles.time}>
                    {new Date(order.createdAt).toLocaleTimeString()}
                  </div>
                </div>
              ))}
          </div>
        </section>

        {/* Trade History */}
        <section className={styles.historySection}>
          <h2 className={styles.sectionTitle}>Trade History</h2>
          <div className={styles.table}>
            <div className={styles.tableHeader}>
              <div>Symbol</div>
              <div>Side</div>
              <div>Units</div>
              <div>Entry</div>
              <div>Exit</div>
              <div>P&L</div>
              <div>Return %</div>
            </div>
            {orders.orders
              .filter((o) => o.status === "FILLED")
              .map((order) => {
                const currentPrice = quotes.quotes[order.symbol]?.last || order.price;
                const pnl = (order.side === "BUY" ? 1 : -1) * (currentPrice - order.price) * order.units;
                const pnlPercent = ((pnl / (order.price * order.units)) * 100) || 0;
                return (
                  <div key={order.id} className={styles.tableRow}>
                    <div>{order.symbol}</div>
                    <div>
                      <span className={`${styles.badge} ${order.side === "BUY" ? styles.buy : styles.sell}`}>
                        {order.side}
                      </span>
                    </div>
                    <div>{order.units.toLocaleString()}</div>
                    <div className={styles.price}>{order.price.toFixed(5)}</div>
                    <div className={styles.price}>{currentPrice.toFixed(5)}</div>
                    <div className={`${styles.price} ${pnl >= 0 ? styles.positive : styles.negative}`}>
                      ${pnl.toFixed(2)}
                    </div>
                    <div className={`${styles.price} ${pnlPercent >= 0 ? styles.positive : styles.negative}`}>
                      {pnlPercent >= 0 ? "+" : ""}{pnlPercent.toFixed(2)}%
                    </div>
                  </div>
                );
              })}
          </div>
        </section>
      </div>
    </div>
  );
}
