# Subsystem: Verification Pipeline (`services/verification`)
**Stream Branch**: `feature/verification`  
**Stream Lead / Owner**: 3 - Verification (VR)

## Overview
Executes isolated, reproducible verification of freelancer code deliverables. Orchestrates Stages A through F using sponsor tool **Render Workflows** to guarantee strict zero-trust sandbox execution.

## Verification Pipeline Stages:
- **Stage A (Intake)**: Pulls repo URL, verifies commit hash, checks submission timestamp against contract deadline.
- **Stage B (Isolated Workspace)**: Spawns clean container via Render Workflows API with zero access to platform database or payment secrets.
- **Stage C (Automated Tests)**: Executes project test suite and AI-generated acceptance assertion tests.
- **Stage D (Cheat & Loophole Scan)**: Scans for fake static responses, skipped tests, empty UI handlers, and leaked credentials.
- **Stage E (Visual Diff)**: Spins up headless browser, captures high-resolution screenshots, and executes multimodal vision comparison against Figma designs.
- **Stage F (Report Assembly & Proof-of-Work Hashing)**: Bundles evidence into structured JSON and computes the SHA-256 tamper-evident fingerprint.

