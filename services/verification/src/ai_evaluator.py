"""
PactPal Verification Pipeline - AI Intake Evaluator
Analyzes seller build notes, commit messages, and submission context using
Google Gemini API (or configured LLM provider) to detect sandbox escape attempts,
prompt injections, and identify safe build instructions.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from pathlib import Path
from .models import AIIntakeAnalysis

def _load_env_if_needed():
    """Load .env from project root if not already loaded."""
    if not os.environ.get("GEMINI_API_KEY"):
        env_path = Path(__file__).resolve().parents[3] / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())

class AIIntakeEvaluator:
    """Interacts with Gemini API to evaluate submission build notes and metadata."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        _load_env_if_needed()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or os.environ.get("GEMINI_MODEL_TEXT", "gemini-2.5-pro")
        self.provider = os.environ.get("AI_PROVIDER", "gemini")

    def is_ai_available(self) -> bool:
        """Check if a valid AI API key is configured."""
        return bool(self.api_key and not self.api_key.startswith("your_"))

    def evaluate_submission(
        self,
        repo_url: str,
        commit_sha: str,
        build_notes: str,
        commit_message: Optional[str] = None,
        submission_number: int = 1
    ) -> AIIntakeAnalysis:
        """
        Evaluates build notes and commit info for safety, framework requirements,
        and potential sandbox security risks.
        """
        if self.is_ai_available():
            try:
                return self._call_gemini_api(repo_url, commit_sha, build_notes, commit_message, submission_number)
            except Exception as e:
                # Log warning and fall back to semantic analyzer
                print(f"[AI EVALUATOR WARNING] Gemini API call failed: {e}. Using semantic analyzer.")

        return self._semantic_fallback_analysis(build_notes, commit_message, submission_number)

    def _call_gemini_api(
        self,
        repo_url: str,
        commit_sha: str,
        build_notes: str,
        commit_message: Optional[str],
        submission_number: int
    ) -> AIIntakeAnalysis:
        """Executes a real LLM prompt to Google Gemini API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        prompt = f"""
You are the Security & Intake Evaluator for PactPal, an automated AI Escrow Referee.
Inspect the following freelance code deliverable submission metadata:
- Repository: {repo_url}
- Commit SHA: {commit_sha}
- Submission Attempt: {submission_number} of 3
- Commit Message: {commit_message or "N/A"}
- Freelancer Build Notes:
\"\"\"
{build_notes or "None provided."}
\"\"\"

Analyze for:
1. Detected framework (e.g. Next.js, React, Node.js, Python FastAPI, static HTML).
2. Clean safe build commands.
3. Security safety flags: Any suspicious commands attempting to read environment variables, bypass tests, disable security checks, or make external outbound network requests.
4. Summary of deliverable changes (if attempt > 1).
5. Risk level: "LOW", "MEDIUM", or "HIGH".

Return strictly a JSON object with this exact schema:
{{
  "detected_framework": "string",
  "build_commands": ["string"],
  "safety_flags": ["string"],
  "summary_of_changes": "string",
  "risk_level": "LOW|MEDIUM|HIGH"
}}
"""
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidate = data["candidates"][0]["content"]["parts"][0]["text"]
            result = json.loads(candidate)
            return AIIntakeAnalysis(
                detected_framework=result.get("detected_framework", "Unknown"),
                build_commands=result.get("build_commands", ["npm run build"]),
                safety_flags=result.get("safety_flags", []),
                summary_of_changes=result.get("summary_of_changes", f"Submission attempt #{submission_number}"),
                risk_level=result.get("risk_level", "LOW"),
                ai_provider_used=f"gemini ({self.model})"
            )

    def _semantic_fallback_analysis(
        self,
        build_notes: str,
        commit_message: Optional[str],
        submission_number: int
    ) -> AIIntakeAnalysis:
        """
        Deterministic semantic inspection used when running offline or without API keys.
        Ensures malicious patterns are caught even without network access.
        """
        flags = []
        notes_lower = (build_notes or "").lower()

        # Check for dangerous or evasive directives
        SUSPICIOUS_PATTERNS = [
            ("curl", "Build notes contain external network call (curl)"),
            ("wget", "Build notes contain external network call (wget)"),
            ("export paypal", "Attempted extraction of PayPal credentials"),
            ("skip-tests", "Explicit directive requesting test execution bypass"),
            ("disable_tests", "Explicit directive attempting to disable test suite"),
            ("rm -rf", "Potentially destructive file deletion command")
        ]

        for pattern, warning in SUSPICIOUS_PATTERNS:
            if pattern in notes_lower:
                flags.append(warning)

        # Framework heuristics
        if "next" in notes_lower:
            framework = "Next.js"
            cmds = ["npm install", "npm run build"]
        elif "react" in notes_lower or "vite" in notes_lower:
            framework = "React / Vite"
            cmds = ["npm install", "npm run build"]
        elif "python" in notes_lower or "requirements.txt" in notes_lower:
            framework = "Python"
            cmds = ["pip install -r requirements.txt"]
        else:
            framework = "Node.js / Standard Web"
            cmds = ["node build.js"]

        risk_level = "HIGH" if len(flags) > 0 else "LOW"
        summary = f"Submission #{submission_number}: {commit_message or 'Standard milestone deliverable'}"

        return AIIntakeAnalysis(
            detected_framework=framework,
            build_commands=cmds,
            safety_flags=flags,
            summary_of_changes=summary,
            risk_level=risk_level,
            ai_provider_used="heuristic-semantic-engine"
        )
