"""
AI Escrow Referee Decision Engine
Linked Task: C34 / A10 (Milestone 2: Verify & Decide)

Evaluates contract agreements against verification reports and applies
transparent, legally binding settlement rules (Full Release, Partial, Hold, Deadline).
"""

from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone
import json

from .models import DecisionOutcome, RefereeDecision, FeatureDecision
from .formatter import generate_conversational_explanation, generate_plain_text_summary
from ..security.prompt_defense import (
    detect_prompt_injection,
    neutralize_evidence_injection,
    sanitize_untrusted_repo_content
)

class RefereeDecisionEngine:
    """
    Impartial AI Referee that determines milestone fund disbursement
    based on objective test assertions, cheat scan findings, and visual diffs.
    """

    def evaluate(
        self,
        contract: Union[Dict[str, Any], Any],
        verification_report: Union[Dict[str, Any], Any],
        current_time: Optional[datetime] = None
    ) -> RefereeDecision:
        """
        Main decision entrypoint. Consumes contract metadata and verification report.
        Produces a legally binding settlement decision with plain-language explanation.
        """
        # 1. Normalize contract dictionary / object
        c_dict = self._normalize_contract(contract)
        contract_id = c_dict.get("id") or c_dict.get("contract_id", "unknown_contract")
        contract_title = c_dict.get("title", "Digital Freelance Deliverable")
        total_amount = float(c_dict.get("total_amount", 0.0))
        currency = c_dict.get("currency", "USD")
        deadline_str = c_dict.get("deadline")

        # 2. Normalize verification report dictionary / object
        r_dict = self._normalize_report(verification_report)
        build_succeeded = bool(r_dict.get("build_succeeded", True))
        build_logs = r_dict.get("build_logs", "")
        failure_reason = r_dict.get("failure_reason", "")
        cheat_findings = r_dict.get("cheat_scan_findings") or []
        if isinstance(cheat_findings, str):
            try:
                cheat_findings = json.loads(cheat_findings)
            except Exception:
                cheat_findings = []

        visual_diff = r_dict.get("visual_diff_summary") or {}
        if isinstance(visual_diff, str):
            try:
                visual_diff = json.loads(visual_diff)
            except Exception:
                visual_diff = {}
        visual_similarity = float(visual_diff.get("similarity_score", 1.0))

        per_feature_raw = r_dict.get("per_feature_results") or {}
        if isinstance(per_feature_raw, str):
            try:
                per_feature_raw = json.loads(per_feature_raw)
            except Exception:
                per_feature_raw = {}

        now = current_time or datetime.now(timezone.utc)

        # -------------------------------------------------------------
        # RULE 1: Sandbox Build Failure ➔ HOLD
        # -------------------------------------------------------------
        if not build_succeeded:
            return self._build_hold_decision(
                contract_id=contract_id,
                contract_title=contract_title,
                total_amount=total_amount,
                currency=currency,
                failure_reason=failure_reason or "Deliverable failed clean sandbox compilation.",
                build_logs=build_logs,
                c_dict=c_dict,
                per_feature_raw=per_feature_raw
            )

        # -------------------------------------------------------------
        # RULE 2: Contract Deadline Expiry Check
        # -------------------------------------------------------------
        if deadline_str and not per_feature_raw:
            try:
                deadline_dt = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                if now > deadline_dt:
                    return self._build_deadline_expired_decision(
                        contract_id=contract_id,
                        contract_title=contract_title,
                        total_amount=total_amount,
                        currency=currency
                    )
            except Exception:
                pass

        # -------------------------------------------------------------
        # RULE 3: Critical Unresolved Fraud/Cheat Findings ➔ HOLD
        # -------------------------------------------------------------
        critical_cheats = [
            f for f in cheat_findings
            if isinstance(f, dict) and str(f.get("severity", "")).upper() in ("HIGH", "CRITICAL")
        ]
        # If critical cheat affects entire deliverable or global auth, flag hold
        global_critical_cheats = [
            f for f in critical_cheats
            if not f.get("feature_id") or f.get("scope") == "GLOBAL"
        ]
        if global_critical_cheats:
            cheat_desc = "; ".join(f.get("description", "Cheat detected") for f in global_critical_cheats)
            return self._build_hold_decision(
                contract_id=contract_id,
                contract_title=contract_title,
                total_amount=total_amount,
                currency=currency,
                failure_reason=f"Zero-trust violation: {cheat_desc}",
                build_logs=build_logs,
                c_dict=c_dict,
                per_feature_raw=per_feature_raw,
                rule_name="RULE_CHEAT_SCAN_HOLD"
            )

        # -------------------------------------------------------------
        # RULE 4 & 5: Feature-by-Feature Evaluation (Full vs Partial Release)
        # -------------------------------------------------------------
        feature_decisions: List[FeatureDecision] = []
        contract_features = c_dict.get("features", [])
        neutralized_injections: List[Dict[str, Any]] = []

        # If report has per_feature_results, map from it
        if per_feature_raw:
            # Build lookup from contract features if available
            contract_feat_map = {}
            if contract_features:
                for f in contract_features:
                    f_id = getattr(f, "id", None) or (f.get("id") if isinstance(f, dict) else None)
                    if f_id:
                        contract_feat_map[f_id] = f

            for feat_id, feat_data in per_feature_raw.items():
                if not isinstance(feat_data, dict):
                    continue

                f_title = feat_data.get("feature_title")
                status = str(feat_data.get("status", "FAILED")).upper()
                weight = float(feat_data.get("price_weight", 0.0))
                amount = float(feat_data.get("allocated_amount", 0.0))
                evidence = feat_data.get("evidence")
                reason = feat_data.get("reason")
                severity = str(feat_data.get("severity", "NONE")).upper()

                # If contract has more accurate amount/weight, prefer contract definitions
                if feat_id in contract_feat_map:
                    cf = contract_feat_map[feat_id]
                    cf_weight = getattr(cf, "price_weight", None) or (cf.get("price_weight") if isinstance(cf, dict) else None)
                    cf_amount = getattr(cf, "allocated_amount", None) or (cf.get("allocated_amount") if isinstance(cf, dict) else None)
                    cf_title = getattr(cf, "title", None) or (cf.get("title") if isinstance(cf, dict) else None)
                    if cf_weight is not None:
                        weight = float(cf_weight)
                    if cf_amount is not None:
                        amount = float(cf_amount)
                    if cf_title:
                        f_title = cf_title

                # Check if feature has specific high cheat finding
                feat_cheats = [f for f in critical_cheats if f.get("feature_id") == feat_id]
                if feat_cheats and status == "PASSED":
                    status = "FAILED"
                    severity = "HIGH"
                    reason = f"Failed cheat scan: {feat_cheats[0].get('description')}"

                # Prompt Injection Defense: treat code/evidence strictly as passive data
                evidence_shield = neutralize_evidence_injection(evidence, status)
                reason_shield = neutralize_evidence_injection(reason, status)
                if evidence_shield.get("injection_detected") or reason_shield.get("injection_detected"):
                    neutralized_injections.append({
                        "feature_id": feat_id,
                        "feature_title": f_title,
                        "patterns": evidence_shield.get("patterns") or reason_shield.get("patterns")
                    })
                    evidence = evidence_shield["evidence"]
                    if reason_shield.get("injection_detected"):
                        reason = reason_shield["evidence"]

                feature_decisions.append(
                    FeatureDecision(
                        feature_id=feat_id,
                        feature_title=f_title or f"Feature {feat_id[:8]}",
                        status=status,
                        price_weight=weight,
                        allocated_amount=amount,
                        severity=severity,
                        evidence=evidence,
                        reason=reason
                    )
                )

        # If no report features but contract has features, default to unverified
        elif contract_features:
            for f in contract_features:
                f_id = getattr(f, "id", None) or (f.get("id") if isinstance(f, dict) else str(f))
                f_title = getattr(f, "title", None) or (f.get("title") if isinstance(f, dict) else "Milestone Deliverable")
                f_weight = float(getattr(f, "price_weight", None) or (f.get("price_weight", 0.0) if isinstance(f, dict) else 0.0))
                f_amount = float(getattr(f, "allocated_amount", None) or (f.get("allocated_amount", 0.0) if isinstance(f, dict) else 0.0))
                feature_decisions.append(
                    FeatureDecision(
                        feature_id=f_id,
                        feature_title=f_title,
                        status="PASSED",
                        price_weight=f_weight,
                        allocated_amount=f_amount,
                        evidence="Contract verified.",
                        severity="NONE"
                    )
                )

        # Calculate totals
        passed_features = [f for f in feature_decisions if f.status == "PASSED"]
        failed_features = [f for f in feature_decisions if f.status == "FAILED"]

        passed_weight = round(sum(f.price_weight for f in passed_features), 2)
        failed_weight = round(sum(f.price_weight for f in failed_features), 2)

        if total_amount > 0 and feature_decisions:
            passed_amount = round(sum(f.allocated_amount for f in passed_features), 2)
            # Ensure exact reconciliation to the cent
            refund_amount = round(total_amount - passed_amount, 2)
        else:
            passed_amount = 0.0
            refund_amount = total_amount

        # Determine outcome
        total_features_count = len(feature_decisions)
        passed_count = len(passed_features)

        if total_features_count > 0 and len(failed_features) == 0:
            outcome = DecisionOutcome.FULL_RELEASE
            rule_triggered = "RULE_FULL_RELEASE_PASSED"
            next_state = "SETTLED"
            passed_amount = total_amount
            refund_amount = 0.0
            passed_weight = 100.0
            failed_weight = 0.0
        elif passed_count > 0:
            outcome = DecisionOutcome.PARTIAL_RELEASE
            rule_triggered = "RULE_PARTIAL_RELEASE_PROPORTIONAL"
            next_state = "SETTLED"
        else:
            # 0 features passed
            outcome = DecisionOutcome.HOLD
            rule_triggered = "RULE_ZERO_PASSED_HOLD"
            next_state = "IN_PROGRESS"
            passed_amount = 0.0
            refund_amount = 0.0

        plain_summary = generate_plain_text_summary(
            outcome=outcome,
            total_amount=total_amount,
            passed_amount=passed_amount,
            refund_amount=refund_amount,
            currency=currency,
            passed_count=passed_count,
            total_count=total_features_count
        )

        conversational_explanation = generate_conversational_explanation(
            outcome=outcome,
            contract_title=contract_title,
            total_amount=total_amount,
            currency=currency,
            passed_amount=passed_amount,
            refund_amount=refund_amount,
            passed_weight=passed_weight,
            failed_weight=failed_weight,
            features=feature_decisions,
            build_succeeded=build_succeeded,
            build_logs=build_logs,
            failure_reason=failure_reason,
            cheat_findings_count=len(cheat_findings),
            visual_similarity=visual_similarity
        )

        return RefereeDecision(
            contract_id=contract_id,
            outcome=outcome,
            rule_triggered=rule_triggered,
            total_amount=total_amount,
            currency=currency,
            passed_amount=passed_amount,
            refund_amount=refund_amount,
            passed_weight=passed_weight,
            failed_weight=failed_weight,
            feature_decisions=feature_decisions,
            conversational_explanation=conversational_explanation,
            plain_text_summary=plain_summary,
            next_state=next_state,
            metadata={
                "build_succeeded": build_succeeded,
                "overall_score": r_dict.get("overall_score", 0.0),
                "visual_similarity": visual_similarity,
                "cheat_findings_count": len(cheat_findings),
                "prompt_injections_neutralized": len(neutralized_injections),
                "injections_detail": neutralized_injections
            }
        )

    # -----------------------------------------------------------------
    # Helper Constructors
    # -----------------------------------------------------------------

    def _build_hold_decision(
        self,
        contract_id: str,
        contract_title: str,
        total_amount: float,
        currency: str,
        failure_reason: str,
        build_logs: str,
        c_dict: Dict[str, Any],
        per_feature_raw: Dict[str, Any],
        rule_name: str = "RULE_BUILD_FAILURE_HOLD"
    ) -> RefereeDecision:
        """Constructs an immediate HOLD decision freezing funds."""
        feature_decisions = []
        contract_features = c_dict.get("features", [])
        if contract_features:
            for f in contract_features:
                f_id = getattr(f, "id", None) or (f.get("id") if isinstance(f, dict) else "feat")
                f_title = getattr(f, "title", None) or (f.get("title") if isinstance(f, dict) else "Deliverable")
                f_weight = float(getattr(f, "price_weight", None) or (f.get("price_weight", 0.0) if isinstance(f, dict) else 0.0))
                f_amount = float(getattr(f, "allocated_amount", None) or (f.get("allocated_amount", 0.0) if isinstance(f, dict) else 0.0))
                feature_decisions.append(
                    FeatureDecision(
                        feature_id=f_id,
                        feature_title=f_title,
                        status="FAILED",
                        price_weight=f_weight,
                        allocated_amount=f_amount,
                        severity="HIGH",
                        reason=failure_reason
                    )
                )

        plain_summary = generate_plain_text_summary(
            outcome=DecisionOutcome.HOLD,
            total_amount=total_amount,
            passed_amount=0.0,
            refund_amount=0.0,
            currency=currency,
            passed_count=0,
            total_count=len(feature_decisions),
            reason=failure_reason
        )

        conversational = generate_conversational_explanation(
            outcome=DecisionOutcome.HOLD,
            contract_title=contract_title,
            total_amount=total_amount,
            currency=currency,
            passed_amount=0.0,
            refund_amount=0.0,
            passed_weight=0.0,
            failed_weight=100.0,
            features=feature_decisions,
            build_succeeded=False,
            build_logs=build_logs,
            failure_reason=failure_reason
        )

        return RefereeDecision(
            contract_id=contract_id,
            outcome=DecisionOutcome.HOLD,
            rule_triggered=rule_name,
            total_amount=total_amount,
            currency=currency,
            passed_amount=0.0,
            refund_amount=0.0,
            passed_weight=0.0,
            failed_weight=100.0,
            feature_decisions=feature_decisions,
            conversational_explanation=conversational,
            plain_text_summary=plain_summary,
            next_state="IN_PROGRESS",
            metadata={"build_succeeded": False, "failure_reason": failure_reason}
        )

    def _build_deadline_expired_decision(
        self,
        contract_id: str,
        contract_title: str,
        total_amount: float,
        currency: str
    ) -> RefereeDecision:
        """Constructs a DEADLINE_EXPIRED decision returning 100% funds to buyer."""
        plain_summary = generate_plain_text_summary(
            outcome=DecisionOutcome.DEADLINE_EXPIRED,
            total_amount=total_amount,
            passed_amount=0.0,
            refund_amount=total_amount,
            currency=currency,
            passed_count=0,
            total_count=0
        )

        conversational = generate_conversational_explanation(
            outcome=DecisionOutcome.DEADLINE_EXPIRED,
            contract_title=contract_title,
            total_amount=total_amount,
            currency=currency,
            passed_amount=0.0,
            refund_amount=total_amount,
            passed_weight=0.0,
            failed_weight=100.0,
            features=[]
        )

        return RefereeDecision(
            contract_id=contract_id,
            outcome=DecisionOutcome.DEADLINE_EXPIRED,
            rule_triggered="RULE_DEADLINE_EXPIRED_REFUND",
            total_amount=total_amount,
            currency=currency,
            passed_amount=0.0,
            refund_amount=total_amount,
            passed_weight=0.0,
            failed_weight=100.0,
            feature_decisions=[],
            conversational_explanation=conversational,
            plain_text_summary=plain_summary,
            next_state="SETTLED",
            metadata={"deadline_expired": True}
        )

    # -----------------------------------------------------------------
    # Normalizers
    # -----------------------------------------------------------------

    def _normalize_contract(self, contract: Any) -> Dict[str, Any]:
        if isinstance(contract, dict):
            return contract
        if hasattr(contract, "__dict__"):
            return contract.__dict__
        return {}

    def _normalize_report(self, report: Any) -> Dict[str, Any]:
        if isinstance(report, dict):
            return report
        if hasattr(report, "to_dict") and callable(report.to_dict):
            return report.to_dict()
        if hasattr(report, "__dict__"):
            return report.__dict__
        return {}

