"use client";
import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Clock, CheckCircle, AlertCircle, Circle, BarChart2, MessageSquare, Activity, FileText, ArrowRight, ShieldCheck, UploadCloud, Scale } from "lucide-react";
import { mockApi, Contract, HoldInfo, Feature } from "@/lib/mockApi";

type TabId = "overview" | "gantt" | "chat" | "activity" | "receipt";

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  DRAFT:       { label: "Draft",       color: "#7C89A8", bg: "rgba(124,137,168,0.1)" },
  REVIEW:      { label: "In Review",   color: "#00A3E0", bg: "rgba(0,163,224,0.1)" },
  SIGNED:      { label: "Signed",      color: "#7A5CFF", bg: "rgba(122,92,255,0.1)" },
  FUNDED:      { label: "Funded",      color: "#FF9800", bg: "rgba(255,152,0,0.1)" },
  IN_PROGRESS: { label: "In Progress", color: "#0066FF", bg: "rgba(0,102,255,0.1)" },
  SUBMITTED:   { label: "Submitted",   color: "#00A3E0", bg: "rgba(0,163,224,0.1)" },
  VERIFYING:   { label: "Verifying",   color: "#7A5CFF", bg: "rgba(122,92,255,0.1)" },
  DECISION:    { label: "Decision",    color: "#FF9800", bg: "rgba(255,152,0,0.1)" },
  SETTLED:     { label: "Settled",     color: "#4CAF50", bg: "rgba(76,175,80,0.1)" },
  DISPUTE:     { label: "Dispute",     color: "#F44336", bg: "rgba(244,67,54,0.1)" },
};

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "overview",  label: "Overview",  icon: <BarChart2 size={16} /> },
  { id: "gantt",     label: "Gantt",     icon: <Activity size={16} /> },
  { id: "chat",      label: "Chat",      icon: <MessageSquare size={16} /> },
  { id: "activity",  label: "Activity",  icon: <Clock size={16} /> },
  { id: "receipt",   label: "Receipt",   icon: <FileText size={16} /> },
];

export default function ContractDashboardPage() {
  const params = useParams();
  const contractId = (params?.id as string) || "pct_099e77";
  const [tab, setTab] = useState<TabId>("overview");
  const [contract, setContract] = useState<Contract | null>(null);
  const [holdInfo, setHoldInfo] = useState<HoldInfo | null>(null);
  const [releaseModalOpen, setReleaseModalOpen] = useState(false);
  const [isReleased, setIsReleased] = useState(false);

  useEffect(() => {
    const loaded = mockApi.getContract(contractId) || mockApi.getContracts()[0];
    if (loaded) {
      setContract(loaded);
      setHoldInfo(mockApi.getHoldInfo(loaded.id));
    }
  }, [contractId]);

  const activeContract = contract || mockApi.getContracts()[0];
  const currentStatus = isReleased ? "SETTLED" : (activeContract.status || "VERIFYING");
  const meta = STATUS_META[currentStatus] || STATUS_META["VERIFYING"];

  const features = activeContract.features || [];
  const passedAmount = features
    .filter((f) => f.status.toUpperCase() === "PASSED")
    .reduce((s, f) => s + (f.allocated_amount || 0), 0);

  const daysLeft = holdInfo?.days_remaining ?? 18;

  const handleConfirmDisburse = () => {
    mockApi.settleContract(activeContract.id, passedAmount);
    setIsReleased(true);
    setReleaseModalOpen(false);
  };

  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "100px 24px 80px" }}>
        {/* Header bar */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            marginBottom: 32,
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div>
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 6 }}>
              <Link href="/dashboard/hirer" style={{ color: "inherit", textDecoration: "none" }}>Contracts</Link>
              {" / "}
              <span style={{ color: "var(--color-text-secondary)" }}>{activeContract.title}</span>
            </div>
            <h1 style={{ fontSize: "clamp(24px, 3.5vw, 40px)", fontWeight: 900, letterSpacing: "-0.02em", color: "white" }}>
              {activeContract.title}
            </h1>
            <div style={{ display: "flex", gap: 10, marginTop: 10, flexWrap: "wrap", alignItems: "center" }}>
              <span
                style={{
                  background: meta.bg,
                  color: meta.color,
                  border: `1px solid ${meta.color}44`,
                  borderRadius: 50,
                  padding: "4px 14px",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: "0.06em",
                }}
                role="status"
                aria-label={`Contract status: ${meta.label}`}
              >
                {meta.label}
              </span>
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                {activeContract.buyer_name || activeContract.buyer_email} → {activeContract.seller_name || activeContract.seller_email}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            {/* Countdown ring */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                background: "rgba(255,152,0,0.08)",
                border: "1px solid rgba(255,152,0,0.25)",
                borderRadius: 16,
                padding: "12px 18px",
              }}
              aria-label={`Escrow hold: ${daysLeft} days remaining`}
            >
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: "50%",
                  border: "3px solid rgba(255,152,0,0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  position: "relative",
                  boxShadow: "0 0 20px rgba(255,152,0,0.3)",
                }}
              >
                <svg style={{ position: "absolute", width: "100%", height: "100%" }} viewBox="0 0 44 44" aria-hidden>
                  <circle
                    cx="22" cy="22" r="20"
                    fill="none"
                    stroke="#FF9800"
                    strokeWidth="3"
                    strokeDasharray="125.6"
                    strokeDashoffset={125.6 * (1 - Math.min(29, Math.max(0, daysLeft)) / 29)}
                    strokeLinecap="round"
                    transform="rotate(-90 22 22)"
                  />
                </svg>
                <span style={{ fontSize: 13, fontWeight: 900, color: "#FF9800", fontFamily: "JetBrains Mono, monospace" }}>
                  {daysLeft}
                </span>
              </div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em" }}>ESCROW HOLD</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#FF9800" }}>{daysLeft} days left</div>
              </div>
            </div>

            {/* Amount */}
            <div
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16,
                padding: "12px 20px",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em" }}>HELD</div>
              <div style={{ fontSize: 20, fontWeight: 900, color: "white", fontFamily: "JetBrains Mono, monospace" }}>
                ${activeContract.total_amount.toLocaleString()}
              </div>
            </div>

            <button
              style={{
                background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                border: "none",
                borderRadius: 50,
                color: "white",
                padding: "12px 24px",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer",
                boxShadow: "0 0 20px rgba(0,102,255,0.4)",
              }}
              aria-label="Quick actions"
            >
              Actions ↓
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div
          style={{
            display: "flex",
            gap: 4,
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            marginBottom: 32,
            overflowX: "auto",
          }}
          role="tablist"
          aria-label="Contract sections"
        >
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              aria-controls={`tab-panel-${t.id}`}
              id={`tab-${t.id}`}
              onClick={() => setTab(t.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 7,
                padding: "10px 18px",
                background: "none",
                border: "none",
                borderBottom: tab === t.id ? "2px solid #0066FF" : "2px solid transparent",
                color: tab === t.id ? "white" : "var(--color-text-muted)",
                fontWeight: tab === t.id ? 700 : 500,
                fontSize: 14,
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.2s",
                marginBottom: -1,
              }}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Tab panels */}
        <div role="tabpanel" id={`tab-panel-${tab}`} aria-labelledby={`tab-${tab}`}>
          {tab === "overview"  && (
            <OverviewTab 
              contractId={activeContract.id} 
              features={features} 
              total={activeContract.total_amount} 
              passedAmount={passedAmount}
              onOpenRelease={() => setReleaseModalOpen(true)}
            />
          )}
          {tab === "gantt"     && <GanttTab />}
          {tab === "chat"      && <ChatTab features={features} />}
          {tab === "activity"  && <ActivityTab />}
          {tab === "receipt"   && <ReceiptTab total={activeContract.total_amount} passedAmount={passedAmount} features={features} />}
        </div>
      </div>

      {/* Release Escrow Modal */}
      {releaseModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(12px)",
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
          }}
        >
          <div
            className="glass-card"
            style={{
              maxWidth: 480,
              width: "100%",
              padding: 32,
              border: "1px solid rgba(76,175,80,0.3)",
              background: "rgba(12,18,34,0.98)",
            }}
          >
            <div style={{ width: 44, height: 44, borderRadius: 12, background: "rgba(76,175,80,0.15)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
              <ShieldCheck size={24} color="var(--color-success)" />
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 800, color: "white", marginBottom: 8 }}>
              Authorize Instant Escrow Release?
            </h2>
            <p style={{ color: "var(--color-text-secondary)", fontSize: 14, lineHeight: 1.6, marginBottom: 20 }}>
              You are about to release <strong style={{ color: "white" }}>${passedAmount}.00</strong> from PayPal escrow to the freelancer. This action is irrevocable and immediately registers a signed SHA-256 settlement receipt.
            </p>
            <div style={{ display: "flex", gap: 12 }}>
              <button
                onClick={() => setReleaseModalOpen(false)}
                style={{
                  flex: 1,
                  padding: "11px",
                  borderRadius: 10,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "transparent",
                  color: "var(--color-text-secondary)",
                  fontSize: 14,
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDisburse}
                style={{
                  flex: 1,
                  padding: "11px",
                  borderRadius: 10,
                  border: "none",
                  background: "linear-gradient(135deg, #4CAF50, #00A3E0)",
                  color: "white",
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                Confirm &amp; Disburse
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

/* ---- Tab content components ---- */

function OverviewTab({
  contractId,
  features,
  total,
  passedAmount,
  onOpenRelease,
}: {
  contractId: string;
  features: Feature[];
  total: number;
  passedAmount: number;
  onOpenRelease: () => void;
}) {
  const statusColors: Record<string, string> = {
    passed: "#4CAF50",
    failed: "#F44336",
    verifying: "#0066FF",
    pending: "#7C89A8",
  };
  const statusIcons: Record<string, React.ReactNode> = {
    passed: <CheckCircle size={14} color="#4CAF50" aria-hidden />,
    failed: <AlertCircle size={14} color="#F44336" aria-hidden />,
    verifying: <Clock size={14} color="#0066FF" aria-hidden />,
    pending: <Circle size={14} color="#7C89A8" aria-hidden />,
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 24 }}>
      {/* Features table */}
      <div
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.07)",
          borderRadius: 24,
          overflow: "hidden",
        }}
        role="region"
        aria-label="Contract features"
      >
        <div style={{ padding: "20px 24px", borderBottom: "1px solid rgba(255,255,255,0.07)", fontWeight: 700, fontSize: 15, color: "white" }}>
          Feature breakdown
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }} role="table" aria-label="Feature breakdown">
          <thead>
            <tr>
              {["Feature", "Weight", "Amount", "Status"].map((h) => (
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
            {features.map((f, i) => {
              const fStatus = (f.status || "PENDING").toLowerCase();
              const color = statusColors[fStatus] || statusColors["pending"];
              const icon = statusIcons[fStatus] || statusIcons["pending"];
              const title = f.title || (f as any).name;
              const weight = f.price_weight ?? (f as any).weight;
              const amount = f.allocated_amount ?? (f as any).amount;

              return (
                <tr
                  key={i}
                  style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}
                >
                  <td style={{ padding: "14px 24px", fontSize: 14, color: "white", fontWeight: 500 }}>{title}</td>
                  <td style={{ padding: "14px 24px", fontSize: 13, color: "var(--color-text-muted)", fontFamily: "JetBrains Mono, monospace" }}>{weight}%</td>
                  <td style={{ padding: "14px 24px", fontSize: 14, fontWeight: 600, color: "white", fontFamily: "JetBrains Mono, monospace" }}>${amount}</td>
                  <td style={{ padding: "14px 24px" }}>
                    <div
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        background: `${color}15`,
                        border: `1px solid ${color}30`,
                        borderRadius: 50,
                        padding: "3px 12px",
                        fontSize: 12,
                        fontWeight: 600,
                        color: color,
                      }}
                    >
                      {icon}
                      {fStatus.charAt(0).toUpperCase() + fStatus.slice(1)}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Sidebar */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Settlement preview */}
        <div
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 20,
            padding: 24,
          }}
          role="region"
          aria-label="Settlement preview"
        >
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em", marginBottom: 16, textTransform: "uppercase" }}>
            Settlement preview
          </div>
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 6 }}>
              <span style={{ color: "var(--color-text-secondary)" }}>Paid to freelancer</span>
              <span style={{ color: "#4CAF50", fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>${passedAmount}</span>
            </div>
            <div
              style={{
                height: 8,
                background: "rgba(255,255,255,0.08)",
                borderRadius: 4,
                overflow: "hidden",
              }}
              role="progressbar"
              aria-valuenow={(passedAmount / total) * 100}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${Math.round((passedAmount / total) * 100)}% paid`}
            >
              <div
                style={{
                  height: "100%",
                  width: `${(passedAmount / total) * 100}%`,
                  background: "linear-gradient(90deg, #4CAF50, #81C784)",
                  borderRadius: 4,
                  transition: "width 1s ease",
                }}
              />
            </div>
          </div>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 6 }}>
              <span style={{ color: "var(--color-text-secondary)" }}>Refunded to buyer</span>
              <span style={{ color: "#F44336", fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>${total - passedAmount}</span>
            </div>
            <div
              style={{
                height: 8,
                background: "rgba(255,255,255,0.08)",
                borderRadius: 4,
                overflow: "hidden",
              }}
              role="progressbar"
              aria-valuenow={((total - passedAmount) / total) * 100}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${Math.round(((total - passedAmount) / total) * 100)}% refunded`}
            >
              <div
                style={{
                  height: "100%",
                  width: `${((total - passedAmount) / total) * 100}%`,
                  background: "linear-gradient(90deg, #F44336, #EF9A9A)",
                  borderRadius: 4,
                  transition: "width 1s ease",
                }}
              />
            </div>
          </div>
        </div>

        {/* Quick actions */}
        <div
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 20,
            padding: 24,
          }}
          role="region"
          aria-label="Quick actions"
        >
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em", marginBottom: 16, textTransform: "uppercase" }}>
            Actions
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <button
              onClick={onOpenRelease}
              style={{
                background: "rgba(76,175,80,0.1)",
                border: "1px solid rgba(76,175,80,0.3)",
                borderRadius: 10,
                color: "#4CAF50",
                padding: "11px 16px",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                textAlign: "left",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
              aria-label="Release escrow"
            >
              <span>Release escrow</span>
              <ArrowRight size={14} aria-hidden />
            </button>

            <Link
              href={`/contracts/${contractId}/submit`}
              style={{
                background: "rgba(0,102,255,0.1)",
                border: "1px solid rgba(0,102,255,0.3)",
                borderRadius: 10,
                color: "#60A5FA",
                padding: "11px 16px",
                fontSize: 13,
                fontWeight: 600,
                textDecoration: "none",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
              aria-label="Submit deliverables"
            >
              <span>Submit deliverables</span>
              <UploadCloud size={14} aria-hidden />
            </Link>

            <Link
              href={`/contracts/${contractId}/settlement`}
              style={{
                background: "rgba(0,163,224,0.1)",
                border: "1px solid rgba(0,163,224,0.3)",
                borderRadius: 10,
                color: "var(--color-secondary)",
                padding: "11px 16px",
                fontSize: 13,
                fontWeight: 600,
                textDecoration: "none",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
              aria-label="View settlement ledger"
            >
              <span>Settlement summary</span>
              <ArrowRight size={14} aria-hidden />
            </Link>

            <Link
              href={`/contracts/${contractId}/dispute`}
              style={{
                background: "rgba(244,67,54,0.1)",
                border: "1px solid rgba(244,67,54,0.3)",
                borderRadius: 10,
                color: "#F44336",
                padding: "11px 16px",
                fontSize: 13,
                fontWeight: 600,
                textDecoration: "none",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
              aria-label="Open dispute"
            >
              <span>Open dispute</span>
              <Scale size={14} aria-hidden />
            </Link>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          [style*="grid-template-columns: 1fr 340px"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}

function GanttTab() {
  return (
    <div
      style={{
        background: "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.07)",
        borderRadius: 24,
        padding: "24px",
        minHeight: 500,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 16,
      }}
      id="bryntum-gantt"
      role="region"
      aria-label="Gantt timeline — Bryntum integration point"
    >
      <div style={{ fontSize: 48, opacity: 0.3 }} aria-hidden>📊</div>
      <div style={{ fontSize: 16, color: "var(--color-text-muted)", textAlign: "center" }}>
        Bryntum Gantt component mounts here
        <br />
        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, color: "rgba(124,137,168,0.5)" }}>
          #bryntum-gantt · min-height: 500px · full-width
        </span>
      </div>
    </div>
  );
}

function ChatTab({ features = [] }: { features?: Feature[] }) {
  const displayFeatures = features.length > 0 ? features : (mockApi.getContracts()[0]?.features || []);
  const messages = [
    { from: "Buyer", msg: "Can you add dark mode support as well?", time: "14:20", type: "user" },
    { from: "AI Referee", msg: "Dark mode estimated: +$120, +3 extra days. Approve to create a mini-agreement?", time: "14:21", type: "ai" },
    { from: "Seller", msg: "I can do it for $100 and 2 days.", time: "14:23", type: "seller" },
    { from: "AI Referee", msg: "Counter accepted. Creating mini-agreement for $100, 2 days. Awaiting buyer authorization.", time: "14:24", type: "ai" },
    { from: "Buyer", msg: "Approved! Let's do it.", time: "14:26", type: "user" },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 20, minHeight: 500 }}>
      {/* Task list panel */}
      <div
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.07)",
          borderRadius: 20,
          overflow: "hidden",
        }}
        role="complementary"
        aria-label="Contract features list"
      >
        <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", fontWeight: 700, fontSize: 14, color: "white" }}>
          Features
        </div>
        {displayFeatures.map((f, i) => {
          const title = f.title || (f as any).name;
          const weight = f.price_weight ?? (f as any).weight;
          const amount = f.allocated_amount ?? (f as any).amount;
          return (
            <div
              key={f.id || i}
              style={{
                padding: "14px 20px",
                borderBottom: "1px solid rgba(255,255,255,0.05)",
                cursor: "pointer",
                transition: "background 0.2s",
              }}
              onMouseEnter={(e) => ((e.currentTarget.style.background = "rgba(0,102,255,0.06)"))}
              onMouseLeave={(e) => ((e.currentTarget.style.background = "transparent"))}
              tabIndex={0}
              role="option"
              aria-label={`${title}: ${f.status}`}
            >
              <div style={{ fontSize: 13, fontWeight: 600, color: "white", marginBottom: 4 }}>{title}</div>
              <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{weight}% · ${amount}</div>
            </div>
          );
        })}
      </div>

      {/* Chat panel */}
      <div
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.07)",
          borderRadius: 20,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
        role="log"
        aria-label="Negotiation chat"
        aria-live="polite"
      >
        <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", fontWeight: 700, fontSize: 14, color: "white" }}>
          Negotiation Chat
        </div>
        <div style={{ flex: 1, padding: "20px", display: "flex", flexDirection: "column", gap: 16, overflowY: "auto" }}>
          {messages.map((m, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: m.type === "user" ? "flex-end" : m.type === "seller" ? "flex-start" : "flex-start",
              }}
            >
              <span style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 4, fontWeight: 600 }}>
                {m.from} · {m.time}
              </span>
              <div
                style={{
                  background: m.type === "ai"
                    ? "rgba(0,102,255,0.1)"
                    : m.type === "user"
                    ? "rgba(255,255,255,0.08)"
                    : "rgba(255,152,0,0.08)",
                  border: `1px solid ${m.type === "ai" ? "rgba(0,102,255,0.3)" : m.type === "user" ? "rgba(255,255,255,0.1)" : "rgba(255,152,0,0.3)"}`,
                  borderRadius: 14,
                  padding: "11px 16px",
                  maxWidth: "75%",
                  fontSize: 14,
                  color: m.type === "ai" ? "#60A5FA" : "var(--color-text-secondary)",
                  lineHeight: 1.5,
                  boxShadow: m.type === "ai" ? "0 0 20px rgba(0,102,255,0.1)" : "none",
                }}
              >
                {m.msg}
              </div>
            </div>
          ))}
        </div>
        <div
          style={{
            padding: "16px 20px",
            borderTop: "1px solid rgba(255,255,255,0.07)",
            display: "flex",
            gap: 10,
          }}
        >
          <input
            style={{
              flex: 1,
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 12,
              color: "white",
              fontSize: 14,
              padding: "10px 16px",
              outline: "none",
              fontFamily: "Inter, sans-serif",
            }}
            placeholder="Type a message..."
            aria-label="Type a message"
          />
          <button
            style={{
              background: "linear-gradient(135deg, #0066FF, #00A3E0)",
              border: "none",
              borderRadius: 12,
              color: "white",
              padding: "10px 18px",
              fontSize: 14,
              fontWeight: 700,
              cursor: "pointer",
            }}
            aria-label="Send message"
          >
            Send
          </button>
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          [style*="grid-template-columns: 280px 1fr"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}

function ActivityTab() {
  const stages = [
    { stage: "A", label: "Intake & Git clone", status: "passed", time: "14:30:01", detail: "Repo cloned: github.com/alex/ecomm-v2 · Commit: 4a9f2b1" },
    { stage: "B", label: "Clean build", status: "passed", time: "14:30:45", detail: "Build succeeded in 38s. 0 errors, 2 warnings." },
    { stage: "C", label: "Automated test suite", status: "passed", time: "14:31:12", detail: "42 tests passed, 0 failed. Coverage: 87%." },
    { stage: "D", label: "Cheat & loophole scan", status: "failed", time: "14:31:30", detail: "HIGH: Hardcoded JWT response in /api/login. Not real auth.", severity: "HIGH" },
    { stage: "E", label: "Visual diff (Figma)", status: "running", time: "14:31:45", detail: "Comparing 4 screens against Figma specs..." },
    { stage: "F", label: "QA multimodal report", status: "pending", time: "—", detail: "Waiting for Stage E to complete." },
  ];

  const stageColors: Record<string, string> = {
    passed: "#4CAF50",
    failed: "#F44336",
    running: "#0066FF",
    pending: "#7C89A8",
  };

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.07)",
        borderRadius: 24,
        overflow: "hidden",
      }}
      role="log"
      aria-label="Verification activity feed"
      aria-live="polite"
    >
      <div style={{ padding: "20px 28px", borderBottom: "1px solid rgba(255,255,255,0.07)", fontWeight: 700, fontSize: 15, color: "white" }}>
        Verification Pipeline — Stages A–F
      </div>
      <div style={{ padding: "24px 28px", display: "flex", flexDirection: "column", gap: 0 }}>
        {stages.map((s, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              gap: 20,
              paddingBottom: i < stages.length - 1 ? 28 : 0,
              position: "relative",
            }}
            role="listitem"
            aria-label={`Stage ${s.stage}: ${s.label} — ${s.status}`}
          >
            {/* Vertical connector */}
            {i < stages.length - 1 && (
              <div
                style={{
                  position: "absolute",
                  left: 20,
                  top: 40,
                  bottom: 0,
                  width: 2,
                  background: stageColors[s.status] === "#7C89A8"
                    ? "rgba(124,137,168,0.2)"
                    : `${stageColors[s.status]}30`,
                }}
                aria-hidden
              />
            )}

            {/* Stage dot */}
            <div
              style={{
                width: 42,
                height: 42,
                borderRadius: "50%",
                background: `${stageColors[s.status]}18`,
                border: `2px solid ${stageColors[s.status]}50`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                fontWeight: 800,
                fontSize: 14,
                color: stageColors[s.status],
                fontFamily: "JetBrains Mono, monospace",
                boxShadow: s.status === "running" ? `0 0 20px ${stageColors[s.status]}40` : "none",
              }}
              aria-hidden
            >
              {s.stage}
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8, marginBottom: 6 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontWeight: 700, fontSize: 15, color: "white" }}>Stage {s.stage}: {s.label}</span>
                  {s.severity && (
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 800,
                        letterSpacing: "0.08em",
                        color: "#F44336",
                        background: "rgba(244,67,54,0.1)",
                        border: "1px solid rgba(244,67,54,0.3)",
                        borderRadius: 50,
                        padding: "2px 10px",
                      }}
                    >
                      {s.severity}
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <span
                    style={{
                      fontSize: 12,
                      fontFamily: "JetBrains Mono, monospace",
                      color: "var(--color-text-muted)",
                    }}
                  >
                    {s.time}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      letterSpacing: "0.06em",
                      color: stageColors[s.status],
                      textTransform: "uppercase",
                    }}
                  >
                    {s.status}
                  </span>
                </div>
              </div>
              <p style={{ fontSize: 13, color: "var(--color-text-muted)", lineHeight: 1.5 }}>{s.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReceiptTab({
  total,
  passedAmount,
  features,
}: {
  total: number;
  passedAmount: number;
  features: Feature[];
}) {
  return (
    <div style={{ maxWidth: 680, margin: "0 auto" }}>
      <div
        style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 28,
          overflow: "hidden",
          boxShadow: "0 0 60px rgba(122,92,255,0.1)",
        }}
        role="region"
        aria-label="Proof-of-work receipt"
      >
        {/* Receipt header */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(122,92,255,0.15), rgba(0,102,255,0.1))",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            padding: "28px 32px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", color: "var(--color-text-muted)", marginBottom: 6 }}>
              PROOF-OF-WORK RECEIPT
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: "white" }}>PactPal Verification Certificate</div>
          </div>
          <div
            style={{
              background: "rgba(76,175,80,0.15)",
              border: "1px solid rgba(76,175,80,0.4)",
              borderRadius: 50,
              padding: "8px 18px",
              fontSize: 12,
              fontWeight: 700,
              color: "#4CAF50",
              display: "flex",
              alignItems: "center",
              gap: 7,
            }}
          >
            <CheckCircle size={14} aria-hidden /> Verified
          </div>
        </div>

        <div style={{ padding: "28px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
          {/* SHA-256 */}
          <div
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(122,92,255,0.2)",
              borderRadius: 14,
              padding: "18px 20px",
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", color: "var(--color-text-muted)", marginBottom: 10 }}>
              SHA-256 FINGERPRINT
            </div>
            <div
              style={{
                fontSize: 13,
                fontFamily: "JetBrains Mono, monospace",
                color: "#A78BFA",
                wordBreak: "break-all",
                lineHeight: 1.6,
              }}
              role="textbox"
              aria-label="SHA-256 fingerprint"
            >
              0xa9f3e8c2d4b16f7a3e2d1c9b8a7f6e5d4c3b2a190887766554433221100aabb
            </div>
            <button
              style={{
                marginTop: 10,
                background: "none",
                border: "1px solid rgba(122,92,255,0.3)",
                borderRadius: 8,
                color: "#A78BFA",
                padding: "5px 14px",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
              }}
              aria-label="Copy SHA-256 fingerprint to clipboard"
            >
              📋 Copy
            </button>
          </div>

          {/* Summary rows */}
          {[
            ["Contract ID", "pact_01JDFG49XK4VD"],
            ["Issued", new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })],
            ["Buyer", "Priya S."],
            ["Seller", "Alex M."],
            ["Total held", `$${total.toLocaleString()} USD`],
            ["Features passed", `${features.filter((f) => (f.status || "").toLowerCase() === "passed").length} of ${features.length}`],
            ["Seller payout", `$${passedAmount.toLocaleString()} USD`],
            ["Buyer refund", `$${(total - passedAmount).toLocaleString()} USD`],
            ["Visual match avg", "94.3%"],
            ["Test coverage", "87%"],
          ].map(([k, v]) => (
            <div
              key={k}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                fontSize: 14,
                paddingBottom: 14,
                borderBottom: "1px solid rgba(255,255,255,0.05)",
              }}
            >
              <span style={{ color: "var(--color-text-muted)" }}>{k}</span>
              <span style={{ fontWeight: 600, color: "white", fontFamily: ["Total held", "Seller payout", "Buyer refund"].includes(k) ? "JetBrains Mono, monospace" : "Inter, sans-serif" }}>
                {v}
              </span>
            </div>
          ))}

          {/* PayPal link */}
          <a
            href="#"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              background: "rgba(0,102,255,0.08)",
              border: "1px solid rgba(0,102,255,0.25)",
              borderRadius: 12,
              color: "#60A5FA",
              padding: "14px",
              fontSize: 14,
              fontWeight: 600,
              textDecoration: "none",
            }}
            aria-label="View PayPal transaction reference"
          >
            🔗 View PayPal reference · PP-R-4A9F3E8C2D4B
          </a>
        </div>
      </div>
    </div>
  );
}

