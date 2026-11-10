"use client";
import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import Link from "next/link";
import { Plus, Shield, Clock, CheckCircle, AlertCircle, Circle } from "lucide-react";
import { mockApi, Contract, ContractStatus, CONTRACT_STATES_META } from "@/lib/mockApi";

const statusMeta: Record<string, { color: string; bg: string; label: string; icon: React.ReactNode }> = {
  DRAFT:       { color: "#7C89A8", bg: "rgba(124,137,168,0.1)", label: "Draft", icon: <Circle size={12} /> },
  REVIEW:      { color: "#00A3E0", bg: "rgba(0,163,224,0.1)", label: "In Review", icon: <Clock size={12} /> },
  SIGNED:      { color: "#7A5CFF", bg: "rgba(122,92,255,0.1)", label: "Signed", icon: <Circle size={12} /> },
  FUNDED:      { color: "#FF9800", bg: "rgba(255,152,0,0.1)", label: "Funded", icon: <Shield size={12} /> },
  IN_PROGRESS: { color: "#0066FF", bg: "rgba(0,102,255,0.1)", label: "In Progress", icon: <Clock size={12} /> },
  SUBMITTED:   { color: "#00A3E0", bg: "rgba(0,163,224,0.1)", label: "Submitted", icon: <Clock size={12} /> },
  VERIFYING:   { color: "#7A5CFF", bg: "rgba(122,92,255,0.1)", label: "Verifying", icon: <Clock size={12} /> },
  DECISION:    { color: "#FF9800", bg: "rgba(255,152,0,0.1)", label: "Decision", icon: <Clock size={12} /> },
  SETTLED:     { color: "#4CAF50", bg: "rgba(76,175,80,0.1)", label: "Settled", icon: <CheckCircle size={12} /> },
  DISPUTE:     { color: "#F44336", bg: "rgba(244,67,54,0.1)", label: "Dispute", icon: <AlertCircle size={12} /> },
};

export default function HirerDashboardPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [filter, setFilter] = useState("ALL");

  useEffect(() => {
    setContracts(mockApi.getContracts());
  }, []);

  const totalHeld = contracts
    .filter((c) => c.status === "FUNDED" || c.status === "IN_PROGRESS" || c.status === "VERIFYING" || c.status === "DECISION")
    .reduce((s, c) => s + c.total_amount, 0);

  const activeCount = contracts.filter((c) => c.status !== "SETTLED" && c.status !== "DRAFT").length;
  const settledCount = contracts.filter((c) => c.status === "SETTLED").length;

  const filteredContracts = contracts.filter((c) => {
    if (filter === "ACTIVE") return c.status !== "SETTLED";
    if (filter === "SETTLED") return c.status === "SETTLED";
    if (filter === "HELD") return c.status === "FUNDED" || c.status === "IN_PROGRESS";
    return true;
  });

  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "100px 24px 80px" }}>
        {/* Page header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 40, flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 6 }}>Hirer Dashboard</div>
            <h1 style={{ fontSize: "clamp(28px, 4vw, 48px)", fontWeight: 900, letterSpacing: "-0.025em", color: "white" }}>
              Welcome back, <span className="gradient-text">Priya</span> 👋
            </h1>
          </div>

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
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
              <div
                style={{
                  padding: "8px 20px",
                  borderRadius: 50,
                  background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                  fontSize: 13,
                  fontWeight: 700,
                  color: "white",
                  boxShadow: "0 0 16px rgba(0,102,255,0.4)",
                }}
                aria-current="page"
              >
                Hiring
              </div>
              <Link
                href="/dashboard/freelancer"
                style={{
                  padding: "8px 20px",
                  borderRadius: 50,
                  fontSize: 13,
                  fontWeight: 600,
                  color: "var(--color-text-muted)",
                  textDecoration: "none",
                }}
                aria-label="Switch to freelancing mode"
              >
                Freelancing
              </Link>
            </div>

            <Link
              href="/hire/create"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                color: "white",
                borderRadius: 50,
                padding: "12px 24px",
                fontSize: 14,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 0 20px rgba(0,102,255,0.4)",
              }}
              aria-label="Post a new project"
            >
              <Plus size={16} aria-hidden /> Post a Project
            </Link>
          </div>
        </div>

        {/* Stats */}
        <div
          style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 32 }}
          role="list"
          aria-label="Dashboard statistics"
        >
          {[
            { label: "In escrow now", value: `$${totalHeld.toLocaleString()}`, color: "#FF9800", icon: "🔒" },
            { label: "Active contracts", value: activeCount.toString(), color: "#0066FF", icon: "📋" },
            { label: "Completed / Settled", value: settledCount.toString(), color: "#4CAF50", icon: "✅" },
            { label: "Total registered", value: contracts.length.toString(), color: "#7A5CFF", icon: "💼" },
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

        {/* Contracts table */}
        <div
          style={{
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.07)",
            borderRadius: 24,
            overflow: "hidden",
          }}
          role="region"
          aria-label="Your contracts"
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "20px 24px",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
            }}
          >
            <div style={{ fontWeight: 700, fontSize: 15, color: "white" }}>All contracts</div>
            <div style={{ display: "flex", gap: 8 }}>
              {["ALL", "ACTIVE", "HELD", "SETTLED"].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  style={{
                    background: filter === f ? "rgba(0,102,255,0.15)" : "rgba(255,255,255,0.05)",
                    border: `1px solid ${filter === f ? "rgba(0,102,255,0.4)" : "rgba(255,255,255,0.08)"}`,
                    borderRadius: 50,
                    color: filter === f ? "#60A5FA" : "var(--color-text-muted)",
                    padding: "5px 14px",
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                  aria-label={`Filter contracts: ${f}`}
                >
                  {f.charAt(0) + f.slice(1).toLowerCase()}
                </button>
              ))}
            </div>
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse" }} role="table" aria-label="Contracts list">
            <thead>
              <tr>
                {["Project", "Seller", "Status", "Amount", "Features", ""].map((h) => (
                  <th
                    key={h}
                    scope="col"
                    style={{
                      textAlign: "left",
                      padding: "10px 24px",
                      fontSize: 11,
                      fontWeight: 700,
                      letterSpacing: "0.08em",
                      color: "var(--color-text-muted)",
                      textTransform: "uppercase",
                      background: "rgba(255,255,255,0.02)",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredContracts.map((c) => {
                const meta = statusMeta[c.status] || statusMeta["DRAFT"];
                return (
                  <tr
                    key={c.id}
                    style={{ borderTop: "1px solid rgba(255,255,255,0.05)", cursor: "pointer", transition: "background 0.2s" }}
                    onMouseEnter={(e) => ((e.currentTarget.style.background = "rgba(0,102,255,0.04)"))}
                    onMouseLeave={(e) => ((e.currentTarget.style.background = "transparent"))}
                  >
                    <td style={{ padding: "16px 24px" }}>
                      <Link href={`/contracts/${c.id}`} style={{ fontWeight: 600, fontSize: 14, color: "white", textDecoration: "none" }}>
                        {c.title}
                      </Link>
                      <div style={{ fontSize: 11, color: "var(--color-text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                        {c.id}
                      </div>
                    </td>
                    <td style={{ padding: "16px 24px", fontSize: 14, color: "var(--color-text-secondary)" }}>
                      {c.seller_name || c.seller_email}
                    </td>
                    <td style={{ padding: "16px 24px" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          background: meta.bg,
                          color: meta.color,
                          border: `1px solid ${meta.color}44`,
                          borderRadius: 50,
                          padding: "3px 12px",
                          fontSize: 11,
                          fontWeight: 700,
                        }}
                        aria-label={`Status: ${meta.label}`}
                      >
                        {meta.icon} {meta.label}
                      </span>
                    </td>
                    <td style={{ padding: "16px 24px", fontSize: 15, fontWeight: 700, color: "white", fontFamily: "JetBrains Mono, monospace" }}>
                      ${c.total_amount.toLocaleString()}
                    </td>
                    <td style={{ padding: "16px 24px", fontSize: 14, color: "var(--color-text-secondary)" }}>
                      {c.features?.length ?? 0} features
                    </td>
                    <td style={{ padding: "16px 24px" }}>
                      {c.status === "REVIEW" ? (
                        <Link
                          href={`/contracts/${c.id}/review`}
                          style={{
                            fontSize: 12,
                            color: "#38BDF8",
                            background: "rgba(0,163,224,0.12)",
                            border: "1px solid rgba(0,163,224,0.3)",
                            padding: "5px 12px",
                            borderRadius: 20,
                            textDecoration: "none",
                            fontWeight: 700,
                            display: "inline-block",
                          }}
                        >
                          Review & Sign →
                        </Link>
                      ) : c.status === "SIGNED" ? (
                        <Link
                          href={`/contracts/${c.id}/fund`}
                          style={{
                            fontSize: 12,
                            color: "#FBBF24",
                            background: "rgba(255,152,0,0.12)",
                            border: "1px solid rgba(255,152,0,0.3)",
                            padding: "5px 12px",
                            borderRadius: 20,
                            textDecoration: "none",
                            fontWeight: 700,
                            display: "inline-block",
                          }}
                        >
                          Fund with PayPal →
                        </Link>
                      ) : (
                        <Link
                          href={`/contracts/${c.id}`}
                          style={{
                            fontSize: 13,
                            color: "#0066FF",
                            textDecoration: "none",
                            fontWeight: 600,
                          }}
                          aria-label={`View contract: ${c.title}`}
                        >
                          View →
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}

