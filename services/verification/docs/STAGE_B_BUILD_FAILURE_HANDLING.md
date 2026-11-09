# Stage B: Build Failure Handling & Fast-Track Reporting (`services/verification`)

## Overview
Under the PactPal Zero-Trust model, code deliverables from freelancers are executed in clean, isolated ephemeral containers. If a deliverable fails to build (e.g., compile error, broken syntax, missing dependencies, or non-zero exit code):
1. **Zero Process Crashes**: The platform runner intercepts the failure gracefully. The server never raises an uncaught exception or crashes.
2. **AI Failure Diagnostics**: The raw compiler stderr/stdout logs are analyzed by the AI Diagnostician (`AIIntakeEvaluator` / Gemini API) to extract the root cause, identify syntax errors or missing packages, and provide actionable remediation advice.
3. **Downstream Stages Skipped**: Stages C (test suites), D (cheat & loophole scan), and E (visual Figma diff) are skipped because an unbuildable project cannot produce runtime output or web pages.
4. **Fast-Track to DECISION**: All contract features are marked as `FAILED` with specific reasons, `overall_score = 0.0`, and the report is handed directly to the AI Referee in the `DECISION` state.
5. **Guaranteed Teardown**: The ephemeral container workspace is completely wiped from the host disk.

---

## Verification Results (C18)

Implemented in [`services/verification/src/runner.py`](file:///d:/PactPal/services/verification/src/runner.py) and verified in [`services/verification/tests/test_build_failure.py`](file:///d:/PactPal/services/verification/tests/test_build_failure.py):
- [x] Broken repository produces a complete `VerificationReport` with `build_succeeded = false` without crashing.
- [x] Raw compiler errors (e.g., `SyntaxError: Unexpected token "<<<"`) are analyzed and diagnosed by the AI evaluator.
- [x] All contract features are marked as `FAILED` with clear build-related failure explanations.
- [x] Downstream stages (`STAGE_C_TESTS`, `STAGE_D_CHEAT_SCAN`, `STAGE_E_VISUAL_DIFF`) are explicitly recorded as skipped.
- [x] Overall score is set to `0.0` and next contract lifecycle state is set to `DECISION`.
- [x] Ephemeral container is destroyed and wiped from disk.
