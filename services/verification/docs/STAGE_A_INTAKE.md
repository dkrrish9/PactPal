# Stage A: Intake Specification (`services/verification`)

## Overview
Stage A (Intake) is the entry gate for all freelancer code deliverables submitted to PactPal. It validates, analyzes, and registers deliverables before dispatching them into isolated Render container sandboxes for build and multi-stage verification (Stages B through F).

---

## Key Responsibilities

1. **Input Validation**:
   - **Repository Link**: Validates public HTTPS, SSH, or local fixture Git URLs.
   - **Commit SHA**: Validates 7-to-64 hex characters or `HEAD` pointer.
2. **Deadline Comparison & `is_late` Flag**:
   - Compares submission UTC timestamp against contract deadline.
   - Calculates exact delay in seconds and human-readable formatting (e.g. `LATE: Submitted 3h 30m after deadline`).
3. **Resubmission Version Tracking**:
   - Manages version increments: Attempt 1 $\rightarrow$ 2 $\rightarrow$ 3.
   - Enforces the hard-stop limit of 3 submissions (`MAX_RESUBMISSION_ATTEMPTS = 3`). Attempt #4 is rejected with `SubmissionLimitExceededError`.
4. **AI-Powered Build Notes & Security Inspection**:
   - Interacts with Google Gemini API (`GEMINI_API_KEY`) to inspect seller notes and instructions.
   - Detects malicious directives (e.g. `curl`, `disable_tests`, unauthorized script injection).
   - Detects target framework and recommends safe build commands.
   - Assigns a risk assessment rating: `LOW`, `MEDIUM`, `HIGH`.
5. **Database Alignment**:
   - Generates immutable `SubmissionRecord` conforming to the database schema in `services/core-api/db/schema.sql` and the shared JSON schema in `shared/schemas/submission.json`.

---

## Verification Test Results (C11)

All 9 unit and integration tests passed:
```text
Ran 9 tests in 0.779s
OK
```
- [x] On-time submissions record `is_late = false` and `delay_seconds = 0`.
- [x] Late submissions calculate exact seconds overdue and record `is_late = true`.
- [x] Resubmissions sequence monotonically (1 $\rightarrow$ 2 $\rightarrow$ 3).
- [x] Resubmissions exceeding 3 are blocked.
- [x] Malformed URLs and invalid SHAs rejected with descriptive errors.
- [x] AI analysis flags suspicious evasion attempts in build notes.
- [x] Git commit inspection resolves commits and extracts author/log data.
