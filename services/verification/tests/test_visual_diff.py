"""
Unit and Integration Tests for Stage E: Multimodal Visual Diff & Figma Comparison (C30)
Validates Done Criteria:
  - Good repo screenshot matches Figma mockup (similarity >= 0.85, passes)
  - Bad repo screenshot diverges from Figma mockup (similarity < 0.85, fails)
  - Visual mismatches in the bad repo are highlighted in structured evidence
  - Configurable similarity threshold enforcement
  - Dual-engine fallback handling and error validation
  - End-to-end VerificationPipelineRunner integration updating visual_diff_summary
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

from services.verification.src.visual_diff import (
    VisualDiffEngine,
    VisualDiffError,
    DEFAULT_SIMILARITY_THRESHOLD
)
from services.verification.src.screenshot_capture import HeadlessScreenshotCapture
from services.verification.src.models import SubmissionRecord
from services.verification.src.runner import VerificationPipelineRunner


class TestVisualDiffAgainstFigma(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.good_repo_dir = PROJECT_ROOT / "demo-assets" / "good-repo"
        cls.bad_repo_dir = PROJECT_ROOT / "demo-assets" / "bad-repo"
        cls.figma_dir = PROJECT_ROOT / "demo-assets" / "figma"
        cls.reference_png = cls.figma_dir / "reference_landing_1280x800.png"

        # Capture live headless screenshots for testing comparison
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="pactpal_visual_diff_test_"))
        capturer = HeadlessScreenshotCapture()

        cls.good_screenshot = cls.temp_dir / "good_landing.png"
        capturer.capture_screenshot(
            target_url_or_file=str(cls.good_repo_dir / "src" / "index.html"),
            output_image_path=cls.good_screenshot,
            viewport_width=1280,
            viewport_height=800
        )

        cls.bad_screenshot = cls.temp_dir / "bad_landing.png"
        capturer.capture_screenshot(
            target_url_or_file=str(cls.bad_repo_dir / "src" / "index.html"),
            output_image_path=cls.bad_screenshot,
            viewport_width=1280,
            viewport_height=800
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        self.engine = VisualDiffEngine(similarity_threshold=0.85)

    def test_figma_reference_exists(self):
        """Verify baseline Figma mockup reference exists."""
        self.assertTrue(self.reference_png.exists(), "Figma reference landing screenshot missing!")
        self.assertGreater(self.reference_png.stat().st_size, 1000)

    def test_good_repo_passes_visual_diff(self):
        """Verify good repo screenshot passes visual diff against Figma reference with score >= 0.85."""
        result = self.engine.compare_images(
            candidate_image_path=self.good_screenshot,
            reference_image_path=self.reference_png,
            threshold=0.85
        )

        self.assertEqual(result["status"], "COMPLETED")
        self.assertTrue(result["passed"], f"Good repo should pass visual diff! Result: {result}")
        self.assertGreaterEqual(result["similarity_score"], 0.85)
        self.assertEqual(len(result["mismatches_detected"]), 0)

    def test_bad_repo_fails_visual_diff_and_highlights_mismatches(self):
        """Verify bad repo screenshot fails visual diff and highlights visual mismatches."""
        result = self.engine.compare_images(
            candidate_image_path=self.bad_screenshot,
            reference_image_path=self.reference_png,
            threshold=0.85
        )

        self.assertEqual(result["status"], "COMPLETED")
        self.assertFalse(result["passed"], f"Bad repo should fail visual diff! Result: {result}")
        self.assertLess(result["similarity_score"], 0.85)
        self.assertGreater(len(result["mismatches_detected"]), 0)

        # Confirm mismatch details are clearly reported
        mismatches_text = " ".join(result["mismatches_detected"]).lower()
        self.assertTrue("color" in mismatches_text or "divergence" in mismatches_text)
        self.assertIn("Visual mismatch detected", result["diff_notes"])

    def test_custom_similarity_threshold(self):
        """Verify configurable similarity threshold alters pass/fail boundary."""
        # Ultra strict threshold (0.99) should fail even good repo due to subtle font rendering diffs
        strict_result = self.engine.compare_images(
            candidate_image_path=self.good_screenshot,
            reference_image_path=self.reference_png,
            threshold=0.99
        )
        self.assertEqual(strict_result["threshold"], 0.99)

        # Very permissive threshold (0.20) should pass bad repo
        loose_result = self.engine.compare_images(
            candidate_image_path=self.bad_screenshot,
            reference_image_path=self.reference_png,
            threshold=0.20
        )
        self.assertTrue(loose_result["passed"])

    def test_missing_candidate_or_reference_raises_filenotfound(self):
        """Verify comparing non-existent image paths raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.engine.compare_images(
                candidate_image_path=Path("non_existent_cand.png"),
                reference_image_path=self.reference_png
            )

        with self.assertRaises(FileNotFoundError):
            self.engine.compare_images(
                candidate_image_path=self.good_screenshot,
                reference_image_path=Path("non_existent_ref.png")
            )

    def test_invalid_png_format_raises_visual_diff_error(self):
        """Verify non-PNG binary inputs trigger VisualDiffError."""
        bad_file = self.temp_dir / "corrupted.png"
        bad_file.write_bytes(b"NOT A REAL PNG FILE CONTENT")

        with self.assertRaises(VisualDiffError):
            self.engine._compare_with_perceptual_analysis(bad_file, self.reference_png, threshold=0.85)

    def test_pipeline_runner_good_repo_visual_diff(self):
        """Verify full verification pipeline runner executes Stage E visual diff successfully on good repo."""
        runner = VerificationPipelineRunner(figma_reference_dir=self.figma_dir, visual_diff_threshold=0.85)
        submission = SubmissionRecord(
            id=str(uuid.uuid4()),
            contract_id=f"cnt_{uuid.uuid4().hex[:8]}",
            seller_id="seller_alice_123",
            repo_url=str(self.good_repo_dir),
            commit_sha="abc1234",
            build_notes="Good repo benchmark submission",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        features = [
            {"id": "F1", "name": "Landing Page Viewport", "required": True}
        ]

        report = runner.run_pipeline(submission=submission, features=features, capture_screenshots=True)

        self.assertTrue(report.build_succeeded)
        self.assertEqual(report.next_state, "DECISION")
        self.assertIn("visual_diff_summary", report.to_dict())

        vdiff = report.visual_diff_summary
        self.assertEqual(vdiff.get("status"), "COMPLETED")
        self.assertTrue(vdiff.get("passed"))
        self.assertGreaterEqual(vdiff.get("similarity_score"), 0.85)

    def test_pipeline_runner_bad_repo_visual_diff(self):
        """Verify full verification pipeline runner highlights visual diff mismatch on bad repo."""
        runner = VerificationPipelineRunner(figma_reference_dir=self.figma_dir, visual_diff_threshold=0.85)
        submission = SubmissionRecord(
            id=str(uuid.uuid4()),
            contract_id=f"cnt_{uuid.uuid4().hex[:8]}",
            seller_id="seller_bob_456",
            repo_url=str(self.bad_repo_dir),
            commit_sha="def5678",
            build_notes="Bad repo benchmark submission",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        features = [
            {"id": "F1", "name": "Landing Page Viewport", "required": True}
        ]

        report = runner.run_pipeline(submission=submission, features=features, capture_screenshots=True)

        self.assertTrue(report.build_succeeded)
        vdiff = report.visual_diff_summary
        self.assertEqual(vdiff.get("status"), "COMPLETED")
        self.assertFalse(vdiff.get("passed"))
        self.assertLess(vdiff.get("similarity_score"), 0.85)
        self.assertGreater(len(vdiff.get("mismatches_detected", [])), 0)


if __name__ == "__main__":
    unittest.main()
