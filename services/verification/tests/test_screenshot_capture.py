"""
Unit and Integration Tests for Stage E Pre-Capture: Headless Screenshots (C26)
Validates:
  - System browser discovery across Windows, Linux, and macOS
  - Headless browser screenshot capture of deliverable HTML pages
  - PNG magic bytes validation and non-empty image checks
  - Cryptographic SHA-256 fingerprinting of captured artifacts
  - Full pipeline integration storing screenshots in visual_diff_summary
"""

import sys
import unittest
import uuid
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.verification.src.screenshot_capture import (
    HeadlessScreenshotCapture,
    BrowserDetector,
    BrowserNotFoundError
)
from services.verification.src.models import SubmissionRecord
from services.verification.src.runner import VerificationPipelineRunner

class TestHeadlessScreenshotCapture(unittest.TestCase):

    def setUp(self):
        self.good_repo_dir = PROJECT_ROOT / "demo-assets" / "good-repo"
        self.test_evidence_dir = Path(tempfile.mkdtemp(prefix="pactpal_test_evidence_"))
        self.runner = VerificationPipelineRunner()

    def tearDown(self):
        shutil.rmtree(self.test_evidence_dir, ignore_errors=True)

    def test_browser_detector_finds_browser(self):
        """Verify browser detector finds an installed browser binary."""
        browser_bin = BrowserDetector.get_browser_binary()
        self.assertIsNotNone(browser_bin)
        self.assertTrue(Path(browser_bin).exists())

    def test_capture_single_page_screenshot(self):
        """Capture a real headless screenshot of good-repo landing page."""
        index_file = self.good_repo_dir / "src" / "index.html"
        self.assertTrue(index_file.exists(), "src/index.html missing in good-repo!")

        output_png = self.test_evidence_dir / "landing_test.png"
        capturer = HeadlessScreenshotCapture()

        result = capturer.capture_screenshot(
            target_url_or_file=str(index_file),
            output_image_path=output_png,
            viewport_width=1280,
            viewport_height=800
        )

        # 1. File existence and size
        self.assertTrue(output_png.exists())
        self.assertGreater(result["file_size_bytes"], 2000, "Screenshot file is unexpectedly small!")

        # 2. Status & Viewport
        self.assertEqual(result["status"], "CAPTURED")
        self.assertEqual(result["viewport"]["width"], 1280)
        self.assertEqual(result["viewport"]["height"], 800)

        # 3. Cryptographic Fingerprint
        self.assertEqual(len(result["sha256_fingerprint"]), 64)

        # 4. AI / Visual Assessment
        self.assertTrue(result["ai_assessment"]["is_rendered"])
        self.assertGreaterEqual(result["ai_assessment"]["visual_completeness_score"], 0.8)

        # 5. PNG Magic Header
        with open(output_png, "rb") as f:
            header = f.read(8)
            self.assertEqual(header, b"\x89PNG\r\n\x1a\n")

    def test_capture_deliverable_key_pages(self):
        """Capture all discovered HTML pages in deliverable repository."""
        capturer = HeadlessScreenshotCapture()
        result = capturer.capture_deliverable_key_pages(
            repo_dir=self.good_repo_dir,
            evidence_dir=self.test_evidence_dir / "batch",
            viewports=[(1280, 800), (375, 667)]
        )

        self.assertEqual(result["status"], "COMPLETED")
        self.assertTrue(result["ready_for_figma_diff"])
        self.assertGreaterEqual(result["total_screenshots"], 2)

        # Verify files were generated on disk
        for item in result["screenshots"]:
            self.assertTrue(Path(item["file_path"]).exists())
            self.assertEqual(len(item["sha256_fingerprint"]), 64)

    def test_pipeline_integration_with_screenshots(self):
        """Verify full verification pipeline captures screenshots into report."""
        submission = SubmissionRecord(
            id=str(uuid.uuid4()),
            contract_id=str(uuid.uuid4()),
            seller_id=str(uuid.uuid4()),
            repo_url=str(self.good_repo_dir),
            commit_sha="c26_screenshot_test",
            build_notes="Testing Stage E screenshot generation.",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        report = self.runner.run_pipeline(submission, capture_screenshots=True)

        self.assertTrue(report.build_succeeded)
        self.assertIn("screenshots", report.visual_diff_summary)
        self.assertGreaterEqual(len(report.visual_diff_summary["screenshots"]), 1)
        self.assertTrue(report.visual_diff_summary["ready_for_figma_diff"])

    def test_nonexistent_file_raises_error(self):
        """Verify capturing non-existent file path raises FileNotFoundError."""
        capturer = HeadlessScreenshotCapture()
        fake_path = self.test_evidence_dir / "does_not_exist.html"

        with self.assertRaises(FileNotFoundError):
            capturer.capture_screenshot(
                target_url_or_file=str(fake_path),
                output_image_path=self.test_evidence_dir / "fail.png"
            )

if __name__ == "__main__":
    unittest.main()
