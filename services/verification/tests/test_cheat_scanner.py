"""
Unit and Integration Tests for Stage D: Cheat & Loophole Scanner (C27)
Validates Done Criteria:
  - Hardcoded trick in the bad repo is flagged with HIGH severity
  - Good repo passes cheat scan with 0 high/critical findings
  - Detects disabled tests (it.skip, xit, commented-out assertions)
  - Detects placeholders (TODO, FIXME, lorem ipsum, not implemented stubs)
  - Detects dead UI elements (href='#', buttons without event handlers)
  - Detects exposed credentials (API keys, private keys, PATs) with CRITICAL severity
  - End-to-end VerificationPipelineRunner integration populates report.cheat_scan_findings
"""

import sys
import unittest
import uuid
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.verification.src.cheat_scanner import CheatScanner, CheatFinding
from services.verification.src.models import SubmissionRecord
from services.verification.src.runner import VerificationPipelineRunner


class TestCheatScanner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.good_repo_dir = PROJECT_ROOT / "demo-assets" / "good-repo"
        cls.bad_repo_dir = PROJECT_ROOT / "demo-assets" / "bad-repo"

    def setUp(self):
        self.scanner = CheatScanner()
        self.temp_repo_dir = Path(tempfile.mkdtemp(prefix="pactpal_cheat_test_"))

    def tearDown(self):
        shutil.rmtree(self.temp_repo_dir, ignore_errors=True)

    def test_bad_repo_hardcoded_trick_flagged_with_high_severity(self):
        """
        DONE CRITERIA (C27):
        Hardcoded trick in the bad repo (src/catalog.js) is flagged with HIGH severity.
        """
        scan_result = self.scanner.scan_repository(self.bad_repo_dir)

        self.assertEqual(scan_result["status"], "COMPLETED")
        self.assertFalse(scan_result["passed"], "Bad repo must fail cheat scan due to hardcoded trick!")
        self.assertTrue(scan_result["has_high_findings"], "Bad repo must trigger high-severity findings!")

        # Verify catalog.js finding details
        high_findings = scan_result["findings_by_severity"]["HIGH"]
        catalog_findings = [f for f in high_findings if "catalog.js" in f["file_path"]]
        self.assertGreater(len(catalog_findings), 0, "No cheat finding reported for catalog.js!")

        # Confirm category and severity
        hardcoded_finding = next(
            (f for f in catalog_findings if f["rule_id"] in ["CHEAT-HARDCODED-MOCK-002", "CHEAT-COMMENT-001"]),
            None
        )
        self.assertIsNotNone(hardcoded_finding, "Expected hardcoded mock or cheat rule match!")
        self.assertEqual(hardcoded_finding["severity"], "HIGH")
        self.assertEqual(hardcoded_finding["category"], "hardcoded_outputs")
        self.assertIn("catalog.js", hardcoded_finding["file_path"])

    def test_good_repo_passes_cheat_scan(self):
        """Verify good repo deliverable has 0 high/critical cheat findings and passes cleanly."""
        scan_result = self.scanner.scan_repository(self.good_repo_dir)

        self.assertEqual(scan_result["status"], "COMPLETED")
        self.assertTrue(scan_result["passed"], "Good repo deliverable must pass cheat scan!")
        self.assertFalse(scan_result["has_critical_findings"])
        self.assertFalse(scan_result["has_high_findings"])
        self.assertEqual(len(scan_result["findings_by_severity"]["CRITICAL"]), 0)
        self.assertEqual(len(scan_result["findings_by_severity"]["HIGH"]), 0)

    def test_detect_disabled_tests(self):
        """Verify scanner flags skipped tests and commented assertions with HIGH severity."""
        test_file = self.temp_repo_dir / "test" / "feature.test.js"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("""
describe('Escrow Feature', () => {
  it.skip('should release milestone payment', () => {
    // skipped test logic
  });

  it('should calculate dispute balance', () => {
    const balance = 100;
    // assert.equal(balance, 100);
  });
});
""", encoding="utf-8")

        result = self.scanner.scan_repository(self.temp_repo_dir)
        disabled_findings = result["findings_by_category"]["disabled_tests"]

        self.assertGreaterEqual(len(disabled_findings), 2)
        rules = [f["rule_id"] for f in disabled_findings]
        self.assertIn("TEST-SKIP-001", rules)
        self.assertIn("TEST-COMMENTED-ASSERT-002", rules)
        self.assertTrue(all(f["severity"] == "HIGH" for f in disabled_findings))

    def test_detect_placeholders_and_unfinished_stubs(self):
        """Verify scanner detects TODOs, lorem ipsum, and not implemented stubs."""
        src_file = self.temp_repo_dir / "src" / "payments.js"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("""
// TODO: implement refund webhook listener
function handleWebhook() {
  throw new Error("Not implemented");
}

const copy = "Lorem Ipsum dolor sit amet";
""", encoding="utf-8")

        result = self.scanner.scan_repository(self.temp_repo_dir)
        placeholder_findings = result["findings_by_category"]["placeholders"]

        self.assertGreaterEqual(len(placeholder_findings), 3)
        rules = [f["rule_id"] for f in placeholder_findings]
        self.assertIn("STUB-TODO-001", rules)
        self.assertIn("STUB-NOT-IMPLEMENTED-003", rules)
        self.assertIn("STUB-LOREM-002", rules)

    def test_detect_dead_ui_elements(self):
        """Verify scanner detects non-interactive anchor tags and unhandled buttons."""
        html_file = self.temp_repo_dir / "src" / "index.html"
        html_file.parent.mkdir(parents=True, exist_ok=True)
        html_file.write_text("""
<!DOCTYPE html>
<html>
<body>
  <a href="#">Dead Navigation Link</a>
  <button>Dead Unbound Button</button>
</body>
</html>
""", encoding="utf-8")

        result = self.scanner.scan_repository(self.temp_repo_dir)
        dead_ui_findings = result["findings_by_category"]["dead_ui"]

        self.assertGreaterEqual(len(dead_ui_findings), 2)
        rules = [f["rule_id"] for f in dead_ui_findings]
        self.assertIn("UI-DEAD-LINK-001", rules)
        self.assertIn("UI-UNBOUND-BUTTON-002", rules)

    def test_detect_exposed_secrets_with_critical_severity(self):
        """Verify scanner detects exposed API keys and private keys with CRITICAL severity."""
        auth_file = self.temp_repo_dir / "src" / "config.js"
        auth_file.parent.mkdir(parents=True, exist_ok=True)
        # Construct sample key safely so it matches scanner without leaking real secrets
        fake_aws = "AKIA" + "1234567890ABCDEF"
        fake_pat = "ghp_" + "a" * 36
        auth_file.write_text(f"""
const AWS_KEY = "{fake_aws}";
const GITHUB_TOKEN = "{fake_pat}";
""", encoding="utf-8")

        result = self.scanner.scan_repository(self.temp_repo_dir)
        secret_findings = result["findings_by_category"]["exposed_keys"]

        self.assertGreaterEqual(len(secret_findings), 2)
        self.assertTrue(result["has_critical_findings"])
        self.assertTrue(all(f["severity"] == "CRITICAL" for f in secret_findings))

        # Verify secrets are masked in report code snippets
        for f in secret_findings:
            self.assertIn("...", f["code_snippet"], "Exposed secrets must be masked in evidence snippets!")

    def test_pipeline_runner_populates_cheat_scan_findings(self):
        """Verify full verification pipeline runner executes Stage D and populates report."""
        runner = VerificationPipelineRunner()
        submission = SubmissionRecord(
            id=str(uuid.uuid4()),
            contract_id=f"cnt_{uuid.uuid4().hex[:8]}",
            seller_id="seller_test_bad",
            repo_url=str(self.bad_repo_dir),
            commit_sha="bad1234",
            build_notes="Testing Stage D cheat scan integration",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        features = [
            {"id": "feat_catalog", "name": "Feature 2: Product Catalog", "required": True}
        ]

        report = runner.run_pipeline(
            submission=submission,
            features=features,
            capture_screenshots=False
        )

        self.assertIsInstance(report.cheat_scan_findings, list)
        self.assertGreater(len(report.cheat_scan_findings), 0)

        # Check that bad-repo catalog cheat is present in report
        catalog_reported = any(
            "catalog.js" in f.get("file_path", "") and f.get("severity") == "HIGH"
            for f in report.cheat_scan_findings
        )
        self.assertTrue(catalog_reported, "Report must contain the high-severity catalog cheat finding!")


if __name__ == "__main__":
    unittest.main()
