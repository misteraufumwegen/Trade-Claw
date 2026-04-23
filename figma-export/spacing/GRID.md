# Spacing & Grid System - Trade-Claw Dashboard

## Base Grid: 8px

All spacing in Trade-Claw follows an **8px base grid** for consistency and scalability.

## Spacing Scale

| Token | Value | Use Cases |
|-------|-------|-----------|
| **XS** | 4px | Micro adjustments, internal component spacing, tight gaps |
| **S** | 8px | Padding in small buttons, minimal margins, element gaps |
| **M** | 16px | Standard padding/margin, form field spacing, list item separation |
| **L** | 24px | Section spacing, card margins, significant visual breaks |
| **XL** | 32px | Major section separation, page padding, layout columns gap |
| **2XL** | 48px | Page-level margins, hero sections, major layout breaks |

## CSS Variables

```css
--spacing-xs: 4px;
--spacing-s: 8px;
--spacing-m: 16px;
--spacing-l: 24px;
--spacing-xl: 32px;
--spacing-2xl: 48px;
```

## Common Component Spacing

### Buttons
- **Padding:** 8px (vertical) × 16px (horizontal) = M
- **Gap (icon + text):** 8px = S
- **Button group gap:** 8px = S

### Form Inputs
- **Padding:** 8px (vertical) × 16px (horizontal) = M
- **Label to input:** 8px = S
- **Input to helper text:** 4px = XS
- **Field group spacing:** 16px = M

### Cards
- **Internal padding:** 16px = M
- **Card to card gap:** 16px-24px = M-L
- **Card margin in grid:** 24px = L

### Lists & Tables
- **Row height:** 40px minimum
- **Cell padding:** 8px-12px = S-M
- **Row separation line:** 1px border with 8px gaps = S

### Sidebar & Navigation
- **Navigation item height:** 40px
- **Icon padding:** 8px = S
- **Section spacing:** 24px = L
- **Sidebar padding:** 16px = M

### Page Layout
- **Page padding (desktop):** 32px = XL
- **Page padding (mobile):** 16px = M
- **Section heading to content:** 16px = M
- **Major section gap:** 32px-48px = XL-2XL

## Padding Patterns

### Standard Component Padding
```
Tight:     4px (XS)          — Icon buttons, badges
Compact:   8px (S)           — Small buttons, chips
Standard:  16px (M)          — Form fields, cards, content areas
Spacious:  24px (L)          — Large sections, main content containers
```

### Margin Patterns
```
Adjacent elements:   8px-16px (S-M)
Section separation:  24px-32px (L-XL)
Page-level break:    32px-48px (XL-2XL)
```

## Layout Grid (Responsive)

### Desktop (1024px+)
- **12-column grid**
- **Column width:** ~85px
- **Gutter:** 24px (L) between columns
- **Page margin:** 32px (XL)

### Tablet (768px-1023px)
- **8-column grid**
- **Column width:** ~80px
- **Gutter:** 16px (M) between columns
- **Page margin:** 24px (L)

### Mobile (320px-767px)
- **4-column grid**
- **Column width:** ~70px
- **Gutter:** 16px (M) between columns
- **Page margin:** 16px (M)

## Implementation Examples

### CSS (using variables)
```css
.card {
  padding: var(--spacing-m);
  margin-bottom: var(--spacing-l);
  gap: var(--spacing-s);
}

.form-field {
  margin-bottom: var(--spacing-m);
}

.form-field > label {
  margin-bottom: var(--spacing-xs);
  display: block;
}

.button-group {
  gap: var(--spacing-s);
  display: flex;
}
```

### React/Tailwind (if using Tailwind)
```jsx
// Spacing scale maps to Tailwind
// p-2 = 8px, p-4 = 16px, p-6 = 24px, p-8 = 32px, p-12 = 48px

<div className="p-4 mb-6">
  <label className="block mb-2">Input Label</label>
  <input className="p-4 mb-4" />
</div>
```

### React (inline with CSS vars)
```jsx
<div style={{ padding: 'var(--spacing-m)', marginBottom: 'var(--spacing-l)' }}>
  <label style={{ marginBottom: 'var(--spacing-xs)' }}>Label</label>
  <input style={{ padding: 'var(--spacing-s) var(--spacing-m)' }} />
</div>
```

## Spacing Utilities (CSS Classes)

```css
/* Padding utilities */
.p-xs { padding: 4px; }
.p-s { padding: 8px; }
.p-m { padding: 16px; }
.p-l { padding: 24px; }
.p-xl { padding: 32px; }
.p-2xl { padding: 48px; }

/* Margin utilities */
.m-xs { margin: 4px; }
.m-s { margin: 8px; }
.m-m { margin: 16px; }
.m-l { margin: 24px; }
.m-xl { margin: 32px; }
.m-2xl { margin: 48px; }

/* Gap (for flex/grid) */
.gap-s { gap: 8px; }
.gap-m { gap: 16px; }
.gap-l { gap: 24px; }
.gap-xl { gap: 32px; }
```

## Responsive Spacing Adjustments

At mobile (< 768px), reduce spacing by one level:

```css
@media (max-width: 767px) {
  .card {
    padding: var(--spacing-s);  /* was M (16px) → S (8px) */
    margin-bottom: var(--spacing-m);  /* was L (24px) → M (16px) */
  }
  
  body {
    padding: var(--spacing-m);  /* was XL (32px) → M (16px) */
  }
}
```

## Best Practices

1. **Always use the spacing scale** — no arbitrary pixel values
2. **Prefer larger spacing over smaller** — gives breathing room
3. **Be consistent within components** — align-left padding should match button padding
4. **Test readability** — at 2x zoom, all spacing should still look balanced
5. **Reduce on mobile** — use fewer/smaller spacing units on < 768px viewports

## Tools

- **Figma:** Use this file as reference for design tokens
- **Frontend:** Import `css-variables.css` and use `--spacing-*` variables
- **QA:** Measure spacing using browser DevTools ruler or pixel grid overlay
