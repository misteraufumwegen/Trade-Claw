# Trade-Claw Design System

**Status:** ✅ HOUR 1-2 Complete  
**Version:** 1.0.0  
**Created:** 2026-04-23  
**Owner:** Erkan (UX/UI Designer)

---

## Overview

This directory contains the complete Trade-Claw Design System foundation — color tokens, typography guidelines, spacing rules, icon specifications, and comprehensive visual documentation.

## 📁 Directory Structure

```
figma-export/
├── README.md                              (this file)
├── design-tokens/
│   ├── tokens.json                        (all design tokens in JSON format)
│   ├── css-variables.css                  (CSS custom properties, ready to import)
│   └── figma-tokens.json                  (optional: for Figma token sync)
├── typography/
│   └── README.md                          (typography system, font guidelines, scales)
├── spacing/
│   └── GRID.md                            (spacing scale, grid system, responsive breakpoints)
├── icons/
│   ├── ICON_GUIDE.md                      (icon specifications, style rules, usage)
│   ├── feather-icons-export/              (recommended: Feather Icons SVG exports)
│   └── custom-trading-icons/              (trading-specific custom SVG icons)
└── documentation/
    ├── DESIGN_TOKENS.md                   (complete design token reference)
    ├── color-palette.html                 (visual color palette reference)
    ├── RESPONSIVE.md                      (responsive design guidelines - HOUR 3+)
    └── COMPONENT_SPECS.md                 (component specifications - HOUR 3-4)
```

## 🎨 Quick Start

### For Developers

1. **Import CSS variables** into your project:
   ```css
   @import '/figma-export/design-tokens/css-variables.css';
   ```

2. **Use variables in your styles:**
   ```css
   body {
     background-color: var(--color-dark);
     color: var(--color-text-primary);
     font-family: var(--font-sans);
   }
   
   .button {
     background-color: var(--color-primary);
     padding: var(--spacing-s) var(--spacing-m);
     border-radius: var(--radius-md);
   }
   ```

3. **Reference design tokens** from `tokens.json` for any property not yet in CSS

### For Designers

1. **View color palette:** Open `documentation/color-palette.html` in browser
2. **Reference complete guide:** Read `documentation/DESIGN_TOKENS.md`
3. **Typography rules:** See `typography/README.md`
4. **Icon guidelines:** Review `icons/ICON_GUIDE.md`
5. **Spacing rules:** Check `spacing/GRID.md`

## 📚 Design Token Categories

### Colors (`design-tokens/tokens.json` / `css-variables.css`)
- **Base:** Dark, Secondary, Primary Teal, Accent Gold, Success Green, Danger Red
- **Text:** Primary, Secondary, Disabled
- **Functional:** Borders, Dividers
- **Semantic:** Profit (Green), Loss (Red), Alert (Gold), Action (Teal)

```css
--color-dark: #0D1117;
--color-primary: #00D9FF;
--color-success: #10B981;
--color-danger: #EF4444;
/* ... and more */
```

### Typography
- **Fonts:** Inter (UI), JetBrains Mono (Data)
- **Weights:** Regular (400), Bold (700)
- **Sizes:** 12px, 14px, 16px, 18px, 20px, 24px, 32px
- **Line Heights:** 1.2 (tight), 1.5 (normal)

```css
--font-sans: 'Inter', -apple-system, ...;
--font-mono: 'JetBrains Mono', ...;
--font-size-base: 16px;
--font-weight-bold: 700;
```

### Spacing (8px Base Grid)
- **Scale:** 4px (XS), 8px (S), 16px (M), 24px (L), 32px (XL), 48px (2XL)
- **Used for:** Padding, margins, gaps, grid gutters
- **Responsive:** Scales down on mobile viewports

```css
--spacing-xs: 4px;
--spacing-s: 8px;
--spacing-m: 16px;
--spacing-l: 24px;
```

### Icons
- **Size:** 24px × 24px (primary), variants at 16px & 32px
- **Stroke:** 2px outline
- **Style:** Outline, no fills
- **Grid:** Snap to 2px grid
- **Radius:** Rounded caps/joins

### Shadows & Elevation
- **Small:** Subtle borders, slight lift
- **Medium:** Cards, dropdowns, hovered elements
- **Large:** Modals, full-screen overlays

### Border Radius
- **None:** 0px (sharp)
- **Small:** 4px
- **Medium:** 8px (default for inputs, buttons, cards)
- **Large:** 12px (prominent elements)

## 🎯 Usage Guidelines

### By Role

**Frontend Developers:**
- Import `css-variables.css` into your project
- Use CSS variables throughout your components
- Reference `documentation/DESIGN_TOKENS.md` for complete specifications
- For icons: use Feather Icons library or custom SVG exports

**UI/UX Designers:**
- Use `color-palette.html` for color references
- Follow guidelines in `typography/`, `spacing/`, `icons/`
- Create components using tokens for consistency

**QA/Testing:**
- Verify spacing matches grid (multiples of 8px)
- Test color contrast (4.5:1 minimum for text)
- Confirm icons are 24px and render crisply
- Check responsive breakpoints (320px, 768px, 1024px+)

**Project Managers:**
- Colors are final (no further palette changes during HOUR 1-6)
- Typography is locked (no font family or weight changes)
- Spacing grid is fixed (8px base, no exceptions)

## 📋 Checklist (HOUR 1-2 Complete)

- [x] Color palette defined (6 semantic + text + functional colors)
- [x] Typography system created (Inter + JetBrains Mono)
- [x] Font sizes scaled (12px–32px on modular scale)
- [x] Line heights set (1.2 tight, 1.5 normal)
- [x] Spacing grid established (8px base: 4px–48px)
- [x] Icon specifications documented (24px, 2px stroke, outline style)
- [x] CSS variables exported (`css-variables.css`)
- [x] Design tokens in JSON format (`tokens.json`)
- [x] Visual documentation created (`color-palette.html`)
- [x] Complete reference guide written (`DESIGN_TOKENS.md`)

## 🔄 Next Steps (HOUR 3-4)

**Component Library** — Elon will create React components using these tokens:
- Button components (Primary, Secondary, Danger + states)
- Card component
- Form input component
- Tables
- Chart components (candlestick, line, equity curve)
- Alerts & notifications

## 📖 Documentation Files

### Files in This Directory

| File | Purpose | Audience |
|------|---------|----------|
| `design-tokens/tokens.json` | Machine-readable tokens | Developers, Token sync tools |
| `design-tokens/css-variables.css` | CSS import ready | Frontend developers |
| `typography/README.md` | Font, size, weight rules | Designers, Developers |
| `spacing/GRID.md` | 8px grid, responsive rules | Designers, Developers |
| `icons/ICON_GUIDE.md` | Icon specs, style rules | Designers, Icon creators |
| `documentation/DESIGN_TOKENS.md` | Complete token reference | All team members |
| `documentation/color-palette.html` | Visual color reference | All team members (browser) |

### How to Use

1. **Developers:** Import `css-variables.css`, use variables
2. **Designers:** Read markdown files, open HTML in browser
3. **Implementers:** Check `DESIGN_TOKENS.md` for component specs
4. **QA:** Use color/spacing guides for verification

## 🔐 Design System Rules

### What's Fixed (No Changes During Sprint)
- ✋ Color palette (6 colors + text + functional)
- ✋ Font families (Inter + JetBrains Mono)
- ✋ Font weights (400, 700 only)
- ✋ Spacing grid (8px base)
- ✋ Icon style (outline, 2px stroke, 24px)

### What's Flexible (Per Component)
- ✅ Border radius (4px–12px range)
- ✅ Shadow elevation (small, medium, large)
- ✅ Font sizes (12px–32px scale)
- ✅ Component-specific padding (using spacing scale)

## 🤝 Handoff to Development (HOUR 3)

When Elon begins HOUR 3-4 (Component Library), he will:
1. Reference this design system
2. Import `css-variables.css` into React project
3. Create reusable components using these tokens
4. Create Storybook documentation with visual examples

## ❓ Questions?

- **Color/Visual Issues:** Contact Erkan (erkan@trade-claw.local)
- **Typography/Font Issues:** Contact Erkan
- **Implementation/CSS Issues:** Ask Elon (CTO)
- **Icon Custom Design:** Contact Erkan

## 📞 Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| **1.0** | 2026-04-23 | Initial system foundation | Erkan |

---

**Last Updated:** 2026-04-23 18:06 CET  
**Status:** ✅ Complete and Committed  
**Commit Hash:** (set after git commit)

---

## How to View

### Color Palette (Visual)
Open in browser: `documentation/color-palette.html`

### Token Reference
Read in editor: `documentation/DESIGN_TOKENS.md`

### Import into Project
```css
@import 'figma-export/design-tokens/css-variables.css';
```

### Use in CSS
```css
body {
  background: var(--color-dark);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}
```

---

**Trade-Claw Design System v1.0** — Ready for Component Library Development
