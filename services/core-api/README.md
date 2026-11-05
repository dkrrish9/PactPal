# Subsystem: Core API & State Machine (`services/core-api`)
**Stream Branch**: `feature/agents` (Backend & State Machine)  
**Linked Tasks**: A1 (Data Map & DB Setup), A2 (Auth & 10-State Machine)

## Overview
Provides the central relational persistence layer, user identity & role authentication (Buyer, Seller, Admin), and strictly drives the 10-state contract state machine.

## Structure
- `auth/`: JWT authentication, role verification middleware (`BUYER`, `SELLER`, `ADMIN`).
- `db/`: Relational database connection pool, migrations, and ORM models matching `docs/DATA_MAP.md`.
- `state_machine/`: Deterministic 10-state transition engine preventing invalid status jumps.
- `routes/`: RESTful endpoints exposing contract CRUD, submission intake, and verification webhook handlers.

