# Stage G: GitHub Seller Feedback & Notification (`services/verification`)

## Overview
Commit **`C36`** delivers the automated feedback delivery mechanism that posts comprehensive AI Escrow Referee reports directly onto the seller's GitHub repository.

**Done Criteria:**
- Seller gets feedback on the repo (via GitHub Commit Comment / Pull Request Review and tamper-evident local evidence receipts).

---

## Capabilities & Architecture

Implemented in [`services/verification/src/github_notifier.py`](file:///d:/PactPal/services/verification/src/github_notifier.py):

1. **Rich Referee Markdown Formatting**:
   - **Verdict Badges**: `🟢 FULL ESCROW RELEASE APPROVED`, `🟡 PARTIAL ESCROW SETTLEMENT`, `🔴 ESCROW ON HOLD`.
   - **Milestone Overview**: Submission number, contract ID, commit SHA, build status, overall score.
   - **Per-Feature Acceptance Table**: Feature title, verdict (`PASSED ✅`, `FAILED ❌`, `PARTIAL ⚠️`), score, line coverage percentage, and evidence summaries.
   - **Security & Cheat Scan Findings**: Location, severity, code snippet, and remediation guidance for detected test bypasses or secret leaks.
   - **Figma Visual Comparison**: Similarity score vs threshold (e.g. 99.2% match vs 38.3% mismatch), color palette fidelity, and viewport layout details.
   - **Code Coverage Summary**: Total lines, covered lines, and global coverage percentage.
   - **Actionable Next Steps**: Clear guidance on settlement disbursement or required resubmission fixes.

2. **GitHub REST API Dispatch**:
   - Parses HTTPS / SSH GitHub URLs into `(owner, repo)`.
   - Posts comments directly to the submission commit via GitHub REST API:
     `POST https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}/comments`
   - Captures comment ID and permanent HTML URL (e.g. `#commitcomment-209228219`).

3. **Tamper-Evident Evidence Persistence**:
   - Writes `evidence/notifications/github_feedback_{commit_sha}.md` containing the complete markdown feedback.
   - Writes `evidence/notifications/github_feedback_{commit_sha}.json` containing the delivery dispatch receipt and timestamp.

---

## Verification & Live Proof

- Tested live against repository `dkrrish9/PactPal`:
  - Successfully posted comment: [Commit 0745dac Comment #209228219](https://github.com/dkrrish9/PactPal/commit/0745dacaca767b934916dc9bf8a6806bada3a605#commitcomment-209228219)
- All 55 verification unit and integration tests passing (`Ran 55 tests in 54.311s, OK`).
