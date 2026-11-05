# Subsystem: Agreement & Negotiation Agents (`services/agents`)
**Stream Branch**: `feature/agents`  
**Stream Lead / Owner**: 2 - Agreement/Negotiation

## Overview
This subsystem powers the intelligent referee brains of PactPal. It is responsible for transforming natural language contracts into locked, priced checklists, orchestrating events across subsystems, enforcing the referee decision rules, detecting cheat attempts, and negotiating mid-project changes.

## Directory Structure
- `agreement_reader/`:
  - `reader.py` / `parser.ts`: Form fields parser converting structured contracts into priced checklists (Tasks A3, A4, A5).
  - `validator.py`: Verification that weights sum to 100%, tests are defined, deadlines are valid.
- `orchestrator/`:
  - `skeleton.py`: AI Orchestrator routing lifecycle events between Agreement, Negotiation, Verification, and Payments (Task A6).
- `referee/`:
  - `decision_engine.py`: Fixed rules engine executing full release, partial release, hold, or deadline triggers (Task A10).
  - `negotiated_release.py`: Agentic offer generator ('fix it or accept 80% now') (Task A14).
- `negotiator/`:
  - `price_negotiator.py`: Change request diffing, price estimation, and mini-agreement builder (Tasks A12, A13).
- `prompts/`:
  - `cheat_scan_prompt.md`: Prompts to identify hardcoded fake outputs, disabled tests, placeholder UI (Task A7).
  - `visual_diff_prompt.md`: Prompts for visual comparison between live screenshots and Figma design (Task A8).
  - `prompt_injection_defense.md`: Strict untrusted input sanitization wrappers (Task A11).

