# Render Workflows & Verification Sandbox Setup

## Overview
PactPal utilizes **Render Workflows** (and isolated ephemeral container runners) as its Zero-Trust execution environment for freelancer code verification. 

When a freelancer submits a project repository, PactPal triggers an ephemeral container run to execute Stages A through F of the verification pipeline. Under our Zero-Trust architecture:
1. **Zero Access to Secrets**: The verification runner is completely isolated from production databases, session secrets, and PayPal payment rails.
2. **Ephemeral Lifecycle**: The container is spun up specifically for the submission, pulls the target commit, builds, tests, runs AI cheat/loophole scans, captures screenshots, and is immediately destroyed.
3. **Reproducibility**: Builds are executed in clean, standardized environments to prevent "works on my machine" discrepancies.

---

## 1. Render API Configuration

### Prerequisites
* Render Account & API Key (from [Render Dashboard -> Account Settings -> API Keys](https://dashboard.render.com/u/settings#api-keys)).
* Render Service ID for the Ephemeral Worker / Job Runner.

### Environment Variables
Configure the following in `.env`:
```ini
RENDER_API_KEY=rnd_xxxxxxxxxxxxxxxxxxxxxxxx
RENDER_WORKFLOW_SERVICE_ID=srv-xxxxxxxxxxxxxxxx
RENDER_WORKFLOW_WORKSPACE=isolated_worker
```

---

## 2. Render Ephemeral Job API Architecture

PactPal interacts with the Render REST API (`https://api.render.com/v1`):

### Trigger Verification Job
```http
POST /v1/services/{serviceId}/jobs HTTP/1.1
Host: api.render.com
Authorization: Bearer ${RENDER_API_KEY}
Content-Type: application/json

{
  "startCommand": "python -m services.verification.pipeline.runner --repo https://github.com/seller/repo --commit 4a7c8e",
  "plan": "starter"
}
```

### Poll Job Status
```http
GET /v1/services/{serviceId}/jobs/{jobId} HTTP/1.1
Host: api.render.com
Authorization: Bearer ${RENDER_API_KEY}
```

Status transitions: `pending` -> `running` -> `succeeded` / `failed`.

### Container Cleanup & Teardown
Render Ephemeral Jobs automatically terminate and deallocate container compute upon command completion. When dynamic services are created via the Render API, they are explicitly deleted:
```http
DELETE /v1/services/{serviceId} HTTP/1.1
Host: api.render.com
Authorization: Bearer ${RENDER_API_KEY}
```

---

## 3. Local & CI Isolated Sandbox Runner

To support offline testing, CI/CD pipelines, and local hackathon validation without incurring cloud costs for every unit test, the verification engine includes a **Local Isolated Container Runner** that enforces the identical security guarantees:
* Sanitized process environment (strips `PAYPAL_*`, `DATABASE_*`, `APP_SECRET`, `JWT_SECRET`).
* Isolated temporary workspace directory.
* Strict execution timeouts (default 120s).
* Cryptographic validation and guaranteed cleanup via `finally` blocks and teardown hooks.
