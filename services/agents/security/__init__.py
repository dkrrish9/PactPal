"""
Agents Security & Defense Package
Linked Tasks: C35 / A11
"""

from .prompt_defense import (
    detect_prompt_injection,
    sanitize_untrusted_repo_content,
    wrap_as_quarantined_data,
    neutralize_evidence_injection,
    InjectionScanResult,
)

__all__ = [
    "detect_prompt_injection",
    "sanitize_untrusted_repo_content",
    "wrap_as_quarantined_data",
    "neutralize_evidence_injection",
    "InjectionScanResult",
]

