# Demo Assets (Linked Task: C22 / A9 / G1)

## Overview
Provides the standardized evaluation benchmark for the PactPal hackathon demo. Built around a realistic freelance deliverable with 4 distinct features.

---

## 1. Specification & Benchmark Architecture

| Feature ID | Feature Name | Expected Module | Good Repo Behavior | Bad Repo Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `feat_profile` | **Feature 1: User Profile Header** | `src/profile.js` | Returns full Alex Morgan profile & verified status. | Clean implementation (passes tests). |
| `feat_catalog` | **Feature 2: Product Catalog & Filter** | `src/catalog.js` | Filters real products array by category/rating. | **Flaw 2: Hardcoded fake answer** (`filterProducts` bypasses dataset and returns static mock objects; caught in Stage D Cheat Scan). |
| `feat_calculator` | **Feature 3: Escrow Milestone Calculator** | `src/calculator.js` | Calculates proportional payout and settled balance. | **Flaw 1: Broken Feature** (Divides by 10 instead of 100, fails test with sellerPayout 8000 instead of 800; caught in Stage C Tests). |
| `feat_contact` | **Feature 4: Dispute & Feedback Form** | `src/contact.js` | Validates email, subject, message lengths and sanitizes payload. | Clean implementation (passes tests). |

---

## 2. Directory Contents

### `figma/` (Client Design Blueprint)
- `design_tokens.json`: Official color palette (`#0F172A`, `#3B82F6`), fonts, padding, grid sizes.
- `reference_design.html`: HTML reference implementation matching the Figma specification.
- `reference_landing_1280x800.png`: Reference baseline screenshot for Stage E visual diff comparison.

### `good-repo/` (Honest Freelancer Deliverable)
- **Build**: `node build.js` packaging `dist/index.html` and bundled `dist/bundle.js`. Exit code `0`.
- **Tests**: `node test/runner.js` executes all 4 feature test suites. **4/4 PASS** (100%).
- **Visuals**: `src/index.html` strictly adheres to Figma tokens and layout. Visual similarity score > 95%.

### `bad-repo/` (Flawed Freelancer Deliverable)
- **Build**: `node build.js` packaging `dist/index.html` and bundled `dist/bundle.js`. Exit code `0`.
- **Flaw 1 (Broken Feature)**: `src/calculator.js` has a math bug, causing `node test/runner.js` to fail on Feature 3 with exit code `1`.
- **Flaw 2 (Cheat Attempt)**: `src/catalog.js` uses hardcoded static bypass returns to fool test assertions without dynamic logic (caught by Stage D Cheat Scan).
- **Flaw 3 (Visual Mismatch)**: `src/index.html` uses Comic Sans, neon pink (`#ff007f`) background, and distorted layout (visual match score < 40%, failing Stage E).

---

## 3. Verification Commands

```bash
# Verify Good Repo (Builds & All Tests Pass)
node demo-assets/good-repo/build.js
node demo-assets/good-repo/test/runner.js

# Verify Bad Repo (Builds cleanly, fails Feature 3 test as planned)
node demo-assets/bad-repo/build.js
node demo-assets/bad-repo/test/runner.js  # Expected exit code: 1
```
