# Failed Build, Late Submission, and Resubmission Limit Scenarios (C53)

## 1. Overview
Task **C53** introduces end-to-end scenario verification covering the three primary exceptional lifecycle conditions in the verification pipeline:
1. **Failed Build**: Compilation or bundling failure during Stage B.
2. **Late Submission**: Deliverable submitted past the contractual milestone deadline.
3. **Resubmission Limit**: Maximum limit of 3 submissions reached, refusing the 4th attempt.

## 2. Done Criteria
- **Each produces the expected report and decision**:
  - **Failed Build**: Generates a fast-track `VerificationReport` with `build_succeeded = False`, `overall_score = 0.0`, downstream stages skipped, per-feature results flagged `FAILED`, and decision `recommendation = "REJECT_AND_HOLD"` (`next_state = "DECISION"`).
  - **Late Submission**: Evaluates delivery timing against the contract deadline, flags `is_late = True`, computes `delay_seconds`, populates `timing_compliance` in the report, notes delay in `git_metadata`, and tags seller notifications with `⚠️ Late Submission`.
  - **Resubmission Limit**: Attempts 1–3 are accepted with sequential version labels (`v1`, `v2`, `v3`) and full reports; attempt 4 is refused with structured refusal payload (`status: REFUSED`, `error: SUBMISSION_LIMIT_EXCEEDED`, `next_action: DISPUTE_REVIEW`).

---

## 3. Scenarios & Expected Behavior

### 3.1 Failed Build Scenario
- **Trigger**: Source code with compilation, bundling, or syntax errors (e.g. `fixtures/broken-repo`).
- **Expected Report**:
  ```json
  {
    "build_succeeded": false,
    "overall_score": 0.0,
    "failure_reason": "Build failed during 'node build.js': Syntax error in source code...",
    "skipped_stages": ["STAGE_C_TESTS", "STAGE_D_CHEAT_SCAN", "STAGE_E_VISUAL_DIFF"],
    "per_feature_results": {
      "feat_auth": { "status": "FAILED", "severity": "HIGH", "reason": "Build failed..." }
    },
    "container_hardening": { "container_hardened": true }
  }
  ```
- **Expected Decision**:
  - `next_state`: `"DECISION"`
  - `recommendation`: `"REJECT_AND_HOLD"` (blocks escrow release, holding funds pending seller fix or dispute).

### 3.2 Late Submission Scenario
- **Trigger**: Seller submits deliverable timestamp after contractual deadline.
- **Expected Report**:
  ```json
  {
    "timing_compliance": {
      "is_late": true,
      "delay_seconds": 18900,
      "status": "LATE",
      "deadline": "2026-11-10T18:15:00+00:00"
    }
  }
  ```
- **Expected Decision**:
  - Seller notification warns: `⚠️ Late Submission`.
  - Report tracks delivery non-compliance for AI Referee review.

### 3.3 Resubmission Limit Scenario
- **Trigger**: Seller attempts a 4th submission after already submitting 3 revisions.
- **Expected Report & Decision for Attempts 1–3**:
  - Status: `"ACCEPTED"`
  - Version labels: `"v1"`, `"v2"`, `"v3"`
  - Normal pipeline report generated.
- **Expected Decision for Attempt 4**:
  ```json
  {
    "status": "REFUSED",
    "accepted": false,
    "error": "SUBMISSION_LIMIT_EXCEEDED",
    "attempt_number": 4,
    "max_allowed": 3,
    "next_action": "DISPUTE_REVIEW",
    "message": "Fourth resubmission is refused: Contract '...' has already reached the maximum allowable limit of 3 submissions..."
  }
  ```

---

## 4. Test Suite Reference
Maintained in `services/verification/tests/test_c53_verification_scenarios.py`:
- `test_failed_build_produces_expected_report_and_decision`
- `test_late_submission_produces_expected_report_and_decision`
- `test_resubmission_limit_produces_expected_report_and_decision`
- `test_combined_lifecycle_failed_build_to_late_resubmission_to_limit`
