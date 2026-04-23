# Icon Style Guide - Trade-Claw Dashboard

## Icon Specifications

| Property | Value | Notes |
|----------|-------|-------|
| **Size** | 24px | Default icon size (24×24 canvas) |
| **Stroke Width** | 2px | Clean, readable outline weight |
| **Style** | Outline | Consistent with modern design systems |
| **Grid** | 24px | Snap to grid for pixel-perfect alignment |
| **Corner Radius** | 2px (minimal) | Slight rounding for softness without over-design |
| **Padding** | 2px | Internal margin from canvas edges |

## Design Rules

### Stroke
- **Weight:** 2px (consistent)
- **Cap:** Rounded (for softer appearance)
- **Join:** Rounded
- **No fills** — outline only for consistency

### Geometry
- **Minimal detail** — easily recognizable at 16px and 24px
- **Balanced proportions** — optical centering for visual weight
- **Avoid thin features** — 2px stroke is minimum, no features <1px
- **Grid alignment** — position elements on 2px grid for crispness

### Consistency
- **Same visual weight** across all icons
- **Aligned baselines** for grouped icons
- **Uniform spacing** from edge to content

## Icon Categories

### Navigation Icons
- Dashboard
- Trading
- Risk Management
- Analytics
- Settings
- Menu
- Close (X)
- Back (Arrow Left)
- Forward (Arrow Right)

### Action Icons
- Plus (Add)
- Minus (Remove)
- Edit
- Delete
- Refresh
- Search
- Filter
- Sort
- Download
- Upload
- Print

### Data/Status Icons
- Eye (Visible)
- Eye Slash (Hidden)
- Check (Success)
- X (Error)
- Alert (Warning)
- Info (Information)
- Help (Question)
- Clock (Time)
- Calendar
- Chart (Analytics)
- Trending Up
- Trending Down

### Trading Icons
- Buy
- Sell
- Position
- Order
- History
- Backtest
- Strategy
- Risk

### Financial Icons
- Dollar ($)
- Euro (€)
- Percent (%)
- Plus (Green +)
- Minus (Red -)
- Arrow Up (Profit)
- Arrow Down (Loss)

### UI Controls
- Chevron Up
- Chevron Down
- Chevron Left
- Chevron Right
- Hamburger Menu
- Vertical Menu
- Settings Gear
- Notification Bell
- User Profile
- Logout

## Usage Rules

### Size Variants
```
16px: Icon-only buttons, small UI elements (40px min click target)
24px: Default size, buttons, list items, form fields
32px: Large buttons, prominent calls-to-action
48px: Hero sections, featured content (rare)
```

### Color Application
- **Primary text:** `--color-text-primary` (#F0F6FC) — default
- **Primary action:** `--color-primary` (#00D9FF) — interactive, highlighted
- **Success:** `--color-success` (#10B981) — positive actions, status
- **Danger:** `--color-danger` (#EF4444) — destructive actions, errors
- **Secondary:** `--color-text-secondary` (#8B949E) — muted, disabled
- **Accent:** `--color-accent` (#FFB700) — warnings, special emphasis

### States
```
Default:   --color-text-primary
Hover:     --color-primary (or apply opacity: 0.8)
Active:    --color-primary + scale(1.05)
Disabled:  --color-text-secondary + opacity: 0.5
```

## Implementation

### SVG Template
```xml
<svg
  xmlns="http://www.w3.org/2000/svg"
  width="24"
  height="24"
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="2"
  stroke-linecap="round"
  stroke-linejoin="round"
>
  <!-- Icon paths here -->
</svg>
```

### React Component
```jsx
export const IconArrowUp = ({ size = 24, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 19V5M5 12l7-7 7 7" />
  </svg>
);
```

### CSS (with Icon Font or SVG Sprite)
```css
.icon {
  width: 24px;
  height: 24px;
  display: inline-block;
  color: var(--color-text-primary);
  flex-shrink: 0;
}

.icon-primary {
  color: var(--color-primary);
}

.icon-success {
  color: var(--color-success);
}

.icon-danger {
  color: var(--color-danger);
}

button:hover .icon {
  color: var(--color-primary);
}
```

## Icon Library Integration

### Recommended Libraries
- **Feather Icons** — Outline style, clean, 24px default (https://feathericons.com/)
- **Heroicons** — Similar outline style, high quality (https://heroicons.com/)
- **React Icons** — Large collection, easy integration (https://react-icons.github.io/react-icons/)

### Custom Icons
If custom icons needed (for trading-specific symbols), maintain consistency with:
- 24px canvas
- 2px stroke weight
- Outline style
- No fills
- Rounded caps and joins

## Accessibility

- Use **semantic SVG** with title/desc for meaningful icons
- Pair with **text labels** for icon-only buttons
- Ensure **sufficient contrast** (4.5:1 minimum)
- Use `aria-label` for icon buttons

Example:
```jsx
<button aria-label="Add new position">
  <IconPlus size={24} />
</button>
```

## File Organization

Icons are stored in:
```
figma-export/icons/
├── ICON_GUIDE.md          (this file)
├── feather-icons-export/  (if using Feather Icons)
├── custom-trading-icons/  (custom SVG files)
└── icon-template.svg      (blank template for new icons)
```

## Quality Checklist

- [ ] Icon is 24px × 24px
- [ ] Stroke weight is consistent (2px)
- [ ] No fills, outline only
- [ ] Corners are rounded (2px radius where applicable)
- [ ] Icon is centered in canvas (2px padding)
- [ ] All strokes snap to grid (2px grid)
- [ ] Icon is recognizable at 16px (squint test)
- [ ] Icon is unique and distinguishable from others
- [ ] All paths use rounded caps/joins
