# PactPal 🤝
> **Zero-Trust Multimodal Escrow Referee for Digital Freelancing**

---

## 1. Problem
Freelance milestones and second-hand digital sales suffer from a fundamental trust gap:
- **Buyers** fear paying for broken code, fake implementations, or low-quality deliverables.
- **Sellers** fear chargebacks, endless scope creep, or non-payment after delivering completed work.

---

## 2. Solution
PactPal is an impartial, automated **AI Escrow Referee** that bridges the trust gap:
1. **Reads Agreement**: Turns contracts into a priced checklist where every feature has a percentage weight and a measurable acceptance test.
2. **Freezes Funds**: Holds buyer funds up front using the **PayPal Orders API** with `AUTHORIZE` intent (guaranteeing funds without premature capture).
3. **Inspects Code**: Spawns isolated **Render Workflows** containers to build the code, execute tests, run cheat/loophole scans, and compare screenshots against Figma designs.
4. **Calculates Proportional Release**: Releases funds for passed features, offers negotiated partial settlement for minor flaws, and refunds unpassed amounts.
5. **Issues Tamper-Evident Receipts**: Issues a cryptographic SHA-256 proof-of-work receipt attached to the transaction.

---

## 3. Sponsor Technologies Used
- **PayPal Orders & Payouts API**: Authorize intent for milestone escrow holding, capture, and partial payouts.
- **Render Workflows**: Isolated, ephemeral verification container sandbox execution.
- **Bryntum Gantt & Scheduler**: Visual milestone schedules, checklist tasks, and hold expiration milestones.

---

## 4. Repository Structure & Subsystem Teams

```
PactPal/
├── .github/                      # CI workflows & PR template
├── docs/                         # Architecture, Contract Lifecycle (10 states), Data Map
├── main.py                       # FastAPI application & master gateway
├── requirements.txt              # FastAPI, Uvicorn, Pydantic, HTTPX
├── services/
│   ├── agents/                   # [AG] Agreement Reader, Referee, Price Negotiator, Prompts
│   ├── core-api/                 # [AG] Relational DB, Auth, 10-State Machine Engine
│   ├── verification/             # [VR] Render Workflows, Stages A-F Verification Pipeline
│   └── payments/                 # [PAY] PayPal Escrow Rails (Authorize, Capture, Payouts)
├── frontend/                     # [FE] Next.js/React Web App & Bryntum Gantt Integration
├── shared/                       # Cross-service TypeScript interfaces & schemas
└── demo-assets/                  # Benchmark Figma designs, Good Repo, and Bad Repo
```

---

## 5. Branching Strategy & Governance

PactPal adheres to strict trunk-based governance with 4 dedicated feature stream branches:

| Branch | Stream | Owner / Backlog |
| :--- | :--- | :--- |
| `main` | Production Trunk | Protected. Direct pushes blocked. PR + 1 review required. |
| `feature/frontend` | Frontend UI | Bryntum Gantt, contract wizard, dashboards, chat. |
| `feature/agents` | Agreement & Agents | Agreement reader, referee, state machine, negotiator. |
| `feature/verification` | Verification Engine | Render container isolation, Stages A-F QA pipeline. |
| `feature/payments` | Payment Rails | PayPal authorize, capture, payouts, refund logic. |

> See [BRANCH_RULES.md](file:///Users/harshitavarshney/PactPal/BRANCH_RULES.md) for full branch rules, PR requirements, and GitHub branch protection setup.

---

## 6. Quickstart & Local Setup

### Prerequisites
- **Python**: 3.10+
- **Node.js**: 18+
- **Git**

---

### Step 1: Clone and Configure Environment

```bash
git clone https://github.com/dkrrish9/PactPal.git
cd PactPal

# Copy environment variables
cp .env.example .env
```

---

### Step 2: Set Up & Run the FastAPI Backend

```bash
# 1. Create a Python virtual environment
python3 -m venv .venv

# 2. Activate the virtual environment
source .venv/bin/activate
# On Windows: .venv\Scripts\activate

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Start the FastAPI server with hot-reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- **Backend API**: `http://localhost:8000`
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Step 3: Set Up & Run the Next.js Frontend

In a separate terminal window:

```bash
cd frontend

# Install frontend dependencies
npm install

# Start Next.js development server
npm run dev
```

- **Web App**: [http://localhost:3000](http://localhost:3000)

---

### Step 4: Verify the Setup

```bash
# 1. Check backend health
curl http://localhost:8000/api/v1/health

# 2. Check main seeded contract
curl http://localhost:8000/api/v1/contracts/pct_099e77

# 3. Check 29-day PayPal hold countdown
curl http://localhost:8000/api/v1/contracts/pct_099e77/hold

# 4. Run automated test suite
PYTHONPATH=. .venv/bin/python3 -m unittest tests/test_fastapi.py
```
