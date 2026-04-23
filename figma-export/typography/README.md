# Typography System - Trade-Claw Dashboard

## Font Families

### Primary: Inter
- **Usage:** UI text, labels, headings, body copy
- **Weights:** 400 (Regular), 700 (Bold)
- **Fallbacks:** -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
- **License:** Open Font License (free, can be self-hosted or via Google Fonts)

### Secondary: JetBrains Mono
- **Usage:** Numbers, prices, data values, code snippets, timestamps
- **Weights:** 400 (Regular)
- **Reason:** Tabular figures improve readability for financial data alignment
- **License:** OFL (open source)

## Font Sizes (Scale)

| Name | Size | Usage |
|------|------|-------|
| **XS** | 12px | Small labels, captions, info text |
| **SM** | 14px | Input labels, secondary text, smaller UI text |
| **Base** | 16px | Body text, default UI text |
| **LG** | 18px | Large body text, section labels |
| **XL** | 20px | Subheadings, prominent data values |
| **2XL** | 24px | Section headings, card titles |
| **3XL** | 32px | Page headings, major titles |

## Font Weights

| Weight | Value | Usage |
|--------|-------|-------|
| Regular | 400 | Body text, default state |
| Bold | 700 | Headings, emphasis, interactive elements |

## Line Heights

| Name | Value | Usage |
|------|-------|-------|
| **Tight** | 1.2 | Headings (compact, prominent) |
| **Normal** | 1.5 | Body text (readable, comfortable) |

## Typographic Styles

### Headings
- **H1 (Page Title):** 32px / Bold / Tight (1.2)
- **H2 (Section Title):** 24px / Bold / Tight (1.2)
- **H3 (Card Title):** 18px / Bold / Normal (1.5)

### Body
- **Large Body:** 16px / Regular / Normal (1.5)
- **Small Body:** 14px / Regular / Normal (1.5)

### Labels & UI
- **Label:** 12px / Bold / Normal, uppercase, 0.5px letter-spacing
- **Input Label:** 14px / Regular / Normal
- **Caption:** 12px / Regular / Normal, color: text-secondary

### Data & Numbers
- **Large Data:** 20px / Bold / JetBrains Mono (e.g., prices, P&L)
- **Data:** 14px / Regular / JetBrains Mono (e.g., positions, timestamps)

## CSS Classes (Pre-built)

Use these classes for quick typography application:

```html
<!-- Headings -->
<h1 class="typo-heading-3xl">Page Title</h1>
<h2 class="typo-heading-2xl">Section Title</h2>
<h3 class="typo-heading-xl">Card Title</h3>

<!-- Body -->
<p class="typo-body-base">Regular paragraph text</p>
<p class="typo-body-sm">Small paragraph text</p>

<!-- Labels -->
<label class="typo-label">Input Label</label>

<!-- Data / Numbers -->
<span class="typo-data">14:32:45</span>
<span class="typo-data-large">$1,234.56</span>
```

## Implementation

1. **Install Fonts:**
   ```bash
   # Via Google Fonts CDN (in HTML <head>)
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
   
   # Or self-host: download from Google Fonts
   ```

2. **Import CSS Variables:**
   ```css
   @import 'css-variables.css';
   ```

3. **Use in Components:**
   ```jsx
   export const Header = () => (
     <h1 style={{ 
       font: 'var(--font-weight-bold) var(--font-size-3xl) / var(--line-height-tight) var(--font-sans)'
     }}>
       Dashboard
     </h1>
   );
   ```

## Accessibility Notes

- Minimum font size for body text: 14px
- Line-height minimum: 1.5 for body text
- Contrast ratio (text vs background): ≥ 4.5:1 for normal text, ≥ 3:1 for large text
- All sizes tested at 2x zoom (200%) and 3x zoom (300%) for readability

## Mobile Responsiveness

Typography scales on smaller viewports:

| Viewport | Heading | Body | Label |
|----------|---------|------|-------|
| 320px (Mobile) | 24px | 14px | 11px |
| 768px (Tablet) | 28px | 15px | 12px |
| 1024px+ (Desktop) | 32px | 16px | 12px |

See `RESPONSIVE.md` for detailed breakpoint guide.
