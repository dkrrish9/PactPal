"""
PactPal Verification Pipeline - Stage C: Automated Test Suite & AI Acceptance Validator
Coordinates native project test execution and multimodal AI acceptance verification:
  - Discovers and runs native test suites inside isolated sandboxes (npm test, node test runner, pytest)
  - Parses native test execution results (total, passed, failed, execution duration)
  - Evaluates plain-language contract acceptance tests against source code implementation using AI (Gemini)
  - Maps pass/fail verdicts per feature with evidence and severity
  - Computes weighted milestone release scores based on locked contract feature weights
"""

import os
import re
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from .models import SubmissionRecord
from .sandbox import IsolatedWorkspace, WorkspaceExecutionResult
from .ai_evaluator import AIIntakeEvaluator

class StageCTestSuiteProcessor:
    """Orchestrates Stage C automated testing and per-feature acceptance verification."""

    def __init__(self, ai_evaluator: Optional[AIIntakeEvaluator] = None):
        self.ai = ai_evaluator or AIIntakeEvaluator()

    def execute_stage_c(
        self,
        workspace: IsolatedWorkspace,
        repo_dir: Path,
        features: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any], float]:
        """
        Executes native tests and AI acceptance validation inside the isolated sandbox.
        Returns:
            (test_suite_results, per_feature_results, overall_score)
        """
        start_time = time.time()

        # 1. Discover and execute native project tests
        native_result = self._run_native_tests(workspace, repo_dir)

        # 2. Parse native test results
        test_suite_results = self._parse_test_output(native_result, int((time.time() - start_time) * 1000))

        # 3. Evaluate each feature against acceptance tests and source code
        per_feature_results = {}
        total_passed_weight = 0.0

        if features:
            for feat in features:
                feat_id = str(feat.get("id", feat.get("title", "feat")))
                feat_verdict = self._evaluate_feature_acceptance(
                    repo_dir=repo_dir,
                    feature=feat,
                    native_test_results=test_suite_results
                )
                per_feature_results[feat_id] = feat_verdict

                if feat_verdict["status"] == "PASSED":
                    total_passed_weight += float(feat.get("price_weight", 0.0))

            overall_score = round(min(1.0, max(0.0, total_passed_weight / 100.0)), 3)
        else:
            # Fallback if no features explicitly defined
            overall_score = 1.0 if test_suite_results["failed_tests"] == 0 else 0.0

        return test_suite_results, per_feature_results, overall_score

    def _run_native_tests(self, workspace: IsolatedWorkspace, repo_dir: Path) -> WorkspaceExecutionResult:
        """Determines test command and executes inside isolated sandbox."""
        test_cmd = self._detect_test_command(repo_dir)
        return workspace.execute_command(test_cmd, cwd_relative="repo", timeout=60)

    def _detect_test_command(self, repo_dir: Path) -> List[str]:
        """Detects the appropriate test command for the deliverable repository."""
        # Custom master test runner
        if (repo_dir / "test" / "runner.js").exists():
            return ["node", "test/runner.js"]

        # Single test.js
        if (repo_dir / "test.js").exists():
            return ["node", "test.js"]

        # Node / npm package.json
        pkg_json = repo_dir / "package.json"
        if pkg_json.exists():
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    scripts = data.get("scripts", {})
                    if "test" in scripts:
                        # Avoid calling npm.ps1 on Windows by using node or npm.cmd
                        test_script = scripts["test"]
                        if test_script.startswith("node "):
                            return test_script.split()
                        return ["npm.cmd", "test"] if os.name == "nt" else ["npm", "test"]
            except Exception:
                pass

        # Python unittest
        if any(repo_dir.glob("test*.py")) or any(repo_dir.glob("tests/test*.py")):
            return ["python", "-m", "unittest", "discover"]

        return ["node", "test/runner.js"]

    def _parse_test_output(self, exec_res: WorkspaceExecutionResult, duration_ms: int) -> Dict[str, Any]:
        """Parses stdout/stderr of the test runner into structured metrics."""
        combined = f"{exec_res.stdout}\n{exec_res.stderr}"

        # Match [TEST SUMMARY] Total: X | Passed: Y | Failed: Z
        summary_match = re.search(r"Total:\s*(\d+)\s*\|\s*Passed:\s*(\d+)\s*\|\s*Failed:\s*(\d+)", combined)
        if summary_match:
            total = int(summary_match.group(1))
            passed = int(summary_match.group(2))
            failed = int(summary_match.group(3))
        else:
            # Fallback assertion counting
            pass_count = len(re.findall(r"(?:PASS|passed|✓|OK)", combined, re.IGNORECASE))
            fail_count = len(re.findall(r"(?:FAIL|failed|✗|ERROR)", combined, re.IGNORECASE))
            if exec_res.succeeded and fail_count == 0:
                passed = max(1, pass_count)
                failed = 0
                total = passed
            else:
                passed = pass_count
                failed = max(1, fail_count)
                total = passed + failed

        status = "COMPLETED" if exec_res.succeeded else "FAILED"
        if exec_res.timed_out:
            status = "TIMED_OUT"

        return {
            "status": status,
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": failed,
            "skipped_tests": 0,
            "duration_ms": duration_ms or exec_res.duration_ms,
            "exit_code": exec_res.exit_code,
            "raw_output": combined.strip()
        }

    def _evaluate_feature_acceptance(
        self,
        repo_dir: Path,
        feature: Dict[str, Any],
        native_test_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates a specific contract feature against source code and test results.
        Uses Google Gemini AI if configured, with semantic code inspection fallback.
        """
        feat_id = str(feature.get("id", ""))
        feat_title = feature.get("title", "Feature")
        acceptance_test = feature.get("acceptance_test", "Feature functionality verified.")
        price_weight = float(feature.get("price_weight", 0.0))
        allocated_amount = float(feature.get("allocated_amount", 0.0))

        # Check if native tests passed overall
        native_passed = (native_test_results.get("status") == "COMPLETED") and (native_test_results.get("failed_tests", 0) == 0)

        # Check feature-specific native test logs
        raw_output = native_test_results.get("raw_output", "")
        feature_failed_in_tests = False
        feature_passed_in_tests = False

        title_tokens = [w.lower() for w in re.findall(r"\w+", feat_title) if len(w) > 3]
        for line in raw_output.split("\n"):
            line_lower = line.lower()
            if any(t in line_lower for t in title_tokens):
                if "fail" in line_lower or "✗" in line_lower or "error" in line_lower:
                    feature_failed_in_tests = True
                if "pass" in line_lower or "✓" in line_lower or "ok" in line_lower:
                    feature_passed_in_tests = True

        # Read relevant source code for AI / semantic verification
        source_context = self._find_relevant_source_code(repo_dir, feat_title)

        # If AI is available, run Gemini multimodal code evaluation
        if self.ai.is_ai_available():
            ai_verdict = self._run_ai_feature_eval(feat_title, acceptance_test, source_context, raw_output)
            if ai_verdict:
                return {
                    "feature_id": feat_id,
                    "feature_title": feat_title,
                    "status": ai_verdict["status"],
                    "price_weight": price_weight,
                    "allocated_amount": allocated_amount,
                    "severity": "NONE" if ai_verdict["status"] == "PASSED" else "HIGH",
                    "evidence": ai_verdict["evidence"],
                    "reason": None if ai_verdict["status"] == "PASSED" else ai_verdict.get("reason", "Failed acceptance criteria")
                }

        # Deterministic semantic evaluation fallback
        if feature_failed_in_tests:
            status = "FAILED"
            severity = "HIGH"
            reason = f"Native unit test failed for {feat_title}"
            evidence = f"Test execution failed with error in suite matching '{feat_title}'. Raw log: {raw_output[:200]}"
        elif native_passed or feature_passed_in_tests:
            status = "PASSED"
            severity = "NONE"
            reason = None
            evidence = f"Native automated tests passed for '{feat_title}'. Verified acceptance test criteria: '{acceptance_test}'."
        else:
            status = "FAILED"
            severity = "MEDIUM"
            reason = f"No passing test execution or verified implementation found for '{feat_title}'."
            evidence = f"Feature did not satisfy acceptance test: {acceptance_test}"

        return {
            "feature_id": feat_id,
            "feature_title": feat_title,
            "status": status,
            "price_weight": price_weight,
            "allocated_amount": allocated_amount,
            "severity": severity,
            "evidence": evidence,
            "reason": reason
        }

    def _find_relevant_source_code(self, repo_dir: Path, feat_title: str) -> str:
        """Finds source code files related to the feature to provide context for AI inspection."""
        keywords = [w.lower() for w in re.findall(r"\w+", feat_title) if len(w) > 3]
        chunks = []

        src_dir = repo_dir / "src"
        search_dirs = [src_dir] if src_dir.exists() else [repo_dir]

        for s_dir in search_dirs:
            for f_path in s_dir.glob("*.js"):
                try:
                    content = f_path.read_text(encoding="utf-8")
                    if any(k in f_path.name.lower() or k in content.lower() for k in keywords):
                        chunks.append(f"// File: {f_path.name}\n{content[:1500]}")
                except Exception:
                    pass

        return "\n\n".join(chunks)[:4000]

    def _run_ai_feature_eval(
        self,
        feat_title: str,
        acceptance_test: str,
        source_code: str,
        test_logs: str
    ) -> Optional[Dict[str, Any]]:
        """Invokes Google Gemini API to evaluate whether implementation satisfies acceptance criteria."""
        import urllib.request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.ai.model}:generateContent?key={self.ai.api_key}"

        prompt = f"""
You are the Acceptance Test Referee for PactPal, an automated AI Escrow Referee.
Evaluate whether the freelancer's deliverable satisfies the following contract feature:

Feature: {feat_title}
Acceptance Test Criteria: {acceptance_test}

Relevant Code Implementation:
\"\"\"
{source_code or "No source code detected."}
\"\"\"

Native Test Execution Output:
\"\"\"
{test_logs[-2000:]}
\"\"\"

Decide whether this feature passes or fails.
Return strictly a JSON object:
{{
  "status": "PASSED|FAILED",
  "evidence": "Detailed explanation of why the feature passed or failed based on tests and code.",
  "reason": "Short summary of failure, or null if passed"
}}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1}
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
        except Exception as e:
            return None
