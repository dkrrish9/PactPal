# PactPal System Architecture

## Overview
PactPal is a Zero-Trust Multimodal Escrow Referee for Digital Freelancing. It resolves the freelancer trust gap by acting as an impartial, automated referee between buyers and sellers. It translates signed contracts into measurable feature checklists, locks buyer funds in escrow via PayPal authorization, executes isolated multi-stage verification in Render Workflows, and releases funds proportionately backed by cryptographic proof-of-work receipts.

---

## 5-Layer Architectural Stack

```mermaid
flowchart TD
    subgraph Layer1["1. Web App Layer (Frontend)"]
        UI["Web App (Next.js / Vite React)"]
        Gantt["Bryntum Gantt & Scheduler Timeline"]
        Chat["Negotiation & Dispute Room"]
        ReceiptView["Proof-of-Work Receipt View"]
    end

    subgraph Layer2["2. Agreement & Decision Layer (Agents)"]
        Reader["AI Agreement Reader"]
        Checklist["Locked Priced Checklist (100%)"]
        Negotiator["AI Price Negotiator (Scope Diff)"]
        Referee["AI Referee Decision Engine"]
        Orchestrator["Event Orchestrator Skeleton"]
    end

    subgraph Layer3["3. Money Layer (PayPal Rails)"]
        AuthHold["PayPal Orders API (AUTHORIZE Intent)"]
        Capture["PayPal Capture (Passed Features)"]
        Payouts["PayPal Payouts API"]
        Refund["Void / Refund (Failed Features)"]
        HoldTracker["29-Day Expiration Watcher"]
    end

    subgraph Layer4["4. Verification Layer (Isolated Runners)"]
        Render["Render Workflows Isolated Containers"]
        StageA["Stage A: Intake & Git Clone"]
        StageB["Stage B: Clean Sandbox Build"]
        StageC["Stage C: Automated Test Suite"]
        StageD["Stage D: Cheat & Loophole Scanner"]
        StageE["Stage E: Vision & Figma Diff"]
        StageF["Stage F: QA Multi-Modal Report"]
    end

    subgraph Layer5["5. Records & Storage Layer (Core-API)"]
        DB[(Hosted Relational DB)]
        Receipts["Tamper-Proof Receipts (SHA-256)"]
        StateMachine["10-State Contract State Machine"]
    end

    UI --> Reader
    Reader --> Checklist
    Checklist --> AuthHold
    UI --> Render
    Render --> StageA --> StageB --> StageC --> StageD --> StageE --> StageF
    StageF --> Referee
    Referee --> Capture
    Referee --> Refund
    Referee --> Receipts
    Referee --> Gantt
```

---

## Subsystem Breakdown & Directory Mapping

| Directory | Subsystem | Owner / Stream | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| `frontend/` | Web App & Timeline | **Frontend (FE)** | Buyer/Seller dashboards, contract creation wizard, Bryntum Gantt timelines, real-time activity feed. |
| `services/agents/` | AI Agents & Decision Engine | **Agreement / Negotiation (AG)** | Form parsing to priced checklists, cheat scan prompts, visual comparison prompts, referee rules, price negotiation. |
| `services/core-api/` | Central Backend & Database | **Agreement / Negotiation (AG)** | Relational data schema (users, contracts, features, payments, receipts), 10-state machine, REST API. |
| `services/verification/` | Isolated Verification Pipeline | **Verification (VR)** | Render Workflows triggers, Stages A-F orchestration, headless browser screenshot capture, visual difference reports. |
| `services/payments/` | Payment Rails & Escrow | **Payments (PAY)** | PayPal Orders API (Authorize), Capture, Payouts, Refund, webhook verification, 29-day expiry countdown. |
| `shared/` | Cross-Service Contracts | **All Teams** | Shared TypeScript interfaces, JSON schemas, state machine enums. |
| `demo-assets/` | Hackathon Demo Assets | **All Teams** | Sample Figma designs, clean "good-repo", flawed "bad-repo". |

