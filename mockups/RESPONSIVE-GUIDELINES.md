# Responsive Design Guidelines - Trade-Claw Dashboard

**Status:** ✅ Complete (HOUR 5-6)  
**Last Updated:** 2026-04-23 18:45 CET

Responsive breakpoints and design annotations for all 5 pages.

---

## 📱 Breakpoint Strategy

The Trade-Claw Dashboard is designed mobile-first with 4 major breakpoints:

| Breakpoint | Width | Device | Layout | Use Case |
|-----------|-------|--------|--------|----------|
| **Mobile** | 320px - 767px | Phone, small tablet | Single column, stacked | On the go, quick checks |
| **Tablet** | 768px - 1023px | iPad, mid-size tablet | 2 columns, mixed layout | Analysis, mobile trading |
| **Laptop** | 1024px - 1919px | Desktop, laptop | 3-4 columns, sidebar | Primary workspace |
| **Desktop** | 1920px+ | Wide monitor, multi-display | Full grid layout | Analytics, monitoring |

---

## 🎨 Layout Transformations by Page

### Page 1: Dashboard

**Desktop (1920px)**
- 2-column layout: Sidebar (240px fixed) + Main content (fluid)
- Grid: 4 columns for account health metrics
- Positions section: 4 columns (4 cards per row)
- Recent trades table: Full width with horizontal scroll

**Laptop (1024px - 1919px)**
- Sidebar: Still visible (sticky, 240px)
- Metrics: 3 columns (3 cards per row)
- Positions: 2 columns (2 cards per row)
- Tables: Maintain horizontal scroll, reduce font size slightly

**Tablet (768px - 1023px)**
- Sidebar: Transforms to horizontal layout (3-column button grid)
- Position: Top of page, sticky/fixed
- Metrics: Stack to 1 column (full width)
- Positions: 1 column (1 card per row)
- Tables: Stack rows vertically on small screens (becomes 2 columns with labels)

**Mobile (320px - 767px)**
- No sidebar visible; Navigation via hamburger menu (TODO: add in frontend)
- All metrics: 1 column, full-width cards
- Positions: 1 column, card height ~180px
- Table: Compact (hide non-essential columns, show on detail view)
- Font size: Reduced (12-14px for body text)
- Padding: Reduced to 8px spacing

---

### Page 2: Trading

**Desktop (1920px)**
- Order entry form (left, 30% width) + Chart (right, 70% width)
- Order form: All fields visible in 2 columns
- Chart: Full candlestick with timeframe controls
- Tables: Full columns (Symbol, Type, Side, Prices, Size, Status, P&L, R/R, Actions)

**Laptop (1024px - 1919px)**
- Form: Still 2-column, but narrower
- Chart: Slightly reduced height
- Tables: Hide low-priority columns (Type, Side becomes abbreviated)

**Tablet (768px - 1023px)**
- Form and Chart: Stack vertically (form on top, chart below)
- Form fields: 1 column (not 2)
- Chart height: ~200px (reduced)
- Tables: Show only Symbol, Entry, Exit, P&L, Status
- Button group: Single column (full width)

**Mobile (320px - 767px)**
- Form: Single column, all fields full width
- Chart: ~150px height (minimal trading chart)
- Tables: Minimum columns only (Symbol, P&L, Status)
- Row styling: Each row shows 2-3 key fields, swipe to reveal more
- Order entry button: Full width, prominent (40px height)

---

### Page 3: Risk Management

**Desktop (1920px)**
- Metrics: 4 columns (Drawdown, Max DD, Win Rate, Avg R/R)
- Risk utilization + Grade distribution: 2 columns
- Heat map: 5 columns (full width, 5 symbols side-by-side)
- Chart: Full width below

**Laptop (1024px - 1919px)**
- Metrics: 2 columns (reflow to fit)
- Risk/Grade: Still 2 columns but narrower
- Heat map: 5 columns (still fits at 1024px)

**Tablet (768px - 1023px)**
- Metrics: 1 column (stack vertically)
- Risk/Grade: Stack vertically
- Heat map: 3 columns (5 items wrap to 2 rows)
- Chart: Full width but reduced height

**Mobile (320px - 767px)**
- All metrics: 1 column, full width
- Risk meter: Full width (bar easier to interact with)
- Grade bars: 5 items, reduced to fit (smaller bars)
- Heat map: 3 columns × 2 rows
- Chart: ~150px height

---

### Page 4: Analytics

**Desktop (1920px)**
- Equity curve: Full width, 400px height
- Stats grid below: 4 columns
- Performance + Risk metrics: 2-column layout side-by-side
- Trade analysis table: Full width with all columns
- Backtest summary: 2 columns (summary + performance)

**Laptop (1024px - 1919px)**
- Equity curve: Full width, 350px height
- Stats: 4 columns but tighter spacing
- Metrics cards: Still 2 columns
- Table: All columns visible

**Tablet (768px - 1023px)**
- Equity curve: Full width, 300px height
- Stats: 2 columns (4 items in 2×2 grid)
- Metrics: Stack to 1 column
- Table: Hide non-critical columns (R/R, Grade)

**Mobile (320px - 767px)**
- Equity curve: Full width, 200px height
- Stats: 1 column, full width cards
- Metrics: Tabbed or collapsible (Performance | Risk tabs)
- Table: Only Show Trade #, Symbol, Entry, Exit, P&L
- Backtest summary: Single column with stacked fields

---

### Page 5: Settings

**Desktop (1920px)**
- Cards: Max width 600px (left-aligned), full layout
- Form rows: 2 columns (2 fields side-by-side)
- Toggles: Full width within card
- Sliders: Full width with value indicator
- Buttons: Right-aligned button group at bottom

**Laptop (1024px - 1919px)**
- Same as desktop, but cards slightly narrower (responsive max-width)
- Form rows: Still 2 columns

**Tablet (768px - 1023px)**
- Form rows: 1 column (stack fields vertically)
- Cards: Full width with 16px margins
- Buttons: Stack vertically on small screens (but show 2-wide at 768px+)

**Mobile (320px - 767px)**
- Cards: Full width with 8px padding
- Form fields: All 1 column
- Form inputs: Full width (100%)
- Buttons: Full width, stacked vertically
- Toggles: Easier to tap (larger hit area)
- Sliders: Full width, easier to drag

---

## 🎯 Component Responsive Behaviors

### Sidebar Navigation
| Breakpoint | State | Behavior |
|-----------|-------|----------|
| 1024px+ | Vertical sidebar (240px, sticky) | Fixed left, always visible |
| 768px - 1023px | Horizontal button row | Top of page, 3 buttons per row, scrollable |
| 320px - 767px | Hidden / Hamburger menu | Collapsible, accessed via menu icon |

### Cards
| Breakpoint | Width | Spacing | Font |
|-----------|-------|---------|------|
| 1920px | Auto (grid: 4, 3, 2 cols) | 24px gap | 16px body, 32px headings |
| 1024px | Auto (grid: 3, 2, 1 cols) | 24px gap | 16px body, 28px headings |
| 768px | Full width | 16px gap | 14px body, 20px headings |
| 320px | Full width | 8px gap | 12px body, 18px headings |

### Tables
| Breakpoint | Scroll | Columns | Font | Rows |
|-----------|--------|---------|------|------|
| 1024px+ | Horizontal scroll | All visible | 14px | Normal height (48px) |
| 768px | Horizontal scroll | 6-7 most important | 13px | Normal (48px) |
| 320px | Vertical cards or horizontal scroll | 3-4 key fields | 12px | Compact (40px) |

**Mobile Table Strategy:**
Option A (Recommended): Show 3-4 key columns, hide others
Option B: Stack rows as cards (label: value pairs)
Option C: Horizontal scroll with thumb indicators

### Buttons
| Breakpoint | Size | Padding | Min Height |
|-----------|------|---------|-----------|
| 1024px+ | Medium | 8px 16px | 40px |
| 768px | Medium | 8px 16px | 40px |
| 320px | Large (full-width) | 12px 16px | 44px (touch target) |

**Mobile Consideration:** Touch targets must be ≥ 44px × 44px per WCAG AA standards.

### Form Inputs
| Breakpoint | Field Layout | Width | Padding |
|-----------|--------------|-------|---------|
| 1024px+ | 2 columns | 50% - gap/2 | 8px 12px |
| 768px | 1-2 columns | Flexible | 8px 12px |
| 320px | 1 column | 100% | 12px 12px |

### Sliders
| Breakpoint | Width | Height | Thumb Size |
|-----------|-------|--------|-----------|
| All | 100% | 6px track | 20px circle |
| 320px (small) | 100% | 6px track | 24px circle (easier to drag) |

---

## 🔧 CSS Media Queries

```css
/* Desktop-first approach */

/* Laptop and Desktop (1024px+) - Default styles */
.layout {
    display: grid;
    grid-template-columns: 240px 1fr;  /* Sidebar + Main */
    gap: 16px;
}

.grid-4col {
    grid-template-columns: repeat(4, 1fr);
}

.grid-3col {
    grid-template-columns: repeat(3, 1fr);
}

.grid-2col {
    grid-template-columns: repeat(2, 1fr);
}

/* Tablet (768px - 1023px) */
@media (max-width: 1023px) {
    .layout {
        grid-template-columns: 1fr;  /* No sidebar */
    }

    .sidebar {
        display: grid;
        grid-template-columns: repeat(3, 1fr);  /* Horizontal nav */
    }

    .grid-4col,
    .grid-3col {
        grid-template-columns: repeat(2, 1fr);  /* 2 columns */
    }

    .grid-2col {
        grid-template-columns: 1fr;  /* 1 column */
    }

    .form-row {
        grid-template-columns: 1fr;  /* Stack form fields */
    }
}

/* Mobile (320px - 767px) */
@media (max-width: 767px) {
    .layout {
        padding: 8px;  /* Reduced padding */
    }

    .sidebar {
        grid-template-columns: 1fr;  /* Vertical menu */
        position: relative;  /* Not sticky */
    }

    .grid-4col,
    .grid-3col,
    .grid-2col {
        grid-template-columns: 1fr;  /* All 1 column */
    }

    body {
        font-size: 14px;  /* Smaller base font */
    }

    .card {
        padding: 12px;  /* Reduced padding */
    }

    .btn-lg {
        width: 100%;  /* Full width buttons */
        padding: 12px 16px;
        min-height: 44px;
    }

    .table {
        font-size: 12px;
    }

    .table th,
    .table td {
        padding: 8px;  /* Compact cells */
    }
}
```

---

## 📐 Typography Scaling

Maintain visual hierarchy across breakpoints:

| Element | Desktop | Laptop | Tablet | Mobile |
|---------|---------|--------|--------|--------|
| Page title (h1) | 28px | 26px | 20px | 20px |
| Section title (h2) | 20px | 18px | 16px | 16px |
| Card header | 12px | 12px | 12px | 11px |
| Body text | 16px | 16px | 14px | 14px |
| Small text | 12px | 12px | 12px | 11px |
| Monospace (data) | 16px | 14px | 14px | 12px |

**Line Height:** Maintain 1.5 for readability on all screens

---

## 🎯 Touch-Friendly Design (Mobile)

- **Minimum touch target:** 44×44px (WCAG AA compliant)
- **Spacing between targets:** 8px minimum
- **Tap-friendly controls:** Buttons, sliders, toggles sized for thumb interaction
- **Horizontal scroll:** Provide visual hints (thumb indicator, gradient fade)
- **Input fields:** Large padding, 40px minimum height for text inputs

---

## 🖼️ Image & Chart Scaling

### Charts (Equity Curve, Candlestick, etc.)
| Breakpoint | Height | Width | Interaction |
|-----------|--------|-------|-------------|
| 1920px | 400px | 100% | Full zoom, pan, crosshair |
| 1024px | 350px | 100% | Zoom, pan, crosshair |
| 768px | 300px | 100% | Pan, basic crosshair |
| 320px | 200px | 100% | Limited interaction (pinch-zoom optional) |

### Heat Maps & Grade Distributions
| Breakpoint | Grid | Item Size |
|-----------|------|-----------|
| 1920px | 5 columns | 100px × 100px |
| 1024px | 5 columns | 80px × 80px |
| 768px | 3 columns | 60px × 60px |
| 320px | 3 columns | 50px × 50px |

---

## 🧪 Testing Checklist

- [ ] Test all pages at 320px (mobile)
- [ ] Test all pages at 768px (tablet)
- [ ] Test all pages at 1024px (laptop edge case)
- [ ] Test all pages at 1920px (desktop)
- [ ] Verify touch targets ≥ 44px on mobile
- [ ] Test horizontal scrolling (tables, charts)
- [ ] Verify text readability at all sizes
- [ ] Test form input focus states on mobile
- [ ] Verify button states (hover, active, disabled)
- [ ] Check image/icon scaling
- [ ] Test on landscape vs. portrait orientation

---

## 📋 Summary Table: Layout Changes by Breakpoint

| Feature | 1920px | 1024px | 768px | 320px |
|---------|--------|--------|-------|-------|
| Sidebar | Fixed vertical | Fixed vertical | Horizontal | Hidden |
| Metrics (4-col) | 4 columns | 3 columns | 2 columns | 1 column |
| Positions (4-col) | 4 columns | 2 columns | 1 column | 1 column |
| Tables | Full width + scroll | Full width + scroll | Reduced columns + scroll | Key columns only |
| Forms (2-col) | 2 columns | 2 columns | 1 column | 1 column |
| Buttons | Inline group | Inline group | Inline / Stack | Full-width stack |
| Padding | 16px | 16px | 16px | 8px |
| Font Size (body) | 16px | 16px | 14px | 14px |

---

## 🎨 Color & Contrast

All colors maintain WCAG AA contrast ratios across all screen sizes:
- Text on dark background: min 4.5:1 ratio
- Interactive elements: min 3:1 ratio
- Status indicators (green/red): checked for colorblind accessibility

---

## 🚀 Implementation Notes for Frontend Team (Elon)

1. **Use CSS Grid + Flexbox** for responsive layouts (no floats)
2. **Mobile-first media queries** (default to mobile, scale up)
3. **Viewport meta tag:** `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
4. **Test with DevTools** device emulation at each breakpoint
5. **Use relative units** (rem, %, em) for scalability
6. **Optimize images** for different pixel densities (1x, 2x, 3x)
7. **Consider landscape orientation** for tablets and large phones
8. **Implement horizontal scroll hints** for tables on small screens
9. **Use touch-friendly libraries** for sliders, date pickers, etc.
10. **Test on real devices** (not just DevTools emulation)

---

**Created by:** Erkan (UX/UI Designer)  
**Design System Version:** 1.0  
**Last Updated:** 2026-04-23 18:45 CET
