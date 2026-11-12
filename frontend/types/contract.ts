/**
 * PactPal Master Contract & Data Models (Phase 1 Specification)
 * Authoritative types matching backend state machine, agreement reader, and payment rails.
 * References:
 *   - services/core-api/state_machine/engine.py
 *   - services/core-api/db/schema.sql
 *   - services/agents/agreement_reader/models.py
 *   - shared/docs/SHARED_API_CONTRACT.md
 *   - shared/schemas/verification_report.json
 */

export type UserRole = "BUYER" | "SELLER" | "ADMIN";

/**
 * Master 10-State Contract Lifecycle
 */
export type ContractStatus =
  | "DRAFT"
  | "REVIEW"
  | "SIGNED"
  | "FUNDED"
  | "IN_PROGRESS"
  | "SUBMITTED"
  | "VERIFYING"
  | "DECISION"
  | "SETTLED"
  | "DISPUTE";

export interface ContractStateMeta {
  label: string;
  shortDesc: string;
  notificationWording: string;
  color: string;
  bg: string;
  border: string;
  step: number;
}

export const CONTRACT_STATES_META: Record<ContractStatus, ContractStateMeta> = {
  DRAFT: {
    label: "Draft",
    shortDesc: "Formulating milestone scope, weights & tests",
    notificationWording: "Contract draft created. Awaiting submission for seller review.",
    color: "#94A3B8",
    bg: "rgba(148, 163, 184, 0.12)",
    border: "rgba(148, 163, 184, 0.3)",
    step: 1,
  },
  REVIEW: {
    label: "In Review",
    shortDesc: "Seller reviewing & counter-proposing terms",
    notificationWording: "Contract submitted for seller review. Awaiting acceptance or counter-terms.",
    color: "#38BDF8",
    bg: "rgba(56, 189, 248, 0.12)",
    border: "rgba(56, 189, 248, 0.3)",
    step: 2,
  },
  SIGNED: {
    label: "Signed",
    shortDesc: "Mutual acceptance confirmed; checklist locked",
    notificationWording: "Terms confirmed by both parties. Agreement Reader locked the priced checklist.",
    color: "#A78BFA",
    bg: "rgba(167, 139, 250, 0.12)",
    border: "rgba(167, 139, 250, 0.3)",
    step: 3,
  },
  FUNDED: {
    label: "Funded",
    shortDesc: "PayPal 29-day authorization hold active in escrow",
    notificationWording: "Buyer funds secured in PayPal escrow hold. Delivery clock started.",
    color: "#FBBF24",
    bg: "rgba(251, 191, 36, 0.12)",
    border: "rgba(251, 191, 36, 0.3)",
    step: 4,
  },
  IN_PROGRESS: {
    label: "In Progress",
    shortDesc: "Freelancer building code towards acceptance tests",
    notificationWording: "Seller active on deliverable. Scope changes can be negotiated via AI Negotiator.",
    color: "#60A5FA",
    bg: "rgba(96, 165, 250, 0.12)",
    border: "rgba(96, 165, 250, 0.3)",
    step: 5,
  },
  SUBMITTED: {
    label: "Submitted",
    shortDesc: "Repo link & commit SHA intake recorded",
    notificationWording: "Deliverable repository submitted on-time. Queued for isolated container verification.",
    color: "#2DD4BF",
    bg: "rgba(45, 212, 191, 0.12)",
    border: "rgba(45, 212, 191, 0.3)",
    step: 6,
  },
  VERIFYING: {
    label: "Verifying",
    shortDesc: "AI Referee running 6-stage container pipeline",
    notificationWording: "Stages A-F executing: AST cheat scan, test suite, and Figma visual diff active.",
    color: "#818CF8",
    bg: "rgba(129, 140, 248, 0.12)",
    border: "rgba(129, 140, 248, 0.3)",
    step: 7,
  },
  DECISION: {
    label: "Decision",
    shortDesc: "Verification complete; payout settlement proposal generated",
    notificationWording: "AI Referee decision rendered with plain-text explanation and compromise offer.",
    color: "#FB923C",
    bg: "rgba(251, 146, 60, 0.12)",
    border: "rgba(251, 146, 60, 0.3)",
    step: 8,
  },
  SETTLED: {
    label: "Settled",
    shortDesc: "PayPal capture & release disbursed to seller",
    notificationWording: "Proportional funds disbursed to seller via PayPal; remainder refunded to buyer.",
    color: "#4ADE80",
    bg: "rgba(74, 222, 128, 0.12)",
    border: "rgba(74, 222, 128, 0.3)",
    step: 9,
  },
  DISPUTE: {
    label: "Dispute",
    shortDesc: "Dispute lodged; escrow paused for mediation",
    notificationWording: "Dispute arbitration opened. Escrow funds locked pending resolution.",
    color: "#F87171",
    bg: "rgba(248, 113, 113, 0.12)",
    border: "rgba(248, 113, 113, 0.3)",
    step: 10,
  },
};

export type FeatureStatus = "PENDING" | "PASSED" | "FAILED" | "DISPUTED";

export interface Feature {
  id: string;
  contract_id: string;
  title: string;
  acceptance_test: string;
  price_weight: number;      // 0 - 100 percentage
  allocated_amount: number;  // USD allocated (penny exact)
  status: FeatureStatus;
  sort_order: number;
  deadline?: string;
  amended?: boolean;
  change_request_id?: string;
}

export interface Submission {
  id: string;
  contract_id: string;
  seller_id: string;
  repo_url: string;
  commit_sha: string;
  branch: string;
  deploy_url?: string;
  build_notes: string;
  submission_number: number;
  is_late: boolean;
  submitted_at: string;
  deadline: string;
}

export interface HoldInfo {
  contract_id: string;
  authorization_id: string;
  amount: string;
  currency: string;
  status: "HELD" | "EXPIRED" | "VOIDED" | "CAPTURED";
  authorized_at: string;
  expires_at: string;
  days_remaining: number;
  seconds_remaining: number;
  is_expired: boolean;
}

export interface Contract {
  id: string;
  title: string;
  description: string;
  buyer_id: string;
  buyer_name: string;
  buyer_email: string;
  seller_id: string;
  seller_name: string;
  seller_email: string;
  status: ContractStatus;
  total_amount: number;
  currency: string;
  deadline: string; // ISO 8601 string
  figma_url?: string;
  repo_url?: string;
  commit_sha?: string;
  submission?: Submission | null;
  paypal_order_id?: string | null;
  paypal_auth_id?: string | null;
  auth_expires_at?: string | null;
  funded_at?: string | null;
  created_at: string;
  updated_at?: string;
  buyer_confirmed_at?: string | null;
  seller_confirmed_at?: string | null;
  checklist_locked?: boolean;
  is_locked?: boolean;
  locked_at?: string | null;
  features: Feature[];
}

/**
 * Proof-of-Work Receipt (Phase 8 Specification)
 * Tamper-evident cryptographic settlement artifact.
 */
export interface ProofOfWorkReceipt {
  receipt_id: string;
  contract_id: string;
  receipt_hash: string; // SHA-256 fingerprint (64 chars)
  settled_at: string;
  status: "SETTLED" | "PENDING";
  financial_dispatch: {
    total_escrow_held: number;
    seller_payout_amount: number;
    buyer_refund_amount: number;
    currency: string;
    passed_weight_percent: number;
    failed_weight_percent: number;
    paypal_order_id: string;
    paypal_auth_id: string;
    paypal_capture_id: string;
    paypal_payout_batch_id: string;
    seller_paypal_email: string;
  };
  deliverable: {
    repo_url: string;
    commit_sha: string;
    submission_timestamp: string;
    is_on_time: boolean;
  };
  verification_metrics: {
    overall_score: number;
    test_suite_status: "PASSED" | "FAILED";
    tests_passed: number;
    tests_total: number;
    coverage_percent: number;
    visual_similarity_score: number;
    cheat_scan_findings_count: number;
  };
  features: Array<{
    id: string;
    title: string;
    price_weight: number;
    allocated_amount: number;
    status: FeatureStatus;
    severity: "NONE" | "LOW" | "MEDIUM" | "HIGH";
    evidence: string;
  }>;
  evidence_links: {
    github_commit_url: string;
    verification_report_url: string;
    visual_diff_url: string;
    paypal_transaction_url: string;
    ast_scan_report_url: string;
  };
  tamper_check: {
    is_valid: boolean;
    algorithm: "SHA-256";
    canonical_payload_digest: string;
    referee_engine: string;
  };
}

/**
 * Agreement Reader Clarification Request (Phase 1 & Phase 3)
 */
export interface ClarificationItem {
  field: string;
  feature_index?: number;
  issue: string;
  suggestion: string;
}

export interface ClarificationRequest {
  contract_id: string;
  issues_count: number;
  clarifications: ClarificationItem[];
  overall_guidance: string;
}

