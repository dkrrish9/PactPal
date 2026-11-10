"""
PactPal Verification Pipeline - Stage D: Cheat & Loophole Scanner (C27)
Scans deliverable repositories for dishonest or insecure practices across 5 core categories:
  1. Hardcoded outputs / fake answers (mock static return bypasses cheating tests) -> HIGH severity
  2. Disabled / skipped tests (it.skip, xit, commented assertions, process.exit(0)) -> HIGH severity
  3. Unfinished placeholders (TODO, FIXME, lorem ipsum, not implemented stubs) -> MEDIUM severity
  4. Dead UI (href="#", buttons without click handlers or dynamic events) -> MEDIUM severity
  5. Exposed secrets & keys (API keys, private keys, database credentials) -> CRITICAL severity

Produces structured JSON findings matching the verification database schema.
"""

import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from .ai_evaluator import AIIntakeEvaluator

# Ignored directories for scanning
IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "venv"
}

# Supported file extensions for code analysis
CODE_EXTENSIONS = {
    ".js", ".jsx", ".ts", ".tsx", ".py", ".html", ".htm", ".json", ".env", ".yaml", ".yml", ".sql"
}


@dataclass
class CheatFinding:
    """Represents a discrete scan finding with severity, source location, and description."""
    category: str        # 'hardcoded_outputs', 'disabled_tests', 'placeholders', 'dead_ui', 'exposed_keys'
    severity: str        # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    rule_id: str         # e.g. 'CHEAT-001', 'TEST-SKIP-001'
    file_path: str       # Relative path within repo
    line_number: int
    code_snippet: str
    description: str
    remediation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CheatScanner:
    """
    Comprehensive static and semantic code scanner for cheats, loopholes, and secrets.
    Dual-engine design: deterministic rule analyzer with optional Gemini AI assistance.
    """

    def __init__(self, ai_evaluator: Optional[AIIntakeEvaluator] = None):
        self.ai = ai_evaluator or AIIntakeEvaluator()

    def scan_repository(self, repo_dir: Path) -> Dict[str, Any]:
        """
        Recursively scans repository source files for cheats, disabled tests,
        placeholders, dead UI elements, and exposed credentials.
        """
        target_dir = Path(repo_dir).resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"Repository directory does not exist: {target_dir}")

        findings: List[CheatFinding] = []

        # Walk through source files
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()

                if ext in CODE_EXTENSIONS or file.startswith(".env"):
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        rel_path = str(file_path.relative_to(target_dir)).replace("\\", "/")
                        self._scan_file(file_path, rel_path, content, findings)
                    except Exception as e:
                        print(f"[CHEAT SCAN WARNING] Could not read {file_path}: {e}")

        # Group findings by severity and category
        by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
        by_category = {
            "hardcoded_outputs": [],
            "disabled_tests": [],
            "placeholders": [],
            "dead_ui": [],
            "exposed_keys": []
        }

        for f in findings:
            by_severity[f.severity].append(f.to_dict())
            by_category[f.category].append(f.to_dict())

        has_critical = len(by_severity["CRITICAL"]) > 0
        has_high = len(by_severity["HIGH"]) > 0
        passed = not (has_critical or has_high)

        # High-level summary
        if not findings:
            summary = "Clean deliverable: No cheats, loopholes, dead UI, or exposed secrets detected."
        elif has_high or has_critical:
            summary = (
                f"Cheat scan detected {len(by_severity['CRITICAL'])} CRITICAL and {len(by_severity['HIGH'])} HIGH severity issues! "
                f"Deliverable contains unauthorized test bypasses, hardcoded fake answers, or exposed credentials."
            )
        else:
            summary = (
                f"Cheat scan completed with {len(by_severity['MEDIUM'])} MEDIUM and {len(by_severity['LOW'])} LOW findings. "
                "No critical cheat attempts detected."
            )

        return {
            "status": "COMPLETED",
            "passed": passed,
            "has_critical_findings": has_critical,
            "has_high_findings": has_high,
            "total_findings": len(findings),
            "findings": [f.to_dict() for f in findings],
            "findings_by_severity": by_severity,
            "findings_by_category": by_category,
            "summary": summary
        }

    def _scan_file(self, file_path: Path, rel_path: str, content: str, findings: List[CheatFinding]):
        """Runs scanner rules against a single file content."""
        lines = content.splitlines()

        # 1. Exposed Secrets & Keys
        self._scan_exposed_secrets(rel_path, lines, findings)

        # 2. Disabled or Skipped Tests
        self._scan_disabled_tests(rel_path, lines, findings)

        # 3. Hardcoded Fake Answers & Test Cheats
        self._scan_hardcoded_outputs(rel_path, content, lines, findings)

        # 4. Unfinished Placeholders & Stubs
        self._scan_placeholders(rel_path, lines, findings)

        # 5. Dead UI & Non-interactive Elements (HTML/JSX)
        if file_path.suffix.lower() in [".html", ".htm", ".jsx", ".tsx"]:
            self._scan_dead_ui(rel_path, lines, findings)

    def _scan_hardcoded_outputs(
        self,
        rel_path: str,
        full_content: str,
        lines: List[str],
        findings: List[CheatFinding]
    ):
        """
        Detects hardcoded fake answers that return static arrays/objects matching
        specific test cases instead of executing dynamic dataset logic.
        """
        # Pattern 1: Explicit cheat comments or bypass identifiers
        cheat_comment_re = re.compile(
            r"//\s*(?:⚠️\s*)?(?:CHEAT|HARDCODED\s+(?:FAKE|MOCK|TEST|ANSWER)|FAKE\s+ANSWER|MOCK\s+BYPASS|STATIC\s+BYPASS)",
            re.IGNORECASE
        )

        for line_idx, line in enumerate(lines, 1):
            if cheat_comment_re.search(line):
                findings.append(CheatFinding(
                    category="hardcoded_outputs",
                    severity="HIGH",
                    rule_id="CHEAT-COMMENT-001",
                    file_path=rel_path,
                    line_number=line_idx,
                    code_snippet=line.strip(),
                    description="Hardcoded cheat or bypass comment identified in source code.",
                    remediation="Remove cheat shortcuts and implement real dynamic business logic."
                ))

        # Pattern 2: Conditional branch checking specific test argument equality followed by static mock array return
        # E.g. if (category === "software") return [{ id: "fake_sw_1" ... }]
        mock_return_re = re.compile(
            r"if\s*\([^)]+(?:===|==)[^)]+\)\s*\{\s*return\s*\[\s*\{[^}]*id:\s*['\"]fake",
            re.IGNORECASE
        )
        if mock_return_re.search(full_content):
            # Locate exact line in source code (excluding comment lines)
            for line_idx, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped.startswith("//") and not stripped.startswith("/*") and not stripped.startswith("*"):
                    if "fake_" in line.lower() or "fake" in line.lower():
                        findings.append(CheatFinding(
                            category="hardcoded_outputs",
                            severity="HIGH",
                            rule_id="CHEAT-HARDCODED-MOCK-002",
                            file_path=rel_path,
                            line_number=line_idx,
                            code_snippet=stripped,
                            description="Hardcoded fake answer: function bypasses dynamic data filtering and returns static mock objects.",
                            remediation="Filter the actual database or dataset dynamically instead of returning static test answers."
                        ))
                        break

        # Pattern 3: Static bypass returning pre-calculated answer on specific inputs
        static_test_branch = re.compile(
            r"if\s*\((?:category|rating|minRating|price|id)\s*===?\s*['\"][^'\"]+['\"]\)\s*\{\s*return\s*\[",
            re.IGNORECASE
        )
        for line_idx, line in enumerate(lines, 1):
            if static_test_branch.search(line):
                # Ensure it's not already reported
                if not any(f.file_path == rel_path and f.line_number == line_idx for f in findings):
                    findings.append(CheatFinding(
                        category="hardcoded_outputs",
                        severity="HIGH",
                        rule_id="CHEAT-BRANCH-STUB-003",
                        file_path=rel_path,
                        line_number=line_idx,
                        code_snippet=line.strip(),
                        description="Input-specific branch returning hardcoded static array instead of evaluating dataset.",
                        remediation="Implement genuine parameter evaluation and query execution."
                    ))

    def _scan_disabled_tests(self, rel_path: str, lines: List[str], findings: List[CheatFinding]):
        """Detects disabled tests, skipped suites, commented assertions, and forced zero exits."""
        # Only check test directories or files with test in name
        is_test_file = "test" in rel_path.lower() or "spec" in rel_path.lower()

        test_skip_re = re.compile(
            r"\b(?:test\.skip|it\.skip|describe\.skip|xit|xtest|xdescribe)\s*\(",
            re.IGNORECASE
        )
        commented_assert_re = re.compile(
            r"^\s*//\s*(?:assert|expect|self\.assert|assert\.)\b"
        )
        process_exit_re = re.compile(
            r"process\.exit\(\s*0\s*\)"
        )

        for line_idx, line in enumerate(lines, 1):
            # Check for skipped tests
            if is_test_file and test_skip_re.search(line):
                findings.append(CheatFinding(
                    category="disabled_tests",
                    severity="HIGH",
                    rule_id="TEST-SKIP-001",
                    file_path=rel_path,
                    line_number=line_idx,
                    code_snippet=line.strip(),
                    description="Disabled or skipped test found (e.g. it.skip / xit / describe.skip).",
                    remediation="Re-enable skipped tests and ensure deliverable satisfies test expectations."
                ))

            # Check for commented-out assertion checks
            if is_test_file and commented_assert_re.search(line):
                findings.append(CheatFinding(
                    category="disabled_tests",
                    severity="HIGH",
                    rule_id="TEST-COMMENTED-ASSERT-002",
                    file_path=rel_path,
                    line_number=line_idx,
                    code_snippet=line.strip(),
                    description="Commented-out test assertion detected. Verification criteria may have been disabled.",
                    remediation="Uncomment assertions and verify code passes without modification of acceptance suite."
                ))

            # Check for forced clean exit inside catch blocks or unconditional skips
            if is_test_file and process_exit_re.search(line):
                prev_context = "\n".join(lines[max(0, line_idx - 6):line_idx - 1]).lower()
                # If inside a catch block or without checking failure/passed status
                if "catch" in prev_context or (
                    "failed" not in prev_context and
                    "failures" not in prev_context and
                    "error" not in prev_context and
                    "passed" not in prev_context
                ):
                    findings.append(CheatFinding(
                        category="disabled_tests",
                        severity="HIGH",
                        rule_id="TEST-FORCED-EXIT-003",
                        file_path=rel_path,
                        line_number=line_idx,
                        code_snippet=line.strip(),
                        description="Forced clean exit (process.exit(0)) detected inside test suite, potentially masking test failures.",
                        remediation="Allow test framework to manage exit codes naturally based on assertion results."
                    ))

    def _scan_placeholders(self, rel_path: str, lines: List[str], findings: List[CheatFinding]):
        """Detects unfinished code placeholders (TODO, FIXME, lorem ipsum, NotImplemented stubs)."""
        placeholder_re = re.compile(
            r"\b(TODO|FIXME|XXX|TBD|HACK)\b\s*[:\s-](.*)",
            re.IGNORECASE
        )
        lorem_re = re.compile(r"\blorem\s+ipsum\b", re.IGNORECASE)
        not_impl_re = re.compile(r"(?:throw\s+new\s+Error\(['\"]not\s+implemented|raise\s+NotImplementedError)", re.IGNORECASE)

        for line_idx, line in enumerate(lines, 1):
            # Ignore test files for placeholder warnings to prevent test fixture noise
            if "test/" in rel_path or "test_" in rel_path:
                continue

            m_todo = placeholder_re.search(line)
            if m_todo:
                findings.append(CheatFinding(
                    category="placeholders",
                    severity="MEDIUM",
                    rule_id="STUB-TODO-001",
                    file_path=rel_path,
                    line_number=line_idx,
                    code_snippet=line.strip()[:100],
                    description=f"Unresolved developer placeholder: '{m_todo.group(1)}'.",
                    remediation="Complete the unfinished implementation before final escrow release."
                ))

            if lorem_re.search(line):
                findings.append(CheatFinding(
                    category="placeholders",
                    severity="MEDIUM",
                    rule_id="STUB-LOREM-002",
                    file_path=rel_path,
                    line_number=line_idx,
                    code_snippet=line.strip()[:100],
                    description="Placeholder 'Lorem Ipsum' dummy text detected in deliverable source.",
                    remediation="Replace placeholder text with client-agreed copy or functional dynamic content."
                ))

            if not_impl_re.search(line):
                findings.append(CheatFinding(
                    category="placeholders",
                    severity="HIGH",
                    rule_id="STUB-NOT-IMPLEMENTED-003",
                    file_path=rel_path,
                    line_number=line_idx,
                    code_snippet=line.strip()[:100],
                    description="Unimplemented function stub throwing 'Not Implemented' exception.",
                    remediation="Provide the full implementation for all contractually defined functions."
                ))

    def _scan_dead_ui(self, rel_path: str, lines: List[str], findings: List[CheatFinding]):
        """Detects dead, non-interactive UI elements (href='#', buttons without handlers)."""
        dead_link_re = re.compile(r"<a\s+[^>]*href=['\"](?:#|javascript:void\(0\);?)['\"][^>]*>", re.IGNORECASE)
        dead_button_re = re.compile(r"<button(?:\s+class=['\"][^'\"]*['\"])?\s*>", re.IGNORECASE)

        for line_idx, line in enumerate(lines, 1):
            if dead_link_re.search(line):
                findings.append(CheatFinding(
                    category="dead_ui",
                    severity="MEDIUM",
                    rule_id="UI-DEAD-LINK-001",
                    file_path=rel_path,
                    line_number=line_idx,
                    code_snippet=line.strip()[:100],
                    description="Dead UI link (<a href='#'>) with no functional destination URL.",
                    remediation="Connect the anchor tag to a real application route or interactive event handler."
                ))

            if dead_button_re.search(line) and "onclick" not in line.lower() and "type=" not in line.lower():
                findings.append(CheatFinding(
                    category="dead_ui",
                    severity="LOW",
                    rule_id="UI-UNBOUND-BUTTON-002",
                    file_path=rel_path,
                    line_number=line_idx,
                    code_snippet=line.strip()[:100],
                    description="Button without explicit click handler, type, or event binding.",
                    remediation="Attach appropriate event listeners or form action attributes."
                ))

    def _scan_exposed_secrets(self, rel_path: str, lines: List[str], findings: List[CheatFinding]):
        """Detects high-risk leaked secrets, API keys, private keys, and passwords."""
        # Skip scanning git or documentation files
        if rel_path.endswith(".md") or "README" in rel_path:
            return

        secret_patterns = [
            (
                "SECRET-PRIVATE-KEY-001",
                re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"),
                "CRITICAL",
                "Unencrypted private key detected in repository.",
                "Immediately rotate the exposed key and store credentials in secure environment vaults."
            ),
            (
                "SECRET-AWS-KEY-002",
                re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
                "CRITICAL",
                "Exposed AWS Access Key ID detected.",
                "Revoke and rotate AWS IAM credentials."
            ),
            (
                "SECRET-OPENAI-KEY-003",
                re.compile(r"\b(sk-[A-Za-z0-9]{32,})\b"),
                "CRITICAL",
                "Exposed OpenAI API Secret Key.",
                "Revoke compromised API key immediately."
            ),
            (
                "SECRET-GOOGLE-KEY-004",
                re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b"),
                "CRITICAL",
                "Exposed Google Cloud / Gemini API key.",
                "Revoke and rotate the exposed API key in Google Cloud Console."
            ),
            (
                "SECRET-GITHUB-PAT-005",
                re.compile(r"\b(gh[pous]_[0-9a-zA-Z]{36})\b"),
                "CRITICAL",
                "Exposed GitHub Personal Access Token.",
                "Revoke the token from GitHub Developer Settings."
            )
        ]

        for line_idx, line in enumerate(lines, 1):
            for rule_id, pattern, severity, desc, remed in secret_patterns:
                m = pattern.search(line)
                if m:
                    # Obfuscate matched secret in snippet
                    secret_val = m.group(0)
                    masked = secret_val[:4] + "..." + secret_val[-4:] if len(secret_val) > 8 else "***"
                    snippet = line.replace(secret_val, masked).strip()

                    findings.append(CheatFinding(
                        category="exposed_keys",
                        severity=severity,
                        rule_id=rule_id,
                        file_path=rel_path,
                        line_number=line_idx,
                        code_snippet=snippet,
                        description=desc,
                        remediation=remed
                    ))
