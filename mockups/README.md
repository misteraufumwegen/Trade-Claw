# Trade-Claw Dashboard - Hi-Fi Mockups & Handoff

**Status:** ✅ Complete (HOUR 5-6)  
**Created by:** Erkan (UX/UI Designer)  
**Date:** 2026-04-23 18:45 CET

---

## 📋 Contents

### Pages (5 Complete Mockups)
- **`pages/1-dashboard.html`** — Account overview, positions, recent trades
- **`pages/2-trading.html`** — Order entry form, active orders, trade history
- **`pages/3-risk-management.html`** — Risk metrics, drawdown, grades, heatmap
- **`pages/4-analytics.html`** — Equity curve, performance stats, trade analysis
- **`pages/5-settings.html`** — OANDA config, risk limits, strategy settings

### Documentation
- **`RESPONSIVE-GUIDELINES.md`** — Breakpoints (320px/768px/1024px/1920px) with annotations
- **`HANDOFF-SPEC.md`** — Complete integration guide for Elon (CTO)
- **`README.md`** — This file

---

## 🎯 How to Use These Mockups

### 1. Open in Browser
```bash
cd mockups/pages
open 1-dashboard.html    # Open in default browser
# or
python -m http.server 8000
# Then visit http://localhost:8000/pages/1-dashboard.html
```

### 2. Check Responsive Design
- Open mockup in browser
- Press `F12` (DevTools)
- Click "Toggle device toolbar" (Ctrl+Shift+M)
- Test at breakpoints:
  - **320px** (Mobile)
  - **768px** (Tablet)
  - **1024px** (Laptop)
  - **1920px** (Desktop)

### 3. Use as Frontend Reference
- All HTML is fully styled with inline CSS
- Components use CSS classes from `figma-components/`
- Copy CSS to your frontend stylesheet
- Build React components wrapping these classes

---

## 🔍 What's Included in Each Page

### Page 1: Dashboard
```
✅ Sidebar navigation (sticky)
✅ Header with controls
✅ 4 Account health metric cards
✅ 4 Active position cards (LONG/SHORT badges)
✅ Recent trades table (Time, Symbol, Type, Entry, Exit, Size, P&L)
✅ Responsive annotations (320px → 1920px)
```

### Page 2: Trading
```
✅ Order entry form (Symbol, Type, Entry, Side, Size, SL, TP, Risk)
✅ Candlestick chart placeholder (for TradingView)
✅ Active orders table (with Cancel action)
✅ Trade history table (with R/R, Grade columns)
✅ Form validation & error states
✅ Responsive: Form stacks under chart on mobile
```

### Page 3: Risk Management
```
✅ 4 Risk metric cards (Drawdown, Max DD, Win Rate, Avg R/R)
✅ Risk utilization meter (visual percentage bar)
✅ Trade grade distribution (A+, A, B, C, D bars)
✅ Account heat map (symbol risk exposure)
✅ Drawdown chart placeholder
✅ Responsive: Metrics stack to 1-column on mobile
```

### Page 4: Analytics
```
✅ Equity curve chart placeholder (line chart)
✅ Stats grid (Starting Equity, Current, Total Return, Ann. Return)
✅ Performance metrics card (Total Trades, Win Rate, Profit Factor, etc.)
✅ Risk metrics card (Sharpe, Max DD, Consecutive Wins/Losses, etc.)
✅ Trade analysis table (with Grade column)
✅ Backtest summary section
✅ Responsive: Stats grid becomes 2-column on tablet
```

### Page 5: Settings
```
✅ OANDA API Configuration section
  - Account Type (Demo/Live)
  - Account ID + API Key
  - Paper Trading toggle
  - Test Connection button
✅ Risk Management Settings
  - Daily Risk Limit slider (5%)
  - Max Drawdown slider (15%)
  - Max Risk per Trade slider (2%)
  - Min Win Rate + Consecutive Loss inputs
✅ Strategy Configuration
  - Active Strategy select
  - Timeframe + Max Open Positions
  - Auto-Trading toggle
  - Stop Loss toggle
✅ Data Source Configuration
  - Primary provider, Historical data, Quote frequency, Backtest period
  - Cache data toggle
✅ Advanced Settings (Logging, Email, Export, Reset)
✅ Full form with validation, toggles, sliders, selects
```

---

## 🎨 Design System Reference

All mockups use the design system defined in `figma-export/`:

### Colors (CSS Variables)
```css
--color-dark: #0D1117              /* Background */
--color-secondary: #161B22         /* Cards */
--color-primary: #00D9FF           /* Teal - CTAs */
--color-accent: #FFB700            /* Gold - Warnings */
--color-success: #10B981           /* Green - Wins */
--color-danger: #EF4444            /* Red - Losses */
--color-text-primary: #F0F6FC      /* Text */
--color-text-secondary: #8B949E    /* Muted text */
--color-border: #30363D            /* Dividers */
```

### Typography
```
Font: Inter (sans), JetBrains Mono (numbers)
Weights: 400 (regular), 700 (bold)
Sizes: 12px (XS), 14px (S), 16px (Base), 20px (XL), 24px (2XL), 28px (Title)
```

### Spacing (8px Grid)
```
4px, 8px, 16px, 24px, 32px, 48px
```

---

## 📱 Responsive Breakpoints Explained

See `RESPONSIVE-GUIDELINES.md` for detailed breakpoint strategy.

### Quick Summary
| Device | Width | Sidebar | Metrics | Layout |
|--------|-------|---------|---------|--------|
| Mobile | 320px | Hidden | 1-column | Stacked |
| Tablet | 768px | Horizontal nav | 2-column | Stacked |
| Laptop | 1024px | Vertical | 3-column | Side-by-side |
| Desktop | 1920px | Vertical | 4-column | Optimal |

---

## 🔌 Integration with Frontend

### Step 1: Copy Component CSS
```bash
cp figma-components/buttons/button.css frontend/src/styles/components/
cp figma-components/cards/card.css frontend/src/styles/components/
cp figma-components/tables/table.css frontend/src/styles/components/
# ... copy all component CSS
```

### Step 2: Copy Design Tokens
```bash
cp figma-export/design-tokens/css-variables.css frontend/src/styles/tokens/
```

### Step 3: Import in React App
```css
/* frontend/src/styles/globals.css */
@import 'tokens/css-variables.css';
@import 'components/buttons.css';
@import 'components/cards.css';
@import 'components/tables.css';
/* ... etc */
```

### Step 4: Build React Components
```tsx
// frontend/src/components/Button.tsx
export const Button = ({ variant = 'primary', size = 'md', ...props }) => (
  <button 
    className={`btn btn-${variant} btn-${size}`} 
    {...props}
  />
);
```

### Step 5: Use in Pages
```tsx
// frontend/src/pages/Dashboard.tsx
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Table } from '../components/Table';

export const Dashboard = () => {
  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <Header />
        <div className="grid-2col">
          <Card title="Account Balance">$50,000</Card>
          <Card title="Equity">$52,500</Card>
        </div>
        {/* ... rest of page */}
      </main>
    </div>
  );
};
```

---

## 📊 Data Models for Integration

See `HANDOFF-SPEC.md` for complete TypeScript interfaces for:
- Account
- Position
- Order
- Trade
- RiskMetrics
- PerformanceStats
- And more...

---

## 🧪 Verification Checklist

### Desktop (1920px)
- [ ] Sidebar visible on left (240px, sticky)
- [ ] 4-column metric grids show as 4 columns
- [ ] All content fits on one screen (no unnecessary scroll)
- [ ] Charts render at full size

### Laptop (1024px)
- [ ] Sidebar still visible (240px)
- [ ] 4-column grids reflow to 3-2-1 as needed
- [ ] Content still readable
- [ ] No horizontal overflow

### Tablet (768px)
- [ ] Sidebar becomes horizontal (3-column button row)
- [ ] All grids are 1 or 2 columns
- [ ] Tables stack or reduce columns
- [ ] Responsive fonts applied (14px body)

### Mobile (320px)
- [ ] No sidebar (hidden / hamburger)
- [ ] All grids are 1 column
- [ ] Touch targets ≥ 44px
- [ ] Padding reduced to 8px
- [ ] Fonts: 12-14px
- [ ] Tables show minimal columns + horizontal scroll

---

## 🚀 Next Steps for Elon (CTO)

1. **Review mockups** in browser
2. **Read HANDOFF-SPEC.md** for full integration guide
3. **Setup React project** with Redux store (see state shape in spec)
4. **Build page components** using these mockups as reference
5. **Connect to backend APIs** (ensure endpoints exist)
6. **Integrate charts** (TradingView Lightweight Charts recommended)
7. **Test responsive** at 4 breakpoints

---

## 📞 Questions?

- **Design questions?** → Contact Erkan
- **Integration questions?** → See HANDOFF-SPEC.md
- **Responsive layout issues?** → Check RESPONSIVE-GUIDELINES.md
- **Component CSS?** → Check figma-components/

---

**Files Summary:**
```
mockups/
├── pages/
│   ├── 1-dashboard.html              (5 pages)
│   ├── 2-trading.html
│   ├── 3-risk-management.html
│   ├── 4-analytics.html
│   └── 5-settings.html
├── RESPONSIVE-GUIDELINES.md          (Breakpoints + annotations)
├── HANDOFF-SPEC.md                   (Complete integration guide)
├── README.md                         (This file)
└── annotations/                      (Reserved for detailed callouts)
```

---

**Created by:** Erkan (UX/UI Designer)  
**Ready for:** Elon (CTO) - Frontend Development Phase  
**Date:** 2026-04-23  
**Status:** ✅ COMPLETE & READY FOR INTEGRATION

Open `pages/1-dashboard.html` in your browser to see the designs!
