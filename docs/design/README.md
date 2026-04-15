# Trade-Claw Frontend Design Specification

**Project:** Trade-Claw Trading Bot Frontend  
**Designer:** Erkan (UX/UI Design Lead)  
**Status:** ✅ Complete & Ready for Development  
**Date:** April 15, 2026  
**Handoff to:** Elon (CTO / Frontend Developer)

---

## 📂 Documentation Structure

This folder contains the complete frontend design specification for Trade-Claw. Use the files below as your source of truth.

### 1️⃣ **START HERE: SUMMARY.md** (5-10 min read)
**What:** Executive summary, checklist, dev guidelines  
**For whom:** Elon (developer), Deniz (quick overview)  
**Contains:**
- Deliverables checklist ✅
- Design highlights (colors, grid, typography)
- Development guidelines (tech stack, naming conventions)
- Next steps & phase breakdown
- Success criteria

👉 **Read this first if you're new to the project.**

---

### 2️⃣ **DESIGN_SYSTEM.md** (Reference)
**What:** Complete design system — colors, typography, spacing, components, animations  
**For whom:** Elon (CSS/TailwindCSS configuration), designers (maintaining consistency)  
**Contains:**
- Color palette (10-color semantic system for dark mode)
- Typography scale (8 font sizes + weights)
- Spacing scale (8px base, 13 steps)
- Border radius, shadows, buttons, inputs, cards, modals, badges
- States & animations (hover, active, focus, disabled, loading)
- Accessibility requirements (WCAG AA)
- Responsive breakpoints
- Icon system (24 icons with sizes)
- Dark mode implementation with CSS variables

👉 **Reference this when building UI components.**

---

### 3️⃣ **WIREFRAMES.md** (Visual Reference)
**What:** Text-based wireframes + interaction flows for all 5 modules  
**For whom:** Elon (layout structure), QA (test cases), Deniz (visual overview)  
**Contains:**
- Module 1: Dashboard (alerts, KPIs, positions, risk status, quick actions)
- Module 2: Trading Console (macro events, entry form, correlation matrix)
- Module 3: Risk Management (hard limits, SL lock, emergency halt, alerts)
- Module 4: Analytics (filters, charts, trade history, stats)
- Module 5: Settings (connection, broker, assets, risk, notifications)
- Desktop & mobile layouts for each module
- 3 detailed interaction flows (trade execution, emergency halt, risk trigger)

👉 **Reference this when implementing layouts and UX flows.**

---

### 4️⃣ **COMPONENTS.md** (Technical Spec)
**What:** Complete React component tree, file structure, component specs, hooks, state management, API integration  
**For whom:** Elon (implementation guide), QA (testing), any future developer  
**Contains:**
- Application folder structure (30+ folders/files)
- 50+ component specs with props, purpose, behavior
- Common components (Button, Card, Modal, Table, etc.)
- Module-specific components (Dashboard, Trading, Risk, Analytics, Settings)
- Redux slices (7 slices: positions, trades, alerts, risk, ui, settings, etc.)
- Custom hooks (6 hooks: usePositions, usePrices, useRisk, useAlerts, useTrades, useCorrelation)
- API integration specs (OANDA v20, worldmonitor.app, correlation engine)
- TypeScript interfaces (Trade, Position, Alert, MacroEvent, etc.)
- Testing strategy & performance guidelines

👉 **Reference this during development for component specs and API integration.**

---

## 🎯 QUICK NAVIGATION

| Need... | File | Section |
|---------|------|---------|
| Overview & checklist | SUMMARY.md | Top section |
| Dev guidelines & naming | SUMMARY.md | Development Guidelines |
| Color palette | DESIGN_SYSTEM.md | Color Palette |
| Typography scale | DESIGN_SYSTEM.md | Typography |
| Spacing & grid | DESIGN_SYSTEM.md | Spacing & Layout |
| Dashboard layout | WIREFRAMES.md | Module 1: Dashboard |
| Trading console layout | WIREFRAMES.md | Module 2: Trading Module |
| Risk management layout | WIREFRAMES.md | Module 3: Risk Management |
| Analytics layout | WIREFRAMES.md | Module 4: Analytics |
| Settings layout | WIREFRAMES.md | Module 5: Settings |
| Trade execution flow | WIREFRAMES.md | Key Interaction Flows |
| Component tree | COMPONENTS.md | Application Structure |
| Component specs | COMPONENTS.md | Core Components |
| State management | COMPONENTS.md | State Management |
| API integration | COMPONENTS.md | API Integration |
| TypeScript types | COMPONENTS.md | Types & Interfaces |
| Testing strategy | COMPONENTS.md | Testing Strategy |

---

## 🚀 GETTING STARTED (For Elon)

### Step 1: Read the Summary (5-10 min)
```
→ Open SUMMARY.md
→ Scan deliverables checklist
→ Review development guidelines section
→ Note the tech stack & folder structure
```

### Step 2: Understand the Design System (15-20 min)
```
→ Open DESIGN_SYSTEM.md
→ Review colors (primary, success, danger, warning, neutral)
→ Copy typography scale into TailwindCSS config
→ Copy spacing scale into TailwindCSS config
→ Note the border radius, shadows, component variants
```

### Step 3: Understand the Wireframes (30 min)
```
→ Open WIREFRAMES.md
→ Read Module 1: Dashboard layout
→ Imagine how each section looks
→ Read the 3 interaction flows at the bottom
→ Get a feel for the UX
```

### Step 4: Deep Dive into Components (60 min)
```
→ Open COMPONENTS.md
→ Review Application Structure (folder setup)
→ Read through the Core Components section
→ Understand the Redux slices
→ Review API integration specs (OANDA, macro, correlation)
→ Check TypeScript interfaces
```

### Step 5: Start Building
```
→ Create React + TS project with Vite
→ Setup TailwindCSS with design tokens from DESIGN_SYSTEM.md
→ Follow folder structure from COMPONENTS.md
→ Build layout components (AppShell, Navbar, Sidebar)
→ Build common components (Button, Card, Modal, etc.)
→ Build page components (Dashboard, Trading, Risk, Analytics, Settings)
→ Integrate Redux & hooks
→ Integrate OANDA API
→ Test & optimize
```

---

## 🎨 DESIGN PHILOSOPHY

**Trade-Claw frontend design is:**

✅ **Dark mode first** — Professional, reduces eye strain, matches trading platforms  
✅ **Real-time focused** — Live updates, WebSocket subscriptions, minimal latency  
✅ **Risk-aware** — Risk limits hardcoded, visual warnings, emergency halt button  
✅ **Accessible** — WCAG AA compliant, 4.5:1 contrast, semantic HTML  
✅ **Responsive** — Mobile-first, works on 375px to 1440px+ viewports  
✅ **Micro-animated** — Subtle motion (100-300ms), not distracting  
✅ **Data-driven** — Charts, tables, analytics for trade review  
✅ **Fast** — < 2s first contentful paint, < 500KB bundle  

---

## 🔧 TECH STACK (Recommended)

```
Frontend:
├─ React 18 + TypeScript
├─ TailwindCSS (for styling)
├─ Redux Toolkit (state management)
├─ React Router (navigation)
├─ React Query / SWR (data caching)
├─ Recharts or Chart.js (charts)
├─ React Icons (icons)
└─ Zod or Yup (validation)

Build & Test:
├─ Vite (fast build)
├─ Jest + React Testing Library (testing)
├─ Prettier (code formatting)
├─ ESLint (code quality)
└─ Vitest (unit tests)

Infrastructure:
├─ Docker (containerization)
├─ GitHub Actions (CI/CD)
├─ Vercel or AWS (hosting)
└─ Sentry (error tracking)

API Integration:
├─ OANDA v20 REST API
├─ OANDA Streaming API (WebSocket)
├─ worldmonitor.app (macro events)
└─ Internal correlation engine
```

---

## 📋 MODULES AT A GLANCE

### Module 1: Dashboard (Landing Page)
**Purpose:** Real-time overview of trading performance  
**Main elements:**
- Key metrics: Today's P&L, Month's P&L, Win Rate, Profit Factor
- Risk status: Drawdown %, position size usage
- Active positions: Real-time list of open trades
- Quick actions: Emergency halt, settings, analytics
- Alert banner: Critical alerts & warnings

### Module 2: Trading Console
**Purpose:** Execute new trades with validation  
**Main elements:**
- Macro events feed (live from worldmonitor.app)
- Strategy selector (Ünal's grades A+/A/B)
- Trade entry form (asset, direction, prices, size, grade)
- Risk/reward validator (must be ≥ 1:3)
- Correlation matrix (heatmap of asset correlations)

### Module 3: Risk Management
**Purpose:** Monitor & enforce risk limits  
**Main elements:**
- Hard limits (position size 10%, drawdown -15%, daily loss -5%)
- Stop-loss immutability (auto-locks SLs when at risk)
- Emergency halt button (closes all positions instantly)
- Live alert feed (critical, warnings, info)

### Module 4: Analytics
**Purpose:** Review trades & performance metrics  
**Main elements:**
- Filters: Time range, asset, grade, status, search
- Charts: Win rate trend, profit factor trend, monthly P&L, drawdown history
- Trade history table: Scrollable, sortable, color-coded P&L
- Statistics: Total trades, win rate, avg win/loss, best/worst

### Module 5: Settings
**Purpose:** Configure broker, assets, notifications  
**Main elements:**
- Connection status: Broker, API key, price feed, system health
- Broker & account: OANDA config, account details (read-only)
- Assets selector: Choose tradable assets
- Risk configuration: Read-only hard limits
- Notifications: Alert preferences

---

## 🎓 DESIGN REFERENCE

Inspiration & benchmarks:
- **TradingView:** Real-time charts, dark mode, responsive
- **Binance:** Clean trading UI, risk management, notifications
- **Interactive Brokers:** Professional, data-heavy, accessible
- **Stripe:** Component system, clear microcopy, error handling

Design tools used:
- Figma (for wireframes & design system)
- CSS Variables (for design token implementation)
- TailwindCSS (for rapid styling)

---

## ✅ HANDOFF CHECKLIST

Before starting development, Elon should confirm:

- [ ] Read SUMMARY.md (especially Development Guidelines section)
- [ ] Reviewed DESIGN_SYSTEM.md (colors, typography, spacing)
- [ ] Reviewed WIREFRAMES.md (layouts & flows)
- [ ] Reviewed COMPONENTS.md (component specs & structure)
- [ ] Tech stack approved (React, TypeScript, TailwindCSS, Redux, etc.)
- [ ] Folder structure matches COMPONENTS.md plan
- [ ] OANDA API key & documentation available
- [ ] worldmonitor.app API endpoint & docs available
- [ ] Design tokens ready to configure in TailwindCSS
- [ ] Access to GitHub repo & deployment pipeline
- [ ] Questions escalated to Deniz (CEO) if needed

---

## 📞 WHO TO ASK

**Design questions?**  
→ Erkan (this file, DESIGN_SYSTEM.md, WIREFRAMES.md)

**Component specs?**  
→ COMPONENTS.md or Erkan

**API integration questions?**  
→ COMPONENTS.md API section or Elon (CTO) if stuck

**Business logic questions?**  
→ Ünal (CFO) for trading rules, Sirin (QM) for requirements

**Overall direction questions?**  
→ Deniz (CEO) via escalation

---

## 📊 PROJECT TIMELINE

| Phase | Owner | Duration | Status |
|-------|-------|----------|--------|
| Design | Erkan | 6-8h | ✅ COMPLETE |
| Frontend Dev | Elon | 40-50h | ⏳ TODO |
| Backend API | TBD | 20-30h | ⏳ TODO |
| Testing & QA | Sirin | 10-15h | ⏳ TODO |
| Deployment | Milan | 5h | ⏳ TODO |
| **TOTAL** | Team | ~100-110h | **6-7 business days** |

---

## 🎯 SUCCESS METRICS

Frontend is production-ready when:

✅ All 5 modules fully functional  
✅ OANDA API integration complete  
✅ Real-time price updates working  
✅ Risk limits enforced (drawdown, position size, daily loss)  
✅ Emergency halt tested & working  
✅ Responsive on mobile, tablet, desktop  
✅ 80%+ unit test coverage  
✅ WCAG AA accessibility audit passed  
✅ Bundle size < 500KB (gzipped)  
✅ Lighthouse score ≥ 90  

---

## 📝 DOCUMENT VERSIONS

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Apr 15, 2026 | Erkan | Initial design spec |

---

## 🔐 DISCLAIMER

This design specification is proprietary to Trade-Claw. Do not share without permission.

All design decisions are final unless approved by Deniz (CEO).

Any changes to this design must go through Erkan (UX/UI) before implementation.

---

**Ready to build?** → Start with SUMMARY.md, then jump to COMPONENTS.md.

**Questions?** → Check the relevant file above, or escalate to Erkan/Deniz.

---

*Design Specification v1.0 | Delivered by Erkan on April 15, 2026 | Ready for Development* ✅
