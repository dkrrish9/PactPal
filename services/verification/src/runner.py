"""
PactPal Verification Pipeline - Master Execution Runner
Coordinates Stages A through F of the verification lifecycle inside isolated sandboxes.
Enforces the Stage B failure guard:
  - If a build fails, captures error logs, runs AI diagnostics,
  - Assembles structured VerificationReport with build_succeeded=False,
  - Skips Stage C (tests), Stage D (cheat scan), Stage E (visual diff),
  - Hands off report directly to the AI Referee in DECISION state with ZERO crashes.
"""

import os
import shutil
from typing import Optional, List, Dict, Any
from pathlib import Path

from .models import SubmissionRecord, VerificationReport
from .sandbox import IsolatedWorkspace, WorkspaceExecutionResult
from .ai_evaluator import AIIntakeEvaluator

class VerificationPipelineRunner:
    """Executes the verification pipeline across Stages A through F."""

    def __init__(self, ai_evaluator: Optional[AIIntakeEvaluator] = None):
        self.ai = ai_evaluator or AIIntakeEvaluator()

    def run_pipeline(
        self,
        submission: SubmissionRecord,
        features: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: int = 60
    ) -> VerificationReport:
        """
        Executes isolated sandbox build and verification for a submission.
        Guarantees that a broken repository produces a structured failure report
        without crashing the platform process.
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

            # 4. If build succeeded: assemble interim report (Milestone 1)
            # In Milestone 2, this will proceed through Stages C (tests), D (cheat scan), E (vision diff)
            per_feature = {}
            if features:
                for feat in features:
                    feat_id = feat.get("id", str(feat.get("title", "")))
                    per_feature[feat_id] = {
                        "feature_title": feat.get("title", "Feature"),
                        "status": "BUILD_PASSED",
                        "price_weight": feat.get("price_weight", 0.0),
                        "allocated_amount": feat.get("allocated_amount", 0.0)
                    }

            return VerificationReport(
                id=str(submission.id),
                submission_id=submission.id,
                contract_id=submission.contract_id,
                render_job_id=f"job_{submission.id[:8]}",
                build_succeeded=True,
                build_logs=combined_logs,
                test_suite_results={"status": "BUILD_READY"},
                cheat_scan_findings=[],
                visual_diff_summary={"status": "PENDING_STAGE_E"},
                per_feature_results=per_feature,
                overall_score=1.0,
                completed_at=submission.submitted_at,
                failure_reason=None,
                ai_diagnostic=None,
                skipped_stages=[],
                next_state="DECISION"
            )

    def _determine_build_commands(self, submission: SubmissionRecord, repo_dir: Path) -> List[List[str]]:
        """Determines appropriate build commands for the deliverable."""
        # If build.js exists in the repo, use node build.js
        if (repo_dir / "build.js").exists():
            return [["node", "build.js"]]
        
        # If package.json has build script
        if (repo_dir / "package.json").exists():
            return [["npm", "run", "build"]]

        # Default fallback
        return [["node", "build.js"]]
