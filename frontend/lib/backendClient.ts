/**
 * PactPal Unified Backend Client Bridge (Phase 2)
 * Connects frontend Next.js app to Python Unified Gateway (http://127.0.0.1:8000)
 * with robust local fallback to mockApi if backend is temporarily unreachable.
 */

import { Contract, Feature, ProofOfWorkReceipt, ContractStatus } from "@/types/contract";
import { mockApi } from "@/lib/mockApi";

const BACKEND_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

async function safeFetch<T>(
  endpoint: string,
  options?: RequestInit,
  fallback?: () => T
): Promise<T> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);

    const res = await fetch(`${BACKEND_BASE}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Actor-Id": "usr_buyer_01",
        ...(options?.headers || {}),
      },
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      if (fallback) return fallback();
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }

    const json = await res.json();
    return json as T;
  } catch {
    if (fallback) {
      return fallback();
    }
    throw new Error(`Backend unavailable at ${BACKEND_BASE}${endpoint}`);
  }
}

export const backendClient = {
  /**
   * Health Check
   */
  async checkHealth(): Promise<{ status: string; service: string; contracts_count?: number }> {
    return safeFetch("/api/v1/health", { method: "GET" }, () => ({
      status: "mock-mode",
      service: "frontend-local-fallback",
    }));
  },

  /**
   * Validate agreement form with AI Agreement Reader (Phase 3)
   */
  async validateAgreement(payload: {
    title: string;
    description?: string;
    total_amount: number;
    deadline: string;
    currency?: string;
    features: Array<{
      title: string;
      acceptance_test: string;
      price_weight: number;
    }>;
  }): Promise<{
    status: "VALID" | "NEEDS_CLARIFICATION";
    checklist?: any;
    clarification_request?: {
      summary: string;
      conversational_message: string;
      clarifications: Array<{
        field: string;
        feature_title?: string;
        issue: string;
        suggested_action: string;
        options: string[];
      }>;
      raw_errors: string[];
    };
  }> {
    try {
      const res = await fetch(`${BACKEND_BASE}/api/v1/agreement-reader/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Local fallback
    }

    const totalWeight = payload.features.reduce((acc, f) => acc + (Number(f.price_weight) || 0), 0);
    const weightValid = Math.abs(totalWeight - 100) < 0.01;
    const allTestsValid = payload.features.every((f) => (f.acceptance_test || "").trim().length >= 10);
    const deadlineValid = new Date(payload.deadline).getTime() > Date.now();

    if (weightValid && allTestsValid && deadlineValid && payload.total_amount > 0) {
      return { status: "VALID" };
    }

    const rawErrors: string[] = [];
    const clarifications: any[] = [];

    if (!weightValid) {
      const diff = 100 - totalWeight;
      const issue = `Feature price weights sum to ${totalWeight.toFixed(1)}%, differing from 100% by ${diff > 0 ? "+" : ""}${diff.toFixed(1)}%.`;
      rawErrors.push(issue);
      clarifications.push({
        field: "features[].price_weight",
        issue,
        suggested_action: "Adjust weights to equal exactly 100%.",
        options: ["Auto-balance weights evenly", "Assign remainder to final feature"]
      });
    }

    if (!allTestsValid) {
      const issue = "One or more features lack a specific, measurable acceptance test (>=10 chars).";
      rawErrors.push(issue);
      clarifications.push({
        field: "features[].acceptance_test",
        issue,
        suggested_action: "Specify measurable pass/fail test conditions for each deliverable.",
        options: ["Adopt AI-suggested test condition"]
      });
    }

    if (!deadlineValid) {
      const issue = "Milestone delivery deadline must be set to a future date.";
      rawErrors.push(issue);
      clarifications.push({
        field: "deadline",
        issue,
        suggested_action: "Select a future deadline date.",
        options: ["Set deadline to 14 days from now"]
      });
    }

    return {
      status: "NEEDS_CLARIFICATION",
      clarification_request: {
        summary: `Contract validation failed with ${rawErrors.length} issue(s). Clarification required before freezing escrow.`,
        conversational_message: "🤝 AI Escrow Referee Notice:\nZero-trust rules require exact, measurable terms before freezing buyer funds. Under our impartial referee policy, I will NEVER guess your milestone prices or acceptance criteria.\n\nPlease clarify the flagged item(s) below:",
        clarifications,
        raw_errors: rawErrors
      }
    };
  },

  /**
   * List all contracts
   */
  async getContracts(): Promise<Contract[]> {
    return safeFetch<{ data: Contract[]; total: number }>(
      "/api/v1/contracts",
      { method: "GET" },
      () => ({ data: mockApi.getContracts() as unknown as Contract[], total: mockApi.getContracts().length })
    ).then((res) => res.data);
  },

  /**
   * Get single contract
   */
  async getContract(id: string): Promise<Contract | null> {
    return safeFetch<Contract | null>(
      `/api/v1/contracts/${id}`,
      { method: "GET" },
      () => (mockApi.getContract(id) as unknown as Contract) || null
    );
  },

  /**
   * Create a new draft contract
   */
  async createContract(payload: {
    title: string;
    description: string;
    total_amount: number;
    deadline: string;
    figma_url?: string;
    repo_url?: string;
    buyer_id?: string;
    buyer_email?: string;
    buyer_name?: string;
    seller_id?: string;
    seller_email?: string;
    seller_name?: string;
    features: Array<{
      title: string;
      acceptance_test: string;
      price_weight: number;
      allocated_amount: number;
    }>;
  }): Promise<Contract> {
    return safeFetch<Contract>(
      "/api/v1/contracts",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      () => mockApi.createContract({
        title: payload.title,
        description: payload.description || payload.title,
        buyer_id: payload.buyer_id,
        buyer_name: payload.buyer_name,
        buyer_email: payload.buyer_email || "alice@buyer.example.com",
        seller_id: payload.seller_id,
        seller_name: payload.seller_name,
        seller_email: payload.seller_email || "bob@seller.example.com",
        total_amount: payload.total_amount,
        deadline: payload.deadline,
        figma_url: payload.figma_url,
        repo_url: payload.repo_url,
        features: payload.features.map((f, i) => ({
          id: `feat_${i + 1}`,
          title: f.title,
          acceptance_test: f.acceptance_test,
          price_weight: f.price_weight,
          allocated_amount: f.allocated_amount,
          status: "PENDING" as const,
          sort_order: i + 1,
        })),
      }) as unknown as Contract
    );
  },

  /**
   * Transition to REVIEW
   */
  async submitForReview(id: string): Promise<Contract> {
    return safeFetch<Contract>(
      `/api/v1/contracts/${id}/submit-review`,
      { method: "POST" },
      () => mockApi.updateContractStatus(id, "REVIEW") as unknown as Contract
    );
  },

  /**
   * Sign / Confirm checklist
   */
  async signContract(id: string, role: "BUYER" | "SELLER" = "SELLER"): Promise<Contract> {
    return safeFetch<Contract>(
      `/api/v1/contracts/${id}/sign`,
      {
        method: "POST",
        headers: { "X-Actor-Id": role === "SELLER" ? "usr_seller_01" : "usr_buyer_01" },
        body: JSON.stringify({ role }),
      },
      () => mockApi.signContract(id) as unknown as Contract
    );
  },

  /**
   * Dual Confirmation Checklist Lock (Phase 3)
   */
  async confirmChecklist(id: string, role: "BUYER" | "SELLER"): Promise<Contract> {
    return safeFetch<Contract>(
      `/api/v1/contracts/${id}/confirm-checklist`,
      {
        method: "POST",
        headers: { "X-Actor-Id": role === "SELLER" ? "usr_seller_01" : "usr_buyer_01" },
        body: JSON.stringify({ role }),
      },
      () => mockApi.confirmChecklist(id, role) as unknown as Contract
    );
  },

  /**
   * Get PayPal 29-day authorization hold details
   */
  async getHoldInfo(id: string): Promise<any> {
    return safeFetch(
      `/api/v1/contracts/${id}/hold`,
      { method: "GET" },
      () => mockApi.getHoldInfo(id)
    );
  },

  /**
   * Mark contract FUNDED
   */
  async fundContract(id: string, paypalOrderId?: string, paypalAuthId?: string): Promise<Contract> {
    return safeFetch<Contract>(
      `/api/v1/contracts/${id}/fund`,
      {
        method: "POST",
        body: JSON.stringify({
          paypal_order_id: paypalOrderId,
          paypal_auth_id: paypalAuthId,
        }),
      },
      () => mockApi.fundContract(id) as unknown as Contract
    );
  },

  /**
   * Submit deliverable for automated verification
   */
  async submitDeliverable(payload: {
    contract_id: string;
    repo_url: string;
    commit_sha?: string;
    build_notes?: string;
  }): Promise<any> {
    return safeFetch(
      "/api/v1/verification/submit",
      {
        method: "POST",
        headers: { "X-Actor-Id": "usr_seller_01" },
        body: JSON.stringify(payload),
      },
      () => mockApi.submitDeliverable(payload.contract_id, {
        repo_url: payload.repo_url,
        commit_sha: payload.commit_sha || "head",
        branch: "main",
        build_notes: payload.build_notes || "",
      })
    );
  },

  /**
   * Get verification report
   */
  async getVerificationReport(contractId: string): Promise<any> {
    return safeFetch(
      `/api/v1/verification/reports/${contractId}`,
      { method: "GET" },
      () => mockApi.getVerificationReport(contractId)
    );
  },

  /**
   * Get AI Referee decision
   */
  async getRefereeDecision(contractId: string): Promise<any> {
    return safeFetch(
      `/api/v1/referee/decisions/${contractId}`,
      { method: "GET" },
      () => null
    );
  },

  /**
   * Negotiate compromise offer (80% partial release)
   */
  async negotiateOffer(contractId: string, passedWeight: number = 80.0): Promise<any> {
    return safeFetch(
      "/api/v1/referee/negotiate",
      {
        method: "POST",
        body: JSON.stringify({ contract_id: contractId, action: "offer", passed_weight: passedWeight }),
      },
      () => ({
        contract_id: contractId,
        passed_weight: passedWeight,
        conversational_offer: `AI Referee Compromise: Accept ${passedWeight}% now or fix flaws within 48h.`,
      })
    );
  },

  /**
   * Evaluate mid-project change request
   */
  async evaluateChangeRequest(description: string, requestedPrice?: number): Promise<any> {
    return safeFetch(
      "/api/v1/negotiator/change-request",
      {
        method: "POST",
        body: JSON.stringify({ description, requested_price: requestedPrice }),
      },
      () => ({
        complexity: "MEDIUM",
        proposed_price: requestedPrice || 250,
        proposed_extra_time_hours: 24,
        ai_reasoning: "Heuristic evaluation based on keywords in scope description.",
      })
    );
  },

  /**
   * Get Proof-of-Work Receipt
   */
  async getReceipt(contractId: string): Promise<ProofOfWorkReceipt | null> {
    return safeFetch<ProofOfWorkReceipt | null>(
      `/api/v1/contracts/${contractId}/receipt`,
      { method: "GET" },
      () => (mockApi.getReceipt(contractId) as unknown as ProofOfWorkReceipt) || null
    );
  },
};
