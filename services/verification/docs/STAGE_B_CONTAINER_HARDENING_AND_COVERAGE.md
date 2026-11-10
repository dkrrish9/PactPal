# Stage B Container Hardening and Test Coverage Numbers (C43)

## 1. Overview
Task **C43** implements container hardening for the untrusted deliverable execution sandbox (`services/verification/src/sandbox.py`) and introduces aggregated test coverage numbers and security finding counts directly into the multi-modal verification report (`services/verification/src/report_assembler.py`).

## 2. Done Criteria
- **Coverage and security counts show up in the report**:
  - The verification report explicitly exposes `coverage_summary` with `total_lines`, `covered_lines`, `uncovered_lines`, `coverage_percentage`, `threshold`, and `status`.
  - The verification report explicitly exposes `security_counts` with counts by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), by category, and `clean` status.
  - The verification report explicitly exposes `container_hardening` with network isolation status, secret scrubbing counts, resource limits, and zero-trust policies.

---

## 3. Container Hardening Architecture (`sandbox.py`)

Untrusted seller code runs under zero-trust air-gapped constraints:
1. **Network Isolation & Offline Execution**:
   - Environment variables enforce offline behavior:
     - `PACTPAL_NETWORK_ISOLATED = "true"`
     - `npm_config_offline = "true"`
     - `npm_config_audit = "false"`
     - `npm_config_fund = "false"`
     - `PIP_NO_INDEX = "true"`
     - `PIP_FIND_LINKS = ""`
     - `DOTNET_CLI_TELEMETRY_OPTOUT = "1"`
     - `NEXT_TELEMETRY_DISABLED = "1"`
2. **Secret Scrubbing & Boundary Verification**:
   - Environment variables with forbidden prefixes (`PAYPAL_`, `DATABASE_`, `DB_`, `APP_`, `JWT_`, `SESSION_`, `RENDER_`, `GEMINI_`, `OPENAI_`, `FIGMA_`, `RECEIPT_`) and secret keywords are strictly stripped.
   - The number of scrubbed variables is logged and exposed in `get_hardening_profile()`.
3. **Resource & Buffer Bounds**:
   - Output buffer cap (`max_output_bytes = 1,000,000`) truncates excessive logs to prevent DOS memory exhaustion.
   - Execution timeout kills runaway processes.
4. **Filesystem Sandbox**:
   - Path traversal attempts (`..`) raise `WorkspaceSecurityError`.
   - Ephemeral temporary directories are completely destroyed upon exit.
5. **Outbound Exfiltration Detection**:
   - `scan_logs_for_exfiltration_attempts` checks logs for probe tools (`curl`, `wget`, `nc`, `.ssh`, `etc/shadow`, cloud metadata).

---

## 4. Coverage Numbers & Security Counts (`report_assembler.py`)

### `coverage_summary` Structure
```json
{
  "total_lines": 140,
  "covered_lines": 122,
  "uncovered_lines": 18,
  "coverage_percentage": 87.1,
  "threshold": 80.0,
  "status": "SATISFACTORY",
  "meets_threshold": true,
  "modules_count": 4,
  "modules": {
    "src/calculator.js": { "lines_total": 35, "lines_covered": 32, "coverage_percent": 91.4 },
    "src/catalog.js": { "lines_total": 45, "lines_covered": 40, "coverage_percent": 88.9 }
  }
}
```

### `security_counts` Structure
```json
{
  "total_security_findings": 2,
  "total_cheat_findings": 2,
  "by_severity": {
    "CRITICAL": 0,
    "HIGH": 2,
    "MEDIUM": 0,
    "LOW": 0,
    "INFO": 0
  },
  "by_category": {
    "hardcoded_outputs": 1,
    "disabled_tests": 1
  },
  "critical_count": 0,
  "high_count": 2,
  "medium_count": 0,
  "low_count": 0,
  "clean": false
}
```

### `container_hardening` Structure
```json
{
  "container_hardened": true,
  "network_isolated": true,
  "offline_mode_enforced": true,
  "secret_scrubbing": {
    "active": true,
    "scrubbed_variables_count": 42,
    "forbidden_prefixes": ["PAYPAL_", "DATABASE_", "DB_", "APP_", "JWT_", ...]
  },
  "resource_limits": {
    "timeout_seconds": 60,
    "max_output_bytes": 1000000,
    "memory_limit_mb": 512
  },
  "filesystem_protection": {
    "ephemeral_workspace": true,
    "path_traversal_blocked": true,
    "auto_cleanup_verified": true
  },
  "security_policy": "ZERO_TRUST_AIR_GAPPED"
}
```

---

## 5. Verification & Tests
Maintained in `services/verification/tests/test_c43_hardening_and_coverage.py`:
- `test_container_hardening_environment_network_isolation`: Verifies offline/isolated environment variables.
- `test_container_hardening_secret_scrubbing_and_counts`: Verifies platform secrets scrubbed and tracked.
- `test_container_hardening_path_traversal_blocked`: Verifies directory traversal prevention.
- `test_container_hardening_exfiltration_detection`: Verifies probe and network detection.
- `test_coverage_numbers_show_up_in_report`: Verifies coverage numbers in report.
- `test_security_counts_show_up_in_report_good_repo`: Verifies 0 issues and clean=True on good repo.
- `test_security_counts_show_up_in_report_bad_repo`: Verifies counts by severity on bad repo.
- `test_container_hardening_shows_up_in_report`: Verifies hardening profile in report.
- `test_seller_feedback_markdown_displays_coverage_and_security_counts`: Verifies feedback markdown integration.
- `test_build_failure_report_contains_default_counts_and_hardening`: Verifies failure report compatibility.
