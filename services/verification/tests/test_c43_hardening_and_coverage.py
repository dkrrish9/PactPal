"""
Unit and Integration Tests for Container Hardening and Test Coverage Numbers in the Report (C43)
Validates Done Criteria:
  - "Coverage and security counts show up in the report"
  - Container hardening (network isolation, secret scrubbing, resource limits, directory traversal defense)
"""

import sys
import unittest
import uuid
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.verification.src.sandbox import (
    IsolatedWorkspace,
    WorkspaceSecurityError,
    FORBIDDEN_ENV_PREFIXES
)
from services.verification.src.report_assembler import ReportAssembler, CoverageAnalyzer
from services.verification.src.models import SubmissionRecord, VerificationReport
from services.verification.src.runner import VerificationPipelineRunner
from services.verification.src.github_notifier import GitHubFeedbackNotifier


class TestContainerHardeningAndReportCounts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.good_repo_dir = PROJECT_ROOT / "demo-assets" / "good-repo"
        cls.bad_repo_dir = PROJECT_ROOT / "demo-assets" / "bad-repo"
        cls.figma_dir = PROJECT_ROOT / "demo-assets" / "figma"

    def setUp(self):
        self.assembler = ReportAssembler()
        self.runner = VerificationPipelineRunner(figma_reference_dir=self.figma_dir)
        self.contract_id = f"cnt_{uuid.uuid4().hex[:8]}"
        self.seller_id = f"usr_{uuid.uuid4().hex[:8]}"

    def _create_submission(self, repo_dir: Path, sub_num: int = 1) -> SubmissionRecord:
        return SubmissionRecord(
            id=str(uuid.uuid4()),
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(repo_dir),
            commit_sha="c43_test_sha",
            build_notes="Testing container hardening and report numbers",
            submission_number=sub_num,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

    # -------------------------------------------------------------------------
    # 1. Container Hardening Tests (C43)
    # -------------------------------------------------------------------------
    def test_container_hardening_environment_network_isolation(self):
        """Verifies container environment enforces air-gapped/offline network isolation."""
        with IsolatedWorkspace() as ws:
            env = ws.clean_env
            self.assertEqual(env.get("PACTPAL_NETWORK_ISOLATED"), "true")
            self.assertEqual(env.get("npm_config_offline"), "true")
            self.assertEqual(env.get("npm_config_audit"), "false")
            self.assertEqual(env.get("PIP_NO_INDEX"), "true")
            self.assertEqual(env.get("DOTNET_CLI_TELEMETRY_OPTOUT"), "1")
            self.assertEqual(env.get("NEXT_TELEMETRY_DISABLED"), "1")

    def test_container_hardening_secret_scrubbing_and_counts(self):
        """Verifies container environment scrubs forbidden platform credentials and tracks count."""
        with IsolatedWorkspace() as ws:
            profile = ws.get_hardening_profile()
            self.assertTrue(profile["container_hardened"])
            self.assertTrue(profile["network_isolated"])
            self.assertTrue(profile["offline_mode_enforced"])
            self.assertTrue(profile["secret_scrubbing"]["active"])
            self.assertGreaterEqual(profile["secret_scrubbing"]["scrubbed_variables_count"], 0)
            self.assertEqual(profile["security_policy"], "ZERO_TRUST_AIR_GAPPED")

            # Assert zero forbidden platform keys exist in clean_env
            for key in ws.clean_env:
                k_upper = key.upper()
                for prefix in FORBIDDEN_ENV_PREFIXES:
                    self.assertFalse(k_upper.startswith(prefix), f"Forbidden key leaked: {key}")

    def test_container_hardening_path_traversal_blocked(self):
        """Verifies attempts to escape workspace via path traversal are blocked."""
        with IsolatedWorkspace() as ws:
            with self.assertRaises(WorkspaceSecurityError) as ctx:
                ws.execute_command(["dir"], cwd_relative="../../Windows")
            self.assertIn("Directory traversal attempt detected", str(ctx.exception))

    def test_container_hardening_exfiltration_detection(self):
        """Verifies heuristic and rule checks detect network exfiltration or probe commands."""
        with IsolatedWorkspace() as ws:
            clean_output = "Build succeeded with 5 tests passing."
            res_clean = ws.scan_logs_for_exfiltration_attempts(clean_output)
            self.assertEqual(res_clean["exfiltration_risk"], "LOW")
            self.assertEqual(len(res_clean["suspicious_probes_detected"]), 0)

            probe_output = "Attempting curl http://169.254.169.254/latest/meta-data/ and reading /etc/shadow"
            res_probe = ws.scan_logs_for_exfiltration_attempts(probe_output)
            self.assertEqual(res_probe["exfiltration_risk"], "HIGH")
            self.assertGreater(len(res_probe["suspicious_probes_detected"]), 0)

    # -------------------------------------------------------------------------
    # 2. Done Criteria: Coverage and Security Counts Show Up in the Report
    # -------------------------------------------------------------------------
    def test_coverage_numbers_show_up_in_report(self):
        """Done Criteria: Code coverage numbers show up prominently in the VerificationReport."""
        sub = self._create_submission(self.good_repo_dir)
        report = self.runner.run_pipeline(submission=sub, capture_screenshots=False, notify_seller=False)

        # 1. Coverage summary exists on report
        self.assertIsNotNone(report.coverage_summary)
        cov = report.coverage_summary

        # 2. Core coverage numbers are present and valid
        self.assertIn("total_lines", cov)
        self.assertIn("covered_lines", cov)
        self.assertIn("uncovered_lines", cov)
        self.assertIn("coverage_percentage", cov)
        self.assertIn("threshold", cov)
        self.assertIn("status", cov)
        self.assertIn("meets_threshold", cov)
        self.assertIn("modules_count", cov)

        self.assertGreater(cov["total_lines"], 0)
        self.assertGreater(cov["covered_lines"], 0)
        self.assertEqual(cov["total_lines"], cov["covered_lines"] + cov["uncovered_lines"])
        self.assertGreaterEqual(cov["coverage_percentage"], 80.0)
        self.assertTrue(cov["meets_threshold"])
        self.assertEqual(cov["status"], "SATISFACTORY")
        self.assertGreater(cov["modules_count"], 0)

        # 3. Report serialization retains coverage numbers
        report_dict = report.to_dict()
        self.assertIn("coverage_summary", report_dict)
        self.assertEqual(report_dict["coverage_summary"]["coverage_percentage"], cov["coverage_percentage"])

    def test_security_counts_show_up_in_report_good_repo(self):
        """Done Criteria: Security counts show up in report for a clean repository."""
        sub = self._create_submission(self.good_repo_dir)
        report = self.runner.run_pipeline(submission=sub, capture_screenshots=False, notify_seller=False)

        # 1. Security counts exist on report
        self.assertIsNotNone(report.security_counts)
        counts = report.security_counts

        # 2. Validate counts structure
        self.assertIn("total_security_findings", counts)
        self.assertIn("total_cheat_findings", counts)
        self.assertIn("by_severity", counts)
        self.assertIn("critical_count", counts)
        self.assertIn("high_count", counts)
        self.assertIn("medium_count", counts)
        self.assertIn("low_count", counts)
        self.assertIn("clean", counts)

        # Good repo should have 0 security findings and clean=True
        self.assertEqual(counts["total_security_findings"], 0)
        self.assertEqual(counts["critical_count"], 0)
        self.assertEqual(counts["high_count"], 0)
        self.assertEqual(counts["medium_count"], 0)
        self.assertEqual(counts["low_count"], 0)
        self.assertTrue(counts["clean"])

        # 3. Report serialization retains security counts
        report_dict = report.to_dict()
        self.assertIn("security_counts", report_dict)
        self.assertEqual(report_dict["security_counts"]["total_security_findings"], 0)

    def test_security_counts_show_up_in_report_bad_repo(self):
        """Done Criteria: Security counts show up in report for a repository with cheat/loopholes."""
        sub = self._create_submission(self.bad_repo_dir)
        report = self.runner.run_pipeline(submission=sub, capture_screenshots=False, notify_seller=False)

        self.assertIsNotNone(report.security_counts)
        counts = report.security_counts

        # Bad repo contains hardcoded answers and cheats
        self.assertGreater(counts["total_security_findings"], 0)
        self.assertFalse(counts["clean"])
        self.assertGreater(counts["high_count"], 0)
        self.assertIn("CRITICAL", counts["by_severity"])
        self.assertIn("HIGH", counts["by_severity"])
        self.assertGreaterEqual(counts["by_severity"]["HIGH"], 1)

        # Serialized dict has security counts
        report_dict = report.to_dict()
        self.assertIn("security_counts", report_dict)
        self.assertEqual(report_dict["security_counts"]["high_count"], counts["high_count"])

    def test_container_hardening_shows_up_in_report(self):
        """Verifies container hardening profile is saved with the report."""
        sub = self._create_submission(self.good_repo_dir)
        report = self.runner.run_pipeline(submission=sub, capture_screenshots=False, notify_seller=False)

        self.assertIsNotNone(report.container_hardening)
        hardening = report.container_hardening
        self.assertTrue(hardening["container_hardened"])
        self.assertTrue(hardening["network_isolated"])
        self.assertEqual(hardening["security_policy"], "ZERO_TRUST_AIR_GAPPED")

        # Serialized dictionary retains container hardening
        report_dict = report.to_dict()
        self.assertIn("container_hardening", report_dict)
        self.assertTrue(report_dict["container_hardening"]["container_hardened"])

    def test_seller_feedback_markdown_displays_coverage_and_security_counts(self):
        """Verifies seller feedback comment incorporates coverage numbers, security counts, and hardening."""
        notifier = GitHubFeedbackNotifier()
        sub = self._create_submission(self.bad_repo_dir)
        report = self.runner.run_pipeline(submission=sub, capture_screenshots=False, notify_seller=False)

        md = notifier.format_referee_feedback_markdown(report=report, submission=sub)

        # Assert coverage numbers in markdown
        self.assertIn("Test Line Coverage", md)
        self.assertIn("Coverage Numbers", md)
        self.assertIn("Global Executable Line Coverage", md)

        # Assert security counts in markdown
        self.assertIn("Security & Loopholes", md)
        self.assertIn("Security & Cheat Scan Findings", md)
        self.assertIn("Container Hardening", md)

    def test_build_failure_report_contains_default_counts_and_hardening(self):
        """Verifies fast-track build failure reports populate coverage numbers, security counts, and hardening."""
        failure_rep = VerificationReport.create_build_failure_report(
            submission_id="sub_fail_1",
            contract_id=self.contract_id,
            build_logs="Syntax error on line 42",
            failure_reason="SyntaxError: unexpected token",
            features=[{"id": "feat1", "title": "Feature 1", "price_weight": 100.0, "allocated_amount": 500.0}]
        )

        self.assertIsNotNone(failure_rep.coverage_summary)
        self.assertEqual(failure_rep.coverage_summary["coverage_percentage"], 0.0)
        self.assertEqual(failure_rep.coverage_summary["status"], "UNAVAILABLE")

        self.assertIsNotNone(failure_rep.security_counts)
        self.assertEqual(failure_rep.security_counts["total_security_findings"], 0)
        self.assertTrue(failure_rep.security_counts["clean"])

        self.assertIsNotNone(failure_rep.container_hardening)
        self.assertTrue(failure_rep.container_hardening["container_hardened"])


if __name__ == "__main__":
    unittest.main()
