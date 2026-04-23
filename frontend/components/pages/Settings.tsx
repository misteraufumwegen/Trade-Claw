"use client";

import { useDispatch, useSelector } from "react-redux";
import { RootState } from "@/lib/store";
import { setTheme } from "@/lib/slices/appSlice";
import { useState } from "react";
import styles from "./Settings.module.css";

export default function Settings() {
  const dispatch = useDispatch();
  const theme = useSelector((state: RootState) => state.app.theme);

  const [settings, setSettings] = useState({
    apiKey: "",
    accountId: "",
    dataSource: "oanda",
    maxLeverage: 10,
    maxDrawdown: 20,
    riskPerTrade: 2,
    enableNotifications: true,
    darkMode: true,
  });

  const handleSaveSettings = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Save to backend
    console.log("Settings saved:", settings);
  };

  return (
    <div className={styles.settings}>
      <h1 className={styles.title}>Settings</h1>

      <form className={styles.form} onSubmit={handleSaveSettings}>
        {/* API Configuration */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>API Configuration</h2>

          <div className={styles.formGroup}>
            <label className={styles.label}>Data Source</label>
            <div className={styles.radioGroup}>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="dataSource"
                  value="oanda"
                  checked={settings.dataSource === "oanda"}
                  onChange={(e) => setSettings({ ...settings, dataSource: e.target.value })}
                  className={styles.radio}
                />
                OANDA (Primary)
              </label>
              <label className={styles.radioLabel}>
                <input
                  type="radio"
                  name="dataSource"
                  value="yfinance"
                  checked={settings.dataSource === "yfinance"}
                  onChange={(e) => setSettings({ ...settings, dataSource: e.target.value })}
                  className={styles.radio}
                />
                Yahoo Finance (Fallback)
              </label>
            </div>
          </div>

          {settings.dataSource === "oanda" && (
            <>
              <div className={styles.formGroup}>
                <label className={styles.label}>OANDA Account ID</label>
                <input
                  type="password"
                  className={styles.input}
                  value={settings.accountId}
                  onChange={(e) => setSettings({ ...settings, accountId: e.target.value })}
                  placeholder="Your OANDA account ID"
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>OANDA API Key</label>
                <input
                  type="password"
                  className={styles.input}
                  value={settings.apiKey}
                  onChange={(e) => setSettings({ ...settings, apiKey: e.target.value })}
                  placeholder="Your OANDA API key"
                />
              </div>
            </>
          )}
        </section>

        {/* Risk Settings */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Risk Management</h2>

          <div className={styles.sliderGroup}>
            <label className={styles.label}>
              Maximum Leverage: <span className={styles.value}>{settings.maxLeverage}x</span>
            </label>
            <input
              type="range"
              min="1"
              max="50"
              value={settings.maxLeverage}
              onChange={(e) => setSettings({ ...settings, maxLeverage: parseInt(e.target.value) })}
              className={styles.slider}
            />
          </div>

          <div className={styles.sliderGroup}>
            <label className={styles.label}>
              Maximum Drawdown: <span className={styles.value}>{settings.maxDrawdown}%</span>
            </label>
            <input
              type="range"
              min="1"
              max="50"
              value={settings.maxDrawdown}
              onChange={(e) => setSettings({ ...settings, maxDrawdown: parseInt(e.target.value) })}
              className={styles.slider}
            />
          </div>

          <div className={styles.sliderGroup}>
            <label className={styles.label}>
              Risk per Trade: <span className={styles.value}>{settings.riskPerTrade}%</span>
            </label>
            <input
              type="range"
              min="0.1"
              max="5"
              step="0.1"
              value={settings.riskPerTrade}
              onChange={(e) => setSettings({ ...settings, riskPerTrade: parseFloat(e.target.value) })}
              className={styles.slider}
            />
          </div>
        </section>

        {/* Notification Settings */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Notifications</h2>

          <div className={styles.checkboxGroup}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={settings.enableNotifications}
                onChange={(e) => setSettings({ ...settings, enableNotifications: e.target.checked })}
                className={styles.checkbox}
              />
              <span>Enable notifications for orders and alerts</span>
            </label>
          </div>
        </section>

        {/* Display Settings */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Display</h2>

          <div className={styles.formGroup}>
            <label className={styles.label}>Theme</label>
            <div className={styles.buttonGroup}>
              <button
                type="button"
                className={`${styles.themeButton} ${theme === "dark" ? styles.active : ""}`}
                onClick={() => dispatch(setTheme("dark"))}
              >
                🌙 Dark
              </button>
              <button
                type="button"
                className={`${styles.themeButton} ${theme === "light" ? styles.active : ""}`}
                onClick={() => dispatch(setTheme("light"))}
              >
                ☀️ Light
              </button>
            </div>
          </div>
        </section>

        {/* Action Buttons */}
        <div className={styles.actions}>
          <button type="submit" className={`${styles.button} ${styles.primary}`}>
            Save Settings
          </button>
          <button type="button" className={`${styles.button} ${styles.secondary}`}>
            Reset to Defaults
          </button>
        </div>
      </form>

      {/* Version Info */}
      <section className={styles.versionSection}>
        <h3 className={styles.versionTitle}>About</h3>
        <div className={styles.versionInfo}>
          <p>Trade-Claw Dashboard v0.1.0</p>
          <p>Built with Next.js, React, and Redux</p>
        </div>
      </section>
    </div>
  );
}
