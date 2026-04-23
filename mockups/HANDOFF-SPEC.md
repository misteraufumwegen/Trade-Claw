# Trade-Claw Dashboard - Handoff Specification for Elon (CTO)

**Status:** ✅ Complete (HOUR 5-6)  
**Created by:** Erkan (UX/UI Designer)  
**For:** Elon (CTO / Frontend + Backend Lead)  
**Date:** 2026-04-23 18:45 CET

---

## 📋 Overview

This document specifies the complete design system, page layouts, component usage, and data models for the Trade-Claw Dashboard. Use this as your integration guide for Hours 6-10 (Frontend) and Hour 11-15 (Integration).

---

## 🎯 Deliverables Summary

### What Erkan Has Delivered (Hours 1-6)
✅ Design System: Color palette, typography, spacing, icons (figma-export/)  
✅ Component Library: Buttons, Cards, Inputs, Sliders, Tables, Alerts, Charts (figma-components/)  
✅ Hi-Fi Mockups: 5 complete pages with annotations (mockups/pages/)  
✅ Responsive Guidelines: Breakpoints 320px / 768px / 1024px / 1920px (RESPONSIVE-GUIDELINES.md)  
✅ This Handoff Spec: Integration guide for you

### What Elon Needs to Build (Hours 6+)
- [ ] React components wrapping CSS from figma-components/
- [ ] Redux state management for data flows
- [ ] API integration (fetch to FastAPI endpoints)
- [ ] Page layouts matching mockups
- [ ] WebSocket for real-time updates
- [ ] Chart libraries (TradingView, Chart.js)
- [ ] Responsive styling verification

---

## 🗂️ File Structure & Assets

### Design System Assets
```
figma-export/
├── design-tokens/
│   ├── tokens.json                 # Design token definitions
│   ├── css-variables.css           # CSS variables for all tokens
│   └── spacing/
├── typography/
├── icons/
└── documentation/

figma-components/
├── buttons/
│   ├── button.css                  # All button variants
│   └── button.html                 # Examples
├── cards/
│   ├── card.css
│   └── card.html
├── inputs/
│   ├── input.css
│   └── input.html
├── sliders/
│   ├── slider.css
│   └── slider.html
├── tables/
│   ├── table.css
│   └── table.html
├── alerts/
│   ├── alert.css
│   └── alert.html
├── charts/
│   ├── chart.css
│   └── chart.html
└── README.md                       # Component library docs
```

### Mockups & Guidelines
```
mockups/
├── pages/
│   ├── 1-dashboard.html            # Complete mockup with styles
│   ├── 2-trading.html
│   ├── 3-risk-management.html
│   ├── 4-analytics.html
│   ├── 5-settings.html
├── RESPONSIVE-GUIDELINES.md        # Breakpoints & annotations
├── HANDOFF-SPEC.md                 # This file
└── annotations/
    └── (reserved for detailed annotations)
```

### Frontend Structure (Your Job)
```
frontend/
├── src/
│   ├── components/
│   │   ├── layouts/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── MainLayout.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Trading.tsx
│   │   │   ├── RiskManagement.tsx
│   │   │   ├── Analytics.tsx
│   │   │   └── Settings.tsx
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Alert.tsx
│   │   │   └── Badge.tsx
│   │   └── charts/
│   │       ├── CandlestickChart.tsx
│   │       ├── EquityCurve.tsx
│   │       └── LineChart.tsx
│   ├── styles/
│   │   ├── globals.css
│   │   ├── components/
│   │   │   ├── buttons.css
│   │   │   ├── cards.css
│   │   │   └── ... (copy from figma-components/)
│   │   └── tokens/
│   │       └── css-variables.css     # Import from figma-export/
│   ├── store/
│   │   ├── index.ts
│   │   ├── slices/
│   │   │   ├── accountSlice.ts
│   │   │   ├── positionsSlice.ts
│   │   │   ├── ordersSlice.ts
│   │   │   ├── quotesSlice.ts
│   │   │   └── backtestSlice.ts
│   │   └── middleware/
│   │       └── websocketMiddleware.ts
│   ├── hooks/
│   │   ├── useQuotes.ts
│   │   ├── useAccount.ts
│   │   ├── useOrders.ts
│   │   └── useWebSocket.ts
│   ├── utils/
│   │   ├── api.ts                  # API client
│   │   └── formatters.ts           # Number formatting
│   └── App.tsx
├── public/
└── package.json
```

---

## 🎨 Design System - Key Values

### Colors
```css
--color-dark: #0D1117              /* Background */
--color-secondary: #161B22         /* Cards, elevated surfaces */
--color-primary: #00D9FF           /* Teal - CTAs, highlights */
--color-accent: #FFB700            /* Gold - warnings, attention */
--color-success: #10B981           /* Green - wins, positive */
--color-danger: #EF4444            /* Red - losses, errors */
--color-text-primary: #F0F6FC      /* Main text */
--color-text-secondary: #8B949E    /* Muted, labels */
--color-border: #30363D            /* Dividers */
```

### Typography
```
Font Family: Inter (sans-serif), JetBrains Mono (numbers/data)
Font Weights: 400 (regular), 700 (bold)

Sizes:
- 12px (XS)
- 14px (S)
- 16px (Base)
- 18px (L)
- 20px (XL)
- 24px (2XL)
- 32px (3XL)

Line Height: 1.2 (headings), 1.5 (body)
```

### Spacing (8px Grid)
```
4px (XS), 8px (S), 16px (M), 24px (L), 32px (XL), 48px (2XL)
```

### Border Radius
```
4px (S), 8px (M), 12px (L)
```

### Shadows
```
Small:  0 1px 2px 0 rgba(0, 0, 0, 0.05)
Medium: 0 4px 6px -1px rgba(0, 0, 0, 0.1)
Large:  0 10px 15px -3px rgba(0, 0, 0, 0.1)
```

---

## 📄 Page Specifications

### Page 1: Dashboard

**Purpose:** Overview of account health, positions, and recent activity

**Components Used:**
- Header (title + action buttons)
- Sidebar navigation (sticky, 240px)
- Card (4 variants: Account Balance, Equity, Available Margin, Risk Remaining)
- Position Card (custom card with badge)
- Table (Recent Trades)
- Grid layout (4-col metrics, 4-col positions)

**Layout Grid:**
```
Desktop (1920px):
┌─────────────┬─────────────────────────────────────────────┐
│   Sidebar   │ Header                                      │
├─────────────┼─────────────────────────────────────────────┤
│  (sticky)   │ 2-col: Balance | Equity                     │
│             ├─────────────────────────────────────────────┤
│             │ 3-col: Margin | Used | Risk Remaining      │
│             ├─────────────────────────────────────────────┤
│             │ 4-col Positions (EUR/USD, GBP/USD, AUD, JPY)│
│             ├─────────────────────────────────────────────┤
│             │ Full-width Table: Recent Trades             │
└─────────────┴─────────────────────────────────────────────┘
```

**Key Sections:**
1. **Account Health** (4 metric cards)
   - Account Balance
   - Equity
   - Available Margin
   - Risk Remaining

2. **Active Positions** (4-column grid of position cards)
   - Symbol
   - Entry, Current, P&L
   - Size
   - Status badge (LONG/SHORT)

3. **Recent Trades** (table)
   - Time, Symbol, Type, Entry, Exit, Size, P&L

**Data Models Needed:**
```typescript
interface Account {
  balance: number;
  equity: number;
  availableMargin: number;
  marginUsed: number;
  riskRemaining: number;
}

interface Position {
  symbol: string;
  side: 'LONG' | 'SHORT';
  entry: number;
  current: number;
  size: number;
  pnl: number;
  pnlPercent: number;
}

interface RecentTrade {
  time: string;
  symbol: string;
  type: string;
  entry: number;
  exit: number;
  size: number;
  pnl: number;
}
```

**API Endpoints Required:**
- `GET /api/account` → Account data
- `GET /api/positions` → Active positions
- `GET /api/trades?limit=10` → Recent trades

---

### Page 2: Trading

**Purpose:** Place new orders, view active orders, trade history

**Components Used:**
- Form with inputs, selects, validation
- Chart (Candlestick for EUR/USD)
- Table (Active Orders)
- Table (Trade History)
- Buttons (Primary, Danger)
- Input fields (text, number)

**Layout Grid:**
```
Desktop (1920px):
┌─────────────────────────┬──────────────────────────────────┐
│  Order Entry Form (30%) │ Chart (70%)                       │
│  - Symbol select        │ Candlestick + Timeframe controls │
│  - Order Type           │                                  │
│  - Entry Price          │                                  │
│  - Side (Long/Short)    │                                  │
│  - Position Size        │                                  │
│  - Stop Loss            │                                  │
│  - Take Profit          │                                  │
│  [Place Order] [Cancel] │                                  │
├─────────────────────────┴──────────────────────────────────┤
│ Active Orders Table                                         │
│ Symbol | Type | Side | Entry | Size | SL | TP | Status   │
├────────────────────────────────────────────────────────────┤
│ Trade History Table                                        │
│ Time | Symbol | Side | Entry | Exit | Size | P&L | R/R  │
└────────────────────────────────────────────────────────────┘
```

**Form Fields:**
```typescript
interface OrderForm {
  symbol: string;           // Select: EUR/USD, GBP/USD, etc.
  orderType: string;        // Select: Market, Limit, Stop
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  positionSize: number;     // Units
  stopLoss: number;
  takeProfit: number;
  riskAmount: number;       // $USD
}

interface Order {
  id: string;
  symbol: string;
  type: string;
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  size: number;
  stopLoss: number;
  takeProfit: number;
  status: 'PENDING' | 'FILLED' | 'CANCELLED';
  createdAt: string;
}

interface Trade {
  id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entry: number;
  exit: number;
  size: number;
  pnl: number;
  rrRatio: number;        // Risk/Reward
  closedAt: string;
}
```

**API Endpoints Required:**
- `POST /api/orders` → Place order
- `GET /api/orders` → List active orders
- `POST /api/orders/{id}/cancel` → Cancel order
- `GET /api/trades` → Trade history
- `GET /api/quotes/{symbol}` → Live quote + OHLC

**Chart Library:**
- **TradingView Lightweight Charts** (recommended for candlestick)
- Data: OHLC bars from backend
- Update frequency: Real-time via WebSocket

---

### Page 3: Risk Management

**Purpose:** Monitor risk metrics, drawdown, win rate, trade grades

**Components Used:**
- Metric Cards (4-column grid)
- Risk Meter (slider + percentage)
- Grade Distribution (bar chart with 5 grades)
- Heat Map (5 symbols, colored by risk level)
- Chart (Drawdown over time)

**Layout Grid:**
```
┌────────────────────────────────────────────────────────────┐
│ 4-col Metrics: Drawdown | Max DD | Win Rate | Avg R/R    │
├─────────────────────────┬──────────────────────────────────┤
│ Risk Utilization        │ Grade Distribution              │
│ [■■■■░░░░░] 45%         │ A+ (12) A (10) B (8) C (7) D (3)│
├─────────────────────────┴──────────────────────────────────┤
│ Account Heat Map (5 symbols, colored by risk)             │
│ [EUR/USD] [GBP/USD] [AUD/USD] [USD/JPY] [NZD/USD]        │
│   Low      Med       Med        Low      High             │
├────────────────────────────────────────────────────────────┤
│ Drawdown Over Time Chart                                  │
└────────────────────────────────────────────────────────────┘
```

**Data Models:**
```typescript
interface RiskMetrics {
  currentDrawdown: number;     // -2.5%
  maxDrawdown: number;         // -8.3%
  winRate: number;             // 62.5
  avgRR: number;               // 1.8
}

interface RiskUtilization {
  daily: {
    used: number;              // $2,250
    limit: number;             // $5,000
    percent: number;           // 45%
  };
}

interface GradeDistribution {
  'A+': number;
  'A': number;
  'B': number;
  'C': number;
  'D': number;
}

interface HeatMapItem {
  symbol: string;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';  // Color coded
  exposure: number;            // % of account
}
```

**API Endpoints Required:**
- `GET /api/risk/metrics` → All risk data
- `GET /api/risk/grades` → Grade distribution
- `GET /api/risk/heatmap` → Symbol risk exposure
- `GET /api/backtest/{id}/drawdown` → Drawdown chart data

---

### Page 4: Analytics

**Purpose:** Performance summary, equity curve, trade analysis, backtest results

**Components Used:**
- Chart (Equity Curve - Line chart)
- Stats Grid (4 columns: Starting, Current, Total Return, Ann. Return)
- Stats Cards (Performance metrics + Risk metrics)
- Table (Trade Analysis with grades)
- Summary Cards (Backtest results)

**Layout Grid:**
```
┌────────────────────────────────────────────────────────────┐
│ Equity Curve                                               │
│ ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁                                             │
│ 4-col Stats: Start | Current | Total Return | Ann Return │
├─────────────────────────┬──────────────────────────────────┤
│ Performance Metrics     │ Risk Metrics                     │
│ - Total Trades         │ - Sharpe Ratio                  │
│ - Win Rate             │ - Max Drawdown                  │
│ - Profit Factor        │ - Consecutive Wins/Losses       │
│ - Avg Win/Loss         │ - Profit/Risk Ratio             │
├────────────────────────────────────────────────────────────┤
│ Trade Analysis Table                                      │
│ # | Symbol | Type | Entry | Exit | Size | P&L | R/R | Grade│
├────────────────────────────────────────────────────────────┤
│ Backtest Results Summary                                  │
│ Period | Total Trades | Win Rate | Return | Max DD       │
└────────────────────────────────────────────────────────────┘
```

**Data Models:**
```typescript
interface EquityCurvePoint {
  timestamp: string;
  equity: number;
  balance: number;
  drawdown: number;
}

interface PerformanceStats {
  totalTrades: number;
  winRate: number;              // %
  profitFactor: number;
  avgWin: number;
  avgLoss: number;
  bestTrade: number;
  worstTrade: number;
}

interface RiskStats {
  sharpeRatio: number;
  maxDrawdown: number;           // %
  consecutiveWins: number;
  consecutiveLosses: number;
  profitRiskRatio: number;
  ulcerIndex: number;
}

interface TradeAnalysisRow {
  tradeNumber: number;
  symbol: string;
  type: string;
  entry: number;
  exit: number;
  size: number;
  pnl: number;
  pnlPercent: number;
  rrRatio: number;
  grade: 'A+' | 'A' | 'B' | 'C' | 'D';
}

interface BacktestSummary {
  period: string;
  totalTrades: number;
  winRate: number;
  totalReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
}
```

**API Endpoints Required:**
- `GET /api/analytics/equity-curve` → Equity curve data
- `GET /api/analytics/performance` → Performance stats
- `GET /api/analytics/risk` → Risk stats
- `GET /api/trades?withGrades=true` → Trade analysis with grades
- `GET /api/backtest/{id}/summary` → Backtest results

**Chart Library:**
- **Chart.js** or **Recharts** for Equity Curve (line chart)
- Real-time updates via WebSocket for live P&L

---

### Page 5: Settings

**Purpose:** Configure OANDA API, risk limits, strategy, data sources

**Components Used:**
- Form inputs (text, password, select)
- Toggles (switches)
- Sliders (for percentages)
- Form sections with dividers
- Alert boxes (info, warning)
- Buttons (Save, Reset, Test)

**Layout:**
```
┌────────────────────────────────────────────────────────────┐
│ OANDA API Configuration                                   │
│ Account Type: [Demo ▼]                                    │
│ Account ID: [123456789]  API Key: [●●●●●●●●●●●●]       │
│ [Toggle] Paper Trading                                    │
│ [Test Connection]                                         │
│                                                            │
│ Risk Management Settings                                  │
│ Daily Risk Limit: [■■■░░] 5%                              │
│ Max Drawdown: [■■■■■░░░] 15%                              │
│ Max Risk per Trade: [■■░░░░░░] 2%                         │
│ Min Win Rate: [40] %   Consecutive Loss Limit: [3]       │
│                                                            │
│ Strategy Configuration                                    │
│ Active Strategy: [Default Trend Following ▼]             │
│ Timeframe: [1D ▼]   Max Open Positions: [5]              │
│ [Toggle] Auto-Trading Enabled                            │
│ [Toggle] Stop Loss Enforcement                           │
│                                                            │
│ Data Source Configuration                                │
│ Primary Provider: [OANDA API ▼]                          │
│ Historical Data: [OANDA ▼]                               │
│ Quote Frequency: [Tick ▼]   Data Period: [1 Year ▼]    │
│ [Toggle] Cache Historical Data                           │
│                                                            │
│ Advanced Settings                                         │
│ [Toggle] Enable Logging                                  │
│ [Toggle] Email Notifications                             │
│ [Export Account History]                                 │
│ [Reset All Settings]                                     │
│                                                            │
│                            [Cancel] [Save All Changes]   │
└────────────────────────────────────────────────────────────┘
```

**Data Models:**
```typescript
interface Settings {
  oanda: OANDAConfig;
  risk: RiskLimits;
  strategy: StrategyConfig;
  dataSource: DataSourceConfig;
  advanced: AdvancedSettings;
}

interface OANDAConfig {
  accountType: 'DEMO' | 'LIVE';
  accountId: string;
  apiKey: string;           // Encrypted in backend
  paperTrading: boolean;
}

interface RiskLimits {
  dailyRiskPercent: number;
  maxDrawdownPercent: number;
  maxRiskPerTradePercent: number;
  minWinRate: number;
  consecutiveLossLimit: number;
}

interface StrategyConfig {
  activeStrategy: string;
  timeframe: string;
  maxOpenPositions: number;
  autoTradingEnabled: boolean;
  stopLossEnforced: boolean;
}

interface DataSourceConfig {
  primaryProvider: string;      // OANDA, yfinance, etc.
  historicalData: string;
  quoteFrequency: string;       // Tick, 1s, 5s, 1m
  backtestPeriod: string;       // 1 year, 2 years, etc.
  cacheData: boolean;
}

interface AdvancedSettings {
  loggingEnabled: boolean;
  emailNotifications: boolean;
}
```

**API Endpoints Required:**
- `GET /api/settings` → Get all settings
- `POST /api/settings` → Save settings
- `POST /api/settings/test-connection` → Test OANDA API
- `POST /api/settings/reset` → Reset to defaults
- `GET /api/settings/export` → Export account history

---

## 🔌 State Management Structure (Redux)

Recommended state shape for your Redux store:

```typescript
interface RootState {
  // Account & Portfolio
  account: {
    balance: number;
    equity: number;
    availableMargin: number;
    marginUsed: number;
    riskRemaining: number;
    loading: boolean;
    error: string | null;
  };

  // Real-time Positions
  positions: {
    bySymbol: {
      [symbol: string]: Position;
    };
    allSymbols: string[];
    loading: boolean;
    error: string | null;
  };

  // Real-time Quotes
  quotes: {
    bySymbol: {
      [symbol: string]: Quote;
    };
    loading: boolean;
    error: string | null;
  };

  // Orders
  orders: {
    active: Order[];
    history: Trade[];
    selectedOrderId: string | null;
    loading: boolean;
    error: string | null;
  };

  // Analytics & Backtest
  analytics: {
    equityCurve: EquityCurvePoint[];
    performanceStats: PerformanceStats;
    riskStats: RiskStats;
    tradeAnalysis: TradeAnalysisRow[];
    backtestResults: BacktestSummary;
    loading: boolean;
    error: string | null;
  };

  // Risk Metrics
  risk: {
    metrics: RiskMetrics;
    utilization: RiskUtilization;
    grades: GradeDistribution;
    heatmap: HeatMapItem[];
    loading: boolean;
    error: string | null;
  };

  // Settings
  settings: Settings & {
    loading: boolean;
    error: string | null;
    unsavedChanges: boolean;
  };

  // WebSocket Status
  websocket: {
    connected: boolean;
    lastUpdate: string | null;
  };
}
```

---

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
├─────────────────────────────────────────────────────────────┤
│  Page Components (Dashboard, Trading, etc.)                │
│         ↕ Redux Dispatch                                   │
│  Redux Store (State Management)                            │
│         ↕ useSelector / useDispatch                        │
│  Custom Hooks (useQuotes, useAccount, etc.)                │
│         ↕ API Calls / WebSocket                            │
├─────────────────────────────────────────────────────────────┤
│                    Backend (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│  API Routes (/api/*)                                       │
│     ↕ Business Logic                                       │
│  Services (OANDA client, yfinance, Backtest engine)       │
│     ↕ External APIs                                        │
│  OANDA API, yfinance API                                   │
├─────────────────────────────────────────────────────────────┤
│                    WebSocket (Real-time)                   │
├─────────────────────────────────────────────────────────────┤
│  /ws endpoint for live quotes, position updates           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📡 WebSocket Integration

For real-time data (quotes, positions, P&L):

```typescript
// Frontend WebSocket Hook
useWebSocket('/ws', {
  onMessage: (data) => {
    dispatch(updateQuotes(data.quotes));
    dispatch(updatePositions(data.positions));
    dispatch(updateAccount(data.account));
  },
  reconnect: true,
  shouldReconnect: () => true,
});
```

**Backend WebSocket Broadcast:**
```
Update frequency: 100ms (10 updates/second) for quotes
Message format:
{
  "type": "quotes",
  "data": {
    "EUR/USD": { "bid": 1.0950, "ask": 1.0952, "time": "..." },
    "GBP/USD": { "bid": 1.2700, "ask": 1.2702, "time": "..." }
  }
}
```

---

## 🎯 Integration Priority & Dependencies

### Phase 1: Core Pages (Hours 6-8)
**Priority:** Highest | **Dependency:** Backend API endpoints working

- [ ] Setup React project + Redux store
- [ ] Create layout components (Header, Sidebar, MainLayout)
- [ ] Build Dashboard page (static mockup → connected to API)
- [ ] Build Trading page (order form + order list)
- [ ] Connect to `GET /api/account`, `GET /api/positions`, `GET /api/orders`

### Phase 2: Charts & Real-time (Hours 9-10)
**Priority:** High | **Dependency:** TradingView + Chart.js libraries, WebSocket ready

- [ ] Integrate TradingView Lightweight Charts (candlestick)
- [ ] Integrate Chart.js for line charts (equity curve)
- [ ] Setup WebSocket middleware in Redux
- [ ] Add real-time quote updates
- [ ] Build Risk Management page (risk metrics + charts)
- [ ] Build Analytics page (equity curve + stats)

### Phase 3: Advanced Features (Hours 11-15)
**Priority:** Medium | **Dependency:** All APIs + WebSocket stable

- [ ] Backtest integration (load results, display)
- [ ] Trade execution flow (form → API → position update)
- [ ] Settings page (OANDA config, risk limits)
- [ ] Form validation + error handling
- [ ] Responsive design verification

---

## 🧪 Testing Checklist for Frontend

- [ ] All pages load without console errors
- [ ] Redux state updates correctly on API responses
- [ ] Forms validate before submission
- [ ] Real-time quotes update via WebSocket
- [ ] Charts render and respond to data changes
- [ ] Responsive design: 320px / 768px / 1024px / 1920px
- [ ] Button states (default, hover, active, disabled)
- [ ] Error handling & fallback UI
- [ ] Performance: Pages load in < 2s, charts render in < 500ms
- [ ] Accessibility: ARIA labels, keyboard navigation, color contrast

---

## 🚀 Recommended Tech Stack

### Frontend
- **Framework:** Next.js or Create React App
- **Language:** TypeScript
- **State:** Redux Toolkit
- **HTTP:** Axios
- **WebSocket:** Socket.io or native WebSocket
- **Charts:** TradingView Lightweight Charts + Chart.js / Recharts
- **UI Components:** Custom (from figma-components CSS)
- **Styling:** CSS modules + CSS variables
- **Testing:** Jest + React Testing Library
- **Build:** Vite (faster than CRA)

### Backend (Elon - Already Started)
- **Framework:** FastAPI
- **Language:** Python
- **ORM:** SQLAlchemy
- **Database:** PostgreSQL
- **Cache:** Redis
- **WebSocket:** FastAPI WebSockets
- **Broker API:** OANDA SDK
- **Data:** yfinance
- **Backtest:** Your custom engine
- **Testing:** Pytest

---

## 📝 CSS Import Strategy

1. Copy all component CSS from `figma-components/` to your `frontend/src/styles/components/`
2. Import design tokens CSS in main layout:
   ```html
   <link rel="stylesheet" href="/styles/design-tokens.css">
   ```
3. Import component stylesheets as needed:
   ```css
   @import 'components/buttons.css';
   @import 'components/cards.css';
   @import 'components/tables.css';
   ```
4. Build React components wrapping these CSS classes:
   ```tsx
   export const Button = ({ variant = 'primary', ...props }) => (
     <button className={`btn btn-${variant}`} {...props} />
   );
   ```

---

## 🎯 Success Criteria for Frontend Integration

✅ All 5 pages render with data from backend  
✅ Real-time quotes update via WebSocket  
✅ Order form validation + submission works  
✅ Charts render correctly (candlestick + equity curve)  
✅ Tables with sorting/filtering functional  
✅ Responsive design verified at all breakpoints  
✅ Error handling + loading states implemented  
✅ Performance: First Contentful Paint < 2s  
✅ No console errors or warnings  
✅ All components match design mockups

---

## 📞 Questions for Elon?

- **Chart library choice?** → Recommend TradingView (best for trading), backup: Chart.js
- **REST vs GraphQL?** → Recommend REST (simpler, aligned with FastAPI)
- **State management:** Redux or Zustand? → Recommend Redux (more features)
- **Testing strategy?** → Unit tests for components, integration tests for page flows
- **Deployment?** → Docker (frontend in Next.js container)

---

## 🎁 Deliverables Ready for You

1. ✅ 5 complete HTML mockups (open in browser)
2. ✅ All CSS components (copy & use)
3. ✅ Design tokens (JSON + CSS variables)
4. ✅ Responsive guidelines (tested at 4 breakpoints)
5. ✅ Data model specs (TypeScript interfaces)
6. ✅ API endpoint list (what backend needs to provide)
7. ✅ Redux state shape (copy & adapt)
8. ✅ This spec (reference during development)

---

**Created by:** Erkan (UX/UI Designer)  
**For:** Elon (CTO)  
**Ready for:** Frontend Development (Hours 6-10)  
**Date:** 2026-04-23 18:45 CET

---

## Next Steps

1. **Elon:** Review this spec + mockups
2. **Elon:** Setup React project + Redux store (match state shape above)
3. **Elon:** Build page components (use HTML mockups as reference)
4. **Elon:** Connect to backend APIs (verify endpoints exist)
5. **Elon:** Integrate WebSocket for real-time updates
6. **Elon:** Test + iterate on responsive design

**Questions?** Jarvis coordinates with Erkan for any spec clarifications.
