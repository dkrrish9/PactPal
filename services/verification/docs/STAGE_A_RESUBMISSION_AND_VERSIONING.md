# Resubmission Handling, Quota Enforcement, and Version Tracking (C39)

## 1. Overview
The **Resubmission Manager** (`services/verification/src/resubmission_manager.py`) manages the lifecycle of deliverable submissions and subsequent seller revisions. It enforces contractual guarantees on submission limits, assigns sequential version identifiers (`v1`, `v2`, `v3`), refuses invalid resubmissions once the quota is exhausted, and tracks historical progression across iterations.

## 2. Core Done Criteria
- **Fourth resubmission is refused**: Sellers may submit deliverables up to 3 times (Attempt 1, Attempt 2, Attempt 3). When a fourth submission is attempted, the request is immediately refused with `status: REFUSED`, error code `SUBMISSION_LIMIT_EXCEEDED`, and escrow is held pending AI Referee dispute review.
- **Versions are listed**: Contract submission history can be retrieved with discrete version records (`v1`, `v2`, `v3`), linked verification reports, overall scores, verdicts, and an active version indicator.

---

## 3. Architecture & Data Structures

### `SubmissionVersion` Dataclass
Represents an immutable version snapshot of a seller's deliverable:
- `version_label`: `'v1'`, `'v2'`, `'v3'`
- `submission_number`: `1`, `2`, `3`
- `submission_id`: Unique identifier
- `contract_id`: Target contract
- `seller_id`: Seller identity
- `repo_url`: Git repository URL
- `commit_sha`: Exact deliverable commit hash
- `submitted_at`: ISO timestamp
- `is_late` & `delay_seconds`: Delivery timing compliance
- `build_notes`: Seller build notes and instructions
- `report_id`: Associated verification report ID (if evaluated)
- `build_succeeded`: Boolean build status
- `overall_score`: 0.0 to 1.0 composite score
- `verdict`: Settlement verdict (`FULL_RELEASE`, `PARTIAL_RELEASE`, `REJECT_AND_HOLD`)
- `is_active`: True for the latest active submission iteration

---

## 4. Workflows

### 4.1 Resubmission Eligibility Check
```python
eligible, attempt_num, reason = resubmission_manager.check_resubmission_eligibility(
    contract_id="contract_123",
    existing_submissions=submissions_list
)
```
- When count < 3: `eligible = True`, returns remaining quota.
- When count >= 3: `eligible = False`, reason indicates refusal.

### 4.2 Handling Deliverable Submissions
```python
result = runner.handle_contract_submission(
    request=intake_request,
    existing_submissions=existing_submissions,
    features=feature_checklist,
    execute_verification=True
)
```
- **Attempts 1-3:**
  ```json
  {
    "status": "ACCEPTED",
    "accepted": true,
    "version_label": "v1",
    "attempt_number": 1,
    "attempts_remaining": 2,
    "submission": { ... },
    "report": { ... }
  }
  ```
- **Attempt 4 (Refusal):**
  ```json
  {
    "status": "REFUSED",
    "accepted": false,
    "error": "SUBMISSION_LIMIT_EXCEEDED",
    "message": "Fourth resubmission is refused: Contract '...' has already reached the maximum allowable limit of 3 submissions. Further submissions are locked pending dispute review.",
    "attempt_number": 4,
    "max_allowed": 3,
    "next_action": "DISPUTE_REVIEW"
  }
  ```

### 4.3 Listing Submission Versions
```python
versions_payload = runner.list_contract_versions(
    contract_id="contract_123",
    submissions=submissions_list,
    reports=reports_list
)
```
Returns:
```json
{
  "contract_id": "contract_123",
  "total_versions": 3,
  "max_allowed_submissions": 3,
  "remaining_submissions": 0,
  "can_resubmit": false,
  "active_version": "v3",
  "versions": [
    { "version_label": "v1", "overall_score": 0.65, "verdict": "PARTIAL_RELEASE", "is_active": false },
    { "version_label": "v2", "overall_score": 0.88, "verdict": "PARTIAL_RELEASE", "is_active": false },
    { "version_label": "v3", "overall_score": 0.98, "verdict": "FULL_RELEASE", "is_active": true }
  ]
}
```

### 4.4 Score Progression and Iteration Deltas
`compute_version_progress_summary(summary)` calculates score deltas between successive iterations to assist AI Referee deliberation.

---

## 5. Verification & Test Suite
Unit and integration tests are maintained in `services/verification/tests/test_resubmission.py`:
- `test_check_resubmission_eligibility_first_three_attempts`: Validates attempts 1, 2, 3 permitted.
- `test_check_resubmission_eligibility_fourth_refused`: Validates attempt 4 refusal.
- `test_handle_submission_request_progression_up_to_limit`: Registers v1, v2, v3.
- `test_handle_submission_request_fourth_resubmission_refused`: Checks refusal structure and dispute transition.
- `test_list_contract_submission_versions_with_reports`: Validates versions listed with reports, verdicts, and active version flag.
- `test_list_contract_versions_from_dictionaries`: Validates raw database dictionary row parsing.
- `test_compute_version_progress_summary`: Validates delta and improvement analysis.
- `test_runner_handle_contract_submission_refuses_fourth`: End-to-end runner refusal on attempt 4.
- `test_runner_list_contract_versions`: End-to-end runner version listing.
