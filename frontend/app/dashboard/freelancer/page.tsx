"use client";
import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import Link from "next/link";
import { ArrowRight, TrendingUp, Clock, CheckCircle, Circle } from "lucide-react";
import { mockApi, Contract, ContractStatus, CONTRACT_STATES_META } from "@/lib/mockApi";
import { getCurrentUser, UserProfile } from "@/lib/supabase";

const earnings = [
  { month: "Sep", amount: 1200 },
  { month: "Oct", amount: 1800 },
  { month: "Nov", amount: 2400 },
];
const maxEarning = Math.max(...earnings.map((e) => e.amount));

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

export default function FreelancerDashboardPage() {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);

  useEffect(() => {
    const user = getCurrentUser();
    setCurrentUser(user);
    const all = mockApi.getContracts();
    if (user && !user.is_demo && user.id !== "usr_seller_01" && !user.email.includes("alex")) {
      const visibleContracts = all.filter((c) => {
        const isFreelancer =
          c.seller_id === user.id ||
          c.seller_email?.toLowerCase() === user.email.toLowerCase() ||
          c.seller_name?.toLowerCase() === user.name?.toLowerCase();
        const isOwnPosted =
          c.buyer_id === user.id ||
          c.buyer_email?.toLowerCase() === user.email.toLowerCase();
        return isFreelancer || !isOwnPosted;
      });
      setContracts(visibleContracts);
    } else {
      setContracts(all);
    }
  }, []);

  const totalEarned = contracts
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
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 6 }}>Freelancer Dashboard</div>
            <h1 style={{ fontSize: "clamp(28px, 4vw, 48px)", fontWeight: 900, letterSpacing: "-0.025em", color: "white" }}>
              Welcome back, <span className="gradient-text-orange">{displayName}</span> 👋
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
              href="/hire"
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
            marginBottom: 32,
          }}
          role="list"
          aria-label="Earnings statistics"
        >
          {[
            { label: "Total earned", value: `$${totalEarned.toLocaleString()}`, color: "#FF9800", icon: "💰" },
            { label: "Active contracts", value: "2", color: "#0066FF", icon: "📋" },
            { label: "Avg. verified score", value: "94%", color: "#4CAF50", icon: "✅" },
            { label: "On-time delivery", value: "100%", color: "#7A5CFF", icon: "⚡" },
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

        {/* Main grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 24 }}>
          {/* My contracts */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ fontSize: 20, fontWeight: 800, color: "white" }}>My contracts</h2>
              <Link href="/work" style={{ fontSize: 14, color: "#FF9800", textDecoration: "none", fontWeight: 600 }}>
                Browse jobs →
              </Link>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }} role="list" aria-label="Your contracts">
              {contracts.map((c) => {
                const meta = statusColors[c.status] || { color: "#7C89A8", bg: "rgba(124,137,168,0.1)", label: c.status };
                const passedCount = c.features?.filter((f) => f.status.toUpperCase() === "PASSED").length ?? 0;
                const totalFeatures = c.features?.length || 1;
                const progress = Math.round((passedCount / totalFeatures) * 100);

                return (
                  <Link
                    key={c.id}
                    href={c.status === "REVIEW" ? `/contracts/${c.id}/review` : `/contracts/${c.id}`}
                    role="listitem"
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: 12,
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.07)",
                      borderRadius: 20,
                      padding: "20px 24px",
                      textDecoration: "none",
                      transition: "all 0.25s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = "rgba(255,152,0,0.3)";
                      e.currentTarget.style.background = "rgba(255,152,0,0.04)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)";
                      e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                    }}
                    aria-label={`Contract: ${c.title}, status ${meta.label}`}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 15, color: "white" }}>{c.title}</div>
                        <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 2 }}>
                          Buyer: {c.buyer_name || c.buyer_email}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                        <span
                          style={{
                            background: meta.bg,
                            color: meta.color,
                            border: `1px solid ${meta.color}44`,
                            borderRadius: 50,
                            padding: "3px 12px",
                            fontSize: 11,
                            fontWeight: 700,
                          }}
                        >
                          {meta.label}
                        </span>
                        <span style={{ fontSize: 16, fontWeight: 800, color: "#FF9800", fontFamily: "JetBrains Mono, monospace" }}>
                          ${c.total_amount.toLocaleString()}
                        </span>
                      </div>
                    </div>
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--color-text-muted)", marginBottom: 6 }}>
                        <span>Verification Progress ({passedCount}/{totalFeatures} passed)</span>
                        <span>{progress}%</span>
                      </div>
                      <div
                        style={{
                          height: 6,
                          background: "rgba(255,255,255,0.08)",
                          borderRadius: 3,
                          overflow: "hidden",
                        }}
                        role="progressbar"
                        aria-valuenow={progress}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={`Progress: ${progress}%`}
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
          </div>

          {/* Earnings chart sidebar */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.07)",
                borderRadius: 20,
                padding: "24px",
              }}
              role="region"
              aria-label="Monthly earnings chart"
            >
              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em", marginBottom: 16, textTransform: "uppercase" }}>
                Monthly earnings
              </div>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 10, height: 120 }}>
                {earnings.map((e) => (
                  <div key={e.month} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#FF9800", fontFamily: "JetBrains Mono, monospace" }}>
                      ${e.amount / 1000}k
                    </div>
                    <div
                      style={{
                        width: "100%",
                        height: `${(e.amount / maxEarning) * 90}px`,
                        background: "linear-gradient(to top, #FF9800, #FFB74D)",
                        borderRadius: "6px 6px 0 0",
                        boxShadow: "0 0 12px rgba(255,152,0,0.3)",
                      }}
                      role="presentation"
                      aria-label={`${e.month}: $${e.amount}`}
                    />
                    <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{e.month}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Next payout */}
            <div
              style={{
                background: "rgba(255,152,0,0.06)",
                border: "1px solid rgba(255,152,0,0.2)",
                borderRadius: 20,
                padding: "24px",
              }}
              role="region"
              aria-label="Next payout information"
            >
              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em", marginBottom: 12, textTransform: "uppercase" }}>
                Next payout
              </div>
              <div style={{ fontSize: 32, fontWeight: 900, color: "#FF9800", fontFamily: "JetBrains Mono, monospace", lineHeight: 1, marginBottom: 6 }}>
                $1,200
              </div>
              <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 16 }}>
                3 of 4 features verified on E-commerce v2
              </div>
              <button
                style={{
                  width: "100%",
                  background: "linear-gradient(135deg, #FF9800, #FF6B00)",
                  border: "none",
                  borderRadius: 12,
                  color: "white",
                  padding: "12px",
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: "pointer",
                  boxShadow: "0 0 20px rgba(255,152,0,0.3)",
                }}
                aria-label="Withdraw earnings"
              >
                Withdraw earnings →
              </button>
            </div>
          </div>
        </div>

        <style>{`
          @media (max-width: 900px) {
            [style*="grid-template-columns: 1fr 320px"] {
              grid-template-columns: 1fr !important;
            }
          }
        `}</style>
      </div>
    </main>
  );
}

