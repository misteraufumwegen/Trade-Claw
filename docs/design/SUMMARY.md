# Trade-Claw Frontend Design Summary
**Prepared by:** Erkan (UX/UI Designer)  
**Date:** April 15, 2026  
**Status:** ✅ Design Specification Complete  
**Handoff Target:** Elon (Frontend Developer)  
**Timeline:** 6-8 hours of design work completed

---

## 📋 DELIVERABLES CHECKLIST

✅ **DESIGN_SYSTEM.md**
- Color palette (dark mode, 10-color semantic system)
- Typography (type scale, font stack, sizes 32px down to 12px)
- Spacing & layout grid (8px base, 12-column responsive)
- Border radius, shadows, component variants
- States & animations, accessibility requirements
- Icon system and motion specifications

✅ **WIREFRAMES.md**
- 5 complete modules with desktop & mobile layouts
- Module 1: Dashboard (alerts, KPIs, positions, risk status, quick actions)
- Module 2: Trading Console (macro events, entry form, correlation matrix)
- Module 3: Risk Management (hard limits, SL lock, emergency halt, alerts)
- Module 4: Analytics (filters, charts, trade history table, stats)
- Module 5: Settings (connection, broker, assets, risk, notifications)
- 3 key interaction flows (trade execution, emergency halt, risk trigger)

✅ **COMPONENTS.md**
- Full React component tree (50+ components)
- File structure & folder organization
- Each component spec with props, purpose, behavior
- Redux state management slices (7 slices)
- Custom hooks (6 hooks for data/logic)
- API integration specs (OANDA, macro, correlation)
- TypeScript interfaces for all data models
- Testing strategy & performance guidelines

✅ **SUMMARY.md** (this document)
- Handoff checklist, naming conventions, dev guidelines

---

## 🎨 DESIGN HIGHLIGHTS

### Color Psychology
- **Primary Blue (#2196F3):** Trust, action, primary CTAs
- **Green (#4CAF50):** Profit, positive, wins
- **Red (#F44336):** Losses, danger, critical alerts
- **Orange (#FF9800):** Warnings, caution, approaching limits
- **Dark Neutral (#1F2937 - #111827):** Professional trading aesthetic

### Grid & Responsive Layout
- 1440px max-width on desktop
- 12-column grid with 24px gutters
- Mobile-first approach: single column → 2 columns (tablet) → 3+ (desktop)
- Touch targets: 44px minimum (buttons, icons)

### Typography Hierarchy
- H1: 32px (page titles)
- H4: 20px (card titles)
- Body: 14px (standard text)
- Label: 12px (form labels, hints)
- **Monospace for prices/numbers:** Fira Code at 13px

### Animation & Micro-interactions
- Button tap: scale 0.98 (100ms)
- Card hover: border highlight + shadow lift
- Toast/alert: slide in from bottom (250ms)
- Spinner: 0.6s rotation (infinite)
- Default transition: 150ms ease-out

### Accessibility (WCAG AA)
- 4.5:1 color contrast minimum
- 2px focus outline on all interactive elements
- Semantic HTML (`<button>`, `<input>`, `<label>`)
- `aria-live` for alerts, `aria-label` for icons
- `prefers-reduced-motion` respected

---

## 🔧 DEVELOPMENT GUIDELINES FOR ELON

### Tech Stack (Assumed)
```
Frontend:
- React 18 + TypeScript
- TailwindCSS (with custom design tokens)
- Redux Toolkit (state management)
- React Router (navigation)
- React Query / SWR (data fetching & caching)
- Chart.js or Recharts (charts)
- React Icons or Heroicons (icons)

Infrastructure:
- Vite or Next.js (build)
- Jest + React Testing Library (testing)
- Prettier + ESLint (code quality)

API:
- OANDA v20 REST + WebSocket
- worldmonitor.app for macro events
- Internal correlation calculations

Deployment:
- Docker (containerization)
- Vercel or AWS (hosting)
```

### Folder Structure (Must Follow)
```
src/
├── pages/              (5 main pages)
├── components/
│   ├── layout/        (AppShell, Navbar, Sidebar)
│   ├── common/        (Button, Card, Modal, etc.)
│   ├── dashboard/     (Dashboard-specific)
│   ├── trading/       (Trading Console-specific)
│   ├── risk/          (Risk Management-specific)
│   ├── analytics/     (Analytics-specific)
│   └── settings/      (Settings-specific)
├── hooks/             (6 custom hooks)
├── services/          (API clients, validators)
├── store/             (Redux slices, store config)
├── types/             (TypeScript interfaces)
├── utils/             (helpers, calculations)
└── styles/            (CSS variables, tailwind config)
```

### Naming Conventions

**Components:**
- PascalCase: `Dashboard.tsx`, `KeyMetrics.tsx`, `TradeEntryForm.tsx`
- Container suffix: `Dashboard.tsx` contains child components
- Descriptive names: `ActivePositions` (not `PosTable`), `RiskStatus` (not `RiskBar`)

**Functions/Hooks:**
- camelCase: `usePositions`, `usePrices`, `getRiskMetrics`
- Prefix hooks with `use`: `useRisk`, `useAlerts`, `useTrades`
- Prefix API calls: `getAccount`, `createTrade`, `updatePosition`

**Types/Interfaces:**
- PascalCase: `Position`, `Trade`, `Alert`, `MacroEvent`
- Suffix with `Props`: `KeyMetricsProps`, `TradeEntryFormProps`
- Use `Interface` for object shapes, `Type` for unions/literals

**Redux Slices:**
- Slice name (camelCase): `positionsSlice`, `alertsSlice`, `riskSlice`
- Actions (camelCase): `addPosition`, `updatePosition`, `clearAlert`
- Selectors: `selectPositions`, `selectAlerts`, `selectRiskMetrics`

**CSS Classes:**
- TailwindCSS utility classes (no custom CSS unless necessary)
- CSS variables for design tokens: `--color-primary-500`, `--space-4`
- Custom classes only for complex layouts: `.correlation-heatmap`

**Files:**
- `.ts` for pure logic/utilities
- `.tsx` for React components
- `.test.ts(x)` for unit tests
- `.styles.ts` for styled components (if used)

### Component Props Pattern
```typescript
interface ComponentProps {
  // Data props (required/optional)
  data?: T;
  items: T[];
  
  // Callback props
  onSubmit?: (data: T) => void;
  onCancel?: () => void;
  
  // UI props (optional)
  loading?: boolean;
  disabled?: boolean;
  className?: string;
  
  // Children (if container)
  children?: ReactNode;
}

export const Component: React.FC<ComponentProps> = ({ ...props }) => {
  // Implementation
};
```

### State Management Rules
1. **Local state:** Component `useState` for form inputs, UI toggles
2. **Redux:** Global state (positions, trades, alerts, risk metrics, settings)
3. **React Query:** API cache (positions, prices, trades history)
4. **Custom hooks:** Derived state, calculations (useRisk, useCorrelation)

**DO NOT mix storage layers — one source of truth per domain.**

### API Integration Pattern
```typescript
// ✅ Good: All OANDA calls in one service
export const oandaClient = {
  async getAccount() { /* ... */ },
  async getPositions() { /* ... */ },
  streamPrices(callback) { /* ... */ },
};

// Component consumes via hook:
const { positions, loading } = usePositions();

// ❌ Bad: Direct API calls in component
const MyComponent = () => {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch('https://api.oanda.com/...') // Don't do this
  }, []);
};
```

### Form Validation Pattern
```typescript
// Validators in services/validators/
export const validateTrade = (trade: TradeEntry): ValidationResult => {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  if (riskReward < 1.3) {
    errors.push("Risk/Reward must be ≥ 1:3");
  }
  if (positionSize > 10) {
    errors.push("Position size exceeds 10%");
  }
  if (correlationWithOpenPositions > 85) {
    warnings.push("High correlation risk");
  }
  
  return { isValid: errors.length === 0, errors, warnings };
};

// Component uses validator:
const [validation, setValidation] = useState<ValidationResult | null>(null);
useEffect(() => {
  setValidation(validateTrade(formData));
}, [formData]);
```

### Testing Requirements (Minimum)
```typescript
// Each component needs at least these tests:

describe('Button', () => {
  it('renders with label', () => { });
  it('calls onClick when clicked', () => { });
  it('disables when disabled prop is true', () => { });
});

describe('usePositions', () => {
  it('fetches positions on mount', () => { });
  it('updates on price change', () => { });
  it('handles API errors gracefully', () => { });
});

describe('validateTrade', () => {
  it('rejects R/R < 1:3', () => { });
  it('rejects position size > 10%', () => { });
  it('warns on high correlation', () => { });
});
```

### Performance Checklist
- [ ] Components memoized with `React.memo` if receiving same props
- [ ] useCallback for functions passed to child components
- [ ] useMemo for expensive calculations
- [ ] Virtualization for long lists (react-window)
- [ ] Code splitting for each module (lazy loading)
- [ ] WebSocket subscriptions (not polling) for live data
- [ ] Image optimization (lazy loading, responsive sizes)
- [ ] Bundle size monitoring (keep < 500KB gzipped)

---

## 🚀 NEXT STEPS FOR ELON

### Phase 1: Setup (Day 1, ~2 hours)
1. Create React + TS project with Vite
2. Install dependencies (React Router, Redux Toolkit, TailwindCSS, Chart.js)
3. Configure TailwindCSS with design tokens from DESIGN_SYSTEM.md
4. Setup folder structure matching COMPONENTS.md
5. Create base components (Button, Card, Modal, Table)
6. Setup Redux store with initial slices

### Phase 2: Core Components (Day 1-2, ~4 hours)
1. Build layout (AppShell, Navbar, Sidebar)
2. Build common components (ProgressBar, Badge, Toast)
3. Build module-specific components (KeyMetrics, RiskStatus, ActivePositions, etc.)
4. Setup routing between 5 pages

### Phase 3: State & API (Day 2, ~4 hours)
1. Setup Redux slices and actions
2. Create hooks (usePositions, usePrices, useRisk, etc.)
3. Implement OANDA API client with WebSocket subscriptions
4. Integrate macro events feed (worldmonitor.app)
5. Setup correlation calculations

### Phase 4: Flows & Logic (Day 2-3, ~4 hours)
1. Trade execution flow (validation → submission → confirmation)
2. Risk limit triggers (drawdown, daily loss, SL lock)
3. Emergency halt logic
4. Analytics (filters, charts, export)

### Phase 5: Polish & Testing (Day 3, ~2 hours)
1. Responsive design (mobile, tablet, desktop)
2. Accessibility audit (contrast, focus indicators, ARIA)
3. Unit & integration tests (aim for 80%+ coverage)
4. Performance optimization

### Phase 6: Deployment & Docs (Day 4, ~1 hour)
1. Docker build
2. Environment config (dev, staging, prod)
3. API documentation
4. Deployment pipeline (GitHub Actions)

---

## 📱 RESPONSIVE BREAKPOINTS

| Device | Viewport | Layout | Notes |
|--------|----------|--------|-------|
| Mobile | 375px | 1 column, stacked | Touch-friendly, large buttons |
| Tablet | 768px | 2 columns | Sidebar collapses to hamburger |
| Desktop | 1024px+ | 3+ columns, full layout | Full sidebar visible |
| Wide | 1440px | Max-width container | Padding added beyond 1440px |

**Key adjustments:**
- Below 640px: single column, hamburger menu, full-width cards
- 641-1024px: 2-column grid, sidebar collapsed
- Above 1024px: 3-column layout, full sidebar always visible

---

## 🔐 SECURITY & DATA HANDLING

### API Key Management
- Never log or expose API keys
- Store in environment variables (`.env.local`)
- Mask in UI: `•••••••••3d7f`
- Can only be changed, not viewed
- Validate on connection test

### Trade Data Privacy
- Prices, positions, P&L visible to frontend
- API keys, account numbers masked/encrypted
- No local storage of sensitive data
- Clear cache on logout

### Risk Limits (Hardcoded, Immutable)
- Max Position Size: 10% (cannot be changed)
- Max Drawdown: -15% (cannot be changed)
- Max Daily Loss: -5% (cannot be changed)
- Min Risk/Reward: 1:3 (cannot be changed)

---

## 📊 MONITORING & OBSERVABILITY

### Metrics to Track (Phase 2)
```typescript
// In each component or hook:
useEffect(() => {
  logMetric('component_loaded', { component: 'Dashboard', duration: 234 });
  logMetric('api_call', { endpoint: '/positions', duration: 145, status: 200 });
}, []);
```

### Error Handling Pattern
```typescript
try {
  await executeOrder(trade);
} catch (error) {
  logError('order_execution_failed', {
    asset: trade.asset,
    error: error.message,
    code: error.code,
  });
  showToast('error', 'Order failed: ' + error.message);
}
```

---

## 🎯 SUCCESS CRITERIA

Frontend is ready for production when:

✅ All 5 modules fully functional (Dashboard, Trading, Risk, Analytics, Settings)  
✅ OANDA API integration working (live prices, order execution)  
✅ Real-time updates (positions, P&L, alerts)  
✅ Risk limits enforced (drawdown, position size, daily loss)  
✅ Emergency halt button works instantly  
✅ Responsive on mobile, tablet, desktop  
✅ 80%+ unit test coverage  
✅ WCAG AA accessibility compliant  
✅ < 500KB bundle size (gzipped)  
✅ First Contentful Paint < 2s on 4G  

---

## 📞 QUESTIONS FOR ELON?

**Design questions?** → Check DESIGN_SYSTEM.md color scheme, typography, spacing  
**Component structure?** → Check COMPONENTS.md for specs  
**Wireframe questions?** → Check WIREFRAMES.md for detailed layouts  
**API questions?** → Review oandaClient, macroApi, correlationApi in COMPONENTS.md  
**Need clarification?** → Escalate to Deniz with specific questions

---

## 🎓 REFERENCE MATERIALS

- **Dark mode trading UI inspiration:** TradingView, Binance, Interactive Brokers
- **Color contrast checker:** WebAIM (ensures 4.5:1 ratio)
- **Responsive design testing:** Chrome DevTools, BrowserStack
- **Performance monitoring:** Lighthouse, Web Vitals
- **Chart library docs:** Recharts or Chart.js (your choice)
- **TailwindCSS config:** Fully documented in DESIGN_SYSTEM.md

---

**Status:** ✅ **READY FOR DEVELOPMENT**

Erkan's design is complete. The wireframes, component specs, design system, and interaction flows are all documented. Elon has everything needed to build a professional, responsive, risk-aware trading frontend.

**Estimated Frontend Development Time:** 40-50 hours (5-6 business days with 1 FTE)

---

*Design delivered: April 15, 2026 | Ready for handoff to Elon*
