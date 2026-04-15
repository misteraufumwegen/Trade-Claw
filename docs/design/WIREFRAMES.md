# Trade-Claw Wireframes
**Version:** 1.0 | **Status:** Design Spec | **Layout:** 5 Modules × 3 Views

---

## MODULE 1: DASHBOARD (Main View)

**Purpose:** At-a-glance trading performance, risk status, and active positions.
**Viewport:** 1440px desktop, 375px mobile

### Desktop Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│ TRADE-CLAW TRADING BOT                   [⚙️ Settings] [📊 Analytics] │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ ALERTS BANNER ─────────────────────────────────────────────────┐  │
│  │ ⚠️  DRAWDOWN ALERT: -12.4% (Approaching limit)                  │ │
│  │ 🔴 Stop-Loss Immutable: ACTIVE (Cannot modify stops)             │ │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  [1] KEY METRICS (Top Row - 4 Cards)                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  │ TODAY'S P&L  │  │ MONTH'S P&L  │  │ WIN RATE     │  │ PROFIT FACT. │
│  │ +$1,245.50   │  │ -$3,420.00   │  │ 65.3%        │  │ 2.14         │
│  │ ↑ +2.3%      │  │ ↓ -1.8%      │  │ (24/37)      │  │ Avg Win:Loss │
│  │ [green]      │  │ [red]        │  │ [green]      │  │ [neutral]    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
│
│  [2] RISK STATUS (Below Metrics)                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ DRAWDOWN STATUS                                                 │  │
│  │ Current: -12.4% | Limit: -15% | Available: -2.6%               │  │
│  │ ████████████░░░ [visual bar, orange]                            │  │
│  │                                                                 │  │
│  │ POSITION SIZE USAGE                                             │  │
│  │ Current: 6.2% | Limit: 10% | Available: 3.8%                   │  │
│  │ ██████░░░░░░░░ [visual bar, blue]                               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│
│  [3] ACTIVE POSITIONS (Left Column - 60%)                              │
│  ┌──────────────────────────────────────────────────────┐             │
│  │ OPEN POSITIONS (3)          [Refresh]                │             │
│  ├──────────────────────────────────────────────────────┤             │
│  │ EURUSD | BUY | Entry: 1.0842 | SL: 1.0815 | TP: 1.0890           │ │
│  │ Size: 2.1% | Unrealized P&L: +$420 | Grade: A                    │ │
│  │ Time Open: 2h 15m | Updated: now                                 │ │
│  ├──────────────────────────────────────────────────────┤             │
│  │ GBPUSD | SELL | Entry: 1.2650 | SL: 1.2680 | TP: 1.2590         │ │
│  │ Size: 1.8% | Unrealized P&L: -$185 | Grade: A+                  │ │
│  │ Time Open: 45m | Updated: 3m ago                                 │ │
│  ├──────────────────────────────────────────────────────┤             │
│  │ USDJPY | BUY | Entry: 149.25 | SL: 148.90 | TP: 150.50          │ │
│  │ Size: 2.3% | Unrealized P&L: +$890 | Grade: B                   │ │
│  │ Time Open: 12m | Updated: 1m ago                                 │ │
│  └──────────────────────────────────────────────────────┘             │
│
│  [4] QUICK ACTIONS (Right Column - 40%)                               │
│  ┌────────────────────────────────────┐                               │
│  │ EMERGENCY HALT BUTTON              │                               │
│  │ [🛑 EMERGENCY HALT]                │                               │
│  │ Closes all positions immediately   │                               │
│  └────────────────────────────────────┘                               │
│                                                                         │
│  ┌────────────────────────────────────┐                               │
│  │ QUICK LINKS                        │                               │
│  │ [→ New Trade]                      │                               │
│  │ [→ Risk Settings]                  │                               │
│  │ [→ Broker Status]                  │                               │
│  │ [→ View Analytics]                 │                               │
│  └────────────────────────────────────┘                               │
│                                                                         │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘

Legend:
[green]    = Success-500 (#4CAF50) — profit, positive
[red]      = Danger-500 (#F44336) — loss, negative
[orange]   = Warning-500 (#FF9800) — caution/alert
[neutral]  = Neutral-400 (#9CA3AF) — neutral info
[blue]     = Primary-500 (#2196F3) — action, info
```

### Mobile Layout (375px)

```
┌──────────────────────────────────────┐
│ TRADE-CLAW      [⚙️] [📊]            │
├──────────────────────────────────────┤
│ ⚠️ DRAWDOWN: -12.4% (Alert)          │
│ 🔴 SL Immutable: ACTIVE              │
├──────────────────────────────────────┤
│ TODAY'S P&L                          │
│ +$1,245.50 (↑ +2.3%)                │
├──────────────────────────────────────┤
│ MONTH'S P&L: -$3,420 (↓ -1.8%)      │
│ WIN RATE: 65.3% | PF: 2.14           │
├──────────────────────────────────────┤
│ DRAWDOWN: -12.4% / -15% [█████░░]   │
│ POSITION SIZE: 6.2% / 10% [██░░░░]  │
├──────────────────────────────────────┤
│ OPEN POSITIONS (3)                   │
│ 1. EURUSD Buy +$420 (A)              │
│    Entry: 1.0842 | SL: 1.0815        │
│    Updated: now                      │
│ ─────────────────────────────────    │
│ 2. GBPUSD Sell -$185 (A+)            │
│    Entry: 1.2650 | SL: 1.2680        │
│    Updated: 3m ago                   │
│ ─────────────────────────────────    │
│ 3. USDJPY Buy +$890 (B)              │
│    Entry: 149.25 | SL: 148.90        │
│    Updated: 1m ago                   │
├──────────────────────────────────────┤
│ [🛑 EMERGENCY HALT]                  │
├──────────────────────────────────────┤
│ [New Trade] [Settings] [Analytics]   │
└──────────────────────────────────────┘
```

---

## MODULE 2: TRADING MODULE

**Purpose:** Execute trades with strategy validation, macro events, and correlation analysis.

### Desktop - Full Trading View

```
┌────────────────────────────────────────────────────────────────────────┐
│ TRADING CONSOLE                             [← Back to Dashboard]       │
├────────────────────────────────────────────────────────────────────────┤
│
│  [1] MACRO EVENTS FEED (Live) — Left Column (25%)                      │
│  ┌────────────────────────────┐                                        │
│  │ 🌍 MACRO EVENTS            │                                        │
│  │ Updated: now               │                                        │
│  ├────────────────────────────┤                                        │
│  │ ⏰ 12:30 (5m) ECB Rate     │                                        │
│  │    Decision (Expected)     │                                        │
│  │ Impact: HIGH 🔴            │                                        │
│  ├────────────────────────────┤                                        │
│  │ 📊 13:00 (35m) US Jobs    │                                        │
│  │    (NFP, Forecast: +150K)  │                                        │
│  │ Impact: HIGH 🔴            │                                        │
│  ├────────────────────────────┤                                        │
│  │ 📈 14:30 (95m) US CPI     │                                        │
│  │    (Forecast: +0.3%)       │                                        │
│  │ Impact: HIGH 🔴            │                                        │
│  ├────────────────────────────┤                                        │
│  │ 📉 16:00 (125m) EZ Retail │                                        │
│  │    (Forecast: -0.1%)       │                                        │
│  │ Impact: MEDIUM 🟠          │                                        │
│  └────────────────────────────┘                                        │
│
│  [2] STRATEGY SELECTOR & ENTRY FORM (Center + Right - 75%)             │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ STRATEGY SELECTOR                                              │   │
│  │ Select a pre-validated strategy or create manual entry:        │   │
│  ├────────────────────────────────────────────────────────────────┤   │
│  │ [Dropdown: Select Strategy]                                    │   │
│  │  > Trend Following (Ünal Grade: A)                            │   │
│  │  > Mean Reversion (Ünal Grade: A+)                            │   │
│  │  > Breakout (Ünal Grade: B)                                   │   │
│  │  > Manual Entry                                               │   │
│  ├────────────────────────────────────────────────────────────────┤   │
│  │ MANUAL TRADE ENTRY                                             │   │
│  ├────────────────────────────────────────────────────────────────┤   │
│  │ [Tab: Entry Details] [Tab: Risk Check] [Tab: Confirm]         │   │
│  ├────────────────────────────────────────────────────────────────┤   │
│  │                                                                │   │
│  │ Asset:          [EUR/USD            ▼]                        │   │
│  │ Direction:      [▼ BUY   ] or [SELL ]                         │   │
│  │ Entry Price:    [1.0842            ]   (Current: 1.0840)     │   │
│  │ Stop Loss:      [1.0815            ]   (Risk: 27 pips)        │   │
│  │ Take Profit:    [1.0890            ]   (Reward: 48 pips)      │   │
│  │ Risk/Reward:    1:1.77 ✓ (Meets 1:3 minimum)                 │   │
│  │ Position Size:  [2.1%               ]   (Risk: $210)          │   │
│  │ Grade:          [Grade: A            ] (Downtrend, Strong SL) │   │
│  │                                                                │   │
│  │ [🔒 SL Lock] ← If immutable, checkbox disabled                │   │
│  │                                                                │   │
│  │ [Execute Trade]                                                │   │
│  └────────────────────────────────────────────────────────────────┘   │
│
│  [3] CORRELATION ANALYZER (Below) — Full Width                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ CORRELATION MATRIX                                             │   │
│  │ Base Asset: [EUR/USD ▼] | Time Window: [4H ▼]                │   │
│  │                                                                │   │
│  │         EUR   GBP   USD   JPY   CHF                           │   │
│  │  EUR    100%   88%   12%   75%   45%                          │   │
│  │  GBP     88%  100%    8%   82%   52%                          │   │
│  │  USD     12%    8%  100%   25%   78%                          │   │
│  │  JPY     75%   82%   25%  100%   38%                          │   │
│  │  CHF     45%   52%   78%   38%  100%                          │   │
│  │                                                                │   │
│  │ [Color key: Red 90%+ | Orange 70-89% | Yellow 50-69% | ...] │   │
│  │                                                                │   │
│  │ ⚠️ EUR & GBP highly correlated (88%) - Risk concentration    │   │
│  │    Recommendation: Reduce EUR position or close one.          │   │
│  └────────────────────────────────────────────────────────────────┘   │
│
└────────────────────────────────────────────────────────────────────────┘
```

### Mobile - Trading View (Stacked)

```
┌──────────────────────────────────────┐
│ TRADING CONSOLE                      │
├──────────────────────────────────────┤
│ [Macro Events] [Entry] [Correlation] │
├──────────────────────────────────────┤
│
│ MACRO EVENTS (Live)                  │
│ ⏰ ECB Rate Decision (5m)            │
│    Impact: HIGH 🔴                   │
│ ─────────────────────────────────    │
│ 📊 US Jobs Report (35m)              │
│    Impact: HIGH 🔴                   │
│ ─────────────────────────────────    │
│ 📈 US CPI (95m)                      │
│    Impact: HIGH 🔴                   │
│
├──────────────────────────────────────┤
│ MANUAL TRADE ENTRY                   │
│                                      │
│ Asset: [EUR/USD        ▼]            │
│ Direction: [BUY] [SELL]              │
│ Entry: [1.0842         ]             │
│ Stop Loss: [1.0815    ]              │
│ Take Profit: [1.0890  ]              │
│ Position Size: [2.1%]                │
│ Grade: A ✓                           │
│                                      │
│ [Execute Trade]                      │
│
├──────────────────────────────────────┤
│ CORRELATION (EUR/USD | 4H)           │
│ GBP: 88% (HIGH)                      │
│ JPY: 75% (HIGH)                      │
│ CHF: 45% (MED)                       │
│                                      │
│ ⚠️ EUR-GBP concentrated risk         │
│
└──────────────────────────────────────┘
```

---

## MODULE 3: RISK MANAGEMENT

**Purpose:** Real-time risk monitoring, limits, and emergency controls.

### Desktop - Risk Panel

```
┌────────────────────────────────────────────────────────────────────────┐
│ RISK MANAGEMENT DASHBOARD                                              │
├────────────────────────────────────────────────────────────────────────┤
│
│  [1] HARD LIMITS (Read-Only, Hardcoded)                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ MAXIMUM POSITION SIZE                                            │  │
│  │ Limit: 10% of account | Current: 6.2% | Status: ✓ SAFE          │  │
│  │ ██████░░░░░░░░ [blue bar]                                        │  │
│  │ Largest Position: EURUSD (2.1%)                                  │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │ MAXIMUM DRAWDOWN                                                 │  │
│  │ Limit: -15% | Current: -12.4% | Status: ⚠️ WARNING             │  │
│  │ ████████████░░░ [orange bar]                                     │  │
│  │ Recovery Needed: +$1,880 to return to zero                       │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │ DAILY LOSS LIMIT                                                 │  │
│  │ Limit: -5% | Current: -2.1% | Status: ✓ SAFE                    │  │
│  │ ██░░░░░░░░░░░░ [blue bar]                                        │  │
│  │ Remaining Daily Risk: -2.9%                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│
│  [2] STOP-LOSS IMMUTABILITY (Protection Feature)                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ STOP-LOSS IMMUTABLE STATUS                                       │  │
│  │                                                                  │  │
│  │ Current Status: [🔴 ACTIVE]                                     │  │
│  │ When Active: Cannot modify/remove stops on open positions       │  │
│  │ Reason: Drawdown approaching -15% limit (safety mode)           │  │
│  │                                                                  │  │
│  │ Auto-Unlock Conditions:                                         │  │
│  │  • Drawdown returns above -12% (recovery begun)                │  │
│  │  • Manual unlock (requires explicit admin action)               │  │
│  │                                                                  │  │
│  │ Immutable Positions:                                            │  │
│  │ ✓ EURUSD (SL: 1.0815) — Cannot modify                           │  │
│  │ ✓ GBPUSD (SL: 1.2680) — Cannot modify                           │  │
│  │ ✓ USDJPY (SL: 148.90) — Cannot modify                           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│
│  [3] EMERGENCY CONTROLS                                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                  │  │
│  │ [🛑 EMERGENCY HALT - CLOSE ALL POSITIONS]                       │  │
│  │                                                                  │  │
│  │ Closes all open trades at market price immediately.            │  │
│  │ Use only in crisis: system error, broker issue, extreme risk   │  │
│  │                                                                  │  │
│  │ Last Trigger: Never                                             │  │
│  │ Active Trades Affected: 3                                       │  │
│  │                                                                  │  │
│  │ [Confirm Emergency Halt] ← Requires explicit click              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│
│  [4] RISK ALERTS (Live Feed)                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ ACTIVE ALERTS                                                    │  │
│  │ [🔴 CRITICAL] 12:45 Drawdown -12.4% (Threshold: -15%)          │  │
│  │ [🟠 WARNING] 12:43 EUR-GBP Correlation 88% (Max: 85%)           │  │
│  │ [🟡 INFO] 12:40 New Trade Executed (EURUSD, Grade A)            │  │
│  │ [🔵 INFO] 12:35 Macro Event: ECB Rate Decision -5m              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│
└────────────────────────────────────────────────────────────────────────┘
```

---

## MODULE 4: ANALYTICS

**Purpose:** Trade review, performance metrics, historical analysis.

### Desktop - Analytics Dashboard

```
┌────────────────────────────────────────────────────────────────────────┐
│ ANALYTICS & PERFORMANCE                                                │
├────────────────────────────────────────────────────────────────────────┤
│
│  [1] FILTER BAR                                                        │
│  ├────────────────────────────────────────────────────────────────────┤
│  │ Time Range: [Last 30 Days ▼] | Asset: [All ▼] | Grade: [All ▼]   │
│  │ Status: [All ▼] | Sort: [Date (Newest) ▼]                         │
│  │ [Search by ticker/notes...]                                       │
│  └────────────────────────────────────────────────────────────────────┘
│
│  [2] PERFORMANCE CHARTS (Top Row)                                      │
│  ┌──────────────────────────┐  ┌──────────────────────────┐            │
│  │ WIN RATE TREND           │  │ PROFIT FACTOR TREND      │            │
│  │ (Last 30 trades)         │  │ (Cumulative)             │            │
│  │                          │  │                          │            │
│  │ 70%  ╱╲                  │  │ 3.0  ╱                   │            │
│  │ 60% ╱  ╲    ╱╲           │  │ 2.5 ╱ ╲╲                │            │
│  │ 50%     ╲  ╱  ╲╱╲        │  │ 2.0     ╲  ╱            │            │
│  │ 40%      ╲╱      ╲      │  │ 1.5       ╲╱             │            │
│  │          [=====] (65%)  │  │          [====] (2.14)   │            │
│  └──────────────────────────┘  └──────────────────────────┘            │
│
│  ┌──────────────────────────┐  ┌──────────────────────────┐            │
│  │ MONTHLY P&L              │  │ DRAWDOWN HISTORY         │            │
│  │ (Cumulative by month)    │  │ (Lowest point per day)   │            │
│  │                          │  │                          │            │
│  │ $5K ├─────────────────   │  │   0% ├─────────────────  │            │
│  │ $0  ├──╱╲╱╲╱╲──────────  │  │ -5%  ├─╱╲ ╱╲             │            │
│  │-$5K ╱  ╲╱  ╲╱╲╱╲──┘    │  │-10%  ├─ ╰─╱  ╲╱╲         │            │
│  │     ├─────────────────   │  │-15%  ├─────────────────  │            │
│  │     Feb  Mar  Apr        │  │      Feb   Mar   Apr     │            │
│  └──────────────────────────┘  └──────────────────────────┘            │
│
│  [3] TRADE HISTORY TABLE                                               │
│  ├────────────────────────────────────────────────────────────────────┤
│  │ # │ Asset  │ Dir │ Entry   │ Exit    │ SL     │ TP     │ P&L    │ G │
│  │───┼────────┼─────┼─────────┼─────────┼────────┼────────┼────────┼───│
│  │37 │EURUSD  │BUY  │1.0842   │1.0867   │1.0815  │1.0890  │+$315   │A  │
│  │36 │GBPUSD  │SELL │1.2650   │1.2620   │1.2680  │1.2590  │+$450   │A+ │
│  │35 │USDJPY  │BUY  │149.25   │149.80   │148.90  │150.50  │+$275   │A  │
│  │34 │EURUSD  │SELL │1.0890   │1.0865   │1.0915  │1.0820  │+$180   │B  │
│  │33 │NZDUSD  │BUY  │0.6185   │0.6195   │0.6150  │0.6220  │+$60    │B  │
│  │32 │AUDCAD  │SELL │0.9142   │0.9120   │0.9165  │0.9100  │-$110   │B  │
│  │31 │EURUSD  │BUY  │1.0720   │1.0695   │1.0690  │1.0750  │-$420   │A  │
│  │30 │GBPJPY  │BUY  │190.30   │188.90   │192.50  │185.00  │-$700   │A+ │
│  │... (scroll for more)                                                │
│  └────────────────────────────────────────────────────────────────────┘
│
│  [4] STATISTICS PANEL (Below Table)                                    │
│  ├────────────────────────────────────────────────────────────────────┤
│  │ Total Trades (filtered): 37                                        │
│  │ Winning Trades: 24 (65%) | Losing Trades: 13 (35%)                │
│  │ Avg Win: +$356 | Avg Loss: -$285 | Profit Factor: 2.14           │
│  │ Best Trade: +$890 (USDJPY) | Worst Trade: -$700 (GBPJPY)         │
│  │ Consecutive Wins: 4 | Consecutive Losses: 3                       │
│  │ Avg Trade Duration: 2h 45m                                         │
│  └────────────────────────────────────────────────────────────────────┘
│
└────────────────────────────────────────────────────────────────────────┘
```

---

## MODULE 5: SETTINGS

**Purpose:** Configuration, API connections, risk limits, asset selection.

### Desktop - Settings Panel

```
┌────────────────────────────────────────────────────────────────────────┐
│ SETTINGS                                                               │
├────────────────────────────────────────────────────────────────────────┤
│
│ [Sidebar Navigation]
│ ├─ Connection Status
│ ├─ Broker & Account
│ ├─ Assets & Markets
│ ├─ Risk Configuration
│ └─ Notifications
│
├────────────────────────────────────────────────────────────────────────┤
│
│  SECTION 1: CONNECTION STATUS (Selected)
│
│  ┌────────────────────────────────────────────────────────────────────┐
│  │ API CONNECTION & BROKER STATUS                                    │
│  ├────────────────────────────────────────────────────────────────────┤
│  │                                                                    │
│  │ Broker Connection                                                 │
│  │ Status: [🟢 CONNECTED] Last Check: 2m ago                         │
│  │ Broker: OANDA (Primary)                                           │
│  │ Account ID: 12345678                                              │
│  │ Account Type: Practice / Live                                     │
│  │ [Test Connection] [Reconnect]                                     │
│  │                                                                    │
│  │ ────────────────────────────────────                              │
│  │ API Key Status                                                    │
│  │ Status: [🟢 VALID]                                                │
│  │ Key: (masked) ...3d7f                                             │
│  │ Last Validated: 1h ago                                            │
│  │ Scopes: Trading, Read Prices, Account Info                        │
│  │                                                                    │
│  │ ────────────────────────────────────                              │
│  │ Price Feed Status                                                 │
│  │ Status: [🟢 LIVE]                                                 │
│  │ Source: OANDA Streaming                                           │
│  │ Last Quote: 1m ago (EURUSD 1.0840)                               │
│  │ Latency: 45ms                                                     │
│  │                                                                    │
│  │ ────────────────────────────────────                              │
│  │ System Health                                                     │
│  │ Uptime: 45 days 3h 22m                                            │
│  │ Last Error: 2d ago (brief timeout, auto-recovered)               │
│  │                                                                    │
│  └────────────────────────────────────────────────────────────────────┘
│
│  SECTION 2: BROKER & ACCOUNT (If Selected)
│
│  ┌────────────────────────────────────────────────────────────────────┐
│  │ BROKER SELECTION                                                  │
│  │ Primary: [OANDA ▼] (currently only option in MVP)                 │
│  │                                                                    │
│  │ API KEY (encrypted)                                               │
│  │ [•••••••••••••••••••3d7f] [Change Key]                           │
│  │                                                                    │
│  │ ACCOUNT DETAILS (Read-Only)                                       │
│  │ Account ID: 12345678                                              │
│  │ Type: Live / Practice                                             │
│  │ Balance: $50,000 USD                                              │
│  │ Equity: $48,750 USD                                               │
│  │ Margin Available: $45,200 USD                                     │
│  │                                                                    │
│  └────────────────────────────────────────────────────────────────────┘
│
│  SECTION 3: ASSETS & MARKETS (If Selected)
│
│  ┌────────────────────────────────────────────────────────────────────┐
│  │ TRADABLE ASSETS                                                   │
│  │ Select which assets are available for trading/correlation:        │
│  │                                                                    │
│  │ [✓] EUR/USD   [✓] GBP/USD   [✓] USD/JPY                          │
│  │ [✓] USD/CHF   [✓] EUR/GBP   [✓] EUR/JPY                          │
│  │ [✓] AUD/USD   [✓] NZD/USD   [✓] CAD/USD                          │
│  │ [✓] USD/CAD   [ ] Gold      [ ] Silver                             │
│  │                                                                    │
│  │ [Save Asset Selection]                                            │
│  │                                                                    │
│  └────────────────────────────────────────────────────────────────────┘
│
│  SECTION 4: RISK CONFIGURATION (If Selected)
│
│  ┌────────────────────────────────────────────────────────────────────┐
│  │ RISK LIMITS (Read-Only, Hardcoded)                                │
│  │                                                                    │
│  │ Max Position Size: 10% per trade                                  │
│  │ Max Daily Loss: 5%                                                │
│  │ Max Drawdown: 15%                                                 │
│  │                                                                    │
│  │ ⓘ These limits are hardcoded for safety and cannot be changed.   │
│  │   Contact admin to modify.                                        │
│  │                                                                    │
│  │ Minimum Risk/Reward Ratio: 1:3 (hardcoded)                       │
│  │                                                                    │
│  └────────────────────────────────────────────────────────────────────┘
│
│  SECTION 5: NOTIFICATIONS (If Selected)
│
│  ┌────────────────────────────────────────────────────────────────────┐
│  │ ALERT SETTINGS                                                    │
│  │                                                                    │
│  │ [✓] Drawdown Alerts (when approaching -12%)                       │
│  │ [✓] Trade Execution Alerts                                        │
│  │ [✓] Macro Event Alerts (live from worldmonitor.app)              │
│  │ [✓] Correlation Warnings (> 85%)                                  │
│  │ [✓] API Connection Status Changes                                 │
│  │ [ ] Hourly Summary Report                                         │
│  │                                                                    │
│  │ Alert Method: [System Notifications + Telegram ▼]                 │
│  │                                                                    │
│  │ [Save Preferences]                                                │
│  │                                                                    │
│  └────────────────────────────────────────────────────────────────────┘
│
└────────────────────────────────────────────────────────────────────────┘
```

---

## KEY INTERACTION FLOWS

### Flow 1: New Trade Execution

```
User clicks [New Trade]
    ↓
→ Trading Module opens (Strategy Selector visible)
    ↓
User selects strategy OR chooses [Manual Entry]
    ↓
→ Entry Form appears with:
  - Asset (pre-selected or dropdown)
  - Direction (BUY/SELL)
  - Entry Price (current quote or custom)
  - Stop Loss (auto-calculated or custom)
  - Take Profit (auto-calculated or custom)
  - Position Size (auto-calculated based on risk)
  - Grade (calculated by Ünal's scoring)
    ↓
System validates:
  ✓ Risk/Reward ≥ 1:3
  ✓ Position Size ≤ 10%
  ✓ Total Exposure ≤ 10%
  ✓ Correlation ≤ 85%
  ✓ No immutable SL conflicts
    ↓
If all valid:
  [Execute Trade] button appears GREEN & enabled
    ↓
User clicks [Execute Trade]
    ↓
→ Confirmation modal:
  "Confirm EURUSD BUY: Entry 1.0842, SL 1.0815, TP 1.0890, Size 2.1%"
  [Cancel] [Confirm]
    ↓
User clicks [Confirm]
    ↓
→ Trade sent to broker (OANDA)
    ↓
Broker responds: SUCCESS or ERROR
    ↓
→ Toast notification: "Trade Executed: EURUSD BUY +$420" (success)
   OR "Trade Failed: Insufficient Margin" (error)
    ↓
→ Dashboard updates:
  - New position appears in Active Positions list
  - P&L updates
  - Risk bars update
  - Correlation matrix updates
```

### Flow 2: Emergency Halt

```
User is alarmed (system error, extreme risk, etc.)
    ↓
User clicks [🛑 EMERGENCY HALT] (visible on Dashboard or Risk Panel)
    ↓
→ Modal appears:
  "⚠️ EMERGENCY HALT
   This will CLOSE ALL OPEN POSITIONS at market price.
   This action CANNOT be undone.
   
   Positions to close: 3
   Estimated loss: ~$50 (market slippage)
   
   [Cancel] [I Understand - Halt All Trades]"
    ↓
User clicks [I Understand - Halt All Trades]
    ↓
→ System sends close orders for all 3 positions
    ↓
Broker responds: All positions closed
    ↓
→ Toast: "EMERGENCY HALT EXECUTED - All positions closed"
→ Dashboard shows:
  - Active Positions: 0
  - All positions moved to Trade History with "Emergency Closed" tag
  - P&L updates with final loss
```

### Flow 3: Risk Limit Triggered (Drawdown -15%)

```
System monitors drawdown: currently -12.4%
    ↓
[Macro event causes 3 losing trades]
    ↓
Drawdown drops to -15.2% (exceeds -15% limit)
    ↓
→ System IMMEDIATELY:
  1. Triggers Stop-Loss Immutable = ACTIVE
  2. Shows CRITICAL alert banner
  3. Disables new trade entries
  4. Locks all existing SLs (cannot modify)
    ↓
Dashboard updates:
  - Banner: "🔴 CRITICAL: Drawdown -15.2% (LIMIT EXCEEDED)"
  - Risk Status shows drawdown in RED
  - SL Immutable status: [🔴 ACTIVE]
  - [New Trade] button DISABLED
    ↓
User cannot:
  - Enter new trades
  - Modify stops on open positions
  - Change risk limits
    ↓
User can still:
  - View positions
  - Manual close (at market price)
  - View analytics
  - Click Emergency Halt
    ↓
Once drawdown recovers to -12% or better:
  - SL Immutable automatically unlocks
  - [New Trade] button re-enabled
  - Warning banner remains but changes to WARNING color
    ↓
Admin can manually unlock via [Manual Unlock] in Risk Settings
```

---

**Next:** Component breakdown & React structure in COMPONENTS.md
