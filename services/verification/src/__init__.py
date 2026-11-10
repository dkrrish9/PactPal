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
from .visual_diff import (
    VisualDiffEngine,
    VisualDiffError,
    DEFAULT_SIMILARITY_THRESHOLD
)
from .cheat_scanner import (
    CheatScanner,
    CheatFinding
)
from .report_assembler import (
    ReportAssembler,
    CoverageAnalyzer
)
from .github_notifier import (
    GitHubFeedbackNotifier,
    GitHubNotifierError
)
from .resubmission_manager import (
    ResubmissionManager,
    SubmissionVersion
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
    "BrowserDetector",
    "VisualDiffEngine",
    "VisualDiffError",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "CheatScanner",
    "CheatFinding",
    "ReportAssembler",
    "CoverageAnalyzer",
    "GitHubFeedbackNotifier",
    "GitHubNotifierError",
    "ResubmissionManager",
    "SubmissionVersion"
]
