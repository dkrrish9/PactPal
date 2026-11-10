# PactPal Front‑End Design Brief

**Subsystem:** Web App & Bryntum Gantt UI (`frontend`)

---

## 1. Project Context
- **Product name:** PactPal
- **Core purpose:** A user‑facing portal that enables **Buyers**, **Sellers**, and **Platform Admins** to create, negotiate, and manage contracts.
- **Unique value proposition:** Integrated **Bryntum Gantt & Scheduler** visualizations for contract feature tasks and a 29‑day PayPal hold countdown that is visible to all parties.
- **Target audiences:**
  - **Buyers** – Create contracts, monitor progress, and release escrow.
  - **Sellers** – View assigned tasks, update status, and request change orders.
  - **Admins** – Oversee all contracts, intervene on disputes, and audit activity.

---

## 2. Design Goals & Principles
| Goal | Why it matters | Success Metric |
|------|----------------|----------------|
| **Clarity** – all contract data must be instantly readable. | Users need confidence in the escrow timeline. | < 2‑second time‑to‑understand for any dashboard view. |
| **Trust & Transparency** – show escrow hold, countdown, and proof‑of‑work receipts. | Reduces friction around PayPal hold. | 90 %+ of users report feeling “in control”. |
| **Responsiveness** – work on desktop, tablet, and limited mobile. | Stakeholders may view contracts on the go. | No layout breakage at 320 px–1920 px. |
| **Consistency** – reuse component library and Bryntum styling. | Faster dev & easier hand‑off to designers. | < 5% UI‑related bugs after release. |
| **Accessibility (WCAG AA)** – color contrast, keyboard navigation, ARIA labels. | Legal compliance & inclusive UX. | Passed automated axe audit. |

---

## 3. Visual Identity (Figma Prompt)
```
Prompt for Figma:
Create a design system for a SaaS contract‑management portal called "PactPal". Use a modern, professional aesthetic with the following palette:
- Primary: #0066FF (blue) – action buttons, links, Gantt bars.
- Secondary: #00A3E0 (lighter blue) – hover states, tags.
- Accent: #FF9800 (orange) – PayPal hold countdown badge, warning alerts.
- Success: #4CAF50 (green) – passed task status.
- Warning: #F44336 (red) – failed task status.
- Neutral greys: #212121 (dark text), #424242 (secondary text), #F5F5F5 (background), #FFFFFF (cards).
Typography: Inter, 14 pt body, 16 pt headings, 20 pt section titles.
Components: Card, Table, Form Input, Modal, Badge, Avatar, Timeline (Bryntum Gantt), Scheduler, Chat bubble, Activity Feed, Tooltip, Dropdown, Pagination.
Create wireframes for the following screens (full‑width desktop, tablet breakpoint at 768 px):
1. Contract Creation Wizard (multi‑step modal).
2. Contract Dashboard (status badge, escrow hold indicator, countdown timer, quick‑action bar).
3. Gantt Chart view (Bryntum Gantt with color‑coded tasks, zoom controls, filter panel).
4. Negotiation Chat (split view: chat on right, task list on left).
5. Verification Activity Feed (vertical feed with icons for each stage A‑F).
6. Proof‑of‑Work Receipt view (card with SHA‑256 fingerprint, test coverage chart, PayPal reference link).
Add interactive prototypes for the countdown timer (animates from 29 days to 0) and for the task‑status toggle (pending → passed → failed). Include component library symbols on a separate page.
Export all frames as Figma design system file.
``` 
```

---

## 4. Information Architecture (Pages & Navigation)
```
+-------------------+--------------------------+
| Top‑level Nav     | Route (React Router)     |
+-------------------+--------------------------+
| Dashboard         | /dashboard               |
| Contracts         | /contracts               |
|   • Create New    | /contracts/new           |
|   • Detail View   | /contracts/:id           |
|   • Gantt Chart   | /contracts/:id/gantt      |
|   • Receipt       | /contracts/:id/receipt    |
| Chat / Negotiation| /contracts/:id/chat      |
| Activity Feed     | /activity                |
| Admin Settings    | /admin (admin only)      |
+-------------------+--------------------------+
```
- **Side bar (collapsed on mobile)** containing icons + labels.
- **Breadcrumb** on detail pages for deep linking.
- **Global Search** (top‑right) for contracts by ID, buyer, or seller.

---

## 5. Core UI Components & Their Props (Figma & Development Mapping)
| Component | Props / Variants | Description |
|-----------|-------------------|-------------|
| **Button** | `variant: primary | secondary | disabled`<br>`size: sm | md | lg` | Standard CTA, used for “Create Contract”, “Send Message”, etc. |
| **Badge** | `type: escrow | status | countdown`<br>`color: primary | accent | success | warning` | Shows escrow hold, contract state, or countdown timer. |
| **Card** | `elevated: true|false`<br>`interactive: true|false` | Wraps Gantt, receipt, or activity items. |
| **Table** | `columns`, `sortable`, `filterable` | Contract list, task list. |
| **Modal / Wizard** | `steps` (array), `currentStep` | Multi‑step contract creation wizard. |
| **Bryntum Gantt** | `tasks`, `dependencies`, `highlightedDays`, `zoomLevel` | Integrated via React wrapper; task colors reflect status. |
| **Scheduler** | `events`, `resourceColumns` | Calendar view for deadlines. |
| **ChatBubble** | `author`, `timestamp`, `type: message|system` | Negotiation chat. |
| **ActivityItem** | `stage (A‑F)`, `icon`, `timestamp`, `detail` | Feed item. |
| **ReceiptCard** | `hash`, `coverageChart`, `paypalLink` | Proof‑of‑work view.

---

## 6. User Flows (High‑Level)
### 6.1 Contract Creation (Buyer)
1. Click **Create Contract** CTA → opens **Contract Creation Wizard** (modal). 
2. Step 1: **Basic Info** – parties, title, start/end dates. 
3. Step 2: **Feature Checklist** – add measurable acceptance tests + weighted pricing. 
4. Step 3: **Escrow Settings** – PayPal hold (auto‑set 29 days). 
5. Review summary → **Submit**. 
6. System creates contract, redirects to **Contract Dashboard**.

### 6.2 Contract Dashboard (All roles)
- Top bar: contract title, status badge, escrow hold indicator, countdown timer.
- Left pane: **Navigation tabs** – Overview, Gantt, Chat, Activity, Receipt.
- Main pane: contextual view (default Overview).
- Action button (right): **Edit**, **Release Escrow**, **Add Task** (seller only).

### 6.3 Gantt Interaction (Seller)
- Tasks displayed as horizontal bars; color‑coded (pending‑gray, passed‑green, failed‑red).
- Hover → tooltip with test coverage, due date.
- Drag‑to‑reschedule → opens **Reschedule Modal** (only for pending tasks).
- Filter panel (top) to show tasks by status.

### 6.4 Negotiation Chat (Buyer ↔ Seller)
- Split view: left side **Task List** (filterable), right side **Chat window**.
- Send message → system logs as **ChatBubble** with timestamp.
- “Request Change” button on a task opens a **Mini‑Agreement Modal** that creates a new sub‑task.

### 6.5 Verification & Receipt (Admin/Seller)
- Activity Feed shows stages A‑F with icons and timestamps.
- After final stage, **Proof‑of‑Work Receipt** auto‑generates:
  - SHA‑256 fingerprint of the contract bundle.
  - Pie chart of test coverage (passed/failed).
  - PayPal reference link (click opens PayPal UI).

---

## 7. Responsive Layout Guidelines
| Breakpoint | Layout Adjustments |
|------------|-------------------|
| **≥ 1280 px** | Full‑width two‑column dashboard; Gantt occupies 70 % width. |
| **768‑1279 px** | Sidebar collapses to icons; dashboard switches to single column with tabs. |
| **≤ 767 px** | Mobile‑first view: hamburger menu, vertical stacking, Gantt replaced by **Scheduler** list view. |

---

## 8. Accessibility Checklist
- **Color contrast** ≥ 4.5:1 (use provided palette). 
- **Keyboard navigation**: All interactive elements reachable via Tab; focus indicator visible. 
- **ARIA labels** for custom components (Gantt bars, chat bubbles). 
- **Screen‑reader friendly**: Provide `role="region"` and descriptive `aria‑label` for charts. 
- **Responsive font scaling** (rem units). 

---

## 9. Assets & Export Requirements for Figma
| Asset | Format | Size/Scale |
|-------|--------|-----------|
| Icons (status, stage) | SVG | 24 px (default) |
| Logos (PactPal) | SVG & PNG | 1×, 2×, 3× |
| Illustration for onboarding | PNG (transparent) | 1280 × 720 |
| Font files (Inter) | OTF/WOFF2 | – |
| Color palette swatches | Figma Styles | – |
| Component library | Figma Components (symbols) | – |

---

## 10. Handoff Notes (Developer ↔ Designer)
- **Design tokens** (colors, spacing, radii) should be exported as JSON via Figma Tokens plugin.
- **Component naming** follows BEM‑like convention: `Button/Primary`, `Badge/Escrow`, `Card/Receipt`.
- **Gantt integration**: Use Bryntum’s React wrapper; expose task data via `tasks.json`. The design should include a placeholder `div#bryntum-gantt` with defined dimensions (full‑width, min‑height 500 px).
- **Animation spec** for countdown: linear decrease, flash when < 1 day.
- **Prototype flows**: Click on “Release Escrow” → modal confirmation → status badge changes to “Released”.

---

## 11. Open Questions (to refine later)
1. **Brand colors** – do we have a secondary accent beyond orange? 
2. **Logo variations** – need dark‑mode version? 
3. **Internationalization** – any RTL languages planned? 
4. **Payment gateway UI** – will PayPal UI be embedded or redirected? 

---

*This document is intended to be dropped directly into Figma as a design brief and into the codebase as the single source of truth for the front‑end UI/UX.*

