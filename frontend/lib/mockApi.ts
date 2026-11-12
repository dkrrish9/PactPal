/**
 * PactPal Mock State Contract & API Client
 * Strict implementation of shared REST API specification:
 * Reference: shared/docs/SHARED_API_CONTRACT.md & docs/CONTRACT_LIFECYCLE.md
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

export const CONTRACT_STATES_META: Record<ContractStatus, {
  label: string;
  shortDesc: string;
  color: string;
  bg: string;
  border: string;
  step: number;
}> = {
  DRAFT: {
    label: "Draft",
    shortDesc: "Buyer formulating project scope & weights",
    color: "#94A3B8",
    bg: "rgba(148, 163, 184, 0.12)",
    border: "rgba(148, 163, 184, 0.3)",
    step: 1,
  },
  REVIEW: {
    label: "In Review",
    shortDesc: "Seller reviewing & counter-proposing terms",
    color: "#38BDF8",
    bg: "rgba(56, 189, 248, 0.12)",
    border: "rgba(56, 189, 248, 0.3)",
    step: 2,
  },
  SIGNED: {
    label: "Signed",
    shortDesc: "Both parties agreed; checklist locked",
    color: "#A78BFA",
    bg: "rgba(167, 139, 250, 0.12)",
    border: "rgba(167, 139, 250, 0.3)",
    step: 3,
  },
  FUNDED: {
    label: "Funded",
    shortDesc: "PayPal 29-day authorization hold active in escrow",
    color: "#FBBF24",
    bg: "rgba(251, 191, 36, 0.12)",
    border: "rgba(251, 191, 36, 0.3)",
    step: 4,
  },
  IN_PROGRESS: {
    label: "In Progress",
    shortDesc: "Freelancer building code towards acceptance tests",
    color: "#60A5FA",
    bg: "rgba(96, 165, 250, 0.12)",
    border: "rgba(96, 165, 250, 0.3)",
    step: 5,
  },
  SUBMITTED: {
    label: "Submitted",
    shortDesc: "Repo link & commit SHA intake recorded",
    color: "#2DD4BF",
    bg: "rgba(45, 212, 191, 0.12)",
    border: "rgba(45, 212, 191, 0.3)",
    step: 6,
  },
  VERIFYING: {
    label: "Verifying",
    shortDesc: "AI Referee running 6-stage microVM pipeline",
    color: "#818CF8",
    bg: "rgba(129, 140, 248, 0.12)",
    border: "rgba(129, 140, 248, 0.3)",
    step: 7,
  },
  DECISION: {
    label: "Decision",
    shortDesc: "Verification complete; payout settlement proposal generated",
    color: "#FB923C",
    bg: "rgba(251, 146, 60, 0.12)",
    border: "rgba(251, 146, 60, 0.3)",
    step: 8,
  },
  SETTLED: {
    label: "Settled",
    shortDesc: "PayPal capture & release disbursed to seller",
    color: "#4ADE80",
    bg: "rgba(74, 222, 128, 0.12)",
    border: "rgba(74, 222, 128, 0.3)",
    step: 9,
  },
  DISPUTE: {
    label: "Dispute",
    shortDesc: "Dispute lodged; escrow paused for mediation",
    color: "#F87171",
    bg: "rgba(248, 113, 113, 0.12)",
    border: "rgba(248, 113, 113, 0.3)",
    step: 10,
  },
};

export interface ChatMessage {
  id: string;
  contract_id: string;
  sender_type: "BUYER" | "SELLER" | "AI_REFEREE";
  sender_name: string;
  content: string;
  sent_at: string;
  metadata?: {
    action?: "COUNTER_OFFER" | "ACCEPT_TERMS" | "VERDICT_SUMMARY" | "DISPUTE_RAISED" | "SCOPE_ADVISORY" | string;
    proposed_amount?: number;
    proposed_deadline?: string;
  } | null;
}

export interface Feature {
  id: string;
  contract_id: string;
  title: string;
  acceptance_test: string;
  price_weight: number;      // 0 - 100 percentage
  allocated_amount: number;  // USD allocated
  status: "PENDING" | "PASSED" | "FAILED" | "DISPUTED";
  sort_order: number;
}

export interface Submission {
  id: string;
  contract_id: string;
  repo_url: string;
  commit_sha: string;
  branch: string;
  deploy_url?: string;
  build_notes: string;
  submitted_at: string;
  version_number: number;
  is_late: boolean;
  deadline: string;
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
  deadline: string; // ISO string
  figma_url?: string;
  repo_url?: string;
  commit_sha?: string;
  submission?: Submission | null;
  paypal_order_id?: string | null;
  paypal_auth_id?: string | null;
  auth_expires_at?: string | null; // ISO string
  created_at: string;
  buyer_confirmed_at?: string | null;
  seller_confirmed_at?: string | null;
  checklist_locked?: boolean;
  is_locked?: boolean;
  locked_at?: string | null;
  counter_offer?: {
    proposed_by: "BUYER" | "SELLER";
    total_amount: number;
    deadline: string;
    note: string;
    proposed_at: string;
  } | null;
  features: Feature[];
}

export interface HoldInfo {
  contract_id: string;
  authorization_id: string;
  amount: string;
  currency: string;
  status: "HELD" | "EXPIRED" | "RELEASED";
  authorized_at: string;
  expires_at: string;
  days_remaining: number;
  seconds_remaining: number;
  is_expired: boolean;
}

export interface VerificationReport {
  id: string;
  submission_id: string;
  contract_id: string;
  render_job_id: string;
  build_succeeded: boolean;
  build_logs: string;
  overall_score: number;
  next_state: string;
  completed_at: string;
  test_suite_results: {
    status: string;
    total_tests: number;
    passed_tests: number;
    failed_tests: number;
    skipped_tests: number;
    coverage_percent: number;
    duration_ms: number;
  };
  cheat_scan_findings: Array<{
    finding_id: string;
    feature_id: string;
    rule_violated: string;
    severity: "HIGH" | "MEDIUM" | "LOW" | "NONE";
    description: string;
    file_path: string;
    line_number: number;
  }>;
  visual_diff_summary: {
    status: string;
    similarity_score: number;
    threshold: number;
    passed: boolean;
    diff_image_url: string;
    notes: string;
  };
  per_feature_results: Record<string, {
    feature_id: string;
    feature_title: string;
    status: "PASSED" | "FAILED" | "PENDING";
    price_weight: number;
    allocated_amount: number;
    severity: string;
    evidence: string;
    reason: string | null;
  }>;
}

export interface ProofOfWorkReceipt {
  id: string;
  contract_id: string;
  contract_title: string;
  receipt_hash: string;
  status: "SETTLED" | "ISSUED" | "VERIFIED";
  generated_at: string;
  issued_at: string;
  settled_at: string;
  submission_id: string;
  verification_report_id: string;
  financial_dispatch: {
    total_amount: number;
    seller_payout_amount: number;
    buyer_refund_amount: number;
    currency: string;
    passed_weight_percent: number;
    failed_weight_percent: number;
    paypal_order_id: string;
    paypal_capture_id: string;
    paypal_payout_batch_id: string;
    paypal_refund_id?: string;
  };
  deliverable: {
    repo_url: string;
    commit_sha: string;
    branch: string;
    deploy_url?: string;
    version_number: number;
    submitted_at: string;
    is_late: boolean;
  };
  verification_metrics: {
    overall_score: number;
    test_suite_status: string;
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
    status: "PASSED" | "FAILED" | "PENDING";
    severity?: string;
    evidence?: string;
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

const STORAGE_KEY = "pactpal_contracts_v1";

const SEED_CONTRACTS: Contract[] = [
  {
    id: "pct_099e77",
    title: "E-commerce Platform v2 & Verification Suite",
    description: "Develop 4-feature responsive store matching Figma design with automated tests.",
    buyer_id: "usr_buyer_01",
    buyer_name: "Priya Sharma",
    buyer_email: "priya@fintech.io",
    seller_id: "usr_seller_01",
    seller_name: "Alex Mercer",
    seller_email: "alex.dev@code.io",
    status: "VERIFYING",
    total_amount: 1500,
    currency: "USD",
    deadline: new Date(Date.now() + 14 * 86400000).toISOString(),
    figma_url: "https://figma.com/design/pactpal-storefront-v2",
    repo_url: "https://github.com/freelancer/pactpal-storefront",
    commit_sha: "a1b8c9d4e5f67890123456789abcdef012345678",
    paypal_order_id: "17M76648VK7664316",
    paypal_auth_id: "8BA1234567890123",
    auth_expires_at: new Date(Date.now() + 18 * 86400000).toISOString(),
    created_at: new Date(Date.now() - 11 * 86400000).toISOString(),
    buyer_confirmed_at: new Date(Date.now() - 11 * 86400000).toISOString(),
    seller_confirmed_at: new Date(Date.now() - 10 * 86400000).toISOString(),
    checklist_locked: true,
    submission: {
      id: "sub_099e_01",
      contract_id: "pct_099e77",
      repo_url: "https://github.com/freelancer/pactpal-storefront",
      commit_sha: "a1b8c9d4e5f67890123456789abcdef012345678",
      branch: "main",
      deploy_url: "https://preview.pactpal-storefront.vercel.app",
      build_notes: "All 4 features implemented and passing unit tests. Built with Next.js 16 and TypeScript.",
      submitted_at: new Date(Date.now() - 2 * 86400000).toISOString(),
      version_number: 1,
      is_late: false,
      deadline: new Date(Date.now() + 14 * 86400000).toISOString(),
    },
    features: [
      {
        id: "feat_01",
        contract_id: "pct_099e77",
        title: "Landing Page & Responsive Navigation",
        acceptance_test: "All 12 sections render, mobile drawer opens, 100% responsive",
        price_weight: 25,
        allocated_amount: 375,
        status: "PASSED",
        sort_order: 1,
      },
      {
        id: "feat_02",
        contract_id: "pct_099e77",
        title: "Login & Session Management",
        acceptance_test: "Login/logout with JWT, session persists across refresh",
        price_weight: 20,
        allocated_amount: 300,
        status: "FAILED",
        sort_order: 2,
      },
      {
        id: "feat_03",
        contract_id: "pct_099e77",
        title: "Interactive Dashboard & Bryntum Gantt",
        acceptance_test: "Gantt timeline renders with status colors and today line",
        price_weight: 30,
        allocated_amount: 450,
        status: "PASSED",
        sort_order: 3,
      },
      {
        id: "feat_04",
        contract_id: "pct_099e77",
        title: "PayPal Escrow Webhook Listeners",
        acceptance_test: "Order authorization and capture webhook listeners respond with 200",
        price_weight: 25,
        allocated_amount: 375,
        status: "PENDING",
        sort_order: 4,
      },
    ],
  },
  {
    id: "pct_draft_01",
    title: "AI Analytics Dashboard & Automation Flow",
    description: "Next.js dashboard consuming multi-agent workflow webhooks with dark theme.",
    buyer_id: "usr_buyer_02",
    buyer_name: "Marcus Vance",
    buyer_email: "marcus@scaleup.co",
    seller_id: "usr_seller_02",
    seller_name: "Elena Rostova",
    seller_email: "elena@uxcraft.design",
    status: "DRAFT",
    total_amount: 2400,
    currency: "USD",
    deadline: new Date(Date.now() + 21 * 86400000).toISOString(),
    figma_url: "https://figma.com/file/ai-analytics-v1",
    created_at: new Date().toISOString(),
    features: [
      {
        id: "feat_d1",
        contract_id: "pct_draft_01",
        title: "Telemetry Ingestion Pipeline",
        acceptance_test: "Ingests 1000 events/sec via WebSocket without UI freeze",
        price_weight: 40,
        allocated_amount: 960,
        status: "PENDING",
        sort_order: 1,
      },
      {
        id: "feat_d2",
        contract_id: "pct_draft_01",
        title: "Interactive XY Charts & Metrics",
        acceptance_test: "Renders multi-line latency and throughput charts with zooming",
        price_weight: 60,
        allocated_amount: 1440,
        status: "PENDING",
        sort_order: 2,
      },
    ],
  },
  {
    id: "pct_review_02",
    title: "Solana Staking Interface & Smart Contract",
    description: "Web3 escrow dApp connected to Solana devnet with Phantom wallet integration.",
    buyer_id: "usr_buyer_03",
    buyer_name: "David Chen",
    buyer_email: "david@crypto-ventures.com",
    seller_id: "usr_seller_01",
    seller_name: "Alex Mercer",
    seller_email: "alex.dev@code.io",
    status: "REVIEW",
    total_amount: 4500,
    currency: "USD",
    deadline: new Date(Date.now() + 30 * 86400000).toISOString(),
    figma_url: "https://figma.com/file/solana-dapp",
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    buyer_confirmed_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    seller_confirmed_at: null,
    checklist_locked: false,
    features: [
      {
        id: "feat_r1",
        contract_id: "pct_review_02",
        title: "Anchor Program Smart Contract",
        acceptance_test: "Passing Rust unit tests with 100% instruction coverage",
        price_weight: 50,
        allocated_amount: 2250,
        status: "PENDING",
        sort_order: 1,
      },
      {
        id: "feat_r2",
        contract_id: "pct_review_02",
        title: "Frontend Wallet Connect & Staking UI",
        acceptance_test: "Connect Phantom wallet and stake test SOL with signature confirmation",
        price_weight: 50,
        allocated_amount: 2250,
        status: "PENDING",
        sort_order: 2,
      },
    ],
  },
  {
    id: "pct_signed_03",
    title: "Mobile App Checkout Flow Redesign",
    description: "Streamlined 1-click cart and checkout flow with Apple Pay & Google Pay.",
    buyer_id: "usr_buyer_01",
    buyer_name: "Priya Sharma",
    buyer_email: "priya@fintech.io",
    seller_id: "usr_seller_03",
    seller_name: "Kenji Sato",
    seller_email: "kenji@tokyocode.jp",
    status: "SIGNED",
    total_amount: 2100,
    currency: "USD",
    deadline: new Date(Date.now() + 25 * 86400000).toISOString(),
    figma_url: "https://figma.com/design/checkout-flow",
    created_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    features: [
      {
        id: "feat_s1",
        contract_id: "pct_signed_03",
        title: "Cart Sheet & State Management",
        acceptance_test: "Persistent cart syncs with local storage and updates totals",
        price_weight: 40,
        allocated_amount: 840,
        status: "PENDING",
        sort_order: 1,
      },
      {
        id: "feat_s2",
        contract_id: "pct_signed_03",
        title: "Express Checkout Payment Sheet",
        acceptance_test: "Apple Pay & Google Pay bottom sheet opens and completes authorization",
        price_weight: 60,
        allocated_amount: 1260,
        status: "PENDING",
        sort_order: 2,
      },
    ],
  },
  {
    id: "pct_settled_04",
    title: "SaaS Multi-Tenant Billing & Stripe Webhook Engine",
    description: "Production-ready recurring subscription and webhook dispatcher verified with 100% test coverage.",
    buyer_id: "usr_buyer_01",
    buyer_name: "Priya Sharma",
    buyer_email: "priya@fintech.io",
    seller_id: "usr_seller_01",
    seller_name: "Alex Mercer",
    seller_email: "alex.dev@code.io",
    status: "SETTLED",
    total_amount: 1800,
    currency: "USD",
    deadline: new Date(Date.now() - 3 * 86400000).toISOString(),
    figma_url: "https://figma.com/design/saas-billing-system",
    repo_url: "https://github.com/freelancer/saas-billing-engine",
    commit_sha: "e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
    paypal_order_id: "19K98765VK1234567",
    paypal_auth_id: "7AA9876543210987",
    auth_expires_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    created_at: new Date(Date.now() - 14 * 86400000).toISOString(),
    buyer_confirmed_at: new Date(Date.now() - 14 * 86400000).toISOString(),
    seller_confirmed_at: new Date(Date.now() - 13 * 86400000).toISOString(),
    checklist_locked: true,
    submission: {
      id: "sub_settled_01",
      contract_id: "pct_settled_04",
      repo_url: "https://github.com/freelancer/saas-billing-engine",
      commit_sha: "e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
      branch: "main",
      deploy_url: "https://billing-engine-prod.vercel.app",
      build_notes: "Production build verified with gVisor isolated test container. Passed 14/14 unit tests.",
      submitted_at: new Date(Date.now() - 5 * 86400000).toISOString(),
      version_number: 1,
      is_late: false,
      deadline: new Date(Date.now() - 3 * 86400000).toISOString(),
    },
    features: [
      {
        id: "feat_set_1",
        contract_id: "pct_settled_04",
        title: "Stripe Webhook Signature Verification",
        acceptance_test: "HMAC SHA-256 signature verification rejects unauthenticated replay requests",
        price_weight: 40,
        allocated_amount: 720,
        status: "PASSED",
        sort_order: 1,
      },
      {
        id: "feat_set_2",
        contract_id: "pct_settled_04",
        title: "Tiered Metered Billing Aggregator",
        acceptance_test: "Computes seat count and API usage overages accurately",
        price_weight: 40,
        allocated_amount: 720,
        status: "PASSED",
        sort_order: 2,
      },
      {
        id: "feat_set_3",
        contract_id: "pct_settled_04",
        title: "Dunning & Failed Payment Recovery Emailer",
        acceptance_test: "Retries 3 times on exponential backoff and emails notification",
        price_weight: 20,
        allocated_amount: 360,
        status: "FAILED",
        sort_order: 3,
      },
    ],
  },
];

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

function loadContracts(): Contract[] {
  if (!isBrowser()) return SEED_CONTRACTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(SEED_CONTRACTS));
      return SEED_CONTRACTS;
    }
    const parsed: Contract[] = JSON.parse(raw);
    let updated = false;
    for (const seed of SEED_CONTRACTS) {
      if (!parsed.some((c) => c.id === seed.id)) {
        parsed.push(seed);
        updated = true;
      }
    }
    if (updated) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed));
    }
    return parsed;
  } catch {
    return SEED_CONTRACTS;
  }
}

function saveContracts(contracts: Contract[]): void {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(contracts));
  } catch (err) {
    console.error("Failed to save contracts:", err);
  }
}

const CHAT_STORAGE_KEY_PREFIX = "pactpal_chat_v1_";

const DEFAULT_MESSAGES: Record<string, ChatMessage[]> = {
  pct_099e77: [
    {
      id: "msg_01",
      contract_id: "pct_099e77",
      sender_type: "BUYER",
      sender_name: "Priya Sharma",
      content: "Hi Alex! I've set up the contract for $1,500 with 4 milestones. Please review the acceptance tests and Figma URL.",
      sent_at: new Date(Date.now() - 11 * 86400000).toISOString(),
    },
    {
      id: "msg_02",
      contract_id: "pct_099e77",
      sender_type: "SELLER",
      sender_name: "Alex Mercer",
      content: "Thanks Priya! The Figma design looks clean. I would recommend 25% weight on Feature 1 and 20% on Feature 2 so responsive breakpoints are thoroughly covered.",
      sent_at: new Date(Date.now() - 10 * 86400000).toISOString(),
      metadata: { action: "COUNTER_OFFER", proposed_amount: 1500 },
    },
    {
      id: "msg_03",
      contract_id: "pct_099e77",
      sender_type: "AI_REFEREE",
      sender_name: "AI Referee",
      content: "Referee Analysis: Weights total 100%. Acceptance criteria are unambiguous. Both parties confirmed checklist. Contract signed & 29-day escrow authorization hold activated.",
      sent_at: new Date(Date.now() - 10 * 86400000 + 3600000).toISOString(),
      metadata: { action: "ACCEPT_TERMS" },
    },
    {
      id: "msg_04",
      contract_id: "pct_099e77",
      sender_type: "SELLER",
      sender_name: "Alex Mercer",
      content: "Code deliverables pushed to repository! Pinned commit a1b8c9d4 with Jest suites passing.",
      sent_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    },
    {
      id: "msg_05",
      contract_id: "pct_099e77",
      sender_type: "AI_REFEREE",
      sender_name: "AI Referee",
      content: "Referee Verdict: 3 of 4 features passed test assertions. AST scan flagged hardcoded mock in auth feature. Payout proposal: $1,125 USD to Alex Mercer, $375 USD refund to Priya Sharma.",
      sent_at: new Date(Date.now() - 1 * 86400000).toISOString(),
      metadata: { action: "VERDICT_SUMMARY", proposed_amount: 1125 },
    },
  ],
};

function loadMessages(contractId: string): ChatMessage[] {
  if (!isBrowser()) return DEFAULT_MESSAGES[contractId] || [];
  try {
    const raw = localStorage.getItem(`${CHAT_STORAGE_KEY_PREFIX}${contractId}`);
    if (!raw) {
      const initial = DEFAULT_MESSAGES[contractId] || [
        {
          id: `msg_init_${contractId}`,
          contract_id: contractId,
          sender_type: "AI_REFEREE",
          sender_name: "AI Referee",
          content: "Welcome to the PactPal negotiation room. All scope changes, counter-terms, and milestone discussions are immutably logged.",
          sent_at: new Date().toISOString(),
        },
      ];
      localStorage.setItem(`${CHAT_STORAGE_KEY_PREFIX}${contractId}`, JSON.stringify(initial));
      return initial;
    }
    return JSON.parse(raw);
  } catch {
    return DEFAULT_MESSAGES[contractId] || [];
  }
}

function saveMessages(contractId: string, messages: ChatMessage[]): void {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(`${CHAT_STORAGE_KEY_PREFIX}${contractId}`, JSON.stringify(messages));
  } catch (err) {
    console.error("Failed to persist messages:", err);
  }
}

export const mockApi = {
  /**
   * Get all contracts
   */
  getContracts(): Contract[] {
    return loadContracts();
  },

  /**
   * Get single contract by ID
   */
  getContract(id: string): Contract | null {
    const list = loadContracts();
    return list.find((c) => c.id === id) || null;
  },

  /**
   * Get negotiation chat messages (C40: persists in localStorage)
   */
  getMessages(contractId: string): ChatMessage[] {
    return loadMessages(contractId);
  },

  /**
   * Send negotiation chat message (C40: AI, Buyer, Seller)
   */
  sendMessage(
    contractId: string,
    data: {
      sender_type: "BUYER" | "SELLER" | "AI_REFEREE";
      sender_name?: string;
      content: string;
      metadata?: any;
    }
  ): ChatMessage {
    const messages = loadMessages(contractId);
    const contract = this.getContract(contractId);
    
    let defaultName = "AI Referee";
    if (data.sender_type === "BUYER") {
      defaultName = contract?.buyer_name || "Buyer";
    } else if (data.sender_type === "SELLER") {
      defaultName = contract?.seller_name || "Alex Mercer";
    }

    const newMessage: ChatMessage = {
      id: `msg_${Math.random().toString(36).substring(2, 9)}`,
      contract_id: contractId,
      sender_type: data.sender_type,
      sender_name: data.sender_name || defaultName,
      content: data.content,
      sent_at: new Date().toISOString(),
      metadata: data.metadata || null,
    };

    messages.push(newMessage);
    saveMessages(contractId, messages);
    return newMessage;
  },

  /**
   * Create a new contract (starts in DRAFT)
   */
  createContract(input: {
    title: string;
    description: string;
    buyer_email: string;
    buyer_name?: string;
    buyer_id?: string;
    seller_email: string;
    seller_name?: string;
    seller_id?: string;
    total_amount: number;
    currency?: string;
    deadline: string;
    figma_url?: string;
    repo_url?: string;
    features: Array<{
      title: string;
      acceptance_test: string;
      price_weight: number;
    }>;
  }): Contract {
    const contracts = loadContracts();
    const newId = `pct_${Math.random().toString(36).substring(2, 8)}`;
    
    const formattedFeatures: Feature[] = input.features.map((f, idx) => ({
      id: `feat_${newId}_${idx + 1}`,
      contract_id: newId,
      title: f.title,
      acceptance_test: f.acceptance_test,
      price_weight: f.price_weight,
      allocated_amount: (input.total_amount * f.price_weight) / 100,
      status: "PENDING",
      sort_order: idx + 1,
    }));

    const newContract: Contract = {
      id: newId,
      title: input.title,
      description: input.description,
      buyer_id: input.buyer_id || `usr_${Math.random().toString(36).substring(2, 6)}`,
      buyer_name: input.buyer_name || input.buyer_email.split("@")[0],
      buyer_email: input.buyer_email,
      seller_id: input.seller_id || `usr_${Math.random().toString(36).substring(2, 6)}`,
      seller_name: input.seller_name || input.seller_email.split("@")[0],
      seller_email: input.seller_email,
      status: "DRAFT",
      total_amount: input.total_amount,
      currency: input.currency || "USD",
      deadline: input.deadline,
      figma_url: input.figma_url,
      repo_url: input.repo_url,
      created_at: new Date().toISOString(),
      features: formattedFeatures,
    };

    contracts.unshift(newContract);
    saveContracts(contracts);
    return newContract;
  },

  /**
   * Submit deliverable for verification (C25)
   * Captures repo link, commit SHA, build note, and computes late flag vs deadline
   */
  submitDeliverable(
    id: string,
    data: {
      repo_url: string;
      commit_sha: string;
      branch: string;
      deploy_url?: string;
      build_notes: string;
    }
  ): { contract: Contract; submission: Submission } | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === id);
    if (idx === -1) return null;

    const now = new Date();
    const deadlineDate = new Date(contracts[idx].deadline);
    const isLate = now.getTime() > deadlineDate.getTime();

    const submission: Submission = {
      id: `sub_${Math.random().toString(36).substring(2, 9)}`,
      contract_id: id,
      repo_url: data.repo_url,
      commit_sha: data.commit_sha,
      branch: data.branch,
      deploy_url: data.deploy_url,
      build_notes: data.build_notes,
      submitted_at: now.toISOString(),
      version_number: (contracts[idx].submission?.version_number || 0) + 1,
      is_late: isLate,
      deadline: contracts[idx].deadline,
    };

    contracts[idx].status = "SUBMITTED";
    contracts[idx].repo_url = data.repo_url;
    contracts[idx].commit_sha = data.commit_sha;
    contracts[idx].submission = submission;

    saveContracts(contracts);
    return { contract: contracts[idx], submission };
  },

  /**
   * Update contract status across the 10 lifecycle states (C33)
   */
  updateContractStatus(id: string, status: ContractStatus): Contract | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === id);
    if (idx === -1) return null;

    contracts[idx].status = status;
    saveContracts(contracts);
    return contracts[idx];
  },

  /**
   * Transition DRAFT -> REVIEW
   */
  submitForReview(id: string): Contract | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === id);
    if (idx === -1) return null;

    contracts[idx].status = "REVIEW";
    saveContracts(contracts);
    return contracts[idx];
  },

  /**
   * Seller signs contract: REVIEW -> SIGNED
   */
  signContract(id: string): Contract | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === id);
    if (idx === -1) return null;

    const now = new Date().toISOString();
    contracts[idx].status = "SIGNED";
    contracts[idx].seller_confirmed_at = now;
    if (!contracts[idx].buyer_confirmed_at) {
      contracts[idx].buyer_confirmed_at = contracts[idx].created_at;
    }
    contracts[idx].checklist_locked = true;
    saveContracts(contracts);
    return contracts[idx];
  },

  /**
   * Dual checklist confirmation (C17 & C19)
   */
  confirmChecklist(id: string, role: "BUYER" | "SELLER"): Contract | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === id);
    if (idx === -1) return null;

    const now = new Date().toISOString();
    if (role === "BUYER") {
      contracts[idx].buyer_confirmed_at = now;
    } else {
      contracts[idx].seller_confirmed_at = now;
    }

    // If both have confirmed, lock checklist and mark SIGNED
    if (contracts[idx].buyer_confirmed_at && contracts[idx].seller_confirmed_at) {
      contracts[idx].checklist_locked = true;
      if (contracts[idx].status === "DRAFT" || contracts[idx].status === "REVIEW") {
        contracts[idx].status = "SIGNED";
      }
    }

    saveContracts(contracts);
    return contracts[idx];
  },

  /**
   * Counter terms (C17: Seller or Buyer counters price, deadline, or features)
   */
  counterContract(
    id: string,
    counterData: {
      proposed_by: "BUYER" | "SELLER";
      total_amount: number;
      deadline: string;
      note: string;
      features?: Feature[];
    }
  ): Contract | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === id);
    if (idx === -1) return null;

    const now = new Date().toISOString();
    contracts[idx].status = "REVIEW";
    contracts[idx].total_amount = counterData.total_amount;
    contracts[idx].deadline = counterData.deadline;
    contracts[idx].checklist_locked = false;

    if (counterData.features && counterData.features.length > 0) {
      contracts[idx].features = counterData.features.map((f, i) => ({
        ...f,
        allocated_amount: (counterData.total_amount * f.price_weight) / 100,
        sort_order: i + 1,
      }));
    } else {
      // Re-allocate existing features with new total amount
      contracts[idx].features = contracts[idx].features.map((f) => ({
        ...f,
        allocated_amount: (counterData.total_amount * f.price_weight) / 100,
      }));
    }

    contracts[idx].counter_offer = {
      proposed_by: counterData.proposed_by,
      total_amount: counterData.total_amount,
      deadline: counterData.deadline,
      note: counterData.note,
      proposed_at: now,
    };

    // Reset opposing confirmation
    if (counterData.proposed_by === "SELLER") {
      contracts[idx].seller_confirmed_at = now;
      contracts[idx].buyer_confirmed_at = null;
    } else {
      contracts[idx].buyer_confirmed_at = now;
      contracts[idx].seller_confirmed_at = null;
    }

    saveContracts(contracts);
    return contracts[idx];
  },

  /**
   * Accept counter offer
   */
  acceptCounter(id: string, role: "BUYER" | "SELLER"): Contract | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === id);
    if (idx === -1) return null;

    const now = new Date().toISOString();
    if (role === "BUYER") {
      contracts[idx].buyer_confirmed_at = now;
    } else {
      contracts[idx].seller_confirmed_at = now;
    }

    contracts[idx].counter_offer = null;
    contracts[idx].checklist_locked = true;
    contracts[idx].status = "SIGNED";

    saveContracts(contracts);
    return contracts[idx];
  },

  /**
   * Buyer authorizes PayPal hold: SIGNED -> FUNDED
   * Initiates 29-day authorization hold countdown
   */
  fundContract(id: string, paypalOrderId?: string): Contract | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === id);
    if (idx === -1) return null;

    const authExpiry = new Date(Date.now() + 29 * 86400000).toISOString();
    contracts[idx].status = "FUNDED";
    contracts[idx].paypal_order_id = paypalOrderId || `PAYPAL_ORDER_${Math.random().toString(36).substring(2, 10).toUpperCase()}`;
    contracts[idx].paypal_auth_id = `AUTH_${Math.random().toString(36).substring(2, 12).toUpperCase()}`;
    contracts[idx].auth_expires_at = authExpiry;

    saveContracts(contracts);
    return contracts[idx];
  },

  /**
   * Calculate real live hold countdown
   */
  getHoldInfo(id: string): HoldInfo | null {
    const contract = this.getContract(id);
    if (!contract || !contract.auth_expires_at) {
      return null;
    }

    const expiresAtMs = new Date(contract.auth_expires_at).getTime();
    const nowMs = Date.now();
    const diffMs = Math.max(0, expiresAtMs - nowMs);
    const secondsRemaining = Math.floor(diffMs / 1000);
    const daysRemaining = Math.floor(secondsRemaining / 86400);

    return {
      contract_id: contract.id,
      authorization_id: contract.paypal_auth_id || "AUTH_DEMO_HOLD",
      amount: contract.total_amount.toFixed(2),
      currency: contract.currency,
      status: diffMs <= 0 ? "EXPIRED" : "HELD",
      authorized_at: contract.created_at,
      expires_at: contract.auth_expires_at,
      days_remaining: daysRemaining,
      seconds_remaining: secondsRemaining,
      is_expired: diffMs <= 0,
    };
  },

  /**
   * Get verification report following shared JSON shape (C07 & C29)
   */
  getVerificationReport(contractId: string): VerificationReport {
    const contract = this.getContract(contractId) || SEED_CONTRACTS[0];
    const features = contract.features || [];

    const perFeatureMap: Record<string, {
      feature_id: string;
      feature_title: string;
      status: "PASSED" | "FAILED" | "PENDING";
      price_weight: number;
      allocated_amount: number;
      severity: string;
      evidence: string;
      reason: string | null;
    }> = {};

    let passedCount = 0;
    features.forEach((f) => {
      const isPassed = f.status === "PASSED";
      if (isPassed) passedCount++;

      perFeatureMap[f.id] = {
        feature_id: f.id,
        feature_title: f.title,
        status: f.status === "DISPUTED" ? "FAILED" : f.status,
        price_weight: f.price_weight,
        allocated_amount: f.allocated_amount,
        severity: isPassed ? "NONE" : (f.title.toLowerCase().includes("login") ? "HIGH" : "MEDIUM"),
        evidence: isPassed
          ? `Unit tests passed: 100% assertions met. Acceptance criteria verified against '${f.acceptance_test.substring(0, 40)}...'.`
          : `Automated test runner detected failure: Acceptance criteria '${f.acceptance_test.substring(0, 40)}...' failed during headless container execution.`,
        reason: isPassed ? null : "AST scanner detected hardcoded fallback or skipped assertion in test runner suite.",
      };
    });

    const overallScore = features.length > 0 ? Math.round((passedCount / features.length) * 100) : 75;

    return {
      id: `rep_${contract.id}`,
      submission_id: contract.submission?.id || `sub_${contract.id}`,
      contract_id: contract.id,
      render_job_id: `rnd_gvisor_${Math.random().toString(36).substring(2, 8)}`,
      build_succeeded: true,
      build_logs: `[gVisor Container Sandbox v2.4]\nCloning git repo: ${contract.repo_url || "https://github.com/freelancer/pactpal-storefront"}\nCommit pinned: ${contract.commit_sha || "a1b8c9d4e5f6"}\nRunning: npm install --frozen-lockfile... Done (2.1s)\nRunning: npm run build... Succeeded with 0 syntax errors.\nContainer isolation intact: 0 platform secrets exposed.`,
      overall_score: overallScore,
      next_state: overallScore >= 75 ? "DECISION" : "DISPUTE",
      completed_at: new Date().toISOString(),
      test_suite_results: {
        status: passedCount === features.length ? "PASSED" : "PARTIAL",
        total_tests: 42,
        passed_tests: 35,
        failed_tests: 7,
        skipped_tests: 0,
        coverage_percent: 88.5,
        duration_ms: 12450,
      },
      cheat_scan_findings: [
        {
          finding_id: "ast_jwt_mock_01",
          feature_id: features[1]?.id || "feat_02",
          rule_violated: "NO_HARDCODED_AUTH_RESPONSES",
          severity: "HIGH",
          description: "Hardcoded fake JWT token in /app/api/auth/route.ts bypasses real credential hashing and database validation.",
          file_path: "app/api/auth/route.ts",
          line_number: 42,
        },
        {
          finding_id: "ast_dead_code_02",
          feature_id: features[0]?.id || "feat_01",
          rule_violated: "CLEAN_DEPENDENCY_AUDIT",
          severity: "LOW",
          description: "Unused debug console.log statement found in mobile drawer event listener.",
          file_path: "components/MobileNav.tsx",
          line_number: 88,
        },
      ],
      visual_diff_summary: {
        status: "DIFF_DETECTED",
        similarity_score: 89.2,
        threshold: 90.0,
        passed: false,
        diff_image_url: "/placeholder-diff.png",
        notes: "Figma button padding was 16px horizontal, implementation measured 24px. Visual mismatch on mobile header.",
      },
      per_feature_results: perFeatureMap,
    };
  },

  /**
   * Settle contract: transitions to SETTLED and generates proof-of-work receipt (C45)
   */
  settleContract(id: string, passedAmount?: number): Contract | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === id);
    if (idx === -1) return null;

    contracts[idx].status = "SETTLED";
    saveContracts(contracts);
    return contracts[idx];
  },

  /**
   * Get cryptographic proof-of-work receipt (Commit C44/C45)
   */
  getReceipt(contractId: string): ProofOfWorkReceipt {
    const contract = this.getContract(contractId) || SEED_CONTRACTS[0];
    const id = contract.id;
    const title = contract.title || "Contract Deliverable Verification";
    const total = contract.total_amount || 1500;
    const currency = contract.currency || "USD";

    // Feature settlement calculation
    const featuresList = contract.features && contract.features.length > 0 ? contract.features : [
      { id: "feat_01", contract_id: id, title: "Landing Page & Responsive Navigation", acceptance_test: "All 12 sections render, mobile drawer opens, 100% responsive", price_weight: 25, allocated_amount: 375, status: "PASSED" as const, sort_order: 1 },
      { id: "feat_02", contract_id: id, title: "Login & Session Management", acceptance_test: "Login/logout with JWT, session persists across refresh", price_weight: 20, allocated_amount: 300, status: "FAILED" as const, sort_order: 2 },
      { id: "feat_03", contract_id: id, title: "Interactive Dashboard & Bryntum Gantt", acceptance_test: "Gantt timeline renders with status colors and today line", price_weight: 30, allocated_amount: 450, status: "PASSED" as const, sort_order: 3 },
      { id: "feat_04", contract_id: id, title: "PayPal Escrow Webhook Listeners", acceptance_test: "Order authorization and capture webhook listeners respond with 200", price_weight: 25, allocated_amount: 375, status: "PASSED" as const, sort_order: 4 },
    ];

    const passedFeatures = featuresList.filter((f) => f.status === "PASSED");
    const passedWeight = passedFeatures.reduce((acc, f) => acc + (f.price_weight || 0), 0);
    const sellerPayout = passedFeatures.reduce((acc, f) => acc + (f.allocated_amount || 0), 0);
    const buyerRefund = Math.max(0, total - sellerPayout);
    const failedWeight = 100 - passedWeight;

    const repoUrl = contract.repo_url || contract.submission?.repo_url || "https://github.com/freelancer/pactpal-storefront";
    const commitSha = contract.commit_sha || contract.submission?.commit_sha || "a1b8c9d4e5f67890123456789abcdef012345678";
    const submittedAt = contract.submission?.submitted_at || new Date(Date.now() - 2 * 86400000).toISOString();
    const settledAt = new Date(Date.now() - 1 * 86400000).toISOString();

    // Deterministic SHA-256 proof-of-work fingerprint
    const receiptHash = `0xa9f3e8c2d4b16f7a3e2d1c9b8a7f6e5d4c3b2a190887766554433221100aabb${commitSha.substring(0, 16)}`;

    return {
      id: `rcpt_${id.replace("pct_", "")}`,
      contract_id: id,
      contract_title: title,
      receipt_hash: receiptHash,
      status: "SETTLED",
      generated_at: settledAt,
      issued_at: settledAt,
      settled_at: settledAt,
      submission_id: contract.submission?.id || `sub_${id}_01`,
      verification_report_id: `vrpt_${id}_final`,
      financial_dispatch: {
        total_amount: total,
        seller_payout_amount: sellerPayout,
        buyer_refund_amount: buyerRefund,
        currency,
        passed_weight_percent: passedWeight,
        failed_weight_percent: failedWeight,
        paypal_order_id: contract.paypal_order_id || "17M76648VK7664316",
        paypal_capture_id: `CAP_${id.toUpperCase()}_PAYOUT`,
        paypal_payout_batch_id: `BATCH_${Math.abs(sellerPayout * 13)}_RELEASE`,
        paypal_refund_id: buyerRefund > 0 ? `REFUND_${id.toUpperCase()}_BUYER` : undefined,
      },
      deliverable: {
        repo_url: repoUrl,
        commit_sha: commitSha,
        branch: contract.submission?.branch || "main",
        deploy_url: contract.submission?.deploy_url || "https://preview.pactpal-storefront.vercel.app",
        version_number: contract.submission?.version_number || 1,
        submitted_at: submittedAt,
        is_late: contract.submission?.is_late || false,
      },
      verification_metrics: {
        overall_score: Math.round(passedWeight * 0.95),
        test_suite_status: passedWeight >= 70 ? "PASSED" : "FAILED",
        tests_passed: passedFeatures.length * 3 + 2,
        tests_total: featuresList.length * 3 + 2,
        coverage_percent: 88.5,
        visual_similarity_score: 94.3,
        cheat_scan_findings_count: featuresList.some((f) => f.status === "FAILED") ? 1 : 0,
      },
      features: featuresList.map((f) => ({
        id: f.id,
        title: f.title,
        price_weight: f.price_weight,
        allocated_amount: f.allocated_amount,
        status: f.status as any,
        severity: f.status === "FAILED" ? "HIGH" : "NONE",
        evidence: f.status === "PASSED" ? "Unit tests passed + visual match confirmed" : "Hardcoded mock response flagged in AST scan",
      })),
      evidence_links: {
        github_commit_url: `${repoUrl}/commit/${commitSha}`,
        verification_report_url: `/contracts/${id}/verification`,
        visual_diff_url: `/contracts/${id}/verification#visual-diff`,
        paypal_transaction_url: "https://sandbox.paypal.com/activity/payment/17M76648VK7664316",
        ast_scan_report_url: `/contracts/${id}/verification#ast-scan`,
      },
      tamper_check: {
        is_valid: true,
        algorithm: "SHA-256",
        canonical_payload_digest: `${id}_canonical_digest_verified_2026`,
        referee_engine: "PactPal-Referee-v2.4-gVisor-isolated",
      },
    };
  },

  /**
   * Accept a scope change / mini-agreement (C48: new task appears automatically in Gantt)
   */
  acceptScopeChange(
    contractId: string, 
    changeItem?: { title?: string; price_weight?: number; allocated_amount?: number }
  ): Contract | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === contractId);
    if (idx === -1) return null;

    const contract = contracts[idx];
    if (!contract.features) contract.features = [];

    const existingIndex = contract.features.findIndex((f) => f.title.includes("Dark Mode"));
    if (existingIndex >= 0) {
      return contract;
    }

    const weight = changeItem?.price_weight || 10;
    const amount = changeItem?.allocated_amount || 150;
    const title = changeItem?.title || "[CR-01] Dark Mode & High-Contrast Theme (Accepted Change)";

    const newFeature: Feature = {
      id: `feat_cr_${Math.random().toString(36).substring(2, 7)}`,
      contract_id: contractId,
      title,
      acceptance_test: "User toggle switches between light and dark themes with localStorage persistence",
      price_weight: weight,
      allocated_amount: amount,
      status: "PASSED",
      sort_order: contract.features.length + 1,
    };

    contract.features.push(newFeature);
    contract.total_amount += amount;
    saveContracts(contracts);
    return contract;
  },

  /**
   * Remove simulated scope change (for demo reset)
   */
  removeScopeChange(contractId: string): Contract | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === contractId);
    if (idx === -1) return null;

    const contract = contracts[idx];
    if (!contract.features) return contract;

    const crIndex = contract.features.findIndex((f) => f.title.includes("Dark Mode"));
    if (crIndex >= 0) {
      const removed = contract.features.splice(crIndex, 1)[0];
      contract.total_amount -= (removed.allocated_amount || 150);
      saveContracts(contracts);
    }
    return contract;
  },

  /**
   * Scheduled deadline watcher simulation (C49/C50: triggers final verification & payout)
   */
  simulateDeadlineWatcher(contractId: string): { contract: Contract; logEntry: string; payoutAmount: number; refundAmount: number } | null {
    const contracts = loadContracts();
    const idx = contracts.findIndex((c) => c.id === contractId);
    if (idx === -1) return null;

    const contract = contracts[idx];
    // Set deadline to past
    contract.deadline = new Date(Date.now() - 3600000).toISOString();
    contract.status = "SETTLED";

    const passedFeatures = (contract.features || []).filter((f) => f.status === "PASSED");
    const passedAmount = passedFeatures.reduce((acc, f) => acc + (f.allocated_amount || 0), 0);
    const refundAmount = Math.max(0, contract.total_amount - passedAmount);

    saveContracts(contracts);

    const logEntry = `[DEADLINE WATCHER] Scheduled deadline watcher fired on ${contract.id}. Deadline expired: final verification executed. Payout: $${passedAmount} USD disbursed, $${refundAmount} USD refunded. Status -> SETTLED.`;

    return {
      contract,
      logEntry,
      payoutAmount: passedAmount,
      refundAmount,
    };
  },

  /**
   * Reset to seed data
   */
  resetToDefaults(): void {
    if (isBrowser()) {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
};

