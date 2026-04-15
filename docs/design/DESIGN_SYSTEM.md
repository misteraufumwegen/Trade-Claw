# Trade-Claw Design System
**Version:** 1.0 | **Status:** Design Spec | **Audience:** Elon (Frontend Developer)

---

## 1. COLOR PALETTE (Dark Mode - Trading-Optimized)

### Core Colors
```
PRIMARY (Trust/Action)
  - primary-50:  #E3F2FD
  - primary-100: #BBDEFB
  - primary-200: #90CAF9
  - primary-300: #64B5F6
  - primary-400: #42A5F5
  - primary-500: #2196F3  ← Main Brand Blue
  - primary-600: #1E88E5
  - primary-700: #1976D2
  - primary-800: #1565C0
  - primary-900: #0D47A1

SECONDARY (Accent/Insights)
  - secondary-300: #81C784  ← Positive Green
  - secondary-400: #66BB6A
  - secondary-500: #4CAF50  ← Main Green (gains)

SUCCESS / GAINS
  - success-50:  #E8F5E9
  - success-200: #81C784
  - success-500: #4CAF50  ← Green (profit, up)
  - success-700: #388E3C

DANGER / LOSSES
  - danger-50:  #FFEBEE
  - danger-200: #EF9A9A
  - danger-500: #F44336  ← Red (loss, down)
  - danger-700: #C62828

WARNING / CAUTION
  - warning-50:  #FFF3E0
  - warning-200: #FFB74D
  - warning-500: #FF9800  ← Orange (alerts, caution)
  - warning-700: #E65100

NEUTRAL (Backgrounds, Text)
  - neutral-0:   #FFFFFF
  - neutral-50:  #F9FAFB  ← Light backgrounds
  - neutral-100: #F3F4F6
  - neutral-200: #E5E7EB
  - neutral-300: #D1D5DB
  - neutral-400: #9CA3AF
  - neutral-500: #6B7280  ← Secondary text
  - neutral-600: #4B5563
  - neutral-700: #374151  ← Primary text
  - neutral-800: #1F2937  ← Cards/containers
  - neutral-900: #111827  ← Dark background
```

### Semantic Assignments
| Element | Color | Use Case |
|---------|-------|----------|
| Background (page) | neutral-900 (#111827) | Main surface |
| Background (cards) | neutral-800 (#1F2937) | Card surfaces, containers |
| Text (primary) | neutral-50 (#F9FAFB) | Body text, labels |
| Text (secondary) | neutral-400 (#9CA3AF) | Hints, disabled |
| Text (accent) | primary-400 (#42A5F5) | Links, CTAs |
| Borders | neutral-700 (#374151) | Card borders, dividers |
| Profit/Positive | success-500 (#4CAF50) | Green numbers, up arrows |
| Loss/Negative | danger-500 (#F44336) | Red numbers, down arrows |
| Alerts/Warnings | warning-500 (#FF9800) | Warning states |
| Primary CTA | primary-500 (#2196F3) | Buttons, key actions |
| Hover (CTA) | primary-600 (#1E88E5) | Button hover state |
| Disabled | neutral-600 (#4B5563) | Disabled states |

---

## 2. TYPOGRAPHY

### Font Stack
```
Font Family (Primary): -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif
Font Family (Monospace): 'Fira Code', 'Monaco', 'Courier New', monospace (for prices, numbers)
Font Weight: 400 (Regular), 500 (Medium), 600 (Semibold), 700 (Bold)
```

### Type Scale
```
h1 - Display / Hero
  Size: 32px / 2rem
  Weight: 700
  Line Height: 1.25
  Letter Spacing: -0.02em
  Use: Page titles, main hero sections
  Example: "Dashboard", "Trade History"

h2 - Heading 1
  Size: 28px / 1.75rem
  Weight: 600
  Line Height: 1.35
  Use: Major section headers
  Example: "Active Positions", "Risk Management"

h3 - Heading 2
  Size: 24px / 1.5rem
  Weight: 600
  Line Height: 1.4
  Use: Subsection headers
  Example: "Today's P&L", "Macro Events"

h4 - Heading 3
  Size: 20px / 1.25rem
  Weight: 600
  Line Height: 1.5
  Use: Card titles, subsection labels
  Example: "Entry Strategy", "Correlation Matrix"

body-lg - Large Body
  Size: 16px / 1rem
  Weight: 500
  Line Height: 1.6
  Use: Important labels, form inputs
  Example: "Position Size", "Stop Loss"

body - Body (default)
  Size: 14px / 0.875rem
  Weight: 400
  Line Height: 1.6
  Use: Standard text, descriptions
  Example: Trade details, status text

body-sm - Small Body
  Size: 12px / 0.75rem
  Weight: 400
  Line Height: 1.5
  Use: Helper text, hints
  Example: "Last updated: 2m ago"

label - Form Labels
  Size: 12px / 0.75rem
  Weight: 600
  Letter Spacing: 0.05em
  Color: neutral-400
  Use: Form field labels
  Example: "Risk Limit", "Asset"

code / monospace
  Size: 13px / 0.8125rem
  Weight: 500
  Font Family: Monospace
  Use: Prices, ticker symbols, technical values
  Example: "USD/JPY", "1.235", "0x1a2b3c"
```

---

## 3. SPACING & LAYOUT

### Spacing Scale (8px base)
```
space-0:   0px
space-1:   4px   (micro spacing)
space-2:   8px   (default, padding inside buttons)
space-3:   12px  (card padding small)
space-4:   16px  (default padding, gaps)
space-5:   20px  (padding large)
space-6:   24px  (section spacing)
space-8:   32px  (major section spacing)
space-10:  40px
space-12:  48px  (hero spacing, large gaps)
space-16:  64px  (page margins)
```

### Layout Grid
```
- Container max-width: 1440px
- Grid columns: 12 (for responsive layout)
- Gutter width: 24px (space-6)
- Margin (sides): 24px (space-6) on desktop, 16px (space-4) on tablet, 12px (space-3) on mobile
```

### Border Radius
```
radius-sm:   4px   (small, buttons, small components)
radius-md:   8px   (standard, cards, inputs)
radius-lg:   12px  (large, modals, major sections)
radius-full: 9999px (pills, badges, circles)
```

---

## 4. SHADOWS & DEPTH

```
shadow-none:     none
shadow-xs:       0 1px 2px 0 rgba(0, 0, 0, 0.05)
shadow-sm:       0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)
shadow-md:       0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)
shadow-lg:       0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)
shadow-xl:       0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)
shadow-elevation-high: 0 20px 40px rgba(0, 0, 0, 0.3) (modals, dropdowns)
```

---

## 5. COMPONENT LIBRARY (React)

### Button Variants
```
Type: Primary
  Background: primary-500
  Text: neutral-50
  Hover: primary-600
  Disabled: neutral-600 (bg), neutral-400 (text)
  Padding: space-2 (4px) vertical × space-4 (16px) horizontal
  Border Radius: radius-md
  Font: body-lg (16px)
  Min Height: 44px (touch-friendly)

Type: Secondary
  Background: neutral-700
  Text: neutral-50
  Hover: neutral-600
  Border: 1px solid neutral-600
  Padding: space-2 × space-4
  
Type: Ghost
  Background: transparent
  Text: primary-400
  Hover: primary-300 (or background neutral-700)
  Border: 1px solid primary-400
  Padding: space-2 × space-4
  
Type: Danger
  Background: danger-500
  Text: neutral-50
  Hover: danger-700
  Use: Emergency Halt, destructive actions

Type: Icon Button
  Size: 40px × 40px (circular)
  Padding: space-2
  Border Radius: radius-full
  Background: hover state only
```

### Input Fields
```
Type: Text/Number Input
  Background: neutral-700
  Border: 1px solid neutral-600
  Border (focus): 2px solid primary-500
  Text: neutral-50
  Placeholder: neutral-500
  Padding: space-3 (12px) × space-4 (16px)
  Border Radius: radius-md
  Font: body
  Height: 44px (touch-friendly)
  
Type: Select/Dropdown
  Same as text input
  
Type: Checkbox
  Size: 20px × 20px
  Background (unchecked): neutral-700
  Border: 2px solid neutral-600
  Background (checked): primary-500
  Border (checked): primary-500
  Icon: checkmark in primary-50
  
Type: Radio Button
  Size: 20px × 20px (circle)
  Same color logic as checkbox
```

### Cards
```
Type: Standard Card
  Background: neutral-800
  Border: 1px solid neutral-700
  Border Radius: radius-lg
  Padding: space-5 (20px)
  Shadow: shadow-sm
  
Type: Interactive Card
  Same + hover: border-color → primary-500 (subtle highlight)
  Cursor: pointer
  
Type: Stat Card
  Padding: space-4 (16px)
  Used for KPIs on dashboard
```

### Modal/Dialog
```
Overlay: rgba(0, 0, 0, 0.7)
Modal Background: neutral-800
Border: 1px solid neutral-700
Border Radius: radius-lg
Padding: space-6 (24px)
Shadow: shadow-elevation-high
Max Width: 600px
Min Width (mobile): 90vw
```

### Tooltip/Badge
```
Type: Badge
  Background: primary-500
  Text: neutral-50
  Padding: space-1 (4px) × space-3 (12px)
  Border Radius: radius-full
  Font: label

Type: Pill Badge (status)
  Same + height: 28px
  Display: inline-flex, align-items: center
```

---

## 6. STATES & ANIMATIONS

### Interactive States
```
Hover:   opacity +10%, scale: 1.02 (subtle)
Active:  opacity +20%, scale: 0.98
Focus:   outline: 2px solid primary-500, outline-offset: 2px
Disabled: opacity 50%, cursor: not-allowed
Loading: spinner animation (0.6s rotation)
```

### Transitions
```
Default:   150ms ease-out (all)
Slow:      300ms ease-out (modals, large movements)
Fast:      80ms ease-out (micro-interactions)
```

### Visual Feedback
```
Success:   success-500 highlight + checkmark icon + subtle pulse (200ms)
Error:     danger-500 highlight + error icon + shake animation (150ms)
Warning:   warning-500 highlight + icon
Loading:   spinner + neutral-400
```

---

## 7. ACCESSIBILITY REQUIREMENTS

- **Color Contrast:** All text ≥ 4.5:1 (WCAG AA standard)
- **Focus Indicators:** 2px solid outline on all interactive elements
- **Touch Targets:** Minimum 44px × 44px
- **Motion:** Respect `prefers-reduced-motion` media query
- **Icons + Text:** All interactive icons paired with descriptive labels or aria-labels
- **Form Labels:** Explicit `<label>` elements with `htmlFor` attributes
- **ARIA:** Use `aria-live`, `aria-label`, `aria-describedby` where needed
- **Semantic HTML:** `<button>`, `<input>`, `<select>`, not divs

---

## 8. RESPONSIVE BREAKPOINTS

```
Mobile:     0px – 640px    (default, single column)
Tablet:     641px – 1024px (2 columns, adjusted spacing)
Desktop:    1025px – 1440px (3+ columns, full layout)
Wide:       1441px+        (max-width container)
```

---

## 9. DARK MODE IMPLEMENTATION

All colors defined above are **dark mode only**. No light mode in MVP.

- **CSS Variables:**
  ```css
  :root {
    --color-primary-500: #2196F3;
    --color-success-500: #4CAF50;
    --color-danger-500: #F44336;
    --color-warning-500: #FF9800;
    --color-neutral-800: #1F2937;
    --color-neutral-900: #111827;
    /* ... all colors ... */
  }
  ```

- **Tailwind Config:** Pre-configured with all colors, spacing, typography, and shadows for easy implementation.

---

## 10. ICON SYSTEM

### Icons Used (React Icons / Heroicons)
```
Dashboard:        Home, TrendingUp, Activity
Trading Module:   Zap, Layers, Grid, Plus, Send
Risk:             AlertTriangle, Lock, XCircle, Shield
Analytics:        BarChart3, LineChart, PieChart, TrendingUp
Settings:         Settings, Sliders, Wifi, Link
General:          ArrowUp, ArrowDown, ChevronRight, Menu, X
Status:           CheckCircle, AlertCircle, XCircle, Clock
```

**Icon Size Standards:**
- Inline (labels): 16px
- Button icons: 20px
- Header icons: 24px
- Large cards: 32px

---

## 11. MOTION & MICRO-INTERACTIONS

```
Button Tap:       Scale 0.98 + 100ms ease-out
Card Hover:       Border highlight + subtle lift (2px shadow increase)
Modal Enter:      Fade in + scale 0.95 → 1 (300ms)
Toast/Alert:      Slide in from bottom + fade (250ms)
Loading Spinner:  Rotation 0 → 360° over 0.6s (infinite)
Dropdown Open:    Slide down + fade in (150ms)
Number Change:    Pulse highlight (200ms) if value changes
```

---

**Next:** Wire frames follow in WIREFRAMES.md
