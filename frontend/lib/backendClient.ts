/**
 * PactPal Unified Backend Client Bridge (Phase 2)
 * Connects frontend Next.js app to Python Unified Gateway (http://127.0.0.1:8000)
 * with robust local fallback to mockApi if backend is temporarily unreachable.
 */

import { Contract, Feature, ContractStatus, ChatMessage } from "@/types/contract";
import { mockApi, ProofOfWorkReceipt } from "@/lib/mockApi";
import { supabase, toUUID, isUUID } from "@/lib/supabase";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://glelhzurkqkrrcsbhlkz.supabase.co";
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "sb_publishable_lG_-_i364GzIiO8oYCzzig_NyOLrG-b";

function getBackendBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_BACKEND_URL) {
    return process.env.NEXT_PUBLIC_BACKEND_URL.replace(/\/$/, "");
  }
  if (typeof window !== "undefined") {
    const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    // In production (Render/Vercel), use relative URL ("") so the browser hits Next.js API routes on the same host,
    // avoiding browser CORS loopback blocks on 127.0.0.1:8000
    return isLocal ? "http://127.0.0.1:8000" : "";
  }
  return "http://127.0.0.1:8000";
}

/**
 * Clean Supabase Public REST fetch helper.
 * Uses the clean public anon key to guarantee that queries never fail with 401
 * even when the client's browser has an expired/corrupted user JWT session.
 */
async function supabaseRestFetch(pathAndQuery: string, init?: RequestInit): Promise<Response> {
  const url = `${SUPABASE_URL}/rest/v1/${pathAndQuery}`;
  return fetch(url, {
    ...init,
    headers: {
      apikey: SUPABASE_ANON_KEY,
      Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
}

function mapSupabaseRowToContract(row: any): Contract {
  const buyerName = row.buyer?.name || "Hirer";
  const buyerEmail = row.buyer?.email || "";
  const sellerName = row.seller?.name || "";
  const sellerEmail = row.seller?.email || "";

  const features: Feature[] = (row.features || [])
    .sort((a: any, b: any) => (a.sort_order || 0) - (b.sort_order || 0))
    .map((f: any, idx: number) => ({
      id: f.id,
      contract_id: f.contract_id || row.id,
      title: f.title,
      acceptance_test: f.acceptance_test,
      price_weight: Number(f.price_weight) || 0,
      allocated_amount: Number(f.allocated_amount) || 0,
      status: f.status || "PENDING",
      sort_order: f.sort_order || idx + 1,
    }));

  return {
    id: row.id,
    title: row.title,
    description: row.description || "",
    status: row.status as ContractStatus,
    total_amount: Number(row.total_amount) || 0,
    currency: row.currency || "USD",
    deadline: row.deadline,
    paypal_order_id: row.paypal_order_id,
    paypal_auth_id: row.paypal_auth_id,
    auth_expires_at: row.auth_expires_at,
    figma_url: row.figma_url,
    repo_url: row.repo_url,
    buyer_id: row.buyer_id,
    buyer_name: buyerName,
    buyer_email: buyerEmail,
    seller_id: row.seller_id,
    seller_name: sellerName,
    seller_email: sellerEmail,
    is_locked: !!row.is_locked,
    checklist_locked: !!row.is_locked,
    buyer_confirmed_at: row.buyer_confirmed_at,
    seller_confirmed_at: row.seller_confirmed_at,
    locked_at: row.locked_at,
    created_at: row.created_at,
    features,
  } as unknown as Contract;
}

async function safeFetch<T>(
  endpoint: string,
  options?: RequestInit,
  fallback?: () => T
): Promise<T> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);
    const baseUrl = getBackendBaseUrl();
    const url = `${baseUrl}${endpoint}`;

    const res = await fetch(url, {
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
    const baseUrl = getBackendBaseUrl();
    throw new Error(`Backend unavailable at ${baseUrl}${endpoint}`);
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
      const baseUrl = getBackendBaseUrl();
      const res = await fetch(`${baseUrl}/api/v1/agreement-reader/validate`, {
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
   * List all contracts directly from Supabase DB with clean public REST recovery
   */
  async getContracts(): Promise<Contract[]> {
    const querySelect = "id,title,description,status,total_amount,currency,deadline,paypal_order_id,paypal_auth_id,auth_expires_at,figma_url,repo_url,buyer_id,seller_id,created_at,updated_at,is_locked,buyer_confirmed_at,seller_confirmed_at,locked_at,features(*),buyer:users!contracts_buyer_id_fkey(id,name,email,paypal_email),seller:users!contracts_seller_id_fkey(id,name,email,paypal_email)";

    try {
      let { data, error } = await supabase
        .from("contracts")
        .select(`
          id,
          title,
          description,
          status,
          total_amount,
          currency,
          deadline,
          paypal_order_id,
          paypal_auth_id,
          auth_expires_at,
          figma_url,
          repo_url,
          buyer_id,
          seller_id,
          created_at,
          updated_at,
          is_locked,
          buyer_confirmed_at,
          seller_confirmed_at,
          locked_at,
          features (*),
          buyer:users!contracts_buyer_id_fkey (id, name, email, paypal_email),
          seller:users!contracts_seller_id_fkey (id, name, email, paypal_email)
        `)
        .order("created_at", { ascending: false });

      // If Supabase returns 401 (e.g. stale/expired user JWT in localStorage), auto-recover via clean public anon REST fetch:
      if (error || !data || data.length === 0) {
        console.warn("Supabase client query issue, attempting clean public anon recovery...", error?.message);
        const res = await supabaseRestFetch(`contracts?select=${encodeURIComponent(querySelect)}&order=created_at.desc`);
        if (res.ok) {
          const restData = await res.json();
          if (restData && restData.length > 0) {
            data = restData;
            error = null;
          }
        }
      }

      if (!error && data && data.length > 0) {
        const mapped = data.map(mapSupabaseRowToContract);
        mockApi.syncContractsFromSupabase(mapped);
        return mapped;
      }
    } catch (err) {
      console.warn("Supabase query note, falling back to clean REST recovery:", err);
      try {
        const res = await supabaseRestFetch(`contracts?select=${encodeURIComponent(querySelect)}&order=created_at.desc`);
        if (res.ok) {
          const restData = await res.json();
          if (restData && restData.length > 0) {
            const mapped = restData.map(mapSupabaseRowToContract);
            mockApi.syncContractsFromSupabase(mapped);
            return mapped;
          }
        }
      } catch (restErr) {
        console.warn("Clean REST recovery error:", restErr);
      }
    }

    return safeFetch<{ data: Contract[]; total: number }>(
      "/api/v1/contracts",
      { method: "GET" },
      () => ({ data: mockApi.getContracts() as unknown as Contract[], total: mockApi.getContracts().length })
    ).then((res) => res.data);
  },

  /**
   * Get single contract by ID from Supabase DB with clean public REST recovery
   */
  async getContract(id: string): Promise<Contract | null> {
    if (!id) return null;
    const targetUuid = toUUID(id);
    const querySelect = "id,title,description,status,total_amount,currency,deadline,paypal_order_id,paypal_auth_id,auth_expires_at,figma_url,repo_url,buyer_id,seller_id,created_at,updated_at,is_locked,buyer_confirmed_at,seller_confirmed_at,locked_at,features(*),buyer:users!contracts_buyer_id_fkey(id,name,email,paypal_email),seller:users!contracts_seller_id_fkey(id,name,email,paypal_email)";

    try {
      let { data, error } = await supabase
        .from("contracts")
        .select(`
          id,
          title,
          description,
          status,
          total_amount,
          currency,
          deadline,
          paypal_order_id,
          paypal_auth_id,
          auth_expires_at,
          figma_url,
          repo_url,
          buyer_id,
          seller_id,
          created_at,
          updated_at,
          is_locked,
          buyer_confirmed_at,
          seller_confirmed_at,
          locked_at,
          features (*),
          buyer:users!contracts_buyer_id_fkey (id, name, email, paypal_email),
          seller:users!contracts_seller_id_fkey (id, name, email, paypal_email)
        `)
        .or(`id.eq.${id},id.eq.${targetUuid}`)
        .maybeSingle();

      if (error || !data) {
        const res = await supabaseRestFetch(
          `contracts?select=${encodeURIComponent(querySelect)}&or=(id.eq.${id},id.eq.${targetUuid})&limit=1`
        );
        if (res.ok) {
          const rows = await res.json();
          if (rows && rows.length > 0) {
            data = rows[0];
            error = null;
          }
        }
      }

      if (!error && data) {
        const mapped = mapSupabaseRowToContract(data);
        return mapped;
      }
    } catch (err) {
      console.warn("Supabase getContract note, attempting clean REST recovery:", err);
      try {
        const res = await supabaseRestFetch(
          `contracts?select=${encodeURIComponent(querySelect)}&or=(id.eq.${id},id.eq.${targetUuid})&limit=1`
        );
        if (res.ok) {
          const rows = await res.json();
          if (rows && rows.length > 0) {
            return mapSupabaseRowToContract(rows[0]);
          }
        }
      } catch {}
    }

    return safeFetch<Contract | null>(
      `/api/v1/contracts/${id}`,
      { method: "GET" },
      () => (mockApi.getContract(id) as unknown as Contract) || (mockApi.getContract(targetUuid) as unknown as Contract) || null
    );
  },

  /**
   * Create a new contract stored directly in Supabase DB.
   * Resolves existing users by email first to prevent 23505 duplicate key and 23503 foreign key constraint errors.
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
    const contractId = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : toUUID(`pct_${Date.now()}_${Math.random()}`);

    const cleanBuyerEmail = (payload.buyer_email || "hirer@pactpal.dev").trim().toLowerCase();
    const cleanBuyerName = payload.buyer_name || cleanBuyerEmail.split("@")[0] || "Hirer";
    let buyerUUID = toUUID(payload.buyer_id || cleanBuyerEmail);

    // 1. Resolve Buyer: check if user already exists in public.users to avoid 23505 conflict
    try {
      const userCheckRes = await supabaseRestFetch(
        `users?select=id,email&email=eq.${encodeURIComponent(cleanBuyerEmail)}&limit=1`
      );
      if (userCheckRes.ok) {
        const existing = await userCheckRes.json();
        if (existing && existing.length > 0 && existing[0].id) {
          buyerUUID = existing[0].id;
        } else {
          // Buyer does not exist yet: create user row
          await supabaseRestFetch("users", {
            method: "POST",
            body: JSON.stringify({
              id: buyerUUID,
              role: "BUYER",
              name: cleanBuyerName,
              email: cleanBuyerEmail,
              updated_at: new Date().toISOString(),
            }),
          });
        }
      }
    } catch (e) {
      console.warn("Buyer lookup note:", e);
    }

    // 2. Resolve Seller: check if seller already exists in public.users
    let sellerUUID: string | null = null;
    const cleanSellerEmail = (payload.seller_email || "").trim().toLowerCase();
    if (cleanSellerEmail || payload.seller_id) {
      const sellerRaw = payload.seller_id || cleanSellerEmail || "usr_seller_01";
      sellerUUID = toUUID(sellerRaw);
      const sellerName = payload.seller_name || cleanSellerEmail.split("@")[0] || "Seller";

      try {
        const sellerCheckRes = await supabaseRestFetch(
          `users?select=id,email&email=eq.${encodeURIComponent(cleanSellerEmail || "alex.dev@code.io")}&limit=1`
        );
        if (sellerCheckRes.ok) {
          const existing = await sellerCheckRes.json();
          if (existing && existing.length > 0 && existing[0].id) {
            sellerUUID = existing[0].id;
          } else if (cleanSellerEmail) {
            await supabaseRestFetch("users", {
              method: "POST",
              body: JSON.stringify({
                id: sellerUUID,
                role: "SELLER",
                name: sellerName,
                email: cleanSellerEmail,
                updated_at: new Date().toISOString(),
              }),
            });
          }
        }
      } catch (e) {
        console.warn("Seller lookup note:", e);
      }
    }

    // 3. Insert contract into Supabase with clean public REST call
    const contractBody = {
      id: contractId,
      buyer_id: buyerUUID,
      seller_id: sellerUUID,
      title: payload.title,
      description: payload.description || payload.title,
      status: "DRAFT",
      total_amount: payload.total_amount,
      currency: "USD",
      deadline: payload.deadline,
      figma_url: payload.figma_url || null,
      repo_url: payload.repo_url || null,
      is_locked: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    try {
      const insertRes = await supabaseRestFetch("contracts", {
        method: "POST",
        body: JSON.stringify(contractBody),
      });

      if (!insertRes.ok) {
        const errText = await insertRes.text();
        console.error("Supabase contract insert error:", insertRes.status, errText);
      } else {
        console.log("Contract successfully persisted to Supabase:", contractId);
      }
    } catch (supaErr) {
      console.warn("Supabase contract creation exception:", supaErr);
    }

    // 4. Insert features linked to contract
    if (payload.features && payload.features.length > 0) {
      const featureRows = payload.features.map((f, i) => ({
        id: toUUID(`${contractId}_feat_${i + 1}`),
        contract_id: contractId,
        title: f.title,
        acceptance_test: f.acceptance_test,
        price_weight: Number(f.price_weight) || 0,
        allocated_amount: Number(f.allocated_amount) || ((payload.total_amount * Number(f.price_weight)) / 100),
        status: "PENDING",
        sort_order: i + 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }));

      try {
        await supabaseRestFetch("features", {
          method: "POST",
          body: JSON.stringify(featureRows),
        });
      } catch (featErr) {
        console.warn("Supabase features insert error:", featErr);
      }
    }

    // 5. Insert initial negotiation chat message in Supabase
    try {
      await supabaseRestFetch("messages", {
        method: "POST",
        body: JSON.stringify({
          id: toUUID(`${contractId}_msg_init`),
          contract_id: contractId,
          sender_id: buyerUUID,
          sender_type: "BUYER",
          content: `Contract initiated: "${payload.title}" with total budget $${payload.total_amount.toLocaleString()}. Milestone checklist created.`,
          metadata: { event: "CONTRACT_CREATED", total_amount: payload.total_amount },
          sent_at: new Date().toISOString(),
        }),
      });
    } catch (msgErr) {
      console.warn("Supabase initial message insert error:", msgErr);
    }

    // 6. Sync to local mock cache for immediate client reactivity
    const localContract = mockApi.createContract({
      id: contractId,
      title: payload.title,
      description: payload.description || payload.title,
      buyer_id: buyerUUID,
      buyer_name: cleanBuyerName,
      buyer_email: cleanBuyerEmail,
      seller_id: sellerUUID || undefined,
      seller_name: payload.seller_name || undefined,
      seller_email: cleanSellerEmail || undefined,
      total_amount: payload.total_amount,
      deadline: payload.deadline,
      figma_url: payload.figma_url,
      repo_url: payload.repo_url,
      features: payload.features.map((f, i) => ({
        title: f.title,
        acceptance_test: f.acceptance_test,
        price_weight: f.price_weight,
      })),
    });

    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("pactpal_contract_created"));
    }

    safeFetch("/api/v1/contracts", {
      method: "POST",
      body: JSON.stringify({ ...payload, id: contractId }),
    }, () => null).catch(() => {});

    return localContract as unknown as Contract;
  },

  /**
   * Freelancer applies & signs agreement terms (stores in Supabase DB)
   */
  async applyToContract(
    id: string,
    freelancer: { id?: string; name?: string; email?: string; note?: string }
  ): Promise<Contract | null> {
    const targetUuid = toUUID(id);
    const sellerUUID = toUUID(freelancer.id || freelancer.email || "usr_seller_01");
    const sellerEmail = freelancer.email || "freelancer@example.com";
    const sellerName = freelancer.name || sellerEmail.split("@")[0];

    try {
      await supabase.from("users").upsert({
        id: sellerUUID,
        role: "SELLER",
        name: sellerName,
        email: sellerEmail,
        updated_at: new Date().toISOString(),
      }, { onConflict: "id" });

      await supabase
        .from("contracts")
        .update({
          seller_id: sellerUUID,
          status: "REVIEW",
          seller_confirmed_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        .or(`id.eq.${id},id.eq.${targetUuid}`);

      await supabase.from("messages").insert({
        contract_id: targetUuid,
        sender_id: sellerUUID,
        sender_type: "SELLER",
        content: `Application Registered: Freelancer ${sellerName} has agreed to specifications and confirmed milestone terms. Awaiting Hirer approval.`,
        metadata: { event: "FREELANCER_APPLIED" },
        sent_at: new Date().toISOString(),
      });
    } catch (e) {
      console.warn("Supabase applyToContract error:", e);
    }

    const res = mockApi.applyToContract(id, freelancer);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("pactpal_contract_updated"));
    }
    return res as unknown as Contract;
  },

  /**
   * Hirer approves freelancer and dual-signs contract (stores in Supabase DB)
   */
  async approveAndSignContract(
    id: string,
    buyer?: { id?: string; name?: string; email?: string }
  ): Promise<Contract | null> {
    const targetUuid = toUUID(id);
    const now = new Date().toISOString();

    try {
      await supabase
        .from("contracts")
        .update({
          status: "SIGNED",
          is_locked: true,
          buyer_confirmed_at: now,
          locked_at: now,
          updated_at: now,
        })
        .or(`id.eq.${id},id.eq.${targetUuid}`);

      await supabase.from("messages").insert({
        contract_id: targetUuid,
        sender_type: "AI_REFEREE",
        content: `Contract Fully Signed! Both Hirer and Freelancer have stamped approval. Status transitioned to SIGNED. Contract has moved to active contracts.`,
        metadata: { event: "CONTRACT_SIGNED" },
        sent_at: now,
      });
    } catch (e) {
      console.warn("Supabase approveAndSignContract error:", e);
    }

    const res = mockApi.approveAndSignContract(id, buyer);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("pactpal_contract_updated"));
    }
    return res as unknown as Contract;
  },

  /**
   * Transition to REVIEW
   */
  async submitForReview(id: string): Promise<Contract> {
    const targetUuid = toUUID(id);
    try {
      await supabase.from("contracts").update({ status: "REVIEW", updated_at: new Date().toISOString() }).or(`id.eq.${id},id.eq.${targetUuid}`);
    } catch (e) {
      console.warn("Supabase submitForReview error:", e);
    }

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
    const targetUuid = toUUID(id);
    try {
      await supabase.from("contracts").update({ status: "SIGNED", updated_at: new Date().toISOString() }).or(`id.eq.${id},id.eq.${targetUuid}`);
    } catch (e) {
      console.warn("Supabase signContract error:", e);
    }

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
   * Dual Confirmation Checklist Lock (Phase 3) - Persisted to Supabase DB
   */
  async confirmChecklist(id: string, role: "BUYER" | "SELLER", actor?: any): Promise<Contract> {
    const targetUuid = toUUID(id);
    const now = new Date().toISOString();

    try {
      const updates: any = { updated_at: now };
      if (role === "BUYER") {
        updates.buyer_confirmed_at = now;
      } else {
        updates.seller_confirmed_at = now;
        updates.status = "REVIEW";
      }

      const { data: curr } = await supabase.from("contracts").select("*").or(`id.eq.${id},id.eq.${targetUuid}`).maybeSingle();
      if (curr) {
        const hasBuyer = updates.buyer_confirmed_at || curr.buyer_confirmed_at;
        const hasSeller = updates.seller_confirmed_at || curr.seller_confirmed_at;
        if (hasBuyer && hasSeller) {
          updates.is_locked = true;
          updates.locked_at = now;
          updates.status = "SIGNED";
        }
      }

      await supabase.from("contracts").update(updates).or(`id.eq.${id},id.eq.${targetUuid}`);
    } catch (e) {
      console.warn("Supabase confirmChecklist error:", e);
    }

    mockApi.confirmChecklist(id, role, actor);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("pactpal_contract_updated"));
    }

    return safeFetch<Contract>(
      `/api/v1/contracts/${id}/confirm-checklist`,
      {
        method: "POST",
        headers: { "X-Actor-Id": role === "SELLER" ? "usr_seller_01" : "usr_buyer_01" },
        body: JSON.stringify({ role }),
      },
      () => mockApi.confirmChecklist(id, role, actor) as unknown as Contract
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
   * Mark contract FUNDED in Supabase DB
   */
  async fundContract(id: string, paypalOrderId?: string, paypalAuthId?: string, expiresAt?: string): Promise<Contract> {
    const targetUuid = toUUID(id);
    const now = new Date().toISOString();
    const finalExpiresAt = expiresAt || new Date(Date.now() + 29 * 86400000).toISOString();
    const pOrderId = paypalOrderId || `ORD-${Date.now()}`;
    const pAuthId = paypalAuthId || `AUTH-${Date.now()}`;

    try {
      await supabase
        .from("contracts")
        .update({
          status: "FUNDED",
          paypal_order_id: pOrderId,
          paypal_auth_id: pAuthId,
          auth_expires_at: finalExpiresAt,
          updated_at: now,
        })
        .or(`id.eq.${id},id.eq.${targetUuid}`);

      const { data: cData } = await supabase.from("contracts").select("total_amount, currency").or(`id.eq.${id},id.eq.${targetUuid}`).maybeSingle();
      await supabase.from("payments").insert({
        id: toUUID(`${targetUuid}_pmt_${Date.now()}`),
        contract_id: targetUuid,
        payment_type: "AUTHORIZATION",
        paypal_reference_id: pAuthId,
        amount: cData?.total_amount || 1500,
        currency: cData?.currency || "USD",
        status: "COMPLETED",
        metadata: { paypal_order_id: pOrderId },
        processed_at: now,
      });
    } catch (e) {
      console.warn("Supabase fundContract error:", e);
    }

    mockApi.fundContract(id, pOrderId, pAuthId);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("pactpal_contract_updated"));
    }

    return safeFetch<Contract>(
      `/api/v1/contracts/${id}/fund`,
      {
        method: "POST",
        body: JSON.stringify({
          paypal_order_id: pOrderId,
          paypal_auth_id: pAuthId,
        }),
      },
      () => mockApi.fundContract(id, pOrderId, pAuthId) as unknown as Contract
    );
  },

  /**
   * Create official PayPal Sandbox order with AUTHORIZE intent (Funds Freezing)
   */
  async createEscrowHold(payload: {
    contract_id: string;
    amount: number;
    currency?: string;
    title?: string;
    origin?: string;
  }): Promise<{ success: boolean; order_id: string; approve_url: string; amount: number; currency: string }> {
    const res = await fetch("/api/paypal/escrow/create-hold", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || !data.approve_url) {
      throw new Error(data.message || data.error || "Failed to initialize PayPal escrow hold.");
    }
    return data;
  },

  /**
   * Execute authorization against approved PayPal order (Funds Frozen for 29 Days)
   */
  async authorizeEscrowHold(payload: {
    contract_id: string;
    order_id: string;
  }): Promise<{ success: boolean; paypal_auth_id: string; auth_expires_at: string; status: string; held_amount?: number }> {
    const res = await fetch("/api/paypal/escrow/authorize-hold", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || !data.paypal_auth_id) {
      throw new Error(data.message || data.error || "Failed to execute PayPal authorization hold.");
    }

    // Persist real PayPal authorization details in Supabase & local state
    await backendClient.fundContract(payload.contract_id, payload.order_id, data.paypal_auth_id, data.auth_expires_at);

    return data;
  },

  /**
   * Capture final payment from frozen PayPal authorization hold
   */
  async captureEscrow(payload: {
    contract_id: string;
    authorization_id: string;
    amount: number;
    currency?: string;
    receipt_hash?: string;
    is_final_capture?: boolean;
  }): Promise<{ success: boolean; capture_id: string; status: string }> {
    const res = await fetch("/api/paypal/escrow/capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    return data;
  },

  /**
   * Submit deliverable for automated verification (persisted to Supabase DB)
   */
  async submitDeliverable(payload: {
    contract_id: string;
    repo_url: string;
    commit_sha?: string;
    branch?: string;
    deploy_url?: string;
    build_notes?: string;
  }): Promise<any> {
    const targetUuid = toUUID(payload.contract_id);
    const now = new Date().toISOString();

    try {
      const { data: cData } = await supabase.from("contracts").select("seller_id").or(`id.eq.${payload.contract_id},id.eq.${targetUuid}`).maybeSingle();
      const sellerId = cData?.seller_id || toUUID("usr_seller_01");

      await supabase
        .from("contracts")
        .update({
          status: "SUBMITTED",
          repo_url: payload.repo_url,
          updated_at: now,
        })
        .or(`id.eq.${payload.contract_id},id.eq.${targetUuid}`);

      await supabase.from("submissions").insert({
        id: toUUID(`${targetUuid}_sub_${Date.now()}`),
        contract_id: targetUuid,
        seller_id: sellerId,
        repo_url: payload.repo_url,
        commit_sha: payload.commit_sha || "head-submission",
        build_notes: payload.build_notes || "",
        submission_number: 1,
        is_late: false,
        submitted_at: now,
      });
    } catch (e) {
      console.warn("Supabase submitDeliverable error:", e);
    }

    mockApi.submitDeliverable(payload.contract_id, {
      repo_url: payload.repo_url,
      commit_sha: payload.commit_sha || "head",
      branch: "main",
      build_notes: payload.build_notes || "",
    });

    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("pactpal_contract_updated"));
    }

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

  /**
   * Get negotiation chat messages directly from Supabase DB with clean public REST recovery
   */
  async getMessages(contractId: string): Promise<ChatMessage[]> {
    const targetUuid = toUUID(contractId);
    try {
      let { data, error } = await supabase
        .from("messages")
        .select("id, contract_id, sender_id, sender_type, content, metadata, sent_at")
        .or(`contract_id.eq.${contractId},contract_id.eq.${targetUuid}`)
        .order("sent_at", { ascending: true });

      // If Supabase returns 401 (e.g. stale token), auto-recover via clean public REST fetch:
      if (error || !data || data.length === 0) {
        try {
          const res = await supabaseRestFetch(
            `messages?select=id,contract_id,sender_id,sender_type,content,metadata,sent_at&or=(contract_id.eq.${contractId},contract_id.eq.${targetUuid})&order=sent_at.asc`
          );
          if (res.ok) {
            const restData = await res.json();
            if (restData && restData.length > 0) {
              data = restData;
              error = null;
            }
          }
        } catch {}
      }

      if (!error && data && data.length > 0) {
        const mapped: ChatMessage[] = data.map((row: any) => {
          let senderName = row.metadata?.sender_name;
          if (!senderName) {
            if (row.sender_type === "BUYER") senderName = "Hirer";
            else if (row.sender_type === "SELLER") senderName = "Freelancer";
            else senderName = "AI Referee";
          }
          return {
            id: row.id,
            contract_id: contractId,
            sender_type: row.sender_type as "BUYER" | "SELLER" | "AI_REFEREE",
            sender_name: senderName,
            content: row.content,
            sent_at: row.sent_at,
            metadata: row.metadata || null,
          };
        });
        mockApi.syncMessagesFromSupabase(contractId, mapped);
        return mapped;
      }
    } catch (err) {
      console.warn("Supabase getMessages error:", err);
    }
    return mockApi.getMessages(contractId);
  },

  /**
   * Send negotiation chat message: persists directly to Supabase DB + local cache
   */
  async sendMessage(
    contractId: string,
    message: {
      sender_type: "BUYER" | "SELLER" | "AI_REFEREE";
      sender_name?: string;
      content: string;
      metadata?: any;
      sender_id?: string;
    }
  ): Promise<ChatMessage> {
    const targetUuid = toUUID(contractId);
    const senderUuid = message.sender_id ? toUUID(message.sender_id) : toUUID(message.sender_type);

    // Save to local mock state first for instant responsiveness
    const localMsg = mockApi.sendMessage(contractId, message);

    try {
      const msgRow = {
        id: toUUID(localMsg.id),
        contract_id: targetUuid,
        sender_id: senderUuid,
        sender_type: message.sender_type,
        content: message.content,
        metadata: { ...(message.metadata || {}), sender_name: localMsg.sender_name },
        sent_at: localMsg.sent_at,
      };

      const res = await supabaseRestFetch("messages", {
        method: "POST",
        body: JSON.stringify(msgRow),
      });

      if (!res.ok) {
        await supabase.from("messages").insert(msgRow);
      }
    } catch (err) {
      console.warn("Supabase sendMessage insert error:", err);
    }

    return localMsg;
  },

  /**
   * Update contract status in Supabase DB + local cache
   */
  async updateContractStatus(id: string, status: ContractStatus): Promise<Contract | null> {
    const targetUuid = toUUID(id);
    const now = new Date().toISOString();
    const updatePayload = {
      status,
      updated_at: now,
    };

    try {
      const res = await supabaseRestFetch(`contracts?or=(id.eq.${id},id.eq.${targetUuid})`, {
        method: "PATCH",
        body: JSON.stringify(updatePayload),
      });
      if (!res.ok) {
        await supabase.from("contracts").update(updatePayload).or(`id.eq.${id},id.eq.${targetUuid}`);
      }
    } catch (err) {
      console.warn("Supabase updateContractStatus note:", err);
      try {
        await supabase.from("contracts").update(updatePayload).or(`id.eq.${id},id.eq.${targetUuid}`);
      } catch {}
    }

    const localUpdated = mockApi.updateContractStatus(id, status);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("pactpal_contract_updated"));
    }
    return localUpdated;
  },

  /**
   * Reset chat messages for a contract in Supabase DB and local cache
   */
  async resetMessages(contractId: string): Promise<void> {
    const targetUuid = toUUID(contractId);
    mockApi.resetMessages(contractId);
    try {
      await supabase
        .from("messages")
        .delete()
        .or(`contract_id.eq.${contractId},contract_id.eq.${targetUuid}`);
    } catch (err) {
      console.warn("Supabase resetMessages delete error:", err);
    }
  },

  /**
   * Propose counter terms: updates Supabase DB + local cache
   */
  async counterContract(
    id: string,
    counterData: {
      proposed_by: "BUYER" | "SELLER";
      total_amount: number;
      deadline: string;
      note: string;
      features?: Feature[];
    }
  ): Promise<Contract | null> {
    const targetUuid = toUUID(id);
    const now = new Date().toISOString();
    const localUpdated = mockApi.counterContract(id, counterData);

    try {
      const updatePayload: any = {
        status: "REVIEW",
        total_amount: counterData.total_amount,
        deadline: counterData.deadline,
        is_locked: false,
        updated_at: now,
      };
      if (counterData.proposed_by === "SELLER") {
        updatePayload.seller_confirmed_at = now;
        updatePayload.buyer_confirmed_at = null;
      } else {
        updatePayload.buyer_confirmed_at = now;
        updatePayload.seller_confirmed_at = null;
      }
      await supabase.from("contracts").update(updatePayload).or(`id.eq.${id},id.eq.${targetUuid}`);

      if (counterData.features && counterData.features.length > 0) {
        for (const f of counterData.features) {
          await supabase
            .from("features")
            .update({
              price_weight: f.price_weight,
              allocated_amount: (counterData.total_amount * f.price_weight) / 100,
              updated_at: now,
            })
            .or(`id.eq.${f.id},id.eq.${toUUID(f.id)}`);
        }
      }
    } catch (err) {
      console.warn("Supabase counterContract error:", err);
    }

    return localUpdated;
  },

  /**
   * Accept counter offer: updates Supabase DB + local cache
   */
  async acceptCounter(id: string, role: "BUYER" | "SELLER"): Promise<Contract | null> {
    const targetUuid = toUUID(id);
    const now = new Date().toISOString();
    const localUpdated = mockApi.acceptCounter(id, role);

    try {
      const updatePayload: any = {
        status: "SIGNED",
        is_locked: true,
        updated_at: now,
      };
      if (role === "BUYER") {
        updatePayload.buyer_confirmed_at = now;
      } else {
        updatePayload.seller_confirmed_at = now;
      }
      await supabase.from("contracts").update(updatePayload).or(`id.eq.${id},id.eq.${targetUuid}`);
    } catch (err) {
      console.warn("Supabase acceptCounter error:", err);
    }

    return localUpdated;
  },

  /**
   * Settle contract: executes real PayPal capture if auth exists, updates Supabase DB + local cache
   */
  async settleContract(id: string, passedAmount?: number): Promise<Contract | null> {
    const targetUuid = toUUID(id);
    const localContract = mockApi.getContract(id);
    let authId = localContract?.paypal_auth_id;

    // Check if live contract in Supabase has paypal_auth_id
    if (!authId) {
      try {
        const { data } = await supabase.from("contracts").select("paypal_auth_id, total_amount, currency").or(`id.eq.${id},id.eq.${targetUuid}`).maybeSingle();
        if (data?.paypal_auth_id) {
          authId = data.paypal_auth_id;
        }
      } catch {}
    }

    let captureId: string | null = null;
    if (authId && !authId.startsWith("AUTH-DEMO") && !authId.startsWith("AUTH_DEMO")) {
      try {
        const capRes = await this.captureEscrow({
          contract_id: id,
          authorization_id: authId,
          amount: passedAmount ?? localContract?.total_amount ?? 1500,
          currency: localContract?.currency || "USD",
          is_final_capture: true,
        });
        if (capRes?.capture_id) {
          captureId = capRes.capture_id;
        }
      } catch (err) {
        console.warn("PayPal escrow capture notice:", err);
      }
    }

    const localUpdated = mockApi.settleContract(id, passedAmount);
    if (localUpdated && captureId) {
      (localUpdated as any).paypal_capture_id = captureId;
    }

    try {
      const now = new Date().toISOString();
      await supabase
        .from("contracts")
        .update({
          status: "SETTLED",
          updated_at: now,
        })
        .or(`id.eq.${id},id.eq.${targetUuid}`);

      if (captureId) {
        await supabase.from("payments").insert({
          id: toUUID(`${targetUuid}_cap_${Date.now()}`),
          contract_id: targetUuid,
          payment_type: "CAPTURE",
          paypal_reference_id: captureId,
          amount: passedAmount ?? localContract?.total_amount ?? 1500,
          currency: localContract?.currency || "USD",
          status: "COMPLETED",
          metadata: { paypal_auth_id: authId },
          processed_at: now,
        });
      }
    } catch (err) {
      console.warn("Supabase settleContract error:", err);
    }

    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("pactpal_contract_updated"));
    }

    return localUpdated;
  },
};
