"use client";

import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import Link from "next/link";
import { ArrowRight, Clock, CheckCircle, Circle, Briefcase, FileSignature, CheckCircle2, Sparkles, User, ExternalLink } from "lucide-react";
import { mockApi, Contract, ContractStatus, CONTRACT_STATES_META } from "@/lib/mockApi";
import { getCurrentUser, UserProfile, toUUID } from "@/lib/supabase";
import { backendClient } from "@/lib/backendClient";

const statusColors: Record<string, { color: string; bg: string; label: string }> = {
  DRAFT:       { color: "#7C89A8", bg: "rgba(124,137,168,0.1)", label: "Draft" },
  REVIEW:      { color: "#00A3E0", bg: "rgba(0,163,224,0.1)", label: "In Review" },
  SIGNED:      { color: "#7A5CFF", bg: "rgba(122,92,255,0.1)", label: "Signed" },
  FUNDED:      { color: "#FF9800", bg: "rgba(255,152,0,0.1)", label: "Funded" },
  IN_PROGRESS: { color: "#0066FF", bg: "rgba(0,102,255,0.1)", label: "In Progress" },
  SUBMITTED:   { color: "#00A3E0", bg: "rgba(0,163,224,0.1)", label: "Submitted" },
  VERIFYING:   { color: "#7A5CFF", bg: "rgba(122,92,255,0.1)", label: "Verifying" },
  DECISION:    { color: "#FF9800", bg: "rgba(255,152,0,0.1)", label: "Decision" },
  SETTLED:     { color: "#4CAF50", bg: "rgba(76,175,80,0.1)", label: "Settled" },
  DISPUTE:     { color: "#F44336", bg: "rgba(244,67,54,0.1)", label: "Dispute" },
};

function isUserBuyer(c: Contract, user: UserProfile | null): boolean {
  if (!user) return false;
  const userEmail = (user.email || "").trim().toLowerCase();
  const userName = (user.name || "").trim().toLowerCase();
  const userId = user.id || "";
  const userUuid = toUUID(userId);

  const buyerEmail = (c.buyer_email || "").trim().toLowerCase();
  const buyerName = (c.buyer_name || "").trim().toLowerCase();
  const buyerId = c.buyer_id || "";

  if (userId && (buyerId === userId || buyerId === userUuid)) return true;
  if (userEmail && buyerEmail && buyerEmail === userEmail) return true;
  if (userName && buyerName && (userName.includes(buyerName) || buyerName.includes(userName))) return true;
  return false;
}

function isUserSeller(c: Contract, user: UserProfile | null): boolean {
  if (!user) return false;
  const userEmail = (user.email || "").trim().toLowerCase();
  const userName = (user.name || "").trim().toLowerCase();
  const userId = user.id || "";
  const userUuid = toUUID(userId);

  const sellerEmail = (c.seller_email || "").trim().toLowerCase();
  const sellerName = (c.seller_name || "").trim().toLowerCase();
  const sellerId = c.seller_id || "";

  if (userId && (sellerId === userId || sellerId === userUuid)) return true;
  if (userEmail && sellerEmail && sellerEmail === userEmail) return true;
  if (userName && sellerName && (userName.includes(sellerName) || sellerName.includes(userName))) return true;
  return false;
}

const DEFAULT_AVAILABLE_PROJECTS: Contract[] = [
  {
    id: "pct_open_saas_01",
    title: "Next.js 15 AI SaaS Landing & Stripe Metered Billing",
    description: "Develop high-converting responsive landing page with Bento grid, interactive pricing calculator, and Stripe webhook subscription sync.",
    buyer_id: "usr_hirer_marcus",
    buyer_name: "Marcus Vance",
    buyer_email: "marcus@scaleup.co",
    seller_id: "usr_seller_open",
    seller_name: "Unassigned Freelancer",
    seller_email: "open@pactpal.dev",
    status: "DRAFT",
    total_amount: 2400,
    currency: "USD",
    deadline: new Date(Date.now() + 18 * 86400000).toISOString(),
    figma_url: "https://figma.com/file/ai-saas-platform",
    created_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    features: [
      { id: "f_av_1", contract_id: "pct_open_saas_01", title: "Interactive Bento Grid & Framer Motion", acceptance_test: "Renders 6 feature cards with smooth spring transitions and responsive mobile drawer", price_weight: 35, allocated_amount: 840, status: "PENDING", sort_order: 1 },
      { id: "f_av_2", contract_id: "pct_open_saas_01", title: "Stripe Metered Usage & Webhook Listeners", acceptance_test: "Handles customer.subscription.created and invoice.paid with 200 OK and idempotent DB sync", price_weight: 40, allocated_amount: 960, status: "PENDING", sort_order: 2 },
      { id: "f_av_3", contract_id: "pct_open_saas_01", title: "Light/Dark Mode Theme Engine", acceptance_test: "Zero flicker theme switch stored in localStorage with Tailwind CSS variables", price_weight: 25, allocated_amount: 600, status: "PENDING", sort_order: 3 },
    ],
  },
  {
    id: "pct_open_fintech_02",
    title: "React Native Fintech App & Biometric Auth Bridge",
    description: "Build iOS and Android cross-platform financial wallet with biometric authentication, instant balance updates, and live exchange rate charts.",
    buyer_id: "usr_hirer_elena",
    buyer_name: "Elena Rostova",
    buyer_email: "elena@uxcraft.design",
    seller_id: "usr_seller_open",
    seller_name: "Unassigned Freelancer",
    seller_email: "open@pactpal.dev",
    status: "REVIEW",
    total_amount: 3200,
    currency: "USD",
    deadline: new Date(Date.now() + 25 * 86400000).toISOString(),
    figma_url: "https://figma.com/file/fintech-wallet-v1",
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    buyer_confirmed_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    features: [
      { id: "f_fn_1", contract_id: "pct_open_fintech_02", title: "FaceID & Fingerprint Native Bridge", acceptance_test: "Biometric prompt triggers and resolves auth token with fallback PIN screen", price_weight: 40, allocated_amount: 1280, status: "PENDING", sort_order: 1 },
      { id: "f_fn_2", contract_id: "pct_open_fintech_02", title: "Live Currency WebSocket & Candle Chart", acceptance_test: "Displays streaming price chart with 60 FPS performance on lower-end devices", price_weight: 35, allocated_amount: 1120, status: "PENDING", sort_order: 2 },
      { id: "f_fn_3", contract_id: "pct_open_fintech_02", title: "Encrypted SQLite Local Vault", acceptance_test: "Stores user credentials and cached ledger using SQLCipher AES-256", price_weight: 25, allocated_amount: 800, status: "PENDING", sort_order: 3 },
    ],
  },
  {
    id: "pct_open_solana_03",
    title: "Solana Smart Contract Escrow & Phantom dApp",
    description: "Rust Anchor program implementing 2-of-2 multisig milestone release with web3 Phantom & Solflare browser wallet adapter.",
    buyer_id: "usr_hirer_david",
    buyer_name: "David Chen",
    buyer_email: "david@crypto-ventures.com",
    seller_id: "usr_seller_open",
    seller_name: "Unassigned Freelancer",
    seller_email: "open@pactpal.dev",
    status: "DRAFT",
    total_amount: 4500,
    currency: "USD",
    deadline: new Date(Date.now() + 30 * 86400000).toISOString(),
    figma_url: "https://figma.com/file/solana-escrow-dapp",
    created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    features: [
      { id: "f_sol_1", contract_id: "pct_open_solana_03", title: "Anchor Rust Smart Contract", acceptance_test: "Passes 100% of Anchor unit tests on localnet for init_vault, deposit, and disburse", price_weight: 50, allocated_amount: 2250, status: "PENDING", sort_order: 1 },
      { id: "f_sol_2", contract_id: "pct_open_solana_03", title: "Next.js Wallet Adapter & PDA Balances", acceptance_test: "Connects to Phantom/Solflare and queries vault PDA token balance in real-time", price_weight: 30, allocated_amount: 1350, status: "PENDING", sort_order: 2 },
      { id: "f_sol_3", contract_id: "pct_open_solana_03", title: "Automated Dispute Fallback Circuit Breaker", acceptance_test: "Triggers return of funds if referee key signs emergency refund instruction", price_weight: 20, allocated_amount: 900, status: "PENDING", sort_order: 3 },
    ],
  },
];

export default function FreelancerDashboardPage() {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [myContracts, setMyContracts] = useState<Contract[]>([]);
  const [availableProjects, setAvailableProjects] = useState<Contract[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  const fetchContracts = async () => {
    const user = getCurrentUser();
    setCurrentUser(user);

    try {
      const all = await backendClient.getContracts();

      // 1. My Contracts: Only contracts where the current user is the SELLER and contract has been funded (Active Contracts)
      const mine = all.filter((c) => {
        if (isUserBuyer(c, user)) return false;
        const isSeller = isUserSeller(c, user);
        const isFundedOrActive =
          c.status === "FUNDED" ||
          c.status === "IN_PROGRESS" ||
          c.status === "SUBMITTED" ||
          c.status === "VERIFYING" ||
          c.status === "DECISION" ||
          c.status === "SETTLED";
        return isSeller && isFundedOrActive;
      });

      // 2. Available Projects: Open projects posted by OTHER hirers, or pending approval/funding
      const available = all.filter((c) => {
        // Must NOT be posted by current user
        if (isUserBuyer(c, user)) return false;

        // If already funded & current user is seller, it belongs in myContracts, not available
        const isAlreadyFundedActive =
          isUserSeller(c, user) &&
          (c.status === "FUNDED" ||
            c.status === "IN_PROGRESS" ||
            c.status === "SUBMITTED" ||
            c.status === "VERIFYING" ||
            c.status === "DECISION" ||
            c.status === "SETTLED");

        if (isAlreadyFundedActive) return false;

        // Available if in DRAFT, REVIEW, or SIGNED (awaiting hirer escrow payment)
        return c.status === "DRAFT" || c.status === "REVIEW" || c.status === "SIGNED";
      });

      // Guarantee available open projects are always present for demo & review
      const existingIds = new Set(available.map((p) => p.id));
      for (const defProj of DEFAULT_AVAILABLE_PROJECTS) {
        if (!existingIds.has(defProj.id)) {
          available.push(defProj);
        }
      }

      setMyContracts(mine);
      setAvailableProjects(available);
    } catch (err) {
      console.error("Failed to load freelancer contracts from Supabase:", err);
      const all = mockApi.getContracts();
      setMyContracts(all.filter((c) => isUserSeller(c, user) && c.status !== "DRAFT"));
      setAvailableProjects(DEFAULT_AVAILABLE_PROJECTS);
    } finally {
      setIsLoaded(true);
    }
  };

  useEffect(() => {
    fetchContracts();

    const handleUpdate = () => fetchContracts();
    window.addEventListener("pactpal_contract_created", handleUpdate);
    window.addEventListener("pactpal_contract_updated", handleUpdate);
    window.addEventListener("pactpal_auth_change", handleUpdate);

    return () => {
      window.removeEventListener("pactpal_contract_created", handleUpdate);
      window.removeEventListener("pactpal_contract_updated", handleUpdate);
      window.removeEventListener("pactpal_auth_change", handleUpdate);
    };
  }, []);

  const totalEarned = myContracts
    .filter((c) => c.status === "SETTLED")
    .reduce((s, c) => s + c.total_amount, 0);

  const displayName = currentUser?.name || "Freelancer";
  const userPayPalEmail = currentUser?.paypal_email || "";

  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "100px 24px 80px" }}>
        {/* Page header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 40, flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 6 }}>
              Freelancer Dashboard
            </div>
            <h1 style={{ fontSize: "clamp(28px, 4vw, 48px)", fontWeight: 900, letterSpacing: "-0.025em", color: "white" }}>
              Welcome back, <span className="gradient-text-orange">{displayName}</span> 
            </h1>
            {userPayPalEmail && (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  marginTop: 10,
                  background: "rgba(255,152,0,0.12)",
                  border: "1px solid rgba(255,152,0,0.35)",
                  padding: "5px 14px",
                  borderRadius: 20,
                }}
              >
                <span style={{ fontSize: 14 }}>💳</span>
                <span style={{ fontSize: 13, color: "#FDBA74", fontFamily: "monospace" }}>
                  PayPal Payouts: {userPayPalEmail}
                </span>
                <span
                  style={{
                    fontSize: 10,
                    background: "#10B981",
                    color: "#000",
                    fontWeight: 800,
                    padding: "2px 6px",
                    borderRadius: 4,
                  }}
                >
                  VERIFIED
                </span>
              </div>
            )}
          </div>

          {/* Role switcher */}
          <div
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 50,
              padding: 4,
              display: "flex",
              gap: 4,
            }}
            role="group"
            aria-label="Switch between Hiring and Freelancing mode"
          >
            <Link
              href="/dashboard/hirer"
              style={{
                padding: "8px 20px",
                borderRadius: 50,
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text-muted)",
                textDecoration: "none",
                transition: "all 0.2s",
              }}
              aria-label="Switch to hiring mode"
            >
              Hiring
            </Link>
            <div
              style={{
                padding: "8px 20px",
                borderRadius: 50,
                background: "linear-gradient(135deg, #FF9800, #FF6B00)",
                fontSize: 13,
                fontWeight: 700,
                color: "white",
                boxShadow: "0 0 16px rgba(255,152,0,0.4)",
              }}
              aria-current="page"
            >
              Freelancing
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: 16,
            marginBottom: 36,
          }}
          role="list"
          aria-label="Earnings statistics"
        >
          {[
            { label: "Total earned", value: `$${totalEarned.toLocaleString()}`, color: "#FF9800", icon: "" },
            { label: "My active contracts", value: `${myContracts.length}`, color: "#0066FF", icon: "" },
            { label: "Open projects to apply", value: `${availableProjects.length}`, color: "#4CAF50", icon: "" },
            { label: "On-time delivery", value: "100%", color: "#7A5CFF", icon: "" },
          ].map((s) => (
            <div
              key={s.label}
              role="listitem"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.07)",
                borderRadius: 20,
                padding: "24px",
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 10 }} aria-hidden>{s.icon}</div>
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 900,
                  fontFamily: "JetBrains Mono, monospace",
                  color: s.color,
                  lineHeight: 1,
                  marginBottom: 6,
                }}
                aria-label={`${s.label}: ${s.value}`}
              >
                {s.value}
              </div>
              <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Main Sections Grid */}
        <div style={{ display: "flex", flexDirection: "column", gap: 40 }}>
          
          {/* SECTION 1: MY ACTIVE CONTRACTS */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div>
                <h2 style={{ fontSize: 22, fontWeight: 800, color: "white", display: "flex", alignItems: "center", gap: 10 }}>
                  <Briefcase size={20} color="#FF9800" /> My Contracts
                  <span
                    style={{
                      fontSize: 12,
                      background: "rgba(255,152,0,0.15)",
                      border: "1px solid rgba(255,152,0,0.3)",
                      color: "#FF9800",
                      padding: "2px 10px",
                      borderRadius: 20,
                      fontWeight: 700,
                    }}
                  >
                    {myContracts.length} Active
                  </span>
                </h2>
                <p style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 4 }}>
                  Contracts that you have accepted, dual-signed with the hirer, and are actively working on.
                </p>
              </div>
            </div>

            {myContracts.length === 0 ? (
              <div
                style={{
                  background: "rgba(255,255,255,0.02)",
                  border: "1px dashed rgba(255,255,255,0.12)",
                  borderRadius: 20,
                  padding: "44px 24px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: 36, marginBottom: 12 }}></div>
                <h3 style={{ fontSize: 18, fontWeight: 800, color: "white", marginBottom: 6 }}>
                  No active contracts yet
                </h3>
                <p style={{ color: "var(--color-text-secondary)", fontSize: 14, maxWidth: 480, margin: "0 auto 20px", lineHeight: 1.6 }}>
                  When you apply to an open project below and the hirer approves &amp; signs the contract with you, it will move into this section.
                </p>
                <a
                  href="#available-projects"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    background: "rgba(255,152,0,0.12)",
                    border: "1px solid rgba(255,152,0,0.3)",
                    color: "#FF9800",
                    borderRadius: 30,
                    padding: "10px 22px",
                    fontSize: 13,
                    fontWeight: 700,
                    textDecoration: "none",
                  }}
                >
                  Explore Available Projects Below ↓
                </a>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }} role="list" aria-label="Your active contracts">
                {myContracts.map((c) => {
                  const meta = statusColors[c.status] || { color: "#7C89A8", bg: "rgba(124,137,168,0.1)", label: c.status };
                  const passedCount = c.features?.filter((f) => f.status.toUpperCase() === "PASSED").length ?? 0;
                  const totalFeatures = c.features?.length || 1;
                  const progress = Math.round((passedCount / totalFeatures) * 100);

                  return (
                    <Link
                      key={c.id}
                      href={`/contracts/${c.id}`}
                      role="listitem"
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 14,
                        background: "rgba(255,255,255,0.03)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: 20,
                        padding: "22px 26px",
                        textDecoration: "none",
                        transition: "all 0.25s ease",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = "rgba(255,152,0,0.4)";
                        e.currentTarget.style.background = "rgba(255,152,0,0.04)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                        e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                        <div>
                          <div style={{ fontWeight: 800, fontSize: 16, color: "white" }}>{c.title}</div>
                          <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 3 }}>
                            Hirer: <strong style={{ color: "white" }}>{c.buyer_name || c.buyer_email}</strong> • Deadline: {new Date(c.deadline).toLocaleDateString()}
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                          <span
                            style={{
                              background: meta.bg,
                              color: meta.color,
                              border: `1px solid ${meta.color}44`,
                              borderRadius: 50,
                              padding: "4px 14px",
                              fontSize: 11,
                              fontWeight: 700,
                            }}
                          >
                            {meta.label}
                          </span>
                          <span style={{ fontSize: 18, fontWeight: 900, color: "#FF9800", fontFamily: "JetBrains Mono, monospace" }}>
                            ${c.total_amount.toLocaleString()}
                          </span>
                        </div>
                      </div>

                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--color-text-muted)", marginBottom: 6 }}>
                          <span>Milestone Verification ({passedCount}/{totalFeatures} passed)</span>
                          <span style={{ fontWeight: 700, color: "white" }}>{progress}%</span>
                        </div>
                        <div
                          style={{
                            height: 6,
                            background: "rgba(255,255,255,0.08)",
                            borderRadius: 3,
                            overflow: "hidden",
                          }}
                        >
                          <div
                            style={{
                              height: "100%",
                              width: `${progress}%`,
                              background: progress === 100
                                ? "linear-gradient(90deg, #4CAF50, #81C784)"
                                : "linear-gradient(90deg, #FF9800, #FFB74D)",
                              borderRadius: 3,
                            }}
                          />
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          {/* SECTION 2: AVAILABLE PROJECTS (POSTED BUT NOT TAKEN) */}
          <div id="available-projects">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
              <div>
                <h2 style={{ fontSize: 22, fontWeight: 800, color: "white", display: "flex", alignItems: "center", gap: 10 }}>
                  <Sparkles size={20} color="#60A5FA" /> Available Projects
                  <span
                    style={{
                      fontSize: 12,
                      background: "rgba(0,102,255,0.15)",
                      border: "1px solid rgba(0,102,255,0.3)",
                      color: "#60A5FA",
                      padding: "2px 10px",
                      borderRadius: 20,
                      fontWeight: 700,
                    }}
                  >
                    {availableProjects.length} Open for Application
                  </span>
                </h2>
                <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 4 }}>
                  Projects posted by hirers that are open for review and application. Click apply to negotiate &amp; dual-sign terms.
                </p>
              </div>

              <Link
                href="/work"
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#60A5FA",
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                Full job feed <ArrowRight size={14} />
              </Link>
            </div>

            {availableProjects.length === 0 ? (
              <div
                style={{
                  background: "rgba(255,255,255,0.02)",
                  border: "1px solid rgba(255,255,255,0.07)",
                  borderRadius: 20,
                  padding: "40px 24px",
                  textAlign: "center",
                }}
              >
                <p style={{ color: "var(--color-text-secondary)", fontSize: 14 }}>
                  No open projects currently available from other hirers. When a hirer posts a new project, it will appear right here!
                </p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {availableProjects.map((proj) => {
                  const isDualSignedAwaitingFund =
                    isUserSeller(proj, currentUser) &&
                    (proj.status === "SIGNED" || (Boolean(proj.seller_confirmed_at) && Boolean(proj.buyer_confirmed_at))) &&
                    proj.status !== "FUNDED";
                  const hasApplied =
                    isUserSeller(proj, currentUser) &&
                    Boolean(proj.seller_confirmed_at) &&
                    !proj.buyer_confirmed_at;

                  return (
                    <div
                      key={proj.id}
                      style={{
                        background: "rgba(255,255,255,0.03)",
                        border: isDualSignedAwaitingFund
                          ? "1px solid rgba(255,152,0,0.4)"
                          : hasApplied
                          ? "1px solid rgba(0,163,224,0.4)"
                          : "1px solid rgba(255,255,255,0.08)",
                        borderRadius: 20,
                        padding: "24px 28px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        flexWrap: "wrap",
                        gap: 20,
                        transition: "all 0.25s ease",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = isDualSignedAwaitingFund
                          ? "rgba(255,152,0,0.6)"
                          : hasApplied
                          ? "rgba(0,163,224,0.6)"
                          : "rgba(96,165,250,0.4)";
                        e.currentTarget.style.background = "rgba(255,255,255,0.04)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = isDualSignedAwaitingFund
                          ? "rgba(255,152,0,0.4)"
                          : hasApplied
                          ? "rgba(0,163,224,0.4)"
                          : "rgba(255,255,255,0.08)";
                        e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 280 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8, flexWrap: "wrap" }}>
                          <span style={{ fontWeight: 800, fontSize: 17, color: "white" }}>
                            {proj.title}
                          </span>
                          {isDualSignedAwaitingFund ? (
                            <span
                              style={{
                                background: "rgba(255,152,0,0.15)",
                                border: "1px solid rgba(255,152,0,0.4)",
                                color: "#FFB74D",
                                padding: "2px 10px",
                                borderRadius: 20,
                                fontSize: 11,
                                fontWeight: 700,
                              }}
                            >
                              ⏳ Dual-Signed · Awaiting Hirer PayPal Escrow Deposit
                            </span>
                          ) : hasApplied ? (
                            <span
                              style={{
                                background: "rgba(0,163,224,0.15)",
                                border: "1px solid rgba(0,163,224,0.4)",
                                color: "#38BDF8",
                                padding: "2px 10px",
                                borderRadius: 20,
                                fontSize: 11,
                                fontWeight: 700,
                              }}
                            >
                               Applied · Awaiting Hirer Approval
                            </span>
                          ) : (
                            <span
                              style={{
                                background: "rgba(76,175,80,0.12)",
                                border: "1px solid rgba(76,175,80,0.3)",
                                color: "#81C784",
                                padding: "2px 10px",
                                borderRadius: 20,
                                fontSize: 11,
                                fontWeight: 700,
                              }}
                            >
                              Open for Application
                            </span>
                          )}
                        </div>

                        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12, lineHeight: 1.5, maxWidth: 640 }}>
                          {proj.description || "Project specifications with weighted milestone acceptance criteria."}
                        </p>

                        <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap", fontSize: 12, color: "var(--color-text-muted)" }}>
                          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                            <User size={13} color="#60A5FA" /> Hirer: <strong style={{ color: "white" }}>{proj.buyer_name || proj.buyer_email}</strong>
                          </span>
                          <span>•</span>
                          <span>
                            Milestones: <strong style={{ color: "white" }}>{proj.features?.length || 0} features</strong>
                          </span>
                          <span>•</span>
                          <span>
                            Deadline: <strong style={{ color: "white" }}>{new Date(proj.deadline).toLocaleDateString()}</strong>
                          </span>
                        </div>
                      </div>

                      {/* Right budget & action */}
                      <div style={{ display: "flex", alignItems: "center", gap: 20, flexShrink: 0 }}>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em" }}>
                            ESCROW BUDGET
                          </div>
                          <div style={{ fontSize: 24, fontWeight: 900, color: "#FF9800", fontFamily: "JetBrains Mono, monospace" }}>
                            ${proj.total_amount.toLocaleString()}
                          </div>
                        </div>

                        <Link
                          href={`/contracts/${proj.id}/review`}
                          style={{
                            background: isDualSignedAwaitingFund
                              ? "rgba(255,152,0,0.15)"
                              : hasApplied
                              ? "rgba(0,163,224,0.15)"
                              : "linear-gradient(135deg, #FF9800, #FF6B00)",
                            border: (isDualSignedAwaitingFund || hasApplied) ? "1px solid rgba(255,152,0,0.4)" : "none",
                            color: "white",
                            borderRadius: 12,
                            padding: "12px 22px",
                            fontSize: 14,
                            fontWeight: 700,
                            textDecoration: "none",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 8,
                            boxShadow: (isDualSignedAwaitingFund || hasApplied) ? "none" : "0 4px 16px rgba(255,152,0,0.35)",
                            transition: "all 0.2s",
                          }}
                        >
                          {isDualSignedAwaitingFund ? (
                            <>
                              View Signed Terms <ArrowRight size={15} />
                            </>
                          ) : hasApplied ? (
                            <>
                              View Negotiation <ArrowRight size={15} />
                            </>
                          ) : (
                            <>
                              Apply &amp; Review Terms <ArrowRight size={15} />
                            </>
                          )}
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>
      </div>
    </main>
  );
}
