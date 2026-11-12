"use client";
import { useState } from "react";
import Link from "next/link";
import { 
  ShieldAlert, 
  Clock, 
  DollarSign, 
  CheckCircle2, 
  AlertTriangle, 
  Play, 
  Search, 
  ArrowUpRight,
  Terminal,
  Activity,
  Layers,
  ChevronRight
} from "lucide-react";
import { mockApi } from "@/lib/mockApi";

interface MockContract {
  id: string;
  title: string;
  buyer: string;
  seller: string;
  amount: number;
  stage: string;
  daysRemaining: number;
  status: "ACTIVE_HOLD" | "VERIFYING" | "DISPUTED" | "SETTLED";
  testsPassed: number;
  testsTotal: number;
}

const INITIAL_CONTRACTS: MockContract[] = [
  {
    id: "pct_98f41e2a",
    title: "SaaS Analytics Dashboard & Bryntum Gantt",
    buyer: "alex@fintech.io",
    seller: "maria.dev@code.io",
    amount: 3200,
    stage: "Stage D: Pixel Match & Visual Regression",
    daysRemaining: 18,
    status: "ACTIVE_HOLD",
    testsPassed: 4,
    testsTotal: 5,
  },
  {
    id: "pct_42c890ab",
    title: "Solana Staking Escrow Smart Contract",
    buyer: "david@web3vc.com",
    seller: "kevin.crypto@dev.com",
    amount: 4500,
    stage: "Stage B: Containerized Unit Tests",
    daysRemaining: 24,
    status: "ACTIVE_HOLD",
    testsPassed: 8,
    testsTotal: 8,
  },
  {
    id: "pct_11e739cd",
    title: "AI Customer Support Agent Integration",
    buyer: "sarah@zenflow.co",
    seller: "chen.ai@neural.io",
    amount: 1800,
    stage: "Dispute Mediation: Mock API Fraud Detected",
    daysRemaining: 4,
    status: "DISPUTED",
    testsPassed: 2,
    testsTotal: 6,
  },
  {
    id: "pct_77b312fe",
    title: "Mobile App Checkout Flow Redesign",
    buyer: "marcus@retailscale.net",
    seller: "elena@uxcraft.design",
    amount: 2100,
    stage: "Stage F: Smart Split Settlement Executed",
    daysRemaining: 0,
    status: "SETTLED",
    testsPassed: 5,
    testsTotal: 5,
  },
];

export default function AdminPage() {
  const [contracts, setContracts] = useState<MockContract[]>(INITIAL_CONTRACTS);
  const [filter, setFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [logs, setLogs] = useState<string[]>([
    "[SYSTEM_INIT] PactPal Admin Core initialized with SHA-256 tamper-evident log.",
    "[ESCROW_HEARTBEAT] PayPal webhook listener active. 29-day timer running for 4 contracts.",
    "[REFEREE_DAEMON] Isolated container test runner pool: 8 active microVM instances.",
  ]);
  const [bannerAlert, setBannerAlert] = useState<string | null>(null);

  const filteredContracts = contracts.filter((c) => {
    const matchesFilter = filter === "ALL" || c.status === filter;
    const matchesSearch =
      c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.buyer.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.seller.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const simulateDeadline = (id: string) => {
    // Invoke mockApi watcher flow (C49/C50)
    mockApi.simulateDeadlineWatcher(id);

    setContracts((prev) =>
      prev.map((c) => {
        if (c.id === id) {
          return {
            ...c,
            daysRemaining: 0,
            status: "SETTLED",
            stage: "Auto-Settled: 29-Day Timer Reached (Prorated Release)",
          };
        }
        return c;
      })
    );
    const logEntry = `[DEADLINE WATCHER C49/C50] Simulated deadline elapsed for ${id}. Auto-triggered final verification and proportional payout settlement.`;
    setLogs((prev) => [logEntry, ...prev]);
    setBannerAlert(`Deadline watcher simulation executed for ${id}. Proportional payout disbursed.`);
    setTimeout(() => setBannerAlert(null), 5000);
  };

  const forceAudit = (id: string) => {
    setContracts((prev) =>
      prev.map((c) => {
        if (c.id === id) {
          return {
            ...c,
            status: "VERIFYING",
            stage: "Stage C: AST Hardcoded Bypass Check in Progress",
          };
        }
        return c;
      })
    );
    const logEntry = `[ADMIN_ACTION] Force AI audit invoked for contract ${id}. Spinning up MicroVM Sandbox...`;
    setLogs((prev) => [logEntry, ...prev]);
    setBannerAlert(`AI Referee Audit triggered for ${id}.`);
    setTimeout(() => setBannerAlert(null), 4000);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        color: "white",
        fontFamily: "Inter, sans-serif",
        paddingTop: 88,
        paddingBottom: 80,
      }}
    >
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 24px" }}>
        
        {/* Top Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "4px 10px",
                  borderRadius: 8,
                  background: "rgba(244,67,54,0.15)",
                  border: "1px solid rgba(244,67,54,0.3)",
                  fontSize: 12,
                  fontWeight: 700,
                  color: "var(--color-danger)",
                  letterSpacing: "0.06em",
                }}
              >
                <ShieldAlert size={14} />
                ADMIN SUPERVISOR CONSOLE
              </div>
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                Internal Operations & Arbitration
              </span>
            </div>
            <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.02em" }}>
              Contract Registry & Sandbox Controls
            </h1>
          </div>

          <div style={{ display: "flex", gap: 12 }}>
            <Link
              href="/dashboard/hirer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "8px 16px",
                borderRadius: 10,
                border: "1px solid rgba(255,255,255,0.12)",
                color: "var(--color-text-secondary)",
                fontSize: 14,
                textDecoration: "none",
              }}
            >
              Hirer View <ArrowUpRight size={14} />
            </Link>
            <Link
              href="/dashboard/freelancer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "8px 16px",
                borderRadius: 10,
                border: "1px solid rgba(255,255,255,0.12)",
                color: "var(--color-text-secondary)",
                fontSize: 14,
                textDecoration: "none",
              }}
            >
              Freelancer View <ArrowUpRight size={14} />
            </Link>
          </div>
        </div>

        {/* Banner Alert */}
        {bannerAlert && (
          <div
            style={{
              padding: "12px 18px",
              borderRadius: 10,
              background: "rgba(0, 102, 255, 0.15)",
              border: "1px solid rgba(0, 102, 255, 0.4)",
              color: "#60A5FA",
              fontSize: 14,
              fontWeight: 500,
              marginBottom: 24,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <CheckCircle2 size={16} />
            {bannerAlert}
          </div>
        )}

        {/* Metric Cards Row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 20, marginBottom: 32 }}>
          {[
            {
              label: "TOTAL ESCROW SECURED",
              val: "$11,600",
              sub: "Locked in PayPal Authorized Hold",
              icon: <DollarSign size={20} color="var(--color-primary)" />,
            },
            {
              label: "ACTIVE CONTRACTS",
              val: contracts.length.toString(),
              sub: "2 Verifications running right now",
              icon: <Activity size={20} color="var(--color-secondary)" />,
            },
            {
              label: "DISPUTED CASES",
              val: "1",
              sub: "Cheat detected (Hardcoded mock return)",
              icon: <AlertTriangle size={20} color="var(--color-accent)" />,
            },
            {
              label: "VERIFICATION RUNTIME",
              val: "100% Isolated",
              sub: "gVisor Firecracker MicroVMs",
              icon: <Layers size={20} color="var(--color-success)" />,
            },
          ].map((metric, i) => (
            <div
              key={i}
              className="glass-card"
              style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 8 }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em" }}>
                  {metric.label}
                </span>
                {metric.icon}
              </div>
              <div style={{ fontSize: 28, fontWeight: 800, fontFamily: "JetBrains Mono, monospace" }}>
                {metric.val}
              </div>
              <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>{metric.sub}</span>
            </div>
          ))}
        </div>

        {/* Main Section: Contracts Table + Controls */}
        <div className="glass-card" style={{ padding: "24px", marginBottom: 32 }}>
          {/* Table Toolbar */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 16,
              marginBottom: 24,
            }}
          >
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-muted)", marginRight: 8 }}>
                FILTER STATUS:
              </span>
              {["ALL", "ACTIVE_HOLD", "DISPUTED", "SETTLED"].map((st) => (
                <button
                  key={st}
                  onClick={() => setFilter(st)}
                  style={{
                    padding: "6px 14px",
                    borderRadius: 8,
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                    background: filter === st ? "rgba(0,102,255,0.2)" : "rgba(255,255,255,0.04)",
                    color: filter === st ? "var(--color-primary)" : "var(--color-text-secondary)",
                    border: filter === st ? "1px solid var(--color-primary)" : "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  {st}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                padding: "8px 14px",
                width: 280,
              }}
            >
              <Search size={14} color="var(--color-text-muted)" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search contract or party..."
                style={{
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  color: "white",
                  fontSize: 13,
                  width: "100%",
                }}
              />
            </div>
          </div>

          {/* Table */}
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "var(--color-text-muted)", fontSize: 12 }}>
                  <th style={{ padding: "12px 16px" }}>CONTRACT / ID</th>
                  <th style={{ padding: "12px 16px" }}>PARTIES</th>
                  <th style={{ padding: "12px 16px" }}>ESCROW</th>
                  <th style={{ padding: "12px 16px" }}>CURRENT PIPELINE STAGE</th>
                  <th style={{ padding: "12px 16px" }}>STATUS</th>
                  <th style={{ padding: "12px 16px", textAlign: "right" }}>ADMIN SIMULATION CONTROLS</th>
                </tr>
              </thead>
              <tbody>
                {filteredContracts.map((c) => {
                  const statusColors: Record<string, { bg: string; text: string }> = {
                    ACTIVE_HOLD: { bg: "rgba(0,102,255,0.15)", text: "#60A5FA" },
                    VERIFYING: { bg: "rgba(0,163,224,0.15)", text: "var(--color-secondary)" },
                    DISPUTED: { bg: "rgba(244,67,54,0.15)", text: "var(--color-danger)" },
                    SETTLED: { bg: "rgba(76,175,80,0.15)", text: "var(--color-success)" },
                  };

                  return (
                    <tr
                      key={c.id}
                      style={{
                        borderBottom: "1px solid rgba(255,255,255,0.05)",
                        transition: "background 0.2s",
                      }}
                    >
                      <td style={{ padding: "16px" }}>
                        <Link
                          href={`/contracts/${c.id}`}
                          style={{
                            fontWeight: 600,
                            color: "white",
                            textDecoration: "none",
                            display: "block",
                            marginBottom: 4,
                          }}
                        >
                          {c.title}
                        </Link>
                        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, color: "var(--color-text-muted)" }}>
                          {c.id}
                        </span>
                      </td>

                      <td style={{ padding: "16px", fontSize: 13 }}>
                        <div style={{ color: "var(--color-text-secondary)" }}>
                          <span style={{ color: "var(--color-text-muted)" }}>Hirer: </span>
                          {c.buyer}
                        </div>
                        <div style={{ color: "var(--color-text-secondary)", marginTop: 2 }}>
                          <span style={{ color: "var(--color-text-muted)" }}>Freelancer: </span>
                          {c.seller}
                        </div>
                      </td>

                      <td style={{ padding: "16px" }}>
                        <div style={{ fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>
                          ${c.amount.toLocaleString()}
                        </div>
                        <div style={{ fontSize: 12, color: "var(--color-text-muted)", display: "flex", alignItems: "center", gap: 4, marginTop: 2 }}>
                          <Clock size={12} /> {c.daysRemaining}d left
                        </div>
                      </td>

                      <td style={{ padding: "16px" }}>
                        <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                          {c.stage}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 4 }}>
                          Passing tests: {c.testsPassed}/{c.testsTotal}
                        </div>
                      </td>

                      <td style={{ padding: "16px" }}>
                        <span
                          style={{
                            padding: "4px 8px",
                            borderRadius: 6,
                            fontSize: 11,
                            fontWeight: 700,
                            background: statusColors[c.status].bg,
                            color: statusColors[c.status].text,
                            letterSpacing: "0.04em",
                          }}
                        >
                          {c.status}
                        </span>
                      </td>

                      <td style={{ padding: "16px", textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: 8 }}>
                          <button
                            onClick={() => simulateDeadline(c.id)}
                            disabled={c.status === "SETTLED"}
                            style={{
                              padding: "6px 12px",
                              borderRadius: 6,
                              fontSize: 12,
                              fontWeight: 600,
                              cursor: c.status === "SETTLED" ? "not-allowed" : "pointer",
                              background: "rgba(255,152,0,0.12)",
                              border: "1px solid rgba(255,152,0,0.3)",
                              color: "var(--color-accent)",
                              opacity: c.status === "SETTLED" ? 0.4 : 1,
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4,
                            }}
                            title="Simulate 29-day timer expiration to trigger settlement"
                          >
                            <Play size={12} />
                            Simulate Deadline
                          </button>

                          <button
                            onClick={() => forceAudit(c.id)}
                            style={{
                              padding: "6px 12px",
                              borderRadius: 6,
                              fontSize: 12,
                              fontWeight: 600,
                              cursor: "pointer",
                              background: "rgba(0,102,255,0.12)",
                              border: "1px solid rgba(0,102,255,0.3)",
                              color: "var(--color-primary)",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4,
                            }}
                          >
                            Force Audit
                          </button>

                          <Link
                            href={`/contracts/${c.id}`}
                            style={{
                              padding: "6px 10px",
                              borderRadius: 6,
                              background: "rgba(255,255,255,0.06)",
                              border: "1px solid rgba(255,255,255,0.1)",
                              color: "white",
                              display: "inline-flex",
                              alignItems: "center",
                              textDecoration: "none",
                            }}
                          >
                            <ChevronRight size={14} />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Admin Audit & Telemetry Console */}
        <div className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <Terminal size={18} color="var(--color-secondary)" />
            <h2 style={{ fontSize: 16, fontWeight: 700, letterSpacing: "0.04em" }}>
              LIVE REFEREE TELEMETRY STREAM (AUDIT TRAIL)
            </h2>
          </div>
          <div
            style={{
              background: "rgba(0,0,0,0.4)",
              borderRadius: 10,
              padding: "16px",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13,
              color: "#94A3B8",
              maxHeight: 220,
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 8,
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            {logs.map((lg, idx) => (
              <div key={idx} style={{ display: "flex", gap: 8 }}>
                <span style={{ color: "var(--color-text-muted)" }}>&gt;</span>
                <span style={{ color: lg.includes("SIMULATION") ? "var(--color-accent)" : lg.includes("ACTION") ? "var(--color-secondary)" : "#CBD5E1" }}>
                  {lg}
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}

