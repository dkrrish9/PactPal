"""
Referee Subsystem Package
Linked Tasks: C34 / C47 / A10 / A14
"""

from .models import DecisionOutcome, RefereeDecision, FeatureDecision
from .decision_engine import RefereeDecisionEngine
from .formatter import generate_conversational_explanation, generate_plain_text_summary
from .negotiated_release import (
    SellerChoice,
    SettlementOffer,
    ChoiceResolution,
    NegotiatedReleaseEngine
)

__all__ = [
    "DecisionOutcome",
    "RefereeDecision",
    "FeatureDecision",
    "RefereeDecisionEngine",
    "generate_conversational_explanation",
    "generate_plain_text_summary",
    "SellerChoice",
    "SettlementOffer",
    "ChoiceResolution",
    "NegotiatedReleaseEngine"
]
