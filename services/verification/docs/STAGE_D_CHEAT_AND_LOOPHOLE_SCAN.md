# Stage D: Cheat & Loophole Scanner (`services/verification`)

## Overview
Commit **`C27`** delivers the automated static and semantic scanner to detect dishonest shortcuts, test manipulation, unfulfilled contract stubs, non-functional UI, and credential leaks in freelancer deliverables.

**Done Criteria:**
- Hardcoded trick in the bad repo (`src/catalog.js`) is flagged with **HIGH** severity.
- Good repo passes cheat scan with 0 high/critical findings.

---

## 5 Inspection Categories & Severity Model

| Category | Description | Severity | Examples / Patterns |
| :--- | :--- | :---: | :--- |
| **`hardcoded_outputs`** | Bypassing dynamic computation by returning static mocks or matching specific test arguments. | **`HIGH`** | Returning `fake_sw_1` on `category === "software"`, static mock return arrays, explicit cheat comments. |
| **`disabled_tests`** | Skipping assertions or test suites to artificially produce green test runs. | **`HIGH`** | `it.skip`, `describe.skip`, `xit`, `xtest`, commented-out assertions (`// assert.equal`), forced exit `process.exit(0)` silencing errors. |
| **`placeholders`** | Unfinished implementation markers or filler copy in production source. | **`MEDIUM`** / **`HIGH`** | `TODO:`, `FIXME:`, `XXX:`, `Lorem Ipsum` copy, `throw new Error("Not implemented")`. |
| **`dead_ui`** | User interface controls that give the appearance of functionality without actual behavior. | **`MEDIUM`** / **`LOW`** | `<a href="#">`, `<a href="javascript:void(0)">`, buttons lacking event listeners or form submit actions. |
| **`exposed_keys`** | Leaked cryptographic keys, tokens, and credentials in deliverable code. | **`CRITICAL`** | Private keys (`BEGIN RSA PRIVATE KEY`), AWS Access Keys (`AKIA...`), OpenAI (`sk-...`), Gemini (`AIza...`), GitHub PATs (`ghp_...`). |

---

## Benchmark Evaluation Results

| Repository Deliverable | Total Findings | Highest Severity | Pass Status | Flagged Issue Details |
| :--- | :---: | :---: | :---: | :--- |
| **`demo-assets/good-repo`** | **`0`** | `None` | **PASSED** | Clean deliverable with real dynamic filtering over `PRODUCTS` dataset. Zero cheats or loopholes. |
| **`demo-assets/bad-repo`** | **`4`** | **`HIGH`** | **FAILED** | **Flagged with HIGH severity:** `src/catalog.js:17` (`CHEAT-HARDCODED-MOCK-002`) - Hardcoded fake answer bypassing dynamic data filtering. |

---

## Pipeline Integration

In [`services/verification/src/runner.py`](file:///d:/PactPal/services/verification/src/runner.py):
1. Runs immediately following Stage C test suite execution in the isolated workspace.
2. Invokes `CheatScanner.scan_repository(clone_dest)`.
3. Populates `VerificationReport.cheat_scan_findings` with structured JSON records matching the `services/core-api` database schema.
4. Masks secret tokens in snippet previews before persisting findings to prevent accidental credential leakage in verification audit logs.
