# Trade-Claw Component Library

**Status:** ✓ Complete (HOUR 3-4)  
**Last Updated:** 2026-04-23 18:30 CET

Component design library for Trade-Claw Dashboard, built with design tokens from HOUR 1-2.

## 📦 Component Catalog

All components follow the Trade-Claw design system and use CSS variables from `figma-export/design-tokens/css-variables.css`.

### 1. **Buttons** (`buttons/`)
CSS and HTML examples for all button states.

**Files:**
- `button.css` — Button styles (Primary, Secondary, Danger)
- `button.html` — Interactive button showcase

**Variants:**
- Primary (default, hover, active, disabled)
- Secondary (outline style)
- Danger (red, for destructive actions)
- Size: Small, Medium, Large
- Icon buttons (square, 40px)

**Usage in Frontend:**
```html
<!-- Primary button -->
<button class="btn btn-primary">Place Order</button>

<!-- Secondary button -->
<button class="btn btn-secondary">Cancel</button>

<!-- Danger button -->
<button class="btn btn-danger" disabled>Delete</button>

<!-- Large full-width -->
<button class="btn btn-primary btn-lg btn-full">Execute Trade</button>
```

---

### 2. **Cards** (`cards/`)
Elevated surfaces for content grouping and data display.

**Files:**
- `card.css` — Card styles (Standard, Data-Card, Hoverable)
- `card.html` — Card component examples

**Variants:**
- Standard Card (with header, content, footer)
- Data Card (grid layout for key metrics)
- Hoverable Cards (clickable, interactive)
- Colored variants (Success, Danger, Accent)

**Usage in Frontend:**
```html
<!-- Standard card -->
<div class="card card-standard">
  <div class="card-header">EUR/USD Position</div>
  <div class="card-content">Active position, risk-reward 1:2.5</div>
  <div class="card-footer">
    <button class="btn btn-primary btn-sm">Details</button>
  </div>
</div>

<!-- Data card (4-column grid) -->
<div class="card card-data">
  <div class="card-data-item">
    <div class="card-data-label">Balance</div>
    <div class="card-data-value">$50,000</div>
  </div>
  <!-- More items... -->
</div>
```

---

### 3. **Inputs** (`inputs/`)
Text fields, number inputs, and form controls.

**Files:**
- `input.css` — Input styles (Text, Number, States)
- `input.html` — Input component examples

**States:**
- Default
- Focus (with teal border + glow)
- Disabled
- Error (red border)
- Success (green border)
- Helper text / Error messages

**Usage in Frontend:**
```html
<!-- Text input with label -->
<div class="input input-full">
  <label class="input-label">Entry Price</label>
  <input type="text" class="input-field" placeholder="e.g., 1.0850">
  <div class="input-helper">Set your entry price for the trade</div>
</div>

<!-- Number input (monospace) -->
<div class="input input-full">
  <label class="input-label">Position Size (Units)</label>
  <input type="number" class="input-field" placeholder="1000" step="1" min="1">
</div>

<!-- Error state -->
<div class="input input-error input-full">
  <label class="input-label">Email</label>
  <input type="email" class="input-field" value="invalid@">
  <div class="input-error-message">Invalid email address</div>
</div>
```

---

### 4. **Sliders** (`sliders/`)
Range controls with visual feedback.

**Files:**
- `slider.css` — Slider styles (Track, Fill, Thumb)
- `slider.html` — Slider component examples

**Features:**
- HTML5 input[type="range"]
- Custom thumb styling (20px circle)
- Colored variants (Success, Danger, Accent)
- Tick marks / Labels
- Range inputs (min/max)
- Disabled state

**Usage in Frontend:**
```html
<!-- Basic slider -->
<div class="slider-container">
  <div class="slider-label">
    <span>Risk Percentage</span>
    <span class="slider-value">50%</span>
  </div>
  <input type="range" min="0" max="100" value="50">
</div>

<!-- Range slider (min/max) -->
<div class="slider-container">
  <input type="range" min="0" max="1000" value="250">
</div>

<!-- Colored slider -->
<div class="slider-container slider-success">
  <input type="range" min="0" max="100" value="65">
</div>
```

---

### 5. **Tables** (`tables/`)
Data grids with hover effects and responsive design.

**Files:**
- `table.css` — Table styles (Headers, Rows, Responsive)
- `table.html` — Table component examples

**Features:**
- Sticky header (sticky on scroll)
- Row hover effects
- Striped rows (alternating background)
- Compact layout
- Row states (active, success, danger)
- Cell badges (with colors)
- Responsive stacking on mobile

**Usage in Frontend:**
```html
<div class="table-container">
  <table class="table table-striped">
    <thead>
      <tr>
        <th>Symbol</th>
        <th class="text-right">P&L</th>
        <th class="text-center">Status</th>
      </tr>
    </thead>
    <tbody>
      <tr class="success">
        <td class="mono">EUR/USD</td>
        <td class="text-right positive">+$700</td>
        <td class="text-center"><span class="cell-badge badge-success">Closed</span></td>
      </tr>
    </tbody>
  </table>
</div>
```

---

### 6. **Alerts & Badges** (`alerts/`)
Notifications, badges, and toast messages.

**Files:**
- `alert.css` — Alert, Badge, Toast styles
- `alert.html` — Alert component examples

**Alert Types:**
- Success (green)
- Danger (red)
- Warning (orange/gold)
- Info (teal)

**Badges:**
- Inline badges (small, colored)
- Badge with icons
- Multiple variants

**Toasts:**
- Fixed bottom-right position
- Auto-close with progress bar (5s)
- Success, Danger, Warning, Info variants
- Close button

**Usage in Frontend:**
```html
<!-- Alert -->
<div class="alert alert-success">
  <div class="alert-icon">✓</div>
  <div class="alert-content">
    <div class="alert-title">Order Executed</div>
    <div class="alert-description">EUR/USD buy order placed at 1.0920</div>
  </div>
  <button class="alert-close">✕</button>
</div>

<!-- Badge -->
<span class="badge badge-success badge-with-icon">
  <span>✓</span>
  <span>Active</span>
</span>

<!-- Toast (positioned fixed) -->
<div class="toast-container">
  <div class="toast toast-success">
    <div class="toast-icon">✓</div>
    <div class="toast-content">
      <div class="toast-title">Trade Closed</div>
      <div class="toast-message">Position closed with +$450 profit</div>
    </div>
    <div class="toast-progress"></div>
  </div>
</div>
```

---

### 7. **Charts** (`charts/`)
Chart stubs and styling guidelines for data visualization.

**Files:**
- `chart.css` — Chart container and styling
- `chart.html` — Chart examples (SVG stubs)

**Chart Types:**
- Candlestick (OHLC)
- Line Chart (price/performance)
- Equity Curve (backtest results)

**Features:**
- Responsive containers
- Grid and axes styling
- Tooltips and crosshairs
- Legend
- Stats overlay
- Timeframe controls

**Implementation Notes:**
- Use **TradingView Lightweight Charts** for candlestick (BEST for trading apps)
- Use **Chart.js** or **Recharts** for line/equity curves
- Support WebSocket for real-time updates
- Implement zoom, pan, crosshair interactions

**Usage in Frontend:**
```html
<!-- Chart container -->
<div class="chart-container">
  <div class="chart-header">
    <div class="chart-title">EUR/USD - Daily</div>
    <div class="chart-timeframe">
      <button>1H</button>
      <button class="active">1D</button>
      <button>1W</button>
    </div>
  </div>
  <div class="chart-canvas" id="candleChart"></div>
</div>

<!-- Initialize with charting library -->
<script>
  // Example using TradingView Lightweight Charts
  const chart = createChart(document.getElementById('candleChart'));
  const candlestickSeries = chart.addCandlestickSeries({color: '#10B981'});
  // Feed OHLC data...
</script>
```

---

## 🎨 Design Tokens Used

All components reference CSS variables from the design system:

```css
/* Colors */
--color-dark: #0D1117
--color-secondary: #161B22
--color-primary: #00D9FF (Teal - CTAs, highlights)
--color-accent: #FFB700 (Gold - Warnings)
--color-success: #10B981 (Green - Wins)
--color-danger: #EF4444 (Red - Losses)
--color-text-primary: #F0F6FC
--color-text-secondary: #8B949E
--color-border: #30363D

/* Typography */
--font-sans: Inter
--font-mono: JetBrains Mono (numbers, data)
--font-size-xs: 12px
--font-size-sm: 14px
--font-size-base: 16px
--font-size-lg: 18px
--font-size-xl: 20px

/* Spacing (8px grid) */
--spacing-xs: 4px
--spacing-s: 8px
--spacing-m: 16px
--spacing-l: 24px
--spacing-xl: 32px
--spacing-2xl: 48px

/* Border Radius */
--radius-sm: 4px
--radius-md: 8px
--radius-lg: 12px

/* Shadows */
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05)
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1)
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1)
```

---

## 📱 Responsive Design

All components support mobile breakpoints:
- **Mobile:** 320px-767px
- **Tablet:** 768px-1023px
- **Desktop:** 1024px+

Examples:
- Tables stack vertically on mobile (single column)
- Charts reduce height on small screens
- Buttons remain 40px min-height for touch targets
- Sliders remain touch-friendly

---

## ✅ Frontend Integration Checklist

When building the frontend (HOUR 6-10):

- [ ] Import `figma-export/design-tokens/css-variables.css` in main layout
- [ ] Copy component CSS files to frontend `src/styles/components/`
- [ ] Build React components wrapping these CSS classes
- [ ] Add interactive state management (buttons, modals, dropdowns)
- [ ] Integrate chart libraries (TradingView, Chart.js)
- [ ] Test responsive behavior on multiple breakpoints
- [ ] Implement animations (slides, fades, tooltips)
- [ ] Add accessibility (ARIA labels, keyboard navigation)

---

## 🚀 Next Steps

**HOUR 5-6: Hi-Fi Mockups**
- Use these components in full page layouts
- Create Dashboard, Trading, Risk, Analytics, Settings pages
- Add responsive annotations
- Generate Handoff Spec for Elon (CTO)

---

## 📄 Files Summary

```
figma-components/
├── buttons/
│   ├── button.css      (Primary, Secondary, Danger states)
│   └── button.html     (Interactive showcase)
├── cards/
│   ├── card.css        (Standard, Data, Hoverable)
│   └── card.html       (Card examples)
├── inputs/
│   ├── input.css       (Text, Number, Error/Success states)
│   └── input.html      (Input examples)
├── sliders/
│   ├── slider.css      (Range, Colored variants)
│   └── slider.html     (Slider examples)
├── tables/
│   ├── table.css       (Headers, Rows, Responsive)
│   └── table.html      (Table examples)
├── alerts/
│   ├── alert.css       (Alerts, Badges, Toasts)
│   └── alert.html      (Alert examples)
├── charts/
│   ├── chart.css       (Chart containers, styling)
│   └── chart.html      (Chart stubs and layout)
└── README.md           (This file)
```

---

## 🔗 Related Files

- Design Tokens: `figma-export/design-tokens/tokens.json`
- CSS Variables: `figma-export/design-tokens/css-variables.css`
- Progress Tracker: `PROGRESS.md`

---

**Created by:** Erkan (UX/UI Designer)  
**Component Library v1.0** — Ready for frontend integration
