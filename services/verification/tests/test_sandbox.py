"""
Unit and Integration Tests for Stage B Isolated Workspace & Sandbox (C15)
Validates:
  - Ephemeral workspace creation and guaranteed cleanup/destruction
  - Zero platform secrets in child process environments
  - Untrusted code execution security boundaries
  - Execution timeout enforcement
  - Directory traversal prevention
  - Exfiltration log scanning
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.verification.src.sandbox import (
    IsolatedWorkspace,
    WorkspaceSecurityError,
    FORBIDDEN_ENV_PREFIXES
)

class TestIsolatedWorkspace(unittest.TestCase):

    def setUp(self):
        # Set dummy platform secrets in parent environment to verify they get scrubbed
        os.environ["PAYPAL_CLIENT_ID"] = "dummy_paypal_client_id_123"
        os.environ["PAYPAL_CLIENT_SECRET"] = "dummy_paypal_secret_xyz"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/pactpal"
        os.environ["APP_SECRET"] = "super_secret_platform_key_999"
        os.environ["JWT_SECRET"] = "jwt_signing_key_abc"

    def test_workspace_creation_and_destruction(self):
        """Verify workspace directory is created and completely destroyed on exit."""
        workspace_path = None
        with IsolatedWorkspace() as ws:
            workspace_path = ws.workspace_path
            self.assertIsNotNone(workspace_path)
            self.assertTrue(workspace_path.exists())
            self.assertTrue(workspace_path.is_dir())

        # Assert total destruction after context exit
        self.assertFalse(workspace_path.exists(), "Workspace directory was not destroyed!")

    def test_zero_platform_secrets_in_environment(self):
        """Verify scrubbed environment strips all platform credentials."""
        with IsolatedWorkspace() as ws:
            clean_env = ws.clean_env
            for key in clean_env:
                k_upper = key.upper()
                for prefix in FORBIDDEN_ENV_PREFIXES:
                    self.assertFalse(
                        k_upper.startswith(prefix),
                        f"Leaked secret prefix {prefix} in key {key}!"
                    )
            # Verify specific keys
            self.assertNotIn("PAYPAL_CLIENT_ID", clean_env)
            self.assertNotIn("PAYPAL_CLIENT_SECRET", clean_env)
            self.assertNotIn("DATABASE_URL", clean_env)
            self.assertNotIn("APP_SECRET", clean_env)
            self.assertNotIn("JWT_SECRET", clean_env)
            # Verify safe container indicators
            self.assertEqual(clean_env.get("PACOPAL_SANDBOX"), "true")

    def test_untrusted_code_cannot_read_secrets(self):
        """Execute a child process inside sandbox and verify it cannot read secrets."""
        test_script = (
            "import os; "
            "pp_key = os.environ.get('PAYPAL_CLIENT_SECRET'); "
            "db_url = os.environ.get('DATABASE_URL'); "
            "print(f'PAYPAL={pp_key},DB={db_url}')"
        )
        with IsolatedWorkspace() as ws:
            res = ws.execute_command([sys.executable, "-c", test_script])
            self.assertTrue(res.succeeded)
            self.assertIn("PAYPAL=None,DB=None", res.stdout)

    def test_timeout_handling(self):
        """Verify long-running commands are terminated when exceeding timeout."""
        # 1-second timeout on a command that sleeps for 5 seconds
        with IsolatedWorkspace(timeout_seconds=1) as ws:
            sleep_cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
            res = ws.execute_command(sleep_cmd)
            self.assertTrue(res.timed_out)
            self.assertFalse(res.succeeded)
            self.assertIn("TIMED OUT", res.stderr)

    def test_directory_traversal_prevention(self):
        """Verify cwd_relative cannot escape outside the workspace."""
        with IsolatedWorkspace() as ws:
            with self.assertRaises(WorkspaceSecurityError):
                ws.execute_command(["dir"], cwd_relative="../../")

    def test_destruction_guarantee_on_exception(self):
        """Verify workspace is destroyed even if code crashes with an unhandled error."""
        workspace_path = None
        try:
            with IsolatedWorkspace() as ws:
                workspace_path = ws.workspace_path
                raise ValueError("Simulated unexpected build pipeline crash!")
        except ValueError:
            pass

        self.assertIsNotNone(workspace_path)
        self.assertFalse(workspace_path.exists(), "Workspace was not cleaned up on exception!")

    def test_exfiltration_log_scanning(self):
        """Verify exfiltration probes are flagged by the AI/semantic inspector."""
        with IsolatedWorkspace() as ws:
            suspicious_output = (
                "Attempting to connect to http://metadata.google.internal/computeMetadata/v1\n"
                "Checking environment for DATABASE_URL\n"
                "Scanning for .ssh/id_rsa keys"
            )
            analysis = ws.scan_logs_for_exfiltration_attempts(suspicious_output)
            self.assertEqual(analysis["exfiltration_risk"], "HIGH")
            self.assertGreaterEqual(len(analysis["suspicious_probes_detected"]), 2)

    def test_build_execution_inside_sandbox(self):
        """Execute a full build lifecycle using the benchmark deliverable fixture."""
        fixture_dir = PROJECT_ROOT / "services" / "verification" / "spike" / "fixtures" / "trivial-repo"
        if fixture_dir.exists():
            with IsolatedWorkspace() as ws:
                # Copy fixture files into isolated workspace
                dest_repo = ws.workspace_path / "repo"
                import shutil
                shutil.copytree(fixture_dir, dest_repo)

                # Execute build.js inside sandbox
                res_build = ws.execute_command(["node", "build.js"], cwd_relative="repo")
                self.assertTrue(res_build.succeeded, f"Build failed: {res_build.stderr}")
                self.assertIn("Build completed successfully", res_build.stdout)

                # Execute test.js inside sandbox
                res_test = ws.execute_command(["node", "test.js"], cwd_relative="repo")
                self.assertTrue(res_test.succeeded, f"Test failed: {res_test.stderr}")
                self.assertIn("Test suite green", res_test.stdout)

if __name__ == "__main__":
    unittest.main()
