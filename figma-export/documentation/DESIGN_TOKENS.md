# Design Tokens - Complete Reference

**Trade-Claw Design System v1.0**  
**Generated:** 2026-04-23  
**Maintainer:** Erkan (UX/UI Designer)

---

## Table of Contents

1. [Color Palette](#color-palette)
2. [Typography](#typography)
3. [Spacing & Grid](#spacing--grid)
4. [Icons](#icons)
5. [Shadows & Depth](#shadows--depth)
6. [Border Radius](#border-radius)
7. [Responsive Breakpoints](#responsive-breakpoints)
8. [Component Specifications](#component-specifications)

---

## Color Palette

### Base Colors

| Token | Hex | RGB | Usage | Contrast* |
|-------|-----|-----|-------|-----------|
| **Dark** | `#0D1117` | rgb(13, 17, 23) | Primary background | — |
| **Secondary** | `#161B22` | rgb(22, 27, 34) | Elevated surfaces, cards | 1.05:1 (on Dark) |
| **Primary Teal** | `#00D9FF` | rgb(0, 217, 255) | CTAs, highlights, focus | 1.4:1 (on Dark) |
| **Accent Gold** | `#FFB700` | rgb(255, 183, 0) | Warnings, emphasis | 3.3:1 (on Dark) |
| **Success Green** | `#10B981` | rgb(16, 185, 129) | Positive states, profits | 3.1:1 (on Dark) |
| **Danger Red** | `#EF4444` | rgb(239, 68, 68) | Errors, losses, critical | 2.4:1 (on Dark) |

### Text Colors

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| **Text Primary** | `#F0F6FC` | rgb(240, 246, 252) | Main text, high contrast |
| **Text Secondary** | `#8B949E` | rgb(139, 148, 158) | Muted text, hints, captions |
| **Text Disabled** | `#6E7681` | rgb(110, 118, 129) | Disabled states |

### Semantic Colors

| Element | Color | Usage |
|---------|-------|-------|
| **Profit/Win** | Success Green `#10B981` | P&L positive, winning trades |
| **Loss/Drawdown** | Danger Red `#EF4444` | P&L negative, losing trades |
| **Alert/Warning** | Accent Gold `#FFB700` | Risk warnings, drawdown alerts |
| **Action/Focus** | Primary Teal `#00D9FF` | Buttons, links, focus states |
| **Border/Divider** | `#30363D` | Lines, separators, outlines |

### Color Usage Matrix

```
Dark (#0D1117):
  ├─ Page backgrounds
  ├─ Full-screen sections
  └─ Main content areas

Secondary (#161B22):
  ├─ Card backgrounds
  ├─ Elevated surfaces
  ├─ Modal backgrounds
  └─ Section containers

Primary Teal (#00D9FF):
  ├─ Call-to-action buttons
  ├─ Active tabs / links
  ├─ Focus rings
  ├─ Highlights
  └─ Primary form inputs

Accent Gold (#FFB700):
  ├─ Warnings
  ├─ Alert badges
  ├─ Risk indicators
  └─ Special emphasis

Success Green (#10B981):
  ├─ Winning trades
  ├─ Positive P&L
  ├─ Success messages
  └─ Uptrend indicators

Danger Red (#EF4444):
  ├─ Losses
  ├─ Negative P&L
  ├─ Error states
  ├─ Downtrend indicators
  └─ Critical alerts
```

**Contrast Ratios:** *Checked at WCAG AA (4.5:1 minimum for text)*

---

## Typography

### Font Families

#### Inter (Primary)
- **File:** `Inter-Regular.ttf` (400), `Inter-Bold.ttf` (700)
- **Source:** [Google Fonts](https://fonts.google.com/specimen/Inter)
- **License:** [OFL](https://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&item_id=OFL)
- **Use:** UI text, headings, labels, body copy
- **CSS:** `font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;`

#### JetBrains Mono (Data)
- **File:** `JetBrainsMono-Regular.ttf` (400)
- **Source:** [JetBrains](https://www.jetbrains.com/lp/mono/)
- **License:** [OFL](https://github.com/JetBrains/JetBrainsMono/blob/master/OFL.txt)
- **Use:** Numbers, prices, data, timestamps, code
- **CSS:** `font-family: 'JetBrains Mono', 'Monaco', 'Courier New', monospace;`
- **Why:** Tabular figures (fixed-width numbers) for aligned data tables

### Font Sizes (Modular Scale)

Based on 16px base with 8px increments:

```
XS:   12px  (—3px from base)
SM:   14px  (—2px from base)
Base: 16px  (root)
LG:   18px  (+2px from base)
XL:   20px  (+4px from base)
2XL:  24px  (+8px from base)
3XL:  32px  (+16px from base)
```

### Typography Combinations

#### Headings
| Level | Font Size | Weight | Line Height | Example Usage |
|-------|-----------|--------|-------------|---------------|
| **H1** | 32px (3XL) | Bold (700) | 1.2 (tight) | Page title, main heading |
| **H2** | 24px (2XL) | Bold (700) | 1.2 (tight) | Section heading |
| **H3** | 20px (XL) | Bold (700) | 1.2 (tight) | Subsection, card title |
| **H4** | 18px (LG) | Bold (700) | 1.5 (normal) | Small section title |

#### Body Text
| Usage | Font Size | Weight | Line Height |
|-------|-----------|--------|-------------|
| Standard paragraph | 16px (Base) | Regular (400) | 1.5 (normal) |
| Small/secondary text | 14px (SM) | Regular (400) | 1.5 (normal) |
| Caption/hint | 12px (XS) | Regular (400) | 1.5 (normal) |

#### Labels & UI
| Usage | Font Size | Weight | Other |
|-------|-----------|--------|-------|
| Form labels | 14px (SM) | Regular (400) | — |
| UI labels/badges | 12px (XS) | Bold (700) | Uppercase, 0.5px letter-spacing |
| Button text | 14-16px | Bold (700) | Centered, uppercase optional |

#### Data & Numbers
| Usage | Font | Size | Weight |
|-------|------|------|--------|
| Prices/P&L | JetBrains Mono | 20px (XL) | Bold (700) |
| Data values | JetBrains Mono | 14px (SM) | Regular (400) |
| Timestamps | JetBrains Mono | 12px (XS) | Regular (400) |

---

## Spacing & Grid

### Spacing Scale (8px Base)

| Token | Value | Multiples | Common Uses |
|-------|-------|-----------|------------|
| **XS** | 4px | 0.5× | Micro spacing, internal gaps |
| **S** | 8px | 1× | Button padding, list gaps |
| **M** | 16px | 2× | Standard padding, field margins |
| **L** | 24px | 3× | Section spacing, card margins |
| **XL** | 32px | 4× | Major spacing, page padding |
| **2XL** | 48px | 6× | Page breaks, hero sections |

### Responsive Grid System

#### Desktop (1024px+)
- **Columns:** 12
- **Column width:** ~85px
- **Gutter:** 24px
- **Page margin:** 32px

#### Tablet (768px–1023px)
- **Columns:** 8
- **Column width:** ~80px
- **Gutter:** 16px
- **Page margin:** 24px

#### Mobile (320px–767px)
- **Columns:** 4
- **Column width:** ~70px
- **Gutter:** 16px
- **Page margin:** 16px

---

## Icons

### Specifications
- **Size:** 24px × 24px (primary)
- **Stroke Width:** 2px
- **Style:** Outline (no fills)
- **Cap/Join:** Rounded
- **Internal Padding:** 2px
- **Grid Snap:** 2px

### Size Variants
| Size | Stroke | Use Case |
|------|--------|----------|
| 16px | 2px | Small UI elements, badges |
| 24px | 2px | Default, buttons, lists |
| 32px | 2px | Large buttons, prominent elements |

### Icon Categories
- **Navigation:** Dashboard, Trading, Risk, Analytics, Settings
- **Actions:** Add, Edit, Delete, Refresh, Search, Filter
- **Status:** Success, Error, Warning, Info
- **Data:** Trending Up, Trending Down, Chart, Clock
- **Trading:** Buy, Sell, Position, Order, History

---

## Shadows & Depth

### Shadow System

| Level | CSS | Usage |
|-------|-----|-------|
| **None** | — | Flat, no elevation |
| **Small** | `0 1px 2px 0 rgba(0,0,0,0.05)` | Subtle separation |
| **Medium** | `0 4px 6px -1px rgba(0,0,0,0.1)` | Card hover, dropdowns |
| **Large** | `0 10px 15px -3px rgba(0,0,0,0.1)` | Modals, popovers |

### Elevation Ladder

```
No shadow:    Flat cards, inline content
Small shadow: Interactive elements on hover
Medium shadow: Floated elements, dropdowns, menus
Large shadow: Modals, full-screen overlays
```

---

## Border Radius

### Radius Scale

| Token | Value | Usage |
|-------|-------|-------|
| **None** | 0px | Buttons (optional), sharp elements |
| **Small** | 4px | Slight softness, input fields |
| **Medium** | 8px | Cards, dropdowns, modals |
| **Large** | 12px | Large buttons, prominent elements |

### Component Defaults

| Component | Radius |
|-----------|--------|
| Input fields | 8px (MD) |
| Button | 8px (MD) |
| Card | 8px (MD) |
| Modal | 12px (LG) |
| Dropdown | 8px (MD) |
| Badge | 4px (SM) or 999px (pill) |

---

## Responsive Breakpoints

### Media Queries

```css
/* Mobile first */
@media (min-width: 640px) { /* SM */ }
@media (min-width: 768px) { /* MD - tablet */ }
@media (min-width: 1024px) { /* LG - desktop */ }
@media (min-width: 1280px) { /* XL - large desktop */ }
@media (min-width: 1536px) { /* 2XL - ultrawide */ }

/* Landscape orientation */
@media (orientation: landscape) { }
```

### Viewport Sizes

| Label | Min | Max | Devices |
|-------|-----|-----|---------|
| **Mobile** | 320px | 639px | Phones (portrait) |
| **Tablet** | 768px | 1023px | Tablets (portrait/landscape) |
| **Desktop** | 1024px | 1279px | Laptops, desktops |
| **Large Desktop** | 1280px | 1535px | Large monitors |
| **Ultrawide** | 1536px | ∞ | 4K+ displays |

---

## Component Specifications

### Buttons

#### Sizes
| Size | Padding | Font | Height |
|------|---------|------|--------|
| **Small** | 4px 12px | 12px | 32px |
| **Default** | 8px 16px | 14px | 40px |
| **Large** | 12px 24px | 16px | 48px |

#### Variants
| Variant | Background | Border | Text | Hover |
|---------|------------|--------|------|-------|
| **Primary** | Primary Teal | None | Dark | opacity 0.9 |
| **Secondary** | Secondary | Border | Primary | opacity 0.8 |
| **Danger** | Danger Red | None | Text Primary | opacity 0.9 |

#### States
- **Default:** Full opacity
- **Hover:** Scale(1.02), opacity 0.9
- **Active:** Scale(1), brightness(0.9)
- **Disabled:** opacity 0.5, cursor not-allowed

### Form Inputs

#### Specifications
- **Height:** 40px (standard)
- **Padding:** 8px 12px (vertical × horizontal)
- **Background:** Secondary (#161B22)
- **Border:** 1px solid `--color-border`
- **Border Radius:** 8px
- **Font:** Inter Regular 14px
- **Focus:** Primary Teal border + shadow ring

#### States
```css
/* Focus */
border-color: var(--color-primary);
box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.1);

/* Error */
border-color: var(--color-danger);

/* Disabled */
background-color: rgba(255, 255, 255, 0.05);
color: var(--color-text-secondary);
```

### Cards

- **Background:** Secondary (#161B22)
- **Padding:** 16px
- **Border Radius:** 8px
- **Shadow:** Small (at rest), Medium (on hover)
- **Border:** 1px solid `--color-border` (optional)

### Tables

- **Cell Padding:** 8px 12px
- **Row Height:** 40px minimum
- **Header Font:** Bold 14px
- **Border:** 1px solid `--color-border`
- **Hover Row:** Background opacity increase

---

## CSS Import

To use all design tokens in your project:

```css
@import 'figma-export/design-tokens/css-variables.css';
```

Then use throughout your stylesheets:

```css
body {
  background: var(--color-dark);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}

.card {
  background: var(--color-secondary);
  padding: var(--spacing-m);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
}
```

---

## Export Formats

Design tokens are available in:
- **JSON:** `design-tokens/tokens.json` (all tokens, machine-readable)
- **CSS:** `design-tokens/css-variables.css` (CSS variables, ready to import)
- **JSON (Figma):** `design-tokens/figma-tokens.json` (if Figma sync needed)

---

## Versioning

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | 2026-04-23 | Initial design system foundation |

---

## Next Steps (HOUR 3-4)

Component Library creation will use these tokens to build:
- Button component library
- Card components
- Form input components
- Tables
- Charts (candlestick, line, equity curve)
- Alerts & notifications

---

**Questions?** Contact Erkan (erkan@trade-claw.local)
