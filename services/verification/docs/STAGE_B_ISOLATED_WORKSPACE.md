# Stage B: Isolated Workspace & Sandbox Specification (`services/verification`)

## Overview
Stage B manages the ephemeral execution environment where untrusted freelancer code is cloned, dependencies installed, and builds executed. 

Per the PactPal Zero-Trust architecture, the verification runner ensures:
1. **Zero Platform Secrets**: The execution environment strictly scrubs all `PAYPAL_*`, `DATABASE_*`, `APP_SECRET`, `JWT_SECRET`, and cloud API keys.
2. **Data Isolation**: Freelancer code has zero access to other users' contracts, previous submissions, or platform system files.
3. **Execution Limits**: Strict timeouts (default 60s) prevent infinite loops, hangs, or resource exhaustion.
4. **Guaranteed Teardown**: The entire ephemeral workspace directory is completely purged and deallocated from the host disk upon exit (`assert not workspace_path.exists()`), even if builds fail or crash.

---

## Security Guarantees & Verification Results (C15)

Implemented in [`services/verification/src/sandbox.py`](file:///d:/PactPal/services/verification/src/sandbox.py) and verified across 17 automated unit and integration tests:

- [x] **Ephemeral Directory Creation & Cleanup**: Uses Python context manager (`IsolatedWorkspace`) to create temporary directories with guaranteed recursive removal via `shutil.rmtree`.
- [x] **Zero Secret Leakage**: Environment scrubber strips all forbidden prefixes (`PAYPAL_`, `DATABASE_`, `APP_`, `JWT_`, `RENDER_`, `GEMINI_`, `OPENAI_`). Tested by running child scripts querying `os.environ` (`PAYPAL=None, DB=None`).
- [x] **Timeout Enforcement**: Commands exceeding the timeout threshold are terminated with `timed_out = True`.
- [x] **Directory Traversal Guard**: Prevents attempts to escape the isolated workspace using `../` or symlinks.
- [x] **AI / Exfiltration Log Scan**: Scans output logs for attempts to probe `/etc/shadow`, AWS/GCP metadata, or system credentials.
- [x] **End-to-End Build Lifecycle**: Successfully runs clean Node.js builds and test suites on deliverable repositories inside the clean sandbox.
