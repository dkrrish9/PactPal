"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import Navbar from "@/components/Navbar";
import { 
  ArrowLeft, 
  AlertTriangle, 
  ShieldAlert, 
  Lock,
  Send, 
  CheckCircle2, 
  XCircle,
  MessageSquare,
  FileCode,
  Scale,
  Clock,
  ExternalLink,
  FileText,
  User,
  Bot,
  Layers,
  ChevronRight,
  ShieldCheck,
  Check
} from "lucide-react";
import { mockApi, Contract, Feature, ChatMessage, ProofOfWorkReceipt } from "@/lib/mockApi";
import { backendClient } from "@/lib/backendClient";
import { getCurrentUser, UserProfile } from "@/lib/supabase";

function isUserHirer(c: Contract | null, user: UserProfile | null): boolean {
  if (!c || !user) return false;
  const userEmail = (user.email || "").trim().toLowerCase();
  const userName = (user.name || "").trim().toLowerCase();
  const userId = user.id || "";

  // If user is explicitly the seller/freelancer, they cannot be the hirer
  const sellerEmail = (c.seller_email || "").trim().toLowerCase();
  const sellerName = (c.seller_name || "").trim().toLowerCase();
  const sellerId = c.seller_id || "";
  if (userId && sellerId && userId === sellerId) return false;
  if (userEmail && sellerEmail && userEmail === sellerEmail) return false;
  if (userName && sellerName && userName === sellerName) return false;

  const buyerEmail = (c.buyer_email || "").trim().toLowerCase();
  const buyerName = (c.buyer_name || "").trim().toLowerCase();
  const buyerId = c.buyer_id || "";

  if (userId && buyerId && userId === buyerId) return true;
  if (userEmail && buyerEmail && userEmail === buyerEmail) return true;
  if (userName && buyerName && (userName === buyerName || userName.includes(buyerName) || buyerName.includes(userName))) return true;
  return false;
}

export default function DisputePage() {
  const params = useParams();
  const rawId = (params?.id as string) || "pct_099e77";

  const [contract, setContract] = useState<Contract | null>(null);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [receipt, setReceipt] = useState<ProofOfWorkReceipt | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [selectedResolution, setSelectedResolution] = useState<string>("partial");
  const [evidenceSubmitted, setEvidenceSubmitted] = useState(false);
  const [resolutionConfirmed, setResolutionConfirmed] = useState(false);

  useEffect(() => {
    setCurrentUser(getCurrentUser());
    async function loadDisputeData() {
      try {
        const live = await backendClient.getContract(rawId);
        if (live) setContract(live as unknown as Contract);
        const liveMsgs = await backendClient.getMessages(rawId);
        if (liveMsgs && liveMsgs.length > 0) setMessages(liveMsgs);
        else setMessages(mockApi.getMessages(rawId));
        setReceipt(mockApi.getReceipt(rawId));
        return;
      } catch {}

      const c = mockApi.getContract(rawId) || mockApi.getContracts()[0];
      setContract(c);
      setReceipt(mockApi.getReceipt(c?.id || rawId));
      setMessages(mockApi.getMessages(c?.id || rawId));
    }
    loadDisputeData();
  }, [rawId]);

  if (!contract) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--color-bg)", color: "white", padding: 60, textAlign: "center" }}>
        Loading Dispute Arbitration Case...
      </div>
    );
  }

  const features: Feature[] = contract.features && contract.features.length > 0 ? contract.features : [
    { id: "feat_01", contract_id: contract.id, title: "Landing Page & Responsive Navigation", acceptance_test: "All 12 sections render, mobile drawer opens", price_weight: 25, allocated_amount: 375, status: "PASSED", sort_order: 1 },
    { id: "feat_02", contract_id: contract.id, title: "Login & Session Management", acceptance_test: "Login/logout with JWT, session persists across refresh", price_weight: 20, allocated_amount: 300, status: "FAILED", sort_order: 2 },
    { id: "feat_03", contract_id: contract.id, title: "Interactive Dashboard & Bryntum Gantt", acceptance_test: "Gantt timeline renders with status colors and today line", price_weight: 30, allocated_amount: 450, status: "PASSED", sort_order: 3 },
    { id: "feat_04", contract_id: contract.id, title: "PayPal Escrow Webhook Listeners", acceptance_test: "Order authorization and capture webhook listeners respond with 200", price_weight: 25, allocated_amount: 375, status: "PASSED", sort_order: 4 },
  ];

  const totalHeld = contract.total_amount || 1500;
  const passedFeatures = features.filter((f) => f.status === "PASSED");
  const passedAmount = passedFeatures.length > 0
    ? passedFeatures.reduce((sum, f) => sum + (f.allocated_amount || (totalHeld * f.price_weight) / 100), 0)
    : Math.round(totalHeld * 0.75);
  const refundAmount = Math.max(0, totalHeld - passedAmount);

  const isViewerHirer = isUserHirer(contract, currentUser);
  const mySenderRole: "BUYER" | "SELLER" = isViewerHirer ? "BUYER" : "SELLER";
  const mySenderName = isViewerHirer
    ? (currentUser?.name || contract.buyer_name || "Hirer")
    : (currentUser?.name || contract.seller_name || "Freelancer");

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const content = `[DISPUTE MEDIATION] ${chatInput.trim()}`;
    setChatInput("");

    const newMsg = await backendClient.sendMessage(contract.id, {
      sender_type: mySenderRole,
      sender_name: mySenderName,
      content,
      metadata: { action: "DISPUTE_RAISED" },
      sender_id: currentUser?.id,
    });

    setMessages((prev) => [...prev, newMsg]);
  };

  const handleConfirmResolution = async () => {
    setResolutionConfirmed(true);
    const newMsg = await backendClient.sendMessage(contract.id, {
      sender_type: "AI_REFEREE",
      sender_name: "AI Referee",
      content: `Arbitration Decision Formally Accepted: Selected resolution pathway '${selectedResolution.toUpperCase()}'. Funds release initiated.`,
      metadata: { action: "VERDICT_SUMMARY", proposed_amount: passedAmount },
    });
    setMessages((prev) => [...prev, newMsg]);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        color: "white",
        fontFamily: "Inter, sans-serif",
      }}
    >
      <Navbar />

      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "100px 24px 80px" }}>
        {/* Navigation Breadcrumb */}
        <Link
          href={`/contracts/${contract.id}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            color: "var(--color-text-secondary)",
            textDecoration: "none",
            fontSize: 14,
            marginBottom: 24,
            transition: "color 0.15s ease",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "white")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "var(--color-text-secondary)")}
        >
          <ArrowLeft size={16} /> Back to Contract Overview ({contract.id})
        </Link>

        {/* Requirement 1: Funds Stay Held Banner */}
        <div
          style={{
            padding: "20px 24px",
            borderRadius: 18,
            background: "linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(245,158,11,0.1) 100%)",
            border: "1px solid rgba(239,68,68,0.4)",
            marginBottom: 28,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 16,
            boxShadow: "0 0 40px rgba(239,68,68,0.08)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                background: "rgba(239,68,68,0.2)",
                border: "1px solid rgba(239,68,68,0.4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Lock size={22} color="#F87171" />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: "0.08em", color: "#F87171", textTransform: "uppercase" }}>
                  FUNDS STAY HELD · ARBITRATION LOCK ACTIVE
                </span>
                <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                  Case ID: DSP-89021
                </span>
              </div>
              <strong style={{ fontSize: 16, color: "white" }}>
                ${totalHeld.toLocaleString()}.00 USD Remains Strictly Held in PayPal Escrow Authorization
              </strong>
              <p style={{ margin: "2px 0 0", fontSize: 12.5, color: "var(--color-text-secondary)" }}>
                Zero-trust rule: Funds will not be disbursed or refunded until mediation is confirmed or 48-hr cure concludes.
              </p>
            </div>
          </div>

          <div
            style={{
              padding: "8px 16px",
              borderRadius: 10,
              background: "rgba(0,0,0,0.4)",
              border: "1px solid rgba(255,255,255,0.1)",
              textAlign: "right",
            }}
          >
            <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>Authorization ID</div>
            <div style={{ fontSize: 13, fontFamily: "JetBrains Mono, monospace", color: "#FBBF24", fontWeight: 700 }}>
              {contract.paypal_auth_id || "8BA1234567890123"}
            </div>
          </div>
        </div>

        {/* Dispute Details & Header */}
        <div
          style={{
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 20,
            padding: "26px",
            marginBottom: 28,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <AlertTriangle size={20} color="#F59E0B" />
            <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>
              Dispute Mediation: Automated AST Cheat Detected
            </h1>
          </div>
          <p style={{ color: "var(--color-text-secondary)", fontSize: 14, margin: "6px 0 0", lineHeight: 1.6 }}>
            The AI Referee flagged Feature 2 (&ldquo;Login & Session Management&rdquo;). AST scanning discovered hardcoded mock JWT token responses bypassing backend database credential validation. 3 of 4 features passed verified container tests.
          </p>
        </div>

        {/* Four Core Requirements Grid (Checklist, Report, Receipt, Chat) */}
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 24, marginBottom: 32 }}>
          {/* Left Column: Checklist & Verification Report & Receipt */}
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            
            {/* 1. CHECKLIST */}
            <div
              style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 20,
                padding: "24px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Layers size={18} color="#60A5FA" />
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>
                    1. Milestone Feature Checklist
                  </h3>
                </div>
                <span style={{ fontSize: 12, color: "#34D399", fontWeight: 700 }}>
                  3 of 4 Features Passed (75%)
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {features.map((f, i) => (
                  <div
                    key={f.id || i}
                    style={{
                      padding: "12px 14px",
                      borderRadius: 12,
                      background: f.status === "PASSED" ? "rgba(16,185,129,0.06)" : "rgba(239,68,68,0.08)",
                      border: `1px solid ${f.status === "PASSED" ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.3)"}`,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12,
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        {f.status === "PASSED" ? (
                          <CheckCircle2 size={14} color="#34D399" />
                        ) : (
                          <XCircle size={14} color="#F87171" />
                        )}
                        <span style={{ fontSize: 13, fontWeight: 600, color: "white" }}>{f.title}</span>
                      </div>
                      <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 2 }}>
                        {f.acceptance_test}
                      </div>
                    </div>
                    <div style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: f.status === "PASSED" ? "#34D399" : "#F87171" }}>
                        {f.status === "PASSED" ? `+$${f.allocated_amount}` : "$0 (Disputed)"}
                      </span>
                      <div style={{ fontSize: 10, color: "var(--color-text-muted)" }}>{f.price_weight}% weight</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 2. REPORT */}
            <div
              style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 20,
                padding: "24px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <FileCode size={18} color="#C084FC" />
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>
                    2. Referee Verification Report Findings
                  </h3>
                </div>
                <Link
                  href={`/contracts/${contract.id}/verification`}
                  style={{ fontSize: 12, color: "#60A5FA", textDecoration: "none", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 4 }}
                >
                  Full Report <ExternalLink size={12} />
                </Link>
              </div>

              {/* Code Snippet AST Scan finding */}
              <div
                style={{
                  background: "rgba(0,0,0,0.5)",
                  borderRadius: 12,
                  padding: "14px",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 12,
                  border: "1px solid rgba(239,68,68,0.25)",
                  color: "#FCA5A5",
                  lineHeight: 1.6,
                  marginBottom: 12,
                }}
              >
                <div style={{ color: "var(--color-text-muted)", marginBottom: 4 }}>// AST Rule: NO_HARDCODED_AUTH_RESPONSES (Line 42)</div>
                <div style={{ color: "#EF4444", textDecoration: "line-through" }}>
                  - const user = await db.users.verifyCredentials(email, passwordHash);
                </div>
                <div style={{ color: "#F59E0B" }}>
                  + return &#123; status: 200, token: &quot;mock_jwt_bypass&quot; &#125;; // [HIGH SEVERITY FLAG]
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 12 }}>
                <div style={{ background: "rgba(255,255,255,0.03)", padding: "10px", borderRadius: 8 }}>
                  <span style={{ color: "var(--color-text-muted)" }}>Unit Test Assertions:</span>
                  <div style={{ color: "white", fontWeight: 700, marginTop: 2 }}>35 of 42 Passed (88.5% Cov)</div>
                </div>
                <div style={{ background: "rgba(255,255,255,0.03)", padding: "10px", borderRadius: 8 }}>
                  <span style={{ color: "var(--color-text-muted)" }}>Figma Visual Match:</span>
                  <div style={{ color: "white", fontWeight: 700, marginTop: 2 }}>89.2% (Threshold: 90.0%)</div>
                </div>
              </div>
            </div>

            {/* 3. RECEIPT (Provisional / Dispute Settlement Card) */}
            <div
              style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 20,
                padding: "24px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <FileText size={18} color="#34D399" />
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>
                    3. Provisional Settlement Receipt
                  </h3>
                </div>
                <Link
                  href={`/contracts/${contract.id}/receipt`}
                  style={{ fontSize: 12, color: "#34D399", textDecoration: "none", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 4 }}
                >
                  Receipt View <ExternalLink size={12} />
                </Link>
              </div>

              <div
                style={{
                  background: "rgba(0,0,0,0.35)",
                  border: "1px solid rgba(122,92,255,0.25)",
                  borderRadius: 12,
                  padding: "14px",
                  fontSize: 12,
                }}
              >
                <div style={{ fontSize: 11, color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: 700, marginBottom: 4 }}>
                  Provisional SHA-256 Digest:
                </div>
                <div style={{ fontFamily: "JetBrains Mono, monospace", color: "#C084FC", wordBreak: "break-all" }}>
                  {receipt?.receipt_hash || "0xa9f3e8c2d4b16f7a3e2d1c9b8a7f6e5d4c3b2a190887766554433221100aabb"}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, paddingTop: 10, borderTop: "1px solid rgba(255,255,255,0.06)", fontSize: 12 }}>
                  <span style={{ color: "#34D399" }}>Proposed Payout: ${passedAmount}.00</span>
                  <span style={{ color: "#F87171" }}>Proposed Refund: ${refundAmount}.00</span>
                </div>
              </div>
            </div>

            {/* Resolution Choice Selector */}
            <div
              style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 20,
                padding: "24px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                <Scale size={18} color="#FBBF24" />
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>
                  Referee Resolution Choice
                </h3>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  {
                    id: "partial",
                    title: "Accept 75% Partial Release Now",
                    desc: `Disburse $${passedAmount}.00 USD to freelancer for 3 passed milestones, and refund $${refundAmount}.00 USD to hirer.`,
                    recommended: true,
                  },
                  {
                    id: "cure",
                    title: "Grant 48-Hour Cure Window",
                    desc: "Allow freelancer 48 hours to fix JWT credential logic and resubmit without penalties.",
                    recommended: false,
                  },
                  {
                    id: "escalate",
                    title: "Escalate to Human Developer Arbiters",
                    desc: "Request formal human arbitration panel review ($75 deposit).",
                    recommended: false,
                  },
                ].map((opt) => (
                  <div
                    key={opt.id}
                    onClick={() => setSelectedResolution(opt.id)}
                    style={{
                      padding: "14px 16px",
                      borderRadius: 12,
                      background: selectedResolution === opt.id ? "rgba(0,102,255,0.12)" : "rgba(255,255,255,0.03)",
                      border: selectedResolution === opt.id ? "1px solid #0066FF" : "1px solid rgba(255,255,255,0.06)",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <span style={{ fontWeight: 700, fontSize: 13, color: "white" }}>{opt.title}</span>
                      {opt.recommended && (
                        <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 6px", borderRadius: 4, background: "rgba(16,185,129,0.2)", color: "#34D399" }}>
                          RECOMMENDED
                        </span>
                      )}
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-secondary)" }}>{opt.desc}</p>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 16 }}>
                {resolutionConfirmed ? (
                  <div style={{ padding: "12px", borderRadius: 10, background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)", color: "#86EFAC", textAlign: "center", fontSize: 13, fontWeight: 700 }}>
                    ✓ Resolution Confirmed: {selectedResolution.toUpperCase()}. Funds release processing.
                  </div>
                ) : (
                  <button
                    onClick={handleConfirmResolution}
                    style={{
                      width: "100%",
                      padding: "12px",
                      borderRadius: 10,
                      background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                      border: "none",
                      color: "white",
                      fontSize: 14,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Execute Resolution ({selectedResolution.toUpperCase()}) →
                  </button>
                )}
              </div>
            </div>

          </div>

          {/* Right Column: 4. ARBITRATION CHAT */}
          <div
            style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 20,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              maxHeight: 740,
            }}
          >
            {/* Chat Header */}
            <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.015)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <MessageSquare size={16} color="#60A5FA" />
                <h3 style={{ fontSize: 15, fontWeight: 700, color: "white", margin: 0 }}>
                  4. Dispute Negotiation Chat
                </h3>
              </div>
              <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: "4px 0 0" }}>
                Multi-party arbitration thread (Hirer, Freelancer, AI Referee)
              </p>
            </div>

            {/* Chat Messages Stream */}
            <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 12 }}>
              {messages.map((m) => {
                const isAi = m.sender_type === "AI_REFEREE";
                const isBuyer = m.sender_type === "BUYER";
                return (
                  <div
                    key={m.id}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: isBuyer ? "flex-end" : "flex-start",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3, fontSize: 11 }}>
                      <span style={{ fontWeight: 700, color: isAi ? "#C084FC" : isBuyer ? "#60A5FA" : "#34D399" }}>
                        {m.sender_name}
                      </span>
                      <span style={{ color: "var(--color-text-muted)" }}>
                        {new Date(m.sent_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                    <div
                      style={{
                        padding: "10px 14px",
                        borderRadius: 12,
                        background: isAi ? "rgba(122,92,255,0.12)" : isBuyer ? "rgba(0,102,255,0.14)" : "rgba(255,255,255,0.05)",
                        border: `1px solid ${isAi ? "rgba(122,92,255,0.3)" : isBuyer ? "rgba(0,102,255,0.25)" : "rgba(255,255,255,0.08)"}`,
                        fontSize: 12.5,
                        color: "white",
                        maxWidth: "88%",
                        lineHeight: 1.5,
                      }}
                    >
                      {m.content}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Chat Input & Sender Indicator */}
            <div style={{ padding: "14px 16px", borderTop: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.015)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>Sending as:</span>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "3px 12px",
                    borderRadius: 20,
                    fontSize: 11,
                    fontWeight: 700,
                    background: isViewerHirer ? "rgba(0,102,255,0.15)" : "rgba(16,185,129,0.15)",
                    color: isViewerHirer ? "#60A5FA" : "#34D399",
                    border: `1px solid ${isViewerHirer ? "rgba(0,102,255,0.3)" : "rgba(16,185,129,0.3)"}`,
                  }}
                >
                  {isViewerHirer ? "" : ""} {mySenderName} ({isViewerHirer ? "Hirer" : "Freelancer"})
                </span>
              </div>

              <form onSubmit={handleSendMessage} style={{ display: "flex", gap: 8 }}>
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Post dispute evidence note..."
                  style={{
                    flex: 1,
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 10,
                    color: "white",
                    fontSize: 13,
                    padding: "8px 12px",
                    outline: "none",
                  }}
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim()}
                  style={{
                    background: chatInput.trim() ? "#0066FF" : "rgba(255,255,255,0.06)",
                    border: "none",
                    borderRadius: 10,
                    color: "white",
                    padding: "8px 14px",
                    cursor: chatInput.trim() ? "pointer" : "not-allowed",
                  }}
                >
                  <Send size={14} />
                </button>
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
