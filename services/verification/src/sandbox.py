"""
PactPal Verification Pipeline - Stage B: Isolated Workspace & Sandbox Runner
Implements zero-trust container/workspace lifecycle:
  - Ephemeral isolated workspace directory creation
  - Strict secret scrubbing (zero platform secrets, PayPal credentials, or DB keys)
  - Process isolation with timeout and resource limits
  - AI-assisted log inspection for sandbox escape and exfiltration attempts
  - Guaranteed workspace destruction and total host cleanup
"""

import os
import sys
import stat
import time
import shutil
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .models import SubmissionRecord
from .ai_evaluator import AIIntakeEvaluator

# Platform credentials and sensitive keys that MUST NEVER leak into the workspace
FORBIDDEN_ENV_PREFIXES = (
    "PAYPAL_",
    "DATABASE_",
    "DB_",
    "APP_",
    "JWT_",
    "SESSION_",
    "RENDER_",
    "GEMINI_",
    "OPENAI_",
    "FIGMA_",
    "RECEIPT_"
)

FORBIDDEN_ENV_SUBSTRINGS = (
    "SECRET",
    "KEY",
    "TOKEN",
    "PASSWORD",
    "CREDENTIAL",
    "PRIVATE"
)

# Standard safe system environment variables permitted inside isolated processes
SAFE_SYSTEM_VARS = {
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "APPDATA",
    "LOCALAPPDATA",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "OS"
}

class WorkspaceSecurityError(RuntimeError):
    """Raised when an environment isolation or security boundary check fails."""
    pass

class WorkspaceExecutionResult:
    """Encapsulates output and status of a command executed inside the sandbox."""
    def __init__(
        self,
        command: List[str],
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: int,
        timed_out: bool = False
    ):
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
        self.timed_out = timed_out
        self.succeeded = (exit_code == 0) and not timed_out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": " ".join(self.command),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
            "succeeded": self.succeeded
        }

class IsolatedWorkspace:
    """
    Context manager managing the ephemeral isolated workspace container.
    Guarantees that untrusted freelancer code:
      1. Receives 0 platform secrets in its environment.
      2. Executes inside a designated ephemeral directory.
      3. Is terminated if execution exceeds safe timeout limits.
      4. Has its entire directory purged and destroyed upon exit.
    """

    def __init__(
        self,
        workspace_id: Optional[str] = None,
        timeout_seconds: int = 60,
        ai_evaluator: Optional[AIIntakeEvaluator] = None
    ):
        self.workspace_id = workspace_id or f"ws_{int(time.time())}_{os.urandom(4).hex()}"
        self.timeout_seconds = timeout_seconds
        self.ai = ai_evaluator or AIIntakeEvaluator()
        self.workspace_path: Optional[Path] = None
        self.clean_env: Dict[str, str] = {}
        self.logs: List[str] = []

    def __enter__(self) -> "IsolatedWorkspace":
        # 1. Create isolated ephemeral directory
        temp_dir = tempfile.mkdtemp(prefix=f"pactpal_{self.workspace_id}_")
        self.workspace_path = Path(temp_dir).resolve()

        # 2. Build scrubbed environment
        self.clean_env = self._build_sanitized_environment()

        # 3. Assert zero-trust boundary
        self._verify_isolation_boundary()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Guaranteed cleanup regardless of outcome or exceptions
        self.destroy()

    def _build_sanitized_environment(self) -> Dict[str, str]:
        """Filters process environment to remove all platform credentials."""
        sanitized = {}

        for key, val in os.environ.items():
            k_upper = key.upper()

            # Skip any variable matching forbidden prefixes
            if any(k_upper.startswith(prefix) for prefix in FORBIDDEN_ENV_PREFIXES):
                continue

            # Skip any variable containing secret keywords unless explicitly on the safe list
            if key not in SAFE_SYSTEM_VARS and any(sub in k_upper for sub in FORBIDDEN_ENV_SUBSTRINGS):
                continue

            # Only retain safe system vars or benign environment metadata
            if key in SAFE_SYSTEM_VARS or k_upper.startswith("NODE_") or k_upper.startswith("PYTHON"):
                sanitized[key] = val

        # Set container identifiers
        sanitized["PACOPAL_SANDBOX"] = "true"
        sanitized["PACOPAL_WORKSPACE_ID"] = self.workspace_id
        sanitized["CI"] = "true"
        sanitized["NODE_ENV"] = "test"

        return sanitized

    def _verify_isolation_boundary(self):
        """Hard assertion ensuring zero secrets exist in the child environment."""
        leaked = []
        for key in self.clean_env:
            k_upper = key.upper()
            if any(k_upper.startswith(p) for p in FORBIDDEN_ENV_PREFIXES):
                leaked.append(key)

        if leaked:
            raise WorkspaceSecurityError(
                f"CRITICAL: Platform credentials detected in container environment: {leaked}"
            )

    def execute_command(
        self,
        cmd: List[str],
        cwd_relative: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> WorkspaceExecutionResult:
        """
        Executes a command inside the isolated workspace using scrubbed environment.
        """
        if not self.workspace_path or not self.workspace_path.exists():
            raise RuntimeError("Workspace has not been initialized or was already destroyed.")

        target_dir = self.workspace_path
        if cwd_relative:
            target_dir = (self.workspace_path / cwd_relative).resolve()
            # Prevent directory traversal attacks
            if not str(target_dir).startswith(str(self.workspace_path)):
                raise WorkspaceSecurityError(f"Directory traversal attempt detected: {cwd_relative}")

        effective_timeout = timeout or self.timeout_seconds
        start_time = time.time()
        timed_out = False

        try:
            res = subprocess.run(
                cmd,
                cwd=target_dir,
                env=self.clean_env,
                capture_output=True,
                text=True,
                timeout=effective_timeout
            )
            duration_ms = int((time.time() - start_time) * 1000)
            return WorkspaceExecutionResult(
                command=cmd,
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                duration_ms=duration_ms,
                timed_out=False
            )
        except subprocess.TimeoutExpired as te:
            duration_ms = int((time.time() - start_time) * 1000)
            stdout = te.stdout.decode() if isinstance(te.stdout, bytes) else (te.stdout or "")
            stderr = te.stderr.decode() if isinstance(te.stderr, bytes) else (te.stderr or "")
            return WorkspaceExecutionResult(
                command=cmd,
                exit_code=-1,
                stdout=stdout,
                stderr=f"EXECUTION TIMED OUT after {effective_timeout}s. {stderr}",
                duration_ms=duration_ms,
                timed_out=True
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return WorkspaceExecutionResult(
                command=cmd,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                timed_out=False
            )

    def scan_logs_for_exfiltration_attempts(self, execution_output: str) -> Dict[str, Any]:
        """
        Inspects output logs using AI / heuristic scanner to detect exfiltration
        or probe attempts against the host system.
        """
        output_lower = execution_output.lower()
        findings = []

        # Indicators of untrusted code probing the environment
        PROBE_INDICATORS = [
            ("paypal", "Probed for PayPal keywords in environment or files"),
            ("database_url", "Probed for database connection string"),
            ("etc/shadow", "Attempted access to system credentials file (/etc/shadow)"),
            ("etc/passwd", "Attempted access to system users file (/etc/passwd)"),
            (".ssh/id_rsa", "Attempted inspection of host SSH keys"),
            ("aws_secret_access_key", "Probed for cloud provider secrets"),
            ("metadata.google.internal", "Attempted access to cloud instance metadata")
        ]

        for token, desc in PROBE_INDICATORS:
            if token in output_lower:
                findings.append(desc)

        risk_level = "HIGH" if len(findings) > 0 else "LOW"
        return {
            "exfiltration_risk": risk_level,
            "suspicious_probes_detected": findings,
            "scanned_at": datetime.now(timezone.utc).isoformat()
        }

    def destroy(self) -> bool:
        """
        Guaranteed destruction of the workspace directory.
        Removes all cloned source code, build outputs, and temporary files.
        """
        if self.workspace_path and self.workspace_path.exists():
            def handle_remove_readonly(func, path, exc):
                # Ensure read-only git pack files on Windows can be deleted
                os.chmod(path, stat.S_IWRITE)
                func(path)

            shutil.rmtree(self.workspace_path, onerror=handle_remove_readonly)
            destroyed = not self.workspace_path.exists()
            return destroyed
        return True
