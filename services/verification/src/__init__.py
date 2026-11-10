"""
PactPal Verification Pipeline Package
"""

from .models import (
    IntakeRequest,
    SubmissionRecord,
    AIIntakeAnalysis,
    VerificationReport
)
from .intake import (
    StageAIntakeProcessor,
    IntakeValidationError,
    SubmissionLimitExceededError
)
from .ai_evaluator import AIIntakeEvaluator
from .sandbox import (
    IsolatedWorkspace,
    WorkspaceSecurityError,
    WorkspaceExecutionResult
)
from .runner import VerificationPipelineRunner
from .test_runner import StageCTestSuiteProcessor
from .screenshot_capture import (
    HeadlessScreenshotCapture,
    BrowserNotFoundError,
    ScreenshotCaptureError,
    BrowserDetector
)

__all__ = [
    "IntakeRequest",
    "SubmissionRecord",
    "AIIntakeAnalysis",
    "VerificationReport",
    "StageAIntakeProcessor",
    "IntakeValidationError",
    "SubmissionLimitExceededError",
    "AIIntakeEvaluator",
    "IsolatedWorkspace",
    "WorkspaceSecurityError",
    "WorkspaceExecutionResult",
    "VerificationPipelineRunner",
    "StageCTestSuiteProcessor",
    "HeadlessScreenshotCapture",
    "BrowserNotFoundError",
    "ScreenshotCaptureError",
    "BrowserDetector"
]
