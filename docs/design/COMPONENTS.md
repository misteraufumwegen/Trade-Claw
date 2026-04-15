# Trade-Claw Component Breakdown
**Version:** 1.0 | **Tech Stack:** React 18 + TypeScript + TailwindCSS | **State:** Redux Toolkit / Zustand (TBD)

---

## 1. APPLICATION STRUCTURE

```
src/
├── pages/
│   ├── Dashboard.tsx          ← Module 1
│   ├── TradingConsole.tsx     ← Module 2
│   ├── RiskManagement.tsx     ← Module 3
│   ├── Analytics.tsx          ← Module 4
│   └── Settings.tsx           ← Module 5
│
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx       (main container, nav)
│   │   ├── Navbar.tsx         (top bar with menu)
│   │   ├── Sidebar.tsx        (navigation)
│   │   └── Footer.tsx         (optional status bar)
│   │
│   ├── common/
│   │   ├── Button.tsx         (all button variants)
│   │   ├── Card.tsx           (standard card wrapper)
│   │   ├── Badge.tsx          (pills, labels)
│   │   ├── Tooltip.tsx        (info popups)
│   │   ├── Modal.tsx          (dialogs)
│   │   ├── Spinner.tsx        (loading indicator)
│   │   ├── Toast.tsx          (notifications)
│   │   ├── ProgressBar.tsx    (risk meters)
│   │   ├── Table.tsx          (data tables)
│   │   └── Charts.tsx         (chart wrapper)
│   │
│   ├── dashboard/
│   │   ├── KeyMetrics.tsx     (4 KPI cards)
│   │   ├── RiskStatus.tsx     (drawdown + position size)
│   │   ├── ActivePositions.tsx (positions table)
│   │   ├── QuickActions.tsx   (links + emergency halt)
│   │   ├── AlertsBanner.tsx   (critical alerts)
│   │   └── Dashboard.tsx      (container)
│   │
│   ├── trading/
│   │   ├── MacroEventsFeed.tsx   (live events list)
│   │   ├── StrategySelector.tsx  (dropdown + grades)
│   │   ├── TradeEntryForm.tsx    (big form)
│   │   ├── CorrelationMatrix.tsx (heatmap)
│   │   ├── RiskRewardValidator.tsx (live validation)
│   │   └── TradingConsole.tsx   (container)
│   │
│   ├── risk/
│   │   ├── HardLimitsPanel.tsx  (position size, drawdown, daily loss)
│   │   ├── StopLossLock.tsx     (SL immutable status)
│   │   ├── EmergencyHalt.tsx    (big red button + modal)
│   │   ├── RiskAlerts.tsx       (live alert feed)
│   │   └── RiskManagement.tsx   (container)
│   │
│   ├── analytics/
│   │   ├── FilterBar.tsx         (time range, asset, grade, sort)
│   │   ├── WinRateTrend.tsx      (line chart)
│   │   ├── ProfitFactorTrend.tsx (line chart)
│   │   ├── MonthlyPnL.tsx        (bar chart)
│   │   ├── DrawdownHistory.tsx   (area chart)
│   │   ├── TradeHistoryTable.tsx (scrollable table)
│   │   ├── Statistics.tsx        (summary stats)
│   │   └── Analytics.tsx         (container)
│   │
│   └── settings/
│       ├── SettingsSidebar.tsx      (nav)
│       ├── ConnectionStatus.tsx     (API status)
│       ├── BrokerAccount.tsx        (OANDA config)
│       ├── AssetsSelector.tsx       (checkboxes)
│       ├── RiskConfiguration.tsx    (read-only limits)
│       ├── NotificationSettings.tsx (alert toggles)
│       └── Settings.tsx             (container)
│
├── hooks/
│   ├── usePositions.ts         (get/update positions)
│   ├── usePrices.ts            (live price feed)
│   ├── useAlerts.ts            (alerts state)
│   ├── useRisk.ts              (risk metrics)
│   ├── useTrades.ts            (trade history)
│   └── useCorrelation.ts       (correlation data)
│
├── services/
│   ├── api/
│   │   ├── oanda.ts            (OANDA API calls)
│   │   ├── trades.ts           (trade history CRUD)
│   │   ├── alerts.ts           (alert management)
│   │   ├── macro.ts            (worldmonitor.app API)
│   │   └── correlation.ts      (correlation calculations)
│   │
│   └── validators/
│       ├── tradeValidator.ts   (R/R ratio, size, correlation)
│       ├── riskValidator.ts    (drawdown, daily loss checks)
│       └── immutabilityCheck.ts (SL lock logic)
│
├── store/
│   ├── slices/
│   │   ├── positionsSlice.ts
│   │   ├── tradesSlice.ts
│   │   ├── alertsSlice.ts
│   │   ├── riskSlice.ts
│   │   ├── uiSlice.ts
│   │   └── settingsSlice.ts
│   │
│   └── store.ts               (Redux configuration)
│
├── types/
│   ├── index.ts               (global types)
│   ├── trade.ts
│   ├── position.ts
│   ├── alert.ts
│   ├── macro.ts
│   ├── broker.ts
│   └── ui.ts
│
├── utils/
│   ├── formatting.ts          (currency, decimals)
│   ├── calculations.ts        (PnL, risk metrics)
│   ├── validators.ts          (form validation)
│   ├── constants.ts           (risk limits, grades)
│   └── time.ts                (date/time formatting)
│
├── styles/
│   ├── tailwind.config.ts     (color vars, spacing)
│   ├── globals.css            (reset, fonts)
│   └── animations.css         (motion)
│
├── App.tsx                    (routing)
└── index.tsx                  (entry point)
```

---

## 2. CORE COMPONENTS (Detailed)

### 2.1 Layout Components

#### AppShell.tsx
```typescript
interface AppShellProps {
  children: ReactNode;
  currentPage: string;
}

/**
 * Main application container.
 * Renders: Navbar, Sidebar, main content area, alerts/toasts
 */
export const AppShell: React.FC<AppShellProps> = ({ children, currentPage }) => {
  // Layout logic
};
```

#### Navbar.tsx
```typescript
/**
 * Top navigation bar
 * - Logo + "TRADE-CLAW TRADING BOT"
 * - Current page title
 * - Quick navigation icons (⚙️ Settings, 📊 Analytics)
 * - API connection indicator (green dot)
 * - Timestamp (last updated: now)
 */
export const Navbar: React.FC = () => {
  // ...
};
```

#### Sidebar.tsx
```typescript
/**
 * Left navigation (Desktop only, hamburger on mobile)
 * Navigation items:
 * - 📊 Dashboard
 * - 🔄 Trading Console
 * - ⚠️ Risk Management
 * - 📈 Analytics
 * - ⚙️ Settings
 */
export const Sidebar: React.FC = () => {
  // ...
};
```

---

### 2.2 Common/Shared Components

#### Button.tsx
```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  icon?: ReactNode;
  loading?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  children: ReactNode;
}

/**
 * Unified button component with all variants
 * Handles loading states, disabled states, hover/focus feedback
 */
export const Button: React.FC<ButtonProps> = ({ variant = 'primary', ...props }) => {
  // ...
};
```

#### Card.tsx
```typescript
interface CardProps {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  interactive?: boolean;
  className?: string;
}

/**
 * Standard card container (neutral-800 bg, border, padding)
 * Interactive variant adds hover border highlight
 */
export const Card: React.FC<CardProps> = ({ ...props }) => {
  // ...
};
```

#### Modal.tsx
```typescript
interface ModalProps {
  isOpen: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  actions?: { label: string; onClick: () => void; variant?: string }[];
  children?: ReactNode;
}

/**
 * Dialog/modal overlay with dark background
 * Centered on screen, max-width 600px
 */
export const Modal: React.FC<ModalProps> = ({ ...props }) => {
  // ...
};
```

#### ProgressBar.tsx
```typescript
interface ProgressBarProps {
  current: number;
  max: number;
  color?: 'blue' | 'orange' | 'green' | 'red';
  showLabel?: boolean;
  animated?: boolean;
}

/**
 * Horizontal progress meter (for drawdown, position size, etc.)
 * Shows visual bar + percentage
 */
export const ProgressBar: React.FC<ProgressBarProps> = ({ ...props }) => {
  // ...
};
```

#### Table.tsx
```typescript
interface Column<T> {
  header: string;
  accessor: keyof T;
  render?: (value: any, row: T) => ReactNode;
  sortable?: boolean;
  width?: string;
}

interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  striped?: boolean;
  compact?: boolean;
  loading?: boolean;
}

/**
 * Flexible table component
 * Supports sorting, custom renderers, row clicks
 */
export const Table: React.FC<TableProps> = ({ ...props }) => {
  // ...
};
```

#### Toast.tsx
```typescript
interface ToastProps {
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration?: number; // ms, 0 = sticky
  onClose?: () => void;
}

/**
 * Notification toast (slides in from bottom)
 * Manages auto-dismiss
 */
export const Toast: React.FC<ToastProps> = ({ ...props }) => {
  // ...
};
```

#### Badge.tsx
```typescript
interface BadgeProps {
  label: string;
  variant?: 'default' | 'success' | 'danger' | 'warning' | 'info';
  icon?: ReactNode;
  size?: 'sm' | 'md';
}

/**
 * Pill-shaped label for status, grades, etc.
 */
export const Badge: React.FC<BadgeProps> = ({ ...props }) => {
  // ...
};
```

---

### 2.3 Dashboard Module Components

#### KeyMetrics.tsx
```typescript
interface KeyMetricsProps {
  todayPnL: number;
  todayReturn: number;
  monthPnL: number;
  monthReturn: number;
  winRate: number;
  profitFactor: number;
}

/**
 * 4 large KPI cards (Today's P&L, Month's P&L, Win Rate, Profit Factor)
 * Shows value, change %, and color (green/red)
 */
export const KeyMetrics: React.FC<KeyMetricsProps> = ({ ...props }) => {
  // ...
};
```

#### RiskStatus.tsx
```typescript
interface RiskStatusProps {
  drawdownCurrent: number;
  drawdownLimit: number;
  positionSizeCurrent: number;
  positionSizeLimit: number;
}

/**
 * Two progress bars:
 * 1. Drawdown status (orange if near limit)
 * 2. Position size usage (blue)
 * Shows numbers and recovery needed
 */
export const RiskStatus: React.FC<RiskStatusProps> = ({ ...props }) => {
  // ...
};
```

#### ActivePositions.tsx
```typescript
interface Position {
  id: string;
  asset: string;
  direction: 'BUY' | 'SELL';
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  size: number;
  unrealizedPnL: number;
  grade: 'A+' | 'A' | 'B';
  timeOpen: Date;
  lastUpdated: Date;
}

interface ActivePositionsProps {
  positions: Position[];
  onRefresh: () => void;
}

/**
 * List of open positions
 * Each row shows: asset, direction, prices, P&L, grade, time
 * Refresh button, live updates every 1-5s
 */
export const ActivePositions: React.FC<ActivePositionsProps> = ({ ...props }) => {
  // ...
};
```

#### AlertsBanner.tsx
```typescript
interface AlertsBannerProps {
  alerts: Alert[];
}

/**
 * Critical alerts banner at top of dashboard
 * Shows: Drawdown warning, SL immutable status, etc.
 * Sticky, dismissible or auto-dismiss after 10s
 */
export const AlertsBanner: React.FC<AlertsBannerProps> = ({ ...props }) => {
  // ...
};
```

---

### 2.4 Trading Module Components

#### MacroEventsFeed.tsx
```typescript
interface MacroEvent {
  id: string;
  time: Date;
  country: string;
  event: string;
  impact: 'LOW' | 'MEDIUM' | 'HIGH';
  forecast?: number;
  actual?: number;
}

interface MacroEventsFeedProps {
  events: MacroEvent[];
  onEventClick?: (event: MacroEvent) => void;
}

/**
 * Live macro events list from worldmonitor.app
 * Shows upcoming events, impact level, time countdown
 * Refreshes every 30s
 */
export const MacroEventsFeed: React.FC<MacroEventsFeedProps> = ({ ...props }) => {
  // ...
};
```

#### TradeEntryForm.tsx
```typescript
interface TradeEntry {
  asset: string;
  direction: 'BUY' | 'SELL';
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  positionSize: number;
  grade: 'A+' | 'A' | 'B' | 'ungraded';
}

interface TradeEntryFormProps {
  onSubmit: (trade: TradeEntry) => Promise<void>;
  onCancel: () => void;
  isImmutable?: boolean; // if SL lock is active
  assets: string[];
}

/**
 * Multi-tab form:
 * Tab 1: Entry Details (asset, direction, prices, size, grade)
 * Tab 2: Risk Check (validation summary)
 * Tab 3: Confirm (review + execute button)
 *
 * Auto-calculates:
 * - Risk/Reward ratio
 * - Position size based on risk
 * - Grade (Ünal's scoring)
 *
 * Validates in real-time, disables Execute if invalid
 */
export const TradeEntryForm: React.FC<TradeEntryFormProps> = ({ ...props }) => {
  // ...
};
```

#### CorrelationMatrix.tsx
```typescript
interface CorrelationData {
  assets: string[];
  matrix: number[][]; // 0-100 (%)
}

interface CorrelationMatrixProps {
  data: CorrelationData;
  baseAsset: string;
  onAssetChange: (asset: string) => void;
  timeWindow: '1H' | '4H' | '1D' | '1W';
}

/**
 * Color-coded correlation heatmap
 * Red (90%+) -> Orange (70-89%) -> Yellow (50-69%) -> Green (<50%)
 * Shows recommendations for correlated positions
 */
export const CorrelationMatrix: React.FC<CorrelationMatrixProps> = ({ ...props }) => {
  // ...
};
```

#### RiskRewardValidator.tsx
```typescript
interface ValidationResult {
  isValid: boolean;
  riskReward: number;
  warnings: string[];
  errors: string[];
}

interface RiskRewardValidatorProps {
  entry: number;
  stopLoss: number;
  takeProfit: number;
  direction: 'BUY' | 'SELL';
  minRatio?: number; // default 1:3
}

/**
 * Live validation component
 * Shows:
 * - R/R ratio (must be ≥ 1:3)
 * - Pips at risk vs reward
 * - Warnings if correlation too high, position too large, etc.
 */
export const RiskRewardValidator: React.FC<RiskRewardValidatorProps> = ({ ...props }) => {
  // ...
};
```

---

### 2.5 Risk Management Components

#### HardLimitsPanel.tsx
```typescript
interface Limits {
  maxPositionSize: number;
  currentPositionSize: number;
  maxDrawdown: number;
  currentDrawdown: number;
  maxDailyLoss: number;
  currentDailyLoss: number;
}

interface HardLimitsPanelProps {
  limits: Limits;
}

/**
 * Read-only display of 3 hard limits:
 * 1. Position Size (10%)
 * 2. Drawdown (-15%)
 * 3. Daily Loss (-5%)
 *
 * Shows progress bars + warnings
 */
export const HardLimitsPanel: React.FC<HardLimitsPanelProps> = ({ ...props }) => {
  // ...
};
```

#### StopLossLock.tsx
```typescript
interface StopLossLockProps {
  isActive: boolean;
  positions: Position[];
  reason: string; // e.g., "Drawdown approaching -15% limit"
}

/**
 * Shows SL immutability status
 * Lists affected positions (cannot modify stops)
 * Shows auto-unlock conditions
 */
export const StopLossLock: React.FC<StopLossLockProps> = ({ ...props }) => {
  // ...
};
```

#### EmergencyHalt.tsx
```typescript
interface EmergencyHaltProps {
  activePositionCount: number;
  onExecute: () => Promise<void>;
  disabled?: boolean;
}

/**
 * Large red button with modal confirmation
 * Modal shows:
 * - Warning message
 * - Positions to close
 * - Estimated loss
 * - Final confirmation button
 */
export const EmergencyHalt: React.FC<EmergencyHaltProps> = ({ ...props }) => {
  // ...
};
```

#### RiskAlerts.tsx
```typescript
interface Alert {
  id: string;
  type: 'critical' | 'warning' | 'info';
  timestamp: Date;
  message: string;
  action?: { label: string; onClick: () => void };
}

interface RiskAlertsProps {
  alerts: Alert[];
  limit?: number; // default 5 recent
}

/**
 * Live alert feed (newest at top)
 * Color-coded by severity (red/orange/blue)
 * Auto-refresh every 5s
 */
export const RiskAlerts: React.FC<RiskAlertsProps> = ({ ...props }) => {
  // ...
};
```

---

### 2.6 Analytics Module Components

#### FilterBar.tsx
```typescript
interface FilterBarProps {
  onFilterChange: (filters: {
    timeRange: string;
    asset: string;
    grade: string;
    status: string;
    sort: string;
    search: string;
  }) => void;
}

/**
 * Filter controls:
 * - Time Range (Last 7 Days, Last 30 Days, All)
 * - Asset (All, EUR/USD, GBP/USD, etc.)
 * - Grade (All, A+, A, B)
 * - Status (All, Won, Lost)
 * - Sort (Date, P&L, Duration)
 * - Search box (for ticker/notes)
 */
export const FilterBar: React.FC<FilterBarProps> = ({ ...props }) => {
  // ...
};
```

#### WinRateTrend.tsx
```typescript
interface WinRateTrendProps {
  data: { date: Date; winRate: number }[];
  period?: 'day' | 'week';
}

/**
 * Line chart showing win rate over time
 * Uses Chart.js or Recharts
 * Tooltip shows exact % and trade count
 */
export const WinRateTrend: React.FC<WinRateTrendProps> = ({ ...props }) => {
  // ...
};
```

#### TradeHistoryTable.tsx
```typescript
interface Trade {
  id: string;
  asset: string;
  direction: 'BUY' | 'SELL';
  entryPrice: number;
  exitPrice: number;
  stopLoss: number;
  takeProfit: number;
  pnl: number;
  grade: 'A+' | 'A' | 'B';
  openTime: Date;
  closeTime: Date;
}

interface TradeHistoryTableProps {
  trades: Trade[];
  onRowClick?: (trade: Trade) => void;
}

/**
 * Scrollable table with columns:
 * # | Asset | Direction | Entry | Exit | SL | TP | P&L | Grade
 *
 * Sortable columns, color-coded P&L (green/red)
 */
export const TradeHistoryTable: React.FC<TradeHistoryTableProps> = ({ ...props }) => {
  // ...
};
```

---

### 2.7 Settings Module Components

#### ConnectionStatus.tsx
```typescript
interface ConnectionStatusProps {
  broker: string;
  status: 'connected' | 'disconnected' | 'connecting';
  lastCheck: Date;
  apiValid: boolean;
  priceLatency: number; // ms
  uptime: number; // seconds
  lastError?: { date: Date; message: string };
}

/**
 * Shows broker connection, API key status, price feed, system health
 * Has [Test Connection] and [Reconnect] buttons
 */
export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ ...props }) => {
  // ...
};
```

#### BrokerAccount.tsx
```typescript
interface AccountDetails {
  brokerId: string;
  accountId: string;
  accountType: 'live' | 'practice';
  balance: number;
  equity: number;
  margin: number;
}

interface BrokerAccountProps {
  account: AccountDetails;
  onApiKeyChange: (newKey: string) => Promise<void>;
}

/**
 * Show/edit broker settings:
 * - Broker selection (OANDA)
 * - API key (masked, changeable)
 * - Account type (read-only)
 * - Account details (read-only)
 */
export const BrokerAccount: React.FC<BrokerAccountProps> = ({ ...props }) => {
  // ...
};
```

#### AssetsSelector.tsx
```typescript
interface AssetsSelectorProps {
  allAssets: string[];
  selected: string[];
  onSave: (selected: string[]) => Promise<void>;
}

/**
 * Checkboxes for tradable assets
 * Pre-populated with defaults
 * Save button commits changes
 */
export const AssetsSelector: React.FC<AssetsSelectorProps> = ({ ...props }) => {
  // ...
};
```

---

## 3. STATE MANAGEMENT (Redux Toolkit)

### Slices

#### positionsSlice.ts
```typescript
export const positionsSlice = createSlice({
  name: 'positions',
  initialState: {
    list: [],
    loading: false,
    error: null,
  },
  reducers: {
    addPosition: (state, action) => { /* ... */ },
    updatePosition: (state, action) => { /* ... */ },
    closePosition: (state, action) => { /* ... */ },
    setLoading: (state, action) => { /* ... */ },
  },
  extraReducers: (builder) => {
    // async thunks
  },
});
```

#### alertsSlice.ts
```typescript
export const alertsSlice = createSlice({
  name: 'alerts',
  initialState: {
    list: [],
    criticalCount: 0,
  },
  reducers: {
    addAlert: (state, action) => { /* ... */ },
    clearAlert: (state, action) => { /* ... */ },
    clearAll: (state) => { /* ... */ },
  },
});
```

#### riskSlice.ts
```typescript
export const riskSlice = createSlice({
  name: 'risk',
  initialState: {
    drawdown: 0,
    daylyLoss: 0,
    positionSizeUsage: 0,
    slImmutable: false,
    halted: false,
  },
  reducers: {
    updateRiskMetrics: (state, action) => { /* ... */ },
    activateSLImmutable: (state) => { /* ... */ },
    deactivateSLImmutable: (state) => { /* ... */ },
    emergencyHalt: (state) => { /* ... */ },
  },
});
```

---

## 4. HOOKS (Custom React Hooks)

### usePositions.ts
```typescript
/**
 * Fetches and manages open positions
 * Auto-updates every 1-5s
 * Handles WebSocket or polling
 */
export const usePositions = () => {
  const dispatch = useDispatch();
  
  useEffect(() => {
    // Subscribe to position updates
  }, [dispatch]);
  
  return { positions: useSelector(state => state.positions.list), loading };
};
```

### usePrices.ts
```typescript
/**
 * Live price feed subscription
 * Pushes updates to price store
 * WebSocket from OANDA
 */
export const usePrices = () => {
  const dispatch = useDispatch();
  
  useEffect(() => {
    // WebSocket subscription
  }, [dispatch]);
};
```

### useRisk.ts
```typescript
/**
 * Calculates and monitors risk metrics
 * - Drawdown (real-time)
 * - Position size usage
 * - Daily P&L loss
 * - Triggers SL immutable if needed
 */
export const useRisk = () => {
  const positions = useSelector(state => state.positions.list);
  const trades = useSelector(state => state.trades.today);
  
  const metrics = useMemo(() => {
    // Calculate metrics
  }, [positions, trades]);
  
  return metrics;
};
```

---

## 5. API INTEGRATION (OANDA)

### services/api/oanda.ts
```typescript
/**
 * OANDA v20 REST API client
 * 
 * Methods:
 * - getAccount() → account details
 * - getPositions() → open positions
 * - createTrade(entry, sl, tp, size) → send order
 * - closePosition(positionId) → close trade
 * - getPrices(assets) → current quotes
 * - streamPrices(assets) → WebSocket subscription
 */
export const oandaClient = {
  async getAccount() { /* ... */ },
  async getPositions() { /* ... */ },
  async createTrade() { /* ... */ },
  // ...
};
```

### services/api/macro.ts
```typescript
/**
 * Macro events from worldmonitor.app
 * 
 * Methods:
 * - getEvents() → upcoming events
 * - subscribeEvents() → WebSocket feed
 */
export const macroApi = {
  async getEvents() { /* ... */ },
  subscribeEvents(callback) { /* ... */ },
};
```

### services/api/correlation.ts
```typescript
/**
 * Calculate correlation between assets
 * 
 * Methods:
 * - getCorrelationMatrix(assets, timeWindow) → matrix
 * - pairwiseCorrelation(asset1, asset2, timeWindow) → single value
 */
export const correlationApi = {
  async getCorrelationMatrix() { /* ... */ },
};
```

---

## 6. TYPES & INTERFACES

### types/trade.ts
```typescript
export interface Trade {
  id: string;
  asset: string;
  direction: 'BUY' | 'SELL';
  entryPrice: number;
  exitPrice: number;
  stopLoss: number;
  takeProfit: number;
  positionSize: number; // %
  pnl: number; // USD
  pnlPercent: number; // %
  grade: 'A+' | 'A' | 'B' | 'ungraded';
  riskRewardRatio: number; // e.g., 1.77
  openTime: Date;
  closeTime: Date;
  duration: number; // minutes
  closedBy: 'tp' | 'sl' | 'manual' | 'emergency';
}
```

### types/position.ts
```typescript
export interface Position {
  id: string;
  asset: string;
  direction: 'BUY' | 'SELL';
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  positionSize: number; // %
  unrealizedPnL: number; // USD
  unrealizedPnLPercent: number; // %
  grade: 'A+' | 'A' | 'B';
  openTime: Date;
  lastUpdated: Date;
  riskRewardRatio: number;
}
```

### types/alert.ts
```typescript
export interface Alert {
  id: string;
  type: 'critical' | 'warning' | 'info';
  category: 'drawdown' | 'position_size' | 'correlation' | 'trade' | 'system';
  message: string;
  timestamp: Date;
  dismissible: boolean;
}
```

---

## 7. TESTING STRATEGY

```
Unit Tests:
├── components/ (each component)
├── hooks/ (usePositions, usePrices, etc.)
├── services/ (API mocks)
├── utils/ (calculations, validators)
└── types/ (type safety)

Integration Tests:
├── Dashboard flow (positions update live)
├── Trading flow (entry → validation → execution)
├── Risk management (SL lock triggers, emergency halt)
└── Settings → API (changes persist)

E2E Tests:
├── Full trade execution (entry to close)
├── Risk limit trigger (drawdown -15%)
├── Emergency halt
└── Analytics (filters, charts)
```

---

## 8. PERFORMANCE CONSIDERATIONS

- **Memoization:** All components using data selectors memoized with `React.memo`
- **Virtualization:** TradeHistoryTable uses react-window for 1000+ rows
- **Debouncing:** FilterBar, search inputs debounced 300ms
- **WebSockets:** Price feed and alerts via WebSocket, not polling
- **Lazy Loading:** Analytics charts lazy-loaded on tab click
- **Code Splitting:** Each module (Dashboard, Trading, Risk, Analytics, Settings) in separate chunks

---

**Status:** ✅ Component library spec complete. Ready for Elon to code.
