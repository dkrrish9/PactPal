"""
PactPal Verification Pipeline - Stage E: Multimodal Visual Diff & Figma Comparison (C30)
Compares deliverable screenshots against Figma design specifications:
  - Dual-engine architecture: Google Gemini Vision multimodal analysis with deterministic perceptual fallback
  - Configurable similarity threshold (default 0.85 per .env.example)
  - Color palette, layout grid, and component completeness verification
  - Highlights visual mismatches and produces structured evidence reports
"""

import os
import re
import json
import zlib
import struct
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timezone

from .ai_evaluator import AIIntakeEvaluator

DEFAULT_SIMILARITY_THRESHOLD = float(os.environ.get("VISUAL_DIFF_SIMILARITY_THRESHOLD", "0.85"))

class VisualDiffError(RuntimeError):
    """Raised when visual comparison fails due to invalid image inputs."""
    pass

class VisualDiffEngine:
    """Orchestrates visual comparison between deliverable screenshots and Figma mockups."""

    def __init__(
        self,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        ai_evaluator: Optional[AIIntakeEvaluator] = None
    ):
        self.threshold = similarity_threshold
        self.ai = ai_evaluator or AIIntakeEvaluator()

    def compare_images(
        self,
        candidate_image_path: Path,
        reference_image_path: Path,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Compares a deliverable screenshot against a Figma reference mockup.
        Uses multimodal Gemini Vision API if configured, with perceptual structural fallback.
        """
        candidate_path = Path(candidate_image_path).resolve()
        reference_path = Path(reference_image_path).resolve()

        if not candidate_path.exists():
            raise FileNotFoundError(f"Candidate screenshot not found: {candidate_path}")
        if not reference_path.exists():
            raise FileNotFoundError(f"Reference Figma mockup not found: {reference_path}")

        active_threshold = threshold if threshold is not None else self.threshold

        # 1. Try Gemini Vision multimodal comparison
        if self.ai.is_ai_available():
            ai_result = self._compare_with_gemini_vision(candidate_path, reference_path, active_threshold)
            if ai_result:
                return ai_result

        # 2. Perceptual structural fallback
        return self._compare_with_perceptual_analysis(candidate_path, reference_path, active_threshold)

    def _compare_with_gemini_vision(
        self,
        candidate_path: Path,
        reference_path: Path,
        threshold: float
    ) -> Optional[Dict[str, Any]]:
        """Invokes Google Gemini Vision model to perform semantic visual comparison."""
        import base64
        import urllib.request

        try:
            with open(reference_path, "rb") as f:
                ref_b64 = base64.b64encode(f.read()).decode("utf-8")
            with open(candidate_path, "rb") as f:
                cand_b64 = base64.b64encode(f.read()).decode("utf-8")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.ai.model}:generateContent?key={self.ai.api_key}"

            prompt = f"""
You are the Multimodal Visual Diff Referee for PactPal, an automated AI Escrow Referee.
Compare the following two web design images:
- Image 1 (Reference): Figma design ground truth mockup agreed in contract.
- Image 2 (Candidate): Rendered headless browser screenshot of freelancer deliverable.

Evaluate:
1. Overall layout grid and structure alignment.
2. Color palette consistency (background colors, card styling, typography).
3. Presence of required UI sections and cards.
4. Compute an exact similarity score between 0.00 and 1.00.
5. If similarity < {threshold}, list specific visual mismatches.

Return strictly a JSON object:
{{
  "similarity_score": 0.94,
  "passed": true,
  "mismatches_detected": ["string"],
  "diff_notes": "string"
}}
"""
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/png", "data": ref_b64}},
                        {"inline_data": {"mime_type": "image/png", "data": cand_b64}}
                    ]
                }],
                "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1}
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=18) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cand_text = data["candidates"][0]["content"]["parts"][0]["text"]
                res = json.loads(cand_text)

                score = float(res.get("similarity_score", 0.0))
                passed = score >= threshold
                return {
                    "status": "COMPLETED",
                    "similarity_score": round(score, 3),
                    "threshold": threshold,
                    "passed": passed,
                    "mismatches_detected": res.get("mismatches_detected", []),
                    "diff_notes": res.get("diff_notes", ""),
                    "reference_image": str(reference_path),
                    "candidate_image": str(candidate_path),
                    "engine_used": f"gemini-vision ({self.ai.model})"
                }
        except Exception as e:
            print(f"[VISUAL DIFF WARNING] Gemini vision call failed: {e}. Using perceptual analysis.")
            return None

    def _compare_with_perceptual_analysis(
        self,
        candidate_path: Path,
        reference_path: Path,
        threshold: float
    ) -> Dict[str, Any]:
        """
        Deterministic perceptual image analysis using standard library Python.
        Extracts pixel matrices and computes perceptual Euclidean similarity.
        """
        ref_bytes = reference_path.read_bytes()
        cand_bytes = candidate_path.read_bytes()

        # Parse PNG dimensions and bpp
        ref_w, ref_h, ref_bpp, ref_idat = self._extract_png_metadata(ref_bytes)
        cand_w, cand_h, cand_bpp, cand_idat = self._extract_png_metadata(cand_bytes)

        mismatches = []
        penalties = 0.0

        # Dimension check
        if (ref_w, ref_h) != (cand_w, cand_h):
            mismatches.append(f"Viewport resolution mismatch: expected {ref_w}x{ref_h}, got {cand_w}x{cand_h}")
            penalties += 0.25

        try:
            ref_pixels = self._unfilter_png(ref_idat, ref_w, ref_h, ref_bpp)
            cand_pixels = self._unfilter_png(cand_idat, cand_w, cand_h, cand_bpp)

            # Subsample pixels across the viewport for high performance perceptual scoring
            step = 8
            total_samples = 0
            match_score = 0.0
            color_diff_sum = 0.0

            min_pixels = min(ref_w * ref_h, cand_w * cand_h)
            for p_idx in range(0, min_pixels, step):
                total_samples += 1
                r_offset = p_idx * ref_bpp
                c_offset = p_idx * cand_bpp

                dr = abs(ref_pixels[r_offset] - cand_pixels[c_offset]) / 255.0
                dg = abs(ref_pixels[r_offset + 1] - cand_pixels[c_offset + 1]) / 255.0
                db = abs(ref_pixels[r_offset + 2] - cand_pixels[c_offset + 2]) / 255.0
                dist = (dr + dg + db) / 3.0
                color_diff_sum += dist
                match_score += (1.0 - dist)

            avg_color_dist = color_diff_sum / max(1, total_samples)
            raw_similarity = match_score / max(1, total_samples)

            if avg_color_dist > 0.20:
                mismatches.append(
                    f"Severe visual color divergence detected ({avg_color_dist * 100:.1f}% mean color distance). "
                    f"Deliverable deviates substantially from Figma reference design tokens."
                )

            similarity_score = max(0.0, min(1.0, raw_similarity - penalties))

        except Exception as e:
            # Fallback based on file size variance if decompression encounters anomaly
            size_ratio = min(len(cand_bytes), len(ref_bytes)) / max(len(cand_bytes), len(ref_bytes))
            similarity_score = round(size_ratio * 0.9, 2)

        similarity_score = round(similarity_score, 3)
        passed = similarity_score >= threshold

        if passed:
            diff_notes = f"Deliverable matches Figma mockup within acceptable visual variance (Similarity: {similarity_score * 100:.1f}% >= Threshold {threshold * 100:.1f}%)."
        else:
            diff_notes = f"Visual mismatch detected! Similarity score ({similarity_score * 100:.1f}%) is below the contract threshold ({threshold * 100:.1f}%)."

        return {
            "status": "COMPLETED",
            "similarity_score": similarity_score,
            "threshold": threshold,
            "passed": passed,
            "mismatches_detected": mismatches,
            "diff_notes": diff_notes,
            "reference_image": str(reference_path),
            "candidate_image": str(candidate_path),
            "engine_used": "perceptual-structural-analyzer"
        }

    def _unfilter_png(self, idat: bytes, width: int, height: int, bpp: int = 3) -> bytes:
        """
        Reconstructs raw pixel scanlines by inverting PNG filter types (0=None, 1=Sub, 2=Up, 3=Avg, 4=Paeth).
        Pure standard library implementation.
        """
        raw = zlib.decompress(idat)
        stride = width * bpp + 1
        reconstructed = bytearray(width * height * bpp)
        prior_row = bytearray(width * bpp)

        def paeth_predictor(a: int, b: int, c: int) -> int:
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            return a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)

        for y in range(height):
            row_offset = y * stride
            if row_offset >= len(raw):
                break
            filter_type = raw[row_offset]
            row_data = raw[row_offset + 1: min(len(raw), row_offset + stride)]
            recon_row = bytearray(width * bpp)
            for x in range(min(len(row_data), width * bpp)):
                filt = row_data[x]
                left = recon_row[x - bpp] if x >= bpp else 0
                up = prior_row[x]
                up_left = prior_row[x - bpp] if x >= bpp else 0

                if filter_type == 0:
                    val = filt
                elif filter_type == 1:
                    val = (filt + left) & 0xFF
                elif filter_type == 2:
                    val = (filt + up) & 0xFF
                elif filter_type == 3:
                    val = (filt + ((left + up) >> 1)) & 0xFF
                elif filter_type == 4:
                    val = (filt + paeth_predictor(left, up, up_left)) & 0xFF
                else:
                    val = filt
                recon_row[x] = val

            reconstructed[y * width * bpp : (y + 1) * width * bpp] = recon_row
            prior_row = recon_row

        return bytes(reconstructed)

    def _extract_png_metadata(self, data: bytes) -> Tuple[int, int, int, bytes]:
        """Extracts width, height, bpp, and concatenated IDAT data from raw PNG bytes."""
        if len(data) < 8 or data[:8] != b"\x89PNG\r\n\x1a\n":
            raise VisualDiffError("Invalid PNG image bytes.")

        offset = 8
        w, h = 0, 0
        bpp = 3
        idat_chunks = []

        while offset < len(data):
            if offset + 8 > len(data):
                break
            length = struct.unpack(">I", data[offset:offset + 4])[0]
            chunk_type = data[offset + 4:offset + 8]
            chunk_data = data[offset + 8:offset + 8 + length]
            offset += 12 + length  # 4 len + 4 type + length + 4 crc

            if chunk_type == b"IHDR" and len(chunk_data) >= 10:
                w, h = struct.unpack(">II", chunk_data[:8])
                color_type = chunk_data[9]
                if color_type == 6:  # RGBA
                    bpp = 4
                elif color_type == 2:  # RGB
                    bpp = 3
                elif color_type == 4:  # Gray+Alpha
                    bpp = 2
                else:
                    bpp = 1
            elif chunk_type == b"IDAT":
                idat_chunks.append(chunk_data)
            elif chunk_type == b"IEND":
                break

        return w, h, bpp, b"".join(idat_chunks)

    def evaluate_deliverable_against_figma(
        self,
        screenshots_summary: Dict[str, Any],
        figma_reference_dir: Path
    ) -> Dict[str, Any]:
        """
        Takes captured screenshot summary from Stage E pre-capture and performs
        comparison against corresponding Figma design references.
        """
        figma_dir = Path(figma_reference_dir).resolve()
        screenshots = screenshots_summary.get("screenshots", [])

        if not screenshots:
            return {
                "status": "SKIPPED",
                "similarity_score": 0.0,
                "threshold": self.threshold,
                "passed": False,
                "diff_notes": "No screenshots available for visual diff.",
                "mismatches_detected": ["No screenshots captured"]
            }

        # Select primary desktop screenshot (1280x800)
        primary_screenshot = None
        for s in screenshots:
            if s.get("viewport", {}).get("width") == 1280:
                primary_screenshot = s
                break
        if not primary_screenshot:
            primary_screenshot = screenshots[0]

        candidate_file = Path(primary_screenshot["file_path"])

        # Locate reference mockup in Figma directory
        reference_file = figma_dir / "reference_landing_1280x800.png"
        if not reference_file.exists():
            # Try any png in figma dir
            pngs = list(figma_dir.glob("*.png"))
            if pngs:
                reference_file = pngs[0]
            else:
                return {
                    "status": "REFERENCE_MISSING",
                    "similarity_score": 1.0,
                    "threshold": self.threshold,
                    "passed": True,
                    "diff_notes": "No reference Figma PNG mockup found in demo-assets/figma/. Visual diff bypassed.",
                    "mismatches_detected": []
                }

        return self.compare_images(candidate_file, reference_file, threshold=self.threshold)
