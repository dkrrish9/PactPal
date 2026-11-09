"""
PactPal Verification Pipeline - Master Execution Runner
Coordinates Stages A through F of the verification lifecycle inside isolated sandboxes.
Enforces:
  - Stage B build failure guard: skips downstream stages and emits report if build fails.
  - Stage C automated testing: executes native test suites and maps per-feature pass/fail with AI checks.
"""

import os
import uuid
import shutil
from typing import Optional, List, Dict, Any
from pathlib import Path

from .models import SubmissionRecord, VerificationReport
from .sandbox import IsolatedWorkspace, WorkspaceExecutionResult
from .ai_evaluator import AIIntakeEvaluator
from .test_runner import StageCTestSuiteProcessor

class VerificationPipelineRunner:
    """Executes the verification pipeline across Stages A through F."""

    def __init__(self, ai_evaluator: Optional[AIIntakeEvaluator] = None):
        self.ai = ai_evaluator or AIIntakeEvaluator()
        self.stage_c = StageCTestSuiteProcessor(ai_evaluator=self.ai)

    def run_pipeline(
        self,
        submission: SubmissionRecord,
        features: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: int = 60
    ) -> VerificationReport:
        """
        Executes isolated sandbox build and verification for a submission.
        Coordinates Stage B Build and Stage C Automated Tests & Feature Mapping.
        """
        # Spawn isolated workspace with zero platform secrets
        with IsolatedWorkspace(workspace_id=submission.id, timeout_seconds=timeout_seconds, ai_evaluator=self.ai) as ws:
            clone_dest = ws.workspace_path / "repo"

            # 1. Intake Repo Setup into Sandbox
            repo_source = submission.repo_url
            local_fixture = Path(repo_source)

            if local_fixture.exists() and local_fixture.is_dir():
                # Copy local fixture directly into workspace
                shutil.copytree(local_fixture, clone_dest)
            else:
                # Execute git clone in sandbox
                clone_cmd = ["git", "clone", repo_source, str(clone_dest)]
                res_clone = ws.execute_command(clone_cmd)
                if not res_clone.succeeded:
                    diagnostic = self.ai.diagnose_build_failure(
                        res_clone.stdout,
                        res_clone.stderr,
                        res_clone.exit_code
                    )
                    return VerificationReport.create_build_failure_report(
                        submission_id=submission.id,
                        contract_id=submission.contract_id,
                        build_logs=f"CLONE FAILURE:\n{res_clone.stderr}",
                        failure_reason=f"Repository clone failed: {diagnostic['root_cause']}",
                        features=features,
                        ai_diagnostic=diagnostic
                    )

            # 2. Stage B: Clean Sandbox Build Execution
            build_commands = self._determine_build_commands(submission, clone_dest)
            build_stdout_chunks = []
            build_stderr_chunks = []
            build_failed = False
            failing_cmd = None
            last_exit_code = 0

            for cmd in build_commands:
                res_cmd = ws.execute_command(cmd, cwd_relative="repo")
                build_stdout_chunks.append(f"[{' '.join(cmd)}] STDOUT:\n{res_cmd.stdout}")
                build_stderr_chunks.append(f"[{' '.join(cmd)}] STDERR:\n{res_cmd.stderr}")

                if not res_cmd.succeeded:
                    build_failed = True
                    failing_cmd = cmd
                    last_exit_code = res_cmd.exit_code
                    break

            combined_stdout = "\n".join(build_stdout_chunks)
            combined_stderr = "\n".join(build_stderr_chunks)
            combined_logs = f"{combined_stdout}\n{combined_stderr}"

            # 3. Build Failure Handling (C18 Done Criteria)
            if build_failed:
                diagnostic = self.ai.diagnose_build_failure(
                    combined_stdout,
                    combined_stderr,
                    last_exit_code
                )
                failure_reason = f"Build failed during '{' '.join(failing_cmd)}': {diagnostic['root_cause']}"

                return VerificationReport.create_build_failure_report(
                    submission_id=submission.id,
                    contract_id=submission.contract_id,
                    build_logs=combined_logs,
                    failure_reason=failure_reason,
                    features=features,
                    ai_diagnostic=diagnostic
                )

            # 4. Stage C: Automated Tests & Per-Feature Mapping (C23 Done Criteria)
            test_suite_results, per_feature_results, overall_score = self.stage_c.execute_stage_c(
                workspace=ws,
                repo_dir=clone_dest,
                features=features
            )

            return VerificationReport(
                id=str(uuid.uuid4()),
                submission_id=submission.id,
                contract_id=submission.contract_id,
                render_job_id=f"job_{submission.id[:8]}",
                build_succeeded=True,
                build_logs=combined_logs,
                test_suite_results=test_suite_results,
                cheat_scan_findings=[],
                visual_diff_summary={"status": "PENDING_STAGE_E"},
                per_feature_results=per_feature_results,
                overall_score=overall_score,
                completed_at=submission.submitted_at,
                failure_reason=None,
                ai_diagnostic=None,
                skipped_stages=[],
                next_state="DECISION"
            )

    def _determine_build_commands(self, submission: SubmissionRecord, repo_dir: Path) -> List[List[str]]:
        """Determines appropriate build commands for the deliverable."""
        if (repo_dir / "build.js").exists():
            return [["node", "build.js"]]
        
        if (repo_dir / "package.json").exists():
            return [["npm", "run", "build"]]

        return [["node", "build.js"]]
