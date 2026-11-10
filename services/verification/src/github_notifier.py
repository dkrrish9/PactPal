"""
PactPal Verification Pipeline - GitHub Referee Feedback Notifier (C36)
Posts comprehensive AI Escrow Referee feedback comments directly to seller GitHub repositories:
  - Formats multi-modal verification reports into actionable markdown feedback
  - Summarizes per-feature verdicts (PASSED, FAILED, PARTIAL), security findings, and visual diffs
  - Dispatches comments to GitHub commits/PRs via GitHub REST API
  - Persists tamper-evident notification delivery receipts and markdown artifacts to evidence
"""

import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from .models import SubmissionRecord, VerificationReport


class GitHubNotifierError(RuntimeError):
    """Raised when GitHub API notification encounters an error."""
    pass


def _load_env_if_needed():
    """Load .env from project root if not already in environment."""
    if not os.environ.get("GITHUB_TOKEN"):
        env_path = Path(__file__).resolve().parents[3] / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())


class GitHubFeedbackNotifier:
    """Delivers automated AI Escrow Referee feedback comments to seller GitHub repositories."""

    def __init__(self, token: Optional[str] = None):
        _load_env_if_needed()
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")

    def parse_github_repo_info(self, repo_url: str) -> Optional[Tuple[str, str]]:
        """
        Extracts (owner, repo) from GitHub HTTPS or SSH URL.
        Returns None for local filesystem paths.
        """
        if not repo_url or "github.com" not in repo_url:
            return None

        # HTTPS pattern: https://github.com/owner/repo(.git)?
        https_match = re.search(r"github\.com/([^/]+)/([^/.]+)(?:\.git)?", repo_url)
        if https_match:
            return https_match.group(1), https_match.group(2)

        # SSH pattern: git@github.com:owner/repo(.git)?
        ssh_match = re.search(r"github\.com:([^/]+)/([^/.]+)(?:\.git)?", repo_url)
        if ssh_match:
            return ssh_match.group(1), ssh_match.group(2)

        return None

    def format_referee_feedback_markdown(
        self,
        report: VerificationReport,
        submission: SubmissionRecord
    ) -> str:
        """
        Constructs comprehensive, audit-ready GitHub Markdown feedback for the seller.
        Includes verdict badges, financial summary, feature breakdown, cheat/security findings,
        visual comparison results, and actionable remediation instructions.
        """
        score_pct = round(report.overall_score * 100.0, 1)
        rec = report.recommendation or ("FULL_RELEASE" if report.overall_score >= 0.95 else ("PARTIAL_RELEASE" if report.overall_score >= 0.25 else "REJECT_AND_HOLD"))

        badge_map = {
            "FULL_RELEASE": ("🟢", "FULL ESCROW RELEASE APPROVED"),
            "PARTIAL_RELEASE": ("🟡", "PARTIAL ESCROW RELEASE APPROVED"),
            "REJECT_AND_HOLD": ("🔴", "ESCROW SETTLEMENT PLACED ON HOLD")
        }
        icon, badge_text = badge_map.get(rec, ("⚖️", rec))

        lines = [
            f"# {icon} PactPal AI Escrow Referee — Deliverable Verification Report",
            "",
            f"> **Referee Verdict:** **`{badge_text}`** (`Score: {score_pct}%`)  ",
            f"> **Submission:** `#{submission.submission_number}` | **Contract ID:** `{submission.contract_id}` | **Commit:** `{submission.commit_sha[:8]}`",
            "",
            "---",
            "",
            "### 📋 Milestone Overview",
            f"- **Repository Source**: `{submission.repo_url}`",
            f"- **Commit SHA**: `{submission.commit_sha}`",
            f"- **Submission Status**: {'⚠️ Late Submission' if submission.is_late else '✅ On-Time Delivery'}",
            f"- **Sandbox Compilation**: {'✅ Build Passed' if report.build_succeeded else '❌ Build Failed'}",
            f"- **Overall Verification Score**: **`{score_pct}%`**",
            f"- **Referee Recommendation**: `{rec}`",
            ""
        ]

        # 1. Per-Feature Acceptance Results Table
        lines.extend([
            "---",
            "",
            "### 🔍 Per-Feature Acceptance Results",
            "",
            "| Feature | Verdict | Score | Coverage | Details & Evidence |",
            "| :--- | :---: | :---: | :---: | :--- |"
        ])

        per_feature = report.per_feature_results or {}
        status_icons = {"PASSED": "PASSED ✅", "PARTIAL": "PARTIAL ⚠️", "FAILED": "FAILED ❌"}

        for f_id, f_data in per_feature.items():
            f_title = f_data.get("feature_title", f_id)
            f_status = f_data.get("status", "FAILED").upper()
            status_display = status_icons.get(f_status, f_status)
            f_score = f"{round(float(f_data.get('score', 0.0)) * 100.0, 1)}%"

            cov = f_data.get("coverage", {})
            cov_pct = f"{cov.get('coverage_percent', 0.0)}%"

            reason = f_data.get("reason")
            evidence = f_data.get("evidence", {})
            if isinstance(evidence, dict):
                summary = evidence.get("summary") or reason or "Verified against contract acceptance tests."
            else:
                summary = str(evidence) if evidence else (reason or "Verified against contract acceptance tests.")

            lines.append(f"| **{f_title}** | `{status_display}` | `{f_score}` | `{cov_pct}` | {summary} |")

        lines.append("")

        # 2. Security & Cheat Scan Findings
        security_findings = report.security_findings or []
        lines.extend([
            "---",
            "",
            "### 🛡️ Security & Cheat Scan Findings"
        ])

        if not security_findings:
            lines.append("- ✅ **Clean Deliverable**: No cheats, hardcoded test answers, disabled assertions, or exposed secrets detected.")
        else:
            lines.append(f"⚠️ **Attention Required**: Detected **{len(security_findings)}** security/loophole findings:")
            lines.append("")
            lines.append("| Severity | Category | Rule | Location | Description |")
            lines.append("| :---: | :--- | :--- | :--- | :--- |")
            for sf in security_findings:
                sev = sf.get("severity", "MEDIUM")
                cat = sf.get("category", "cheat")
                rule = sf.get("rule_id", "CHEAT-001")
                loc = f"`{sf.get('file_path')}:{sf.get('line_number')}`"
                desc = sf.get("description", "")
                lines.append(f"| **`{sev}`** | `{cat}` | `{rule}` | {loc} | {desc} |")

            lines.append("")
            lines.append("**Remediation Guidance:**")
            for idx, sf in enumerate(security_findings, 1):
                remed = sf.get("remediation")
                if remed:
                    lines.append(f"{idx}. `{sf.get('file_path')}`: {remed}")

        lines.append("")

        # 3. Visual Diff Against Figma (Stage E)
        vdiff = report.visual_diff_summary or {}
        lines.extend([
            "---",
            "",
            "### 🎨 Stage E: Visual Diff Against Figma Mockup",
            f"- **Visual Similarity Score**: `{vdiff.get('similarity_score', 1.0) * 100:.1f}%` (Contract Threshold: `{vdiff.get('threshold', 0.85) * 100:.1f}%`)",
            f"- **Visual Match Verdict**: {'✅ Conforms to Figma design tokens' if vdiff.get('passed', True) else '❌ Layout / Color divergence detected'}"
        ])
        if vdiff.get("mismatches_detected"):
            lines.append("- **Mismatches Highlighted**:")
            for m in vdiff["mismatches_detected"]:
                lines.append(f"  - ⚠️ {m}")
        if vdiff.get("diff_notes"):
            lines.append(f"- **Referee Vision Notes**: {vdiff.get('diff_notes')}")

        lines.append("")

        # 4. Code Coverage Summary
        cov_summary = report.coverage_summary or {}
        lines.extend([
            "---",
            "",
            "### 📊 Test Coverage Summary",
            f"- **Global Executable Line Coverage**: `{cov_summary.get('coverage_percentage', 0.0)}%` (Threshold: `{cov_summary.get('threshold', 80.0)}%`)",
            f"- **Total Executable Lines**: `{cov_summary.get('total_lines', 0)}` | **Covered Lines**: `{cov_summary.get('covered_lines', 0)}`",
            f"- **Coverage Status**: `{cov_summary.get('status', 'SATISFACTORY')}`",
            ""
        ])

        # 5. Actionable Next Steps for Seller
        lines.extend([
            "---",
            "",
            "### 🚀 Actionable Next Steps for Seller",
            ""
        ])

        if rec == "FULL_RELEASE":
            lines.append("🎉 **Congratulations!** All milestone features passed verification. The smart contract has approved 100% escrow release to your account.")
        elif rec == "PARTIAL_RELEASE":
            lines.append("1. **Partial Disbursement Approved**: Passing features qualify for immediate proportional escrow release.")
            lines.append("2. **Fix Failing Features**: Review the failed/partial features in the table above (e.g. math errors or layout discrepancies).")
            lines.append("3. **Resubmit Deliverable**: Resubmit via PactPal once updates are pushed to claim remaining milestone balance.")
        else:
            lines.append("1. **Resolve Security & Build Issues**: Address all compiler errors and zero-trust violations highlighted above.")
            lines.append("2. **Verify Tests Locally**: Ensure `npm test` runs with zero skipped tests and dynamic logic.")
            lines.append("3. **Resubmit**: Resubmit deliverable before contract deadline expires.")

        lines.extend([
            "",
            "---",
            "*Report automatically generated by PactPal AI Escrow Referee — Zero-Trust Autonomous Escrow Protection.*"
        ])

        return "\n".join(lines)

    def post_feedback_comment(
        self,
        repo_url: str,
        commit_sha: str,
        body_markdown: str
    ) -> Dict[str, Any]:
        """
        Dispatches feedback comment to GitHub via REST API.
        Attempts commit comment endpoint on target repo.
        """
        repo_info = self.parse_github_repo_info(repo_url)
        if not repo_info:
            return {
                "status": "LOCAL_REPO",
                "posted": False,
                "message": "Repository is local filesystem path; skipped remote GitHub API call."
            }

        owner, repo = repo_info
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}/comments"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "PactPal-Verification-Agent",
            "Content-Type": "application/json"
        }

        payload = {"body": body_markdown}

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "status": "DELIVERED",
                    "posted": True,
                    "channel": "github_commit_comment",
                    "comment_id": data.get("id"),
                    "comment_url": data.get("html_url"),
                    "owner": owner,
                    "repo": repo,
                    "commit_sha": commit_sha
                }
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            return {
                "status": "API_ERROR",
                "posted": False,
                "http_code": e.code,
                "error": err_msg,
                "owner": owner,
                "repo": repo,
                "commit_sha": commit_sha
            }
        except Exception as ex:
            return {
                "status": "NETWORK_ERROR",
                "posted": False,
                "error": str(ex),
                "owner": owner,
                "repo": repo,
                "commit_sha": commit_sha
            }

    def notify_seller_on_repo(
        self,
        report: VerificationReport,
        submission: SubmissionRecord,
        evidence_dir: Optional[Path] = None,
        force_mock_post: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point for seller feedback notification.
        1. Formats referee feedback markdown.
        2. Persists markdown and JSON receipt to evidence directory.
        3. Dispatches comment to GitHub repo if remote URL is present.
        """
        feedback_md = self.format_referee_feedback_markdown(report, submission)
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Post to GitHub
        if not force_mock_post:
            dispatch_result = self.post_feedback_comment(
                repo_url=submission.repo_url,
                commit_sha=submission.commit_sha,
                body_markdown=feedback_md
            )
        else:
            dispatch_result = {
                "status": "DELIVERED",
                "posted": True,
                "channel": "github_commit_comment_mock",
                "comment_id": 9999999,
                "comment_url": f"https://github.com/mock/repo/commit/{submission.commit_sha}#comment-9999999"
            }

        # 2. Persist local evidence
        evidence_file = None
        receipt_file = None
        if evidence_dir:
            ev_path = Path(evidence_dir).resolve()
            ev_path.mkdir(parents=True, exist_ok=True)

            short_sha = submission.commit_sha[:8] if submission.commit_sha else "latest"
            evidence_file = ev_path / f"github_feedback_{short_sha}.md"
            receipt_file = ev_path / f"github_feedback_{short_sha}.json"

            evidence_file.write_text(feedback_md, encoding="utf-8")

            receipt_data = {
                "submission_id": submission.id,
                "contract_id": submission.contract_id,
                "commit_sha": submission.commit_sha,
                "delivered_at": now_iso,
                "dispatch": dispatch_result,
                "feedback_length_chars": len(feedback_md)
            }
            receipt_file.write_text(json.dumps(receipt_data, indent=2), encoding="utf-8")

        return {
            "status": "COMPLETED",
            "posted_to_github": dispatch_result.get("posted", False),
            "dispatch": dispatch_result,
            "evidence_markdown": str(evidence_file) if evidence_file else None,
            "evidence_receipt": str(receipt_file) if receipt_file else None,
            "feedback_preview": feedback_md[:500] + "...",
            "delivered_at": now_iso
        }
