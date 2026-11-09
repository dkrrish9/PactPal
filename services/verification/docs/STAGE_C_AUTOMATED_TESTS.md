# Stage C: Automated Tests & Feature Mapping (`services/verification`)

## Overview
Stage C runs after Stage B has verified a clean sandbox build. It executes automated unit, integration, and acceptance tests inside the isolated container and maps the results feature-by-feature against the locked contract checklist items.

---

## Key Responsibilities

1. **Native Project Test Execution**:
   - Automatically detects and runs native test suites (`npm test`, `node test/runner.js`, `pytest`).
   - Parses outputs into total, passed, and failed test metrics with execution duration.
2. **AI Acceptance Test Validation**:
   - Translates plain-language acceptance test criteria from the contract into code verification checks.
   - Leverages **Google Gemini API** (`GEMINI_API_KEY`) to inspect whether implementation files genuinely satisfy the client's acceptance criteria, with deterministic AST/semantic fallback.
3. **Per-Feature Pass/Fail Mapping**:
   - Every contract feature is evaluated independently and assigned:
     - `status`: `"PASSED"` | `"FAILED"`
     - `price_weight`: The feature's percentage weight from the contract checklist.
     - `allocated_amount`: The dollar amount held in escrow for this feature.
     - `severity`: `"NONE"` for passing features, `"HIGH"` or `"MEDIUM"` for failing features.
     - `evidence`: Detailed execution logs and code verification notes.
     - `reason`: Null if passed, or specific defect summary if failed.
4. **Proportional Release Scoring**:
   - Calculates the milestone release score based on the sum of weights for passed features:
     $$\text{overall\_score} = \frac{\sum_{\text{passed features}} \text{price\_weight}}{100}$$

---

## Verification Results (C23)

Implemented in [`services/verification/src/test_runner.py`](file:///d:/PactPal/services/verification/src/test_runner.py) and benchmarked using [`demo-assets/good-repo`](file:///d:/PactPal/demo-assets/good-repo/):

- [x] **Native Test Execution**: All 4 native test suites in `good-repo` executed and passed 100%.
- [x] **Per-Feature Mapping for Good Repo**: All 4 features mapped to `status = "PASSED"` with `severity = "NONE"` and `overall_score = 1.0` (100%).
- [x] **Proportional Weighted Payout Validation**: When 1 feature fails (20% weight), the other 3 features pass and `overall_score` strictly equals `0.80` (80.0%), enabling accurate partial releases.
- [x] **25/25 Tests Passing**: Full verification test suite green in 3.10s.
