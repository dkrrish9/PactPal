"""
AI Price Negotiator
Linked Task: C38 / A12 (Milestone 3: Money & Extras)

Evaluates mid-project scope change requests against original contracts,
calculating market-fair price increments, deadline extensions, and objective reasoning.
"""

import os
import re
import json
import urllib.request
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone

from .models import ComplexityLevel, ChangeRequestProposal

# Market pricing heuristics (hourly baseline: $50/hr USD)
HOURLY_RATE_DEFAULT = 50.0

COMPLEXITY_RULES = [
    {
        "keywords": ["payment", "stripe", "paypal", "payout", "subscription", "billing", "checkout", "escrow"],
        "level": ComplexityLevel.HIGH,
        "hours": 48,
        "base_price": 400.00,
        "category": "Payment Processing & Financial Rails",
        "tasks": ["Gateway credential configuration", "Webhook signature verification", "Idempotency handling", "Sandbox reconciliation tests"],
        "test_template": "Execute test transaction in sandbox; verify webhook receipt and order status update."
    },
    {
        "keywords": ["oauth", "google auth", "apple auth", "jwt", "session", "login", "authentication", "sso", "2fa"],
        "level": ComplexityLevel.MEDIUM,
        "hours": 32,
        "base_price": 250.00,
        "category": "Authentication & Session Security",
        "tasks": ["OAuth2 provider configuration", "Secure token cookie handling", "User identity linking", "Protected route middleware"],
        "test_template": "Authenticate via OAuth callback; verify valid session cookie returned and user profile saved."
    },
    {
        "keywords": ["websocket", "realtime", "real-time", "socket", "chat", "live feed", "streaming"],
        "level": ComplexityLevel.HIGH,
        "hours": 40,
        "base_price": 350.00,
        "category": "Real-Time Infrastructure",
        "tasks": ["Socket server setup", "Connection reconnection logic", "Room message dispatching", "Client event listeners"],
        "test_template": "Establish socket connection; broadcast test event and assert message receipt within 500ms."
    },
    {
        "keywords": ["database", "migration", "postgres", "sql", "model", "schema", "prisma", "foreign key"],
        "level": ComplexityLevel.MEDIUM,
        "hours": 24,
        "base_price": 200.00,
        "category": "Database Architecture & Persistence",
        "tasks": ["Schema migration file creation", "ORM model mapping", "Index optimization", "Data integrity constraints"],
        "test_template": "Apply migration cleanly; verify foreign key constraints and query execution index speed."
    },
    {
        "keywords": ["dark mode", "theme", "responsive", "css", "tailwind", "layout", "animation", "figma styling"],
        "level": ComplexityLevel.LOW,
        "hours": 16,
        "base_price": 120.00,
        "category": "UI Design & Responsive Styling",
        "tasks": ["CSS variable theme definition", "Component theme toggling", "Mobile viewport media queries", "Visual regression check"],
        "test_template": "Toggle theme switch; verify root DOM class and background color token update."
    },
    {
        "keywords": ["copy", "typo", "text", "rename", "label", "button color", "icon"],
        "level": ComplexityLevel.TRIVIAL,
        "hours": 4,
        "base_price": 40.00,
        "category": "Content & Minor Presentation",
        "tasks": ["String replacement in template", "Lint check"],
        "test_template": "Load page; assert presence of new text string in target component."
    }
]

class PriceNegotiator:
    """
    AI Negotiator that calculates objective scope differences, price increments,
    and deadline extensions for contract change requests.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = os.environ.get("GEMINI_MODEL_TEXT", "gemini-2.5-pro")

    def evaluate_change_request(
        self,
        contract: Union[Dict[str, Any], Any],
        description: str,
        proposed_by_id: Optional[str] = None,
        user_proposed_price: Optional[float] = None,
        user_proposed_hours: Optional[int] = None
    ) -> ChangeRequestProposal:
        """
        Evaluates a requested scope change against the existing contract.
        Proposes recommended extra funding, deadline hours, and market reasoning.
        """
        c_dict = self._normalize_contract(contract)
        contract_id = c_dict.get("id") or c_dict.get("contract_id", "unknown_contract")
        original_features = c_dict.get("features", [])
        total_amount = float(c_dict.get("total_amount", 1000.00))

        # Check for Gemini LLM evaluation if available
        if self._is_gemini_available():
            try:
                return self._evaluate_with_gemini(
                    contract_id=contract_id,
                    contract_title=c_dict.get("title", ""),
                    original_features=original_features,
                    description=description,
                    proposed_by_id=proposed_by_id,
                    user_proposed_price=user_proposed_price,
                    user_proposed_hours=user_proposed_hours
                )
            except Exception as e:
                # Fall back gracefully to deterministic market heuristic
                pass

        return self._evaluate_with_heuristic(
            contract_id=contract_id,
            contract_title=c_dict.get("title", "Digital Freelance Project"),
            original_features=original_features,
            description=description,
            proposed_by_id=proposed_by_id,
            user_proposed_price=user_proposed_price,
            user_proposed_hours=user_proposed_hours,
            total_amount=total_amount
        )

    def _evaluate_with_heuristic(
        self,
        contract_id: str,
        contract_title: str,
        original_features: List[Any],
        description: str,
        proposed_by_id: Optional[str],
        user_proposed_price: Optional[float],
        user_proposed_hours: Optional[int],
        total_amount: float
    ) -> ChangeRequestProposal:
        """Deterministic market rate heuristic engine."""
        desc_lower = description.lower()

        # Match complexity rule
        matched_rule = None
        for rule in COMPLEXITY_RULES:
            if any(kw in desc_lower for kw in rule["keywords"]):
                matched_rule = rule
                break

        if not matched_rule:
            # Default Medium feature
            matched_rule = {
                "level": ComplexityLevel.MEDIUM,
                "hours": 24,
                "base_price": 200.00,
                "category": "Custom Feature Development",
                "tasks": ["Component structure", "API integration", "Unit test coverage"],
                "test_template": "Verify acceptance criteria execution and return status code 200."
            }

        complexity = matched_rule["level"]
        rec_price = matched_rule["base_price"]
        rec_hours = matched_rule["hours"]

        # If user supplied proposals, evaluate variance against market benchmark
        final_price = user_proposed_price if user_proposed_price is not None and user_proposed_price > 0 else rec_price
        final_hours = user_proposed_hours if user_proposed_hours is not None and user_proposed_hours > 0 else rec_hours

        # Generate feature title from description with proper acronym casing
        def format_word(w: str) -> str:
            upper = w.upper()
            if upper in ("OAUTH", "JWT", "API", "CSS", "UI", "SQL", "DB", "REST", "SSO", "2FA"):
                return "OAuth" if upper == "OAUTH" else upper
            return w.capitalize()

        words = [format_word(w) for w in re.findall(r"[A-Za-z0-9]+", description)[:5]]
        suggested_title = " ".join(words) if words else "Additional Scope Feature"

        # Generate acceptance test
        suggested_test = matched_rule.get("test_template", "Verify automated test assertions pass.")

        # Relative weight suggestion
        relative_weight = round((final_price / (total_amount + final_price)) * 100.0, 1)

        # Build comprehensive AI Reasoning
        reasoning_lines = [
            f"### 🤖 AI Price Negotiator Scope Assessment",
            f"**Requested Scope**: \"{description}\"",
            f"**Classification**: `{matched_rule['category']}` (Complexity: **{complexity.value}**)",
            "",
            "#### 📊 Cost & Timeline Breakdown",
            f"- **Recommended Extra Funding**: `${rec_price:,.2f} USD` (Estimated Dev Effort: ~{rec_hours} hours @ ${HOURLY_RATE_DEFAULT:.0f}/hr)",
            f"- **Recommended Deadline Extension**: `+{rec_hours} hours`",
            "",
            "#### 🛠️ Required Implementation Tasks:"
        ]
        for task in matched_rule.get("tasks", []):
            reasoning_lines.append(f"  1. {task}")

        if user_proposed_price is not None or user_proposed_hours is not None:
            reasoning_lines.append("")
            reasoning_lines.append("#### ⚖️ Evaluation of User Proposal:")
            if user_proposed_price is not None:
                diff = user_proposed_price - rec_price
                if abs(diff) < 30.0:
                    reasoning_lines.append(f"- Proposed price `${user_proposed_price:,.2f}` aligns closely with market baseline (`${rec_price:,.2f}`).")
                elif diff > 0:
                    reasoning_lines.append(f"- Proposed price `${user_proposed_price:,.2f}` is higher than market benchmark (+${diff:,.2f}), reflecting premium delivery.")
                else:
                    reasoning_lines.append(f"- Proposed price `${user_proposed_price:,.2f}` is below standard market baseline (-${abs(diff):,.2f}).")
            if user_proposed_hours is not None:
                reasoning_lines.append(f"- Proposed timeline `+{user_proposed_hours}h` vs recommended `+{rec_hours}h`.")

        reasoning_lines.append("")
        reasoning_lines.append("#### 📜 Verification Guideline:")
        reasoning_lines.append(f"If accepted, this scope will be appended to the checklist with the acceptance test: `{suggested_test}`")

        ai_reasoning = "\n".join(reasoning_lines)

        return ChangeRequestProposal(
            contract_id=contract_id,
            description=description,
            proposed_price=final_price,
            proposed_extra_time_hours=final_hours,
            ai_reasoning=ai_reasoning,
            complexity=complexity,
            suggested_feature_title=suggested_title,
            suggested_acceptance_test=suggested_test,
            suggested_weight_percent=relative_weight,
            proposed_by_id=proposed_by_id,
            metadata={
                "benchmark_price": rec_price,
                "benchmark_hours": rec_hours,
                "category": matched_rule["category"]
            }
        )

    def _is_gemini_available(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("your_"))

    def _evaluate_with_gemini(
        self,
        contract_id: str,
        contract_title: str,
        original_features: List[Any],
        description: str,
        proposed_by_id: Optional[str],
        user_proposed_price: Optional[float],
        user_proposed_hours: Optional[int]
    ) -> ChangeRequestProposal:
        """Invokes Google Gemini API to analyze scope diff and price dynamically."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        prompt = f"""
You are the AI Price Negotiator for PactPal, an automated escrow referee.
A buyer or seller has requested a scope change mid-project.

Existing Contract: {contract_title}
Original Features: {json.dumps([f.get('title') if isinstance(f, dict) else getattr(f, 'title', str(f)) for f in original_features])}

Requested Scope Change:
\"\"\"
{description}
\"\"\"

Analyze the scope diff against original features and return strictly JSON:
{{
  "complexity": "TRIVIAL|LOW|MEDIUM|HIGH|EXTREME",
  "proposed_price": 250.00,
  "proposed_extra_time_hours": 48,
  "suggested_feature_title": "Google OAuth Authentication",
  "suggested_acceptance_test": "Acceptance test for automated verification in isolated container",
  "ai_reasoning": "Clear explanation of why this price and time are fair based on frontend, backend, and security effort."
}}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2}
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidate = data["candidates"][0]["content"]["parts"][0]["text"]
            res_json = json.loads(candidate)

        return ChangeRequestProposal(
            contract_id=contract_id,
            description=description,
            proposed_price=float(res_json.get("proposed_price", 200.0)),
            proposed_extra_time_hours=int(res_json.get("proposed_extra_time_hours", 24)),
            ai_reasoning=res_json.get("ai_reasoning", "AI Price evaluation complete."),
            complexity=ComplexityLevel(res_json.get("complexity", "MEDIUM")),
            suggested_feature_title=res_json.get("suggested_feature_title", "New Feature"),
            suggested_acceptance_test=res_json.get("suggested_acceptance_test", "Verify feature functionality."),
            proposed_by_id=proposed_by_id
        )

    def _normalize_contract(self, contract: Any) -> Dict[str, Any]:
        if isinstance(contract, dict):
            return contract
        if hasattr(contract, "__dict__"):
            return contract.__dict__
        return {}
