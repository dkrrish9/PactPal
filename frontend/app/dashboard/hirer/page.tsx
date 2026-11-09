"use client";
import Navbar from "@/components/Navbar";
import Link from "next/link";
import { Plus, Shield, Clock, CheckCircle, AlertCircle, Circle } from "lucide-react";

const contracts = [
  { id: "1", title: "E-commerce Platform v2", seller: "Alex M.", status: "VERIFYING", amount: 1500, daysLeft: 12 },
  { id: "2", title: "Mobile fitness app", seller: "Chen W.", status: "IN_PROGRESS", amount: 1800, daysLeft: 20 },
  { id: "3", title: "Brand identity kit", seller: "Sara K.", status: "SETTLED", amount: 600, daysLeft: 0 },
  { id: "4", title: "AI chatbot integration", seller: "Mo T.", status: "FUNDED", amount: 900, daysLeft: 25 },
];

const statusMeta: Record<string, { color: string; bg: string; label: string; icon: React.ReactNode }> = {
  DRAFT:       { color: "#7C89A8", bg: "rgba(124,137,168,0.1)", label: "Draft", icon: <Circle size={12} /> },
  FUNDED:      { color: "#FF9800", bg: "rgba(255,152,0,0.1)", label: "Funded", icon: <Shield size={12} /> },
  IN_PROGRESS: { color: "#0066FF", bg: "rgba(0,102,255,0.1)", label: "In Progress", icon: <Clock size={12} /> },
  VERIFYING:   { color: "#7A5CFF", bg: "rgba(122,92,255,0.1)", label: "Verifying", icon: <Clock size={12} /> },
  SETTLED:     { color: "#4CAF50", bg: "rgba(76,175,80,0.1)", label: "Settled", icon: <CheckCircle size={12} /> },
  DISPUTE:     { color: "#F44336", bg: "rgba(244,67,54,0.1)", label: "Dispute", icon: <AlertCircle size={12} /> },
};

export default function HirerDashboardPage() {
  const totalHeld = contracts.filter((c) => c.status !== "SETTLED").reduce((s, c) => s + c.amount, 0);

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
            { label: "Active contracts", value: "3", color: "#0066FF", icon: "📋" },
            { label: "Completed", value: "1", color: "#4CAF50", icon: "✅" },
            { label: "Total spent", value: "$4,800", color: "#7A5CFF", icon: "💸" },
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
              {["All", "Active", "Verifying", "Settled"].map((f) => (
                <button
                  key={f}
                  style={{
                    background: f === "All" ? "rgba(0,102,255,0.15)" : "rgba(255,255,255,0.05)",
                    border: `1px solid ${f === "All" ? "rgba(0,102,255,0.4)" : "rgba(255,255,255,0.08)"}`,
                    borderRadius: 50,
                    color: f === "All" ? "#60A5FA" : "var(--color-text-muted)",
                    padding: "5px 14px",
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                  aria-label={`Filter contracts: ${f}`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse" }} role="table" aria-label="Contracts list">
            <thead>
              <tr>
                {["Project", "Seller", "Status", "Amount", "Days left", ""].map((h) => (
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
              {contracts.map((c, i) => {
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
                    </td>
                    <td style={{ padding: "16px 24px", fontSize: 14, color: "var(--color-text-secondary)" }}>{c.seller}</td>
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
                      ${c.amount.toLocaleString()}
                    </td>
                    <td style={{ padding: "16px 24px", fontSize: 14, color: c.daysLeft < 5 ? "#FF9800" : "var(--color-text-secondary)" }}>
                      {c.daysLeft > 0 ? `${c.daysLeft}d` : "—"}
                    </td>
                    <td style={{ padding: "16px 24px" }}>
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

