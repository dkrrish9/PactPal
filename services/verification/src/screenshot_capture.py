"""
PactPal Verification Pipeline - Stage E Pre-Capture: Headless Browser Screenshots (C26)
Captures high-resolution, pixel-accurate screenshots of freelancer deliverables:
  - Multi-platform browser discovery (Chrome, Chromium, Edge on Windows/Linux/macOS)
  - Headless rendering of deliverable web pages in isolated container workspaces
  - Configurable viewports (Desktop 1280x800, Mobile 375x667)
  - Cryptographic SHA-256 fingerprinting of captured screenshots for tamper-evident proof
  - Multimodal AI visual inspection verifying non-blank rendering and UI completeness
"""

import os
import sys
import shutil
import hashlib
import tempfile
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .ai_evaluator import AIIntakeEvaluator

class BrowserNotFoundError(FileNotFoundError):
    """Raised when no compatible headless browser binary is located."""
    pass

class ScreenshotCaptureError(RuntimeError):
    """Raised when screenshot capture execution fails or produces invalid images."""
    pass

class BrowserDetector:
    """Discovers installed headless browser binaries across operating systems."""

    @classmethod
    def get_browser_binary(cls) -> str:
        # 1. Check explicit environment override
        env_bin = os.environ.get("CHROME_BIN") or os.environ.get("BROWSER_BIN")
        if env_bin and Path(env_bin).exists():
            return env_bin

        # 2. Check standard system candidates based on platform
        candidates = []
        if os.name == "nt":  # Windows
            candidates = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe")
            ]
        elif sys.platform == "darwin":  # macOS
            candidates = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Chromium.app/Contents/MacOS/Chromium"
            ]
        else:  # Linux / Render isolated container
            candidates = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium"
            ]

        # 3. Check explicit candidate paths
        for path in candidates:
            if path and Path(path).exists() and os.access(path, os.X_OK if os.name != "nt" else os.R_OK):
                return path

        # 4. Check PATH search
        for name in ["chrome", "google-chrome", "chromium", "chromium-browser", "msedge"]:
            found = shutil.which(name)
            if found:
                return found

        raise BrowserNotFoundError(
            "No compatible headless browser (Chrome, Chromium, Edge) detected on system PATH. "
            "Please ensure Google Chrome or Chromium is installed."
        )

class HeadlessScreenshotCapture:
    """Orchestrates headless browser screenshot generation and artifact fingerprinting."""

    PNG_MAGIC_BYTES = b"\x89PNG\r\n\x1a\n"

    def __init__(self, browser_binary: Optional[str] = None, ai_evaluator: Optional[AIIntakeEvaluator] = None):
        self.browser_path = browser_binary or BrowserDetector.get_browser_binary()
        self.ai = ai_evaluator or AIIntakeEvaluator()

    def capture_screenshot(
        self,
        target_url_or_file: str,
        output_image_path: Path,
        viewport_width: int = 1280,
        viewport_height: int = 800,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Launches headless browser and captures a high-resolution PNG screenshot.
        Computes SHA-256 cryptographic hash and validates PNG headers.
        """
        output_image_path = Path(output_image_path).resolve()
        output_image_path.parent.mkdir(parents=True, exist_ok=True)

        # Normalize URL
        if not target_url_or_file.startswith("http://") and not target_url_or_file.startswith("https://") and not target_url_or_file.startswith("file://"):
            local_file = Path(target_url_or_file).resolve()
            if not local_file.exists():
                raise FileNotFoundError(f"Target page file does not exist: {target_url_or_file}")
            target_url = local_file.as_uri()
        else:
            target_url = target_url_or_file

        # Ephemeral user profile directory to isolate cookies/cache
        temp_profile = tempfile.mkdtemp(prefix="pactpal_headless_profile_")

        chrome_args = [
            self.browser_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            f"--user-data-dir={temp_profile}",
            f"--window-size={viewport_width},{viewport_height}",
            f"--screenshot={output_image_path}",
            target_url
        ]

        start_time = time.time()
        try:
            # Execute browser capture
            res = subprocess.run(
                chrome_args,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            # Validate screenshot file was generated
            if not output_image_path.exists():
                raise ScreenshotCaptureError(
                    f"Headless browser exited without creating screenshot. Stderr: {res.stderr}"
                )

            file_size = output_image_path.stat().st_size
            if file_size < 100:  # Minimum valid PNG size
                raise ScreenshotCaptureError(f"Generated screenshot file is suspiciously small ({file_size} bytes).")

            # Validate PNG magic bytes header
            with open(output_image_path, "rb") as f:
                header = f.read(8)
                if header != self.PNG_MAGIC_BYTES:
                    raise ScreenshotCaptureError("Captured artifact is not a valid PNG image format.")

                # Compute SHA-256 hash for proof-of-work fingerprinting
                f.seek(0)
                sha256_hash = hashlib.sha256(f.read()).hexdigest()

            duration_ms = int((time.time() - start_time) * 1000)

            # AI Visual Inspection
            ai_assessment = self.ai.inspect_screenshot(output_image_path)

            return {
                "status": "CAPTURED",
                "target_url": target_url,
                "file_path": str(output_image_path),
                "file_name": output_image_path.name,
                "viewport": {"width": viewport_width, "height": viewport_height},
                "file_size_bytes": file_size,
                "sha256_fingerprint": sha256_hash,
                "duration_ms": duration_ms,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "ai_assessment": ai_assessment
            }

        finally:
            # Clean up ephemeral browser profile
            shutil.rmtree(temp_profile, ignore_errors=True)

    def capture_deliverable_key_pages(
        self,
        repo_dir: Path,
        evidence_dir: Path,
        viewports: Optional[List[Tuple[int, int]]] = None
    ) -> Dict[str, Any]:
        """
        Discovers all HTML entry points in the deliverable and captures screenshots across viewports.
        """
        evidence_dir = Path(evidence_dir).resolve()
        evidence_dir.mkdir(parents=True, exist_ok=True)
        viewports = viewports or [(1280, 800)]

        # 1. Discover key HTML pages in deliverable
        discovered_pages = []
        for search_subdir in ["dist", "src", "."]:
            dir_to_check = repo_dir / search_subdir
            if dir_to_check.exists():
                for html_file in dir_to_check.glob("*.html"):
                    if html_file.name not in [p["name"] for p in discovered_pages]:
                        discovered_pages.append({
                            "name": html_file.stem,
                            "path": html_file
                        })

        if not discovered_pages:
            raise ScreenshotCaptureError(f"No HTML pages discovered in repository {repo_dir}")

        captured_list = []
        total_duration = 0

        for page in discovered_pages:
            for w, h in viewports:
                image_name = f"{page['name']}_{w}x{h}.png"
                out_path = evidence_dir / image_name

                capture_res = self.capture_screenshot(
                    target_url_or_file=str(page["path"]),
                    output_image_path=out_path,
                    viewport_width=w,
                    viewport_height=h
                )
                captured_list.append(capture_res)
                total_duration += capture_res["duration_ms"]

        return {
            "status": "COMPLETED",
            "total_screenshots": len(captured_list),
            "evidence_dir": str(evidence_dir),
            "screenshots": captured_list,
            "total_duration_ms": total_duration,
            "ready_for_figma_diff": True
        }
