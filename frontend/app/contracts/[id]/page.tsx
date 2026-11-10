"use client";
import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import Link from "next/link";
import { useParams } from "next/navigation";
import { 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  Circle, 
  BarChart2, 
  MessageSquare, 
  Activity, 
  FileText, 
  ArrowRight, 
  ShieldCheck, 
  UploadCloud, 
  Scale, 
  GitBranch, 
  ExternalLink, 
  AlertTriangle,
  Play,
  Pause,
  RotateCcw,
  Zap,
  ChevronRight,
  Terminal as TerminalIcon,
  Sparkles
} from "lucide-react";
import { mockApi, Contract, HoldInfo, Feature, Submission, ContractStatus, CONTRACT_STATES_META } from "@/lib/mockApi";

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
  const [simulatedStatus, setSimulatedStatus] = useState<ContractStatus | null>(null);

  useEffect(() => {
    const loaded = mockApi.getContract(contractId) || mockApi.getContracts()[0];
    if (loaded) {
      setContract(loaded);
      setHoldInfo(mockApi.getHoldInfo(loaded.id));
    }
  }, [contractId]);

  const activeContract = contract || mockApi.getContracts()[0];
  const currentStatus: ContractStatus = simulatedStatus || (isReleased ? "SETTLED" : (activeContract.status || "VERIFYING"));
  const meta = CONTRACT_STATES_META[currentStatus] || CONTRACT_STATES_META["VERIFYING"];

  const handleSimulateStatus = (status: ContractStatus) => {
    setSimulatedStatus(status);
    mockApi.updateContractStatus(activeContract.id, status);
    if (contract) {
      setContract({ ...contract, status });
    }
  };

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

            {activeContract.status === "REVIEW" ? (
              <Link
                href={`/contracts/${activeContract.id}/review`}
                style={{
                  background: "linear-gradient(135deg, #00A3E0, #0066FF)",
                  borderRadius: 50,
                  color: "white",
                  padding: "12px 24px",
                  fontSize: 14,
                  fontWeight: 700,
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  boxShadow: "0 0 20px rgba(0,163,224,0.4)",
                }}
              >
                Review & Counter (C17) →
              </Link>
            ) : activeContract.status === "SIGNED" ? (
              <Link
                href={`/contracts/${activeContract.id}/fund`}
                style={{
                  background: "linear-gradient(135deg, #FF9800, #F57C00)",
                  borderRadius: 50,
                  color: "white",
                  padding: "12px 24px",
                  fontSize: 14,
                  fontWeight: 700,
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  boxShadow: "0 0 20px rgba(255,152,0,0.4)",
                }}
              >
                Fund Escrow with PayPal (C20) →
              </Link>
            ) : (
              <Link
                href={`/contracts/${activeContract.id}/review`}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.15)",
                  borderRadius: 50,
                  color: "white",
                  padding: "12px 24px",
                  fontSize: 14,
                  fontWeight: 700,
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                Review Checklist 📋
              </Link>
            )}
          </div>
        </div>

        {/* The 10 Contract Lifecycle State Stepper (C33 Core Requirement) */}
        <div
          style={{
            background: "rgba(255, 255, 255, 0.02)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: 20,
            padding: "20px 24px",
            marginBottom: 28,
          }}
          role="region"
          aria-label="10-state contract lifecycle stepper"
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Sparkles size={16} color="#60A5FA" />
              <span style={{ fontSize: 13, fontWeight: 800, color: "white", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                10-State Contract Lifecycle Stepper (C33)
              </span>
              <span
                style={{
                  background: meta.bg,
                  color: meta.color,
                  border: `1px solid ${meta.border}`,
                  padding: "2px 10px",
                  borderRadius: 20,
                  fontSize: 11,
                  fontWeight: 800,
                }}
              >
                CURRENT: {currentStatus}
              </span>
            </div>

            {/* State Simulator Selector */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Simulate Any State:</span>
              <select
                value={currentStatus}
                onChange={(e) => handleSimulateStatus(e.target.value as ContractStatus)}
                style={{
                  background: "rgba(0,0,0,0.6)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: 10,
                  color: "white",
                  fontSize: 12,
                  fontWeight: 700,
                  padding: "5px 12px",
                  outline: "none",
                  cursor: "pointer",
                }}
                aria-label="Simulate contract state"
              >
                {Object.keys(CONTRACT_STATES_META).map((st) => (
                  <option key={st} value={st} style={{ background: "#0F172A", color: "white" }}>
                    {CONTRACT_STATES_META[st as ContractStatus].step}. {CONTRACT_STATES_META[st as ContractStatus].label} ({st})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Stepper items row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(105px, 1fr))",
              gap: 8,
            }}
          >
            {Object.entries(CONTRACT_STATES_META).map(([stKey, stMeta]) => {
              const isActive = currentStatus === stKey;
              const isPast = CONTRACT_STATES_META[currentStatus]?.step > stMeta.step;
              return (
                <button
                  key={stKey}
                  onClick={() => handleSimulateStatus(stKey as ContractStatus)}
                  title={`${stMeta.label}: ${stMeta.shortDesc}`}
                  style={{
                    background: isActive ? stMeta.bg : isPast ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.01)",
                    border: `1px solid ${isActive ? stMeta.border : isPast ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.05)"}`,
                    borderRadius: 12,
                    padding: "10px 6px",
                    textAlign: "center",
                    cursor: "pointer",
                    transition: "all 0.2s",
                    position: "relative",
                  }}
                >
                  <div
                    style={{
                      fontSize: 10,
                      fontWeight: 800,
                      fontFamily: "JetBrains Mono, monospace",
                      color: isActive ? stMeta.color : isPast ? "#81C784" : "var(--color-text-muted)",
                      marginBottom: 2,
                    }}
                  >
                    {isPast ? "✓" : `0${stMeta.step}`}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: isActive ? "white" : isPast ? "rgba(255,255,255,0.85)" : "var(--color-text-muted)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {stMeta.label}
                  </div>
                  {isActive && (
                    <div
                      style={{
                        position: "absolute",
                        bottom: 0,
                        left: "15%",
                        right: "15%",
                        height: 2,
                        background: stMeta.color,
                        borderRadius: 2,
                        boxShadow: `0 0 10px ${stMeta.color}`,
                      }}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Milestone Action Callout Banner */}
        {activeContract.status === "REVIEW" && (
          <div
            style={{
              marginBottom: 28,
              padding: "18px 24px",
              background: "rgba(0, 163, 224, 0.1)",
              border: "1px solid rgba(0, 163, 224, 0.35)",
              borderRadius: 18,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 24 }}>📝</span>
              <div>
                <strong style={{ color: "white", fontSize: 15 }}>C17 Seller Review & Checklist Confirmation</strong>
                <p style={{ color: "var(--color-text-secondary)", fontSize: 13, margin: 0 }}>
                  Freelancer can accept terms, propose counter terms (price/weights/deadline), and dual-confirm the checklist.
                </p>
              </div>
            </div>
            <Link
              href={`/contracts/${activeContract.id}/review`}
              style={{
                background: "linear-gradient(135deg, #00A3E0, #0066FF)",
                color: "white",
                padding: "10px 22px",
                borderRadius: 30,
                fontSize: 13,
                fontWeight: 700,
                textDecoration: "none",
              }}
            >
              Open Seller Review Page →
            </Link>
          </div>
        )}

        {activeContract.status === "SIGNED" && (
          <div
            style={{
              marginBottom: 28,
              padding: "18px 24px",
              background: "rgba(255, 152, 0, 0.1)",
              border: "1px solid rgba(255, 152, 0, 0.35)",
              borderRadius: 18,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 24 }}>🔒</span>
              <div>
                <strong style={{ color: "white", fontSize: 15 }}>C20 Escrow Funding & Authorization Hold</strong>
                <p style={{ color: "var(--color-text-secondary)", fontSize: 13, margin: 0 }}>
                  Both parties have signed! Buyer must now authorize the 29-day PayPal hold to activate escrow.
                </p>
              </div>
            </div>
            <Link
              href={`/contracts/${activeContract.id}/fund`}
              style={{
                background: "linear-gradient(135deg, #FF9800, #F57C00)",
                color: "white",
                padding: "10px 22px",
                borderRadius: 30,
                fontSize: 13,
                fontWeight: 700,
                textDecoration: "none",
              }}
            >
              Open PayPal Funding Page →
            </Link>
          </div>
        )}

        {(activeContract.status === "VERIFYING" || activeContract.status === "SUBMITTED" || activeContract.status === "DECISION" || activeContract.status === "SETTLED") && (
          <div
            style={{
              marginBottom: 28,
              padding: "18px 24px",
              background: "rgba(122, 92, 255, 0.1)",
              border: "1px solid rgba(122, 92, 255, 0.35)",
              borderRadius: 18,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 24 }}>🤖</span>
              <div>
                <strong style={{ color: "white", fontSize: 15 }}>C29 AI Referee Verification Results</strong>
                <p style={{ color: "var(--color-text-secondary)", fontSize: 13, margin: 0 }}>
                  Review per-feature verdicts, test suite evidence, and side-by-side Figma vs headless browser screenshots.
                </p>
              </div>
            </div>
            <Link
              href={`/contracts/${activeContract.id}/verification`}
              style={{
                background: "linear-gradient(135deg, #7A5CFF, #0066FF)",
                color: "white",
                padding: "10px 22px",
                borderRadius: 30,
                fontSize: 13,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 0 20px rgba(122,92,255,0.4)",
              }}
            >
              View Verification Results (C29) →
            </Link>
          </div>
        )}

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
              submission={activeContract.submission}
              deadline={activeContract.deadline}
              onOpenRelease={() => setReleaseModalOpen(true)}
            />
          )}
          {tab === "gantt"     && <GanttTab />}
          {tab === "chat"      && <ChatTab features={features} />}
          {tab === "activity"  && <ActivityTab submission={activeContract.submission} />}
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
  submission,
  deadline,
  onOpenRelease,
}: {
  contractId: string;
  features: Feature[];
  total: number;
  passedAmount: number;
  submission?: Submission | null;
  deadline?: string;
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
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Latest Seller Submission Card (C25 Core Requirement) */}
      {submission && (
        <div
          style={{
            background: "rgba(255, 255, 255, 0.03)",
            border: `1px solid ${submission.is_late ? "rgba(244, 67, 54, 0.35)" : "rgba(76, 175, 80, 0.35)"}`,
            borderRadius: 20,
            padding: "24px 28px",
            boxShadow: submission.is_late ? "0 0 30px rgba(244,67,54,0.08)" : "0 0 30px rgba(76,175,80,0.08)",
          }}
          role="region"
          aria-label="Latest deliverable submission"
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 14, marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 28 }}>📦</span>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <h3 style={{ fontSize: 17, fontWeight: 800, color: "white", margin: 0 }}>
                    Seller Submission (Version {submission.version_number})
                  </h3>
                  {/* Late Flag Badge (C25) */}
                  <span
                    style={{
                      background: submission.is_late ? "rgba(244, 67, 54, 0.15)" : "rgba(76, 175, 80, 0.15)",
                      border: `1px solid ${submission.is_late ? "rgba(244, 67, 54, 0.4)" : "rgba(76, 175, 80, 0.4)"}`,
                      color: submission.is_late ? "#EF5350" : "#81C784",
                      padding: "3px 10px",
                      borderRadius: 20,
                      fontSize: 11,
                      fontWeight: 800,
                      letterSpacing: "0.06em",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    {submission.is_late ? <AlertTriangle size={12} /> : <CheckCircle size={12} />}
                    {submission.is_late ? "LATE SUBMISSION" : "ON-TIME SUBMISSION"}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 2 }}>
                  Intake recorded on: {new Date(submission.submitted_at).toLocaleString()}
                </div>
              </div>
            </div>

            <Link
              href={`/contracts/${contractId}/verification`}
              style={{
                background: "rgba(122,92,255,0.12)",
                border: "1px solid rgba(122,92,255,0.35)",
                borderRadius: 10,
                color: "#A78BFA",
                padding: "11px 16px",
                fontSize: 13,
                fontWeight: 600,
                textDecoration: "none",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
              aria-label="View verification report"
            >
              <span>Verification report (C29)</span>
              <ShieldCheck size={14} aria-hidden />
            </Link>

            <Link
              href={`/contracts/${contractId}/submit`}
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "#60A5FA",
                background: "rgba(0,102,255,0.1)",
                border: "1px solid rgba(0,102,255,0.25)",
                padding: "8px 16px",
                borderRadius: 20,
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              Submit New Revision →
            </Link>
          </div>

          {/* Submission Details Strip */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 16,
              background: "rgba(0,0,0,0.25)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: 14,
              padding: "16px 20px",
              marginBottom: 16,
            }}
          >
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", marginBottom: 4 }}>
                REPOSITORY URL
              </div>
              <a
                href={submission.repo_url}
                target="_blank"
                rel="noreferrer"
                style={{
                  color: "#60A5FA",
                  fontSize: 13,
                  fontWeight: 600,
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  wordBreak: "break-all",
                }}
              >
                <GitBranch size={13} /> {submission.repo_url} <ExternalLink size={12} />
              </a>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", marginBottom: 4 }}>
                COMMIT SHA & BRANCH
              </div>
              <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 13, color: "white", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ background: "rgba(255,255,255,0.08)", padding: "2px 8px", borderRadius: 6, fontSize: 11, color: "#93C5FD" }}>
                  {submission.branch}
                </span>
                <span title={submission.commit_sha}>
                  {submission.commit_sha.substring(0, 10)}...
                </span>
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", marginBottom: 4 }}>
                AGREED DEADLINE
              </div>
              <div style={{ fontSize: 13, color: "white", fontWeight: 600 }}>
                {new Date(submission.deadline).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
              </div>
            </div>
          </div>

          {/* Build Note */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", marginBottom: 6 }}>
              SELLER BUILD NOTE & VERIFICATION INSTRUCTIONS
            </div>
            <div
              style={{
                fontSize: 13,
                color: "var(--color-text-secondary)",
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.05)",
                borderRadius: 10,
                padding: "12px 16px",
                lineHeight: 1.5,
              }}
            >
              {submission.build_notes}
            </div>
          </div>
        </div>
      )}

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
              href={`/contracts/${contractId}/verification`}
              style={{
                background: "rgba(122,92,255,0.12)",
                border: "1px solid rgba(122,92,255,0.35)",
                borderRadius: 10,
                color: "#A78BFA",
                padding: "11px 16px",
                fontSize: 13,
                fontWeight: 600,
                textDecoration: "none",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
              aria-label="View verification report"
            >
              <span>Verification report (C29)</span>
              <ShieldCheck size={14} aria-hidden />
            </Link>

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

function ActivityTab({ submission }: { submission?: Submission | null }) {
  const [activeStageIndex, setActiveStageIndex] = useState<number>(4);
  const [isSimulating, setIsSimulating] = useState<boolean>(true);
  const [expandedStage, setExpandedStage] = useState<number | null>(null);
  const [eventLogs, setEventLogs] = useState<Array<{ time: string; text: string; type: "info" | "pass" | "warn" | "fail" }>>([
    { time: "14:30:00.120", text: "MicroVM sandbox initialized in gVisor container (rnd_gvisor_89f0).", type: "info" },
    { time: "14:30:01.440", text: `Cloned repo: ${submission?.repo_url || "https://github.com/freelancer/pactpal-storefront"} (branch: ${submission?.branch || "main"}).`, type: "pass" },
    { time: "14:30:02.100", text: `Pinned commit SHA: ${submission?.commit_sha?.substring(0, 8) || "a1b8c9d4"} — immutable verification lock active.`, type: "info" },
    { time: "14:30:45.320", text: "Clean container build finished in 38s (0 syntax errors).", type: "pass" },
    { time: "14:31:12.890", text: "Automated test suite: 42 assertions executed, 35 passed, 7 failed.", type: "warn" },
    { time: "14:31:30.400", text: "AST cheat-scan flagged hardcoded mock token in app/api/auth/route.ts:42 (HIGH severity).", type: "fail" },
    { time: "14:31:45.150", text: "Headless Chrome captured 1440x900 viewport; calculating visual pixel similarity vs Figma...", type: "info" },
  ]);

  const stagesData = [
    { 
      stage: "A", 
      label: "Intake & Git clone", 
      defaultTime: "14:30:01", 
      detail: submission 
        ? `Repo cloned: ${submission.repo_url} · Commit: ${submission.commit_sha.substring(0, 8)} · ${submission.is_late ? "⚠️ LATE SUBMISSION" : "✅ ON-TIME"}`
        : "Repo cloned: github.com/freelancer/pactpal-storefront · Commit: a1b8c9d4 · ✅ ON-TIME",
      logs: [
        "$ git init /sandbox/workspace",
        "$ git remote add origin " + (submission?.repo_url || "https://github.com/freelancer/pactpal-storefront"),
        "$ git fetch --depth=1 origin " + (submission?.branch || "main"),
        "$ git checkout " + (submission?.commit_sha || "a1b8c9d4e5f67890123456789abcdef012345678"),
        "HEAD is now at " + (submission?.commit_sha?.substring(0, 8) || "a1b8c9d4") + " feat: implement milestone features",
        "[OK] Workspace integrity verified. Network proxy isolated to sandbox localhost.",
      ]
    },
    { 
      stage: "B", 
      label: "Clean build in microVM", 
      defaultTime: "14:30:45", 
      detail: "Clean container build succeeded in 38s. Zero platform secrets exposed.",
      logs: [
        "$ npm install --frozen-lockfile",
        "added 342 packages in 12.4s",
        "$ npm run build",
        "> pactpal-storefront@0.1.0 build",
        "> next build",
        "✓ Creating an optimized production build",
        "✓ Compiled successfully in 18.2s",
        "[OK] Build artifact ready. Exit code: 0.",
      ]
    },
    { 
      stage: "C", 
      label: "Automated test suite", 
      defaultTime: "14:31:12", 
      detail: "Jest test runner: 42 assertions executed. 35 passed, 7 failed. Coverage: 88.5%.",
      logs: [
        "$ npm test -- --coverage --ci",
        "PASS tests/unit/landing.test.tsx",
        "PASS tests/unit/navigation.test.tsx",
        "PASS tests/unit/cart.test.tsx",
        "FAIL tests/unit/auth.test.tsx",
        "  ● Session Authentication › persists across browser refresh",
        "    Expected real JWT session token, received hardcoded string 'mock_jwt_token_123'",
        "Tests: 7 failed, 35 passed, 42 total",
        "Coverage: 88.5% Stmts, 84.2% Branch",
      ]
    },
    { 
      stage: "D", 
      label: "Cheat & loophole scan", 
      defaultTime: "14:31:30", 
      detail: "HIGH: Hardcoded mock token in /app/api/auth/route.ts:42 violates acceptance contract.", 
      severity: "HIGH",
      logs: [
        "$ ast-walker --scan-mocks --ast-rules ./rules.json",
        "[AST] Parsing 24 source TypeScript files into AST nodes...",
        "[AST WARNING] File: app/api/auth/route.ts:42",
        "  Rule: NO_HARDCODED_AUTH_RESPONSES",
        "  Snippet: return NextResponse.json({ token: 'mock_jwt_token_123' })",
        "  Verdict: Stubbed auth violates acceptance criteria #2.",
        "[AST] Scan finished with 1 HIGH finding.",
      ]
    },
    { 
      stage: "E", 
      label: "Visual diff (Figma vs Headless)", 
      defaultTime: "14:31:45", 
      detail: "Headless Chromium visual regression: 89.2% similarity (Figma threshold: 90.0%).",
      logs: [
        "$ chromium-headless --virtual-time-budget=5000 --window-size=1440,900 --screenshot",
        "[PIXELMATCH] Target: figma-specs/desktop_v2.png",
        "[PIXELMATCH] Actual: artifacts/renders/viewport_1440x900.png",
        "[PIXELMATCH] Total pixels: 1,296,000",
        "[PIXELMATCH] Mismatched pixels: 139,968 (10.8% delta)",
        "[PIXELMATCH] Similarity Score: 89.2% vs Threshold 90.0%",
        "[DIFF] Delta concentrated around header padding and button font-size.",
      ]
    },
    { 
      stage: "F", 
      label: "QA multimodal report & decision", 
      defaultTime: "14:32:00", 
      detail: "Evaluation complete. Recommended settlement: $1,125 USD released, $375 USD refunded.",
      logs: [
        "[DECISION ENGINE] Merging stages A through E into unified JSON report...",
        "[ALLOCATION] Feature 01: PASSED ($375 released)",
        "[ALLOCATION] Feature 02: FAILED ($300 held/refunded)",
        "[ALLOCATION] Feature 03: PASSED ($450 released)",
        "[ALLOCATION] Feature 04: PASSED ($300 released)",
        "[SUMMARY] Total released: $1,125 USD | Total refunded: $375 USD",
        "[STATUS] State transitioning: VERIFYING -> DECISION",
      ]
    },
  ];

  // Live ticker simulation (Feed updates as the Referee works)
  useEffect(() => {
    if (!isSimulating) return;

    const timer = setInterval(() => {
      setActiveStageIndex((prev) => {
        if (prev < stagesData.length - 1) {
          const next = prev + 1;
          const nowStr = new Date().toLocaleTimeString() + "." + Math.floor(Math.random() * 900 + 100);
          setEventLogs((logs) => [
            ...logs,
            {
              time: nowStr,
              text: `Stage ${stagesData[next].stage} (${stagesData[next].label}) active — executing container tasks...`,
              type: "info",
            },
          ]);
          return next;
        } else {
          return prev;
        }
      });
    }, 4000);

    return () => clearInterval(timer);
  }, [isSimulating, stagesData]);

  const handleRestartSimulation = () => {
    setActiveStageIndex(0);
    setIsSimulating(true);
    setEventLogs([
      {
        time: new Date().toLocaleTimeString() + ".001",
        text: "AI Referee simulation restarted by user. Booting container microVM...",
        type: "info",
      },
      {
        time: new Date().toLocaleTimeString() + ".250",
        text: "Stage A: Intake & Git clone started for commit " + (submission?.commit_sha?.substring(0, 8) || "a1b8c9d4"),
        type: "pass",
      },
    ]);
  };

  const handleFastForward = () => {
    setActiveStageIndex(5);
    setIsSimulating(false);
    setEventLogs((logs) => [
      ...logs,
      {
        time: new Date().toLocaleTimeString() + ".999",
        text: "Fast-forward: All 6 stages completed. Payout settlement proposal ready.",
        type: "pass",
      },
    ]);
  };

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
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 24,
        overflow: "hidden",
      }}
      role="log"
      aria-label="Verification live activity feed"
      aria-live="polite"
    >
      {/* Top Controls Bar */}
      <div
        style={{
          padding: "18px 28px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 14,
          background: "rgba(0,0,0,0.2)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: isSimulating ? "#4CAF50" : "#FF9800",
              boxShadow: isSimulating ? "0 0 10px #4CAF50" : "none",
            }}
          />
          <span style={{ fontWeight: 800, fontSize: 15, color: "white" }}>
            Live Verification Pipeline — Stages A to F (C33)
          </span>
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              background: isSimulating ? "rgba(76,175,80,0.15)" : "rgba(255,152,0,0.15)",
              color: isSimulating ? "#81C784" : "#FFB74D",
              padding: "2px 8px",
              borderRadius: 20,
            }}
          >
            {isSimulating ? "FEED STREAMING LIVE" : "FEED PAUSED"}
          </span>
        </div>

        {/* Live Simulation Controls */}
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            onClick={() => setIsSimulating(!isSimulating)}
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.15)",
              color: "white",
              padding: "6px 14px",
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            {isSimulating ? <Pause size={12} /> : <Play size={12} />}
            {isSimulating ? "Pause Feed" : "Resume Feed"}
          </button>

          <button
            onClick={handleRestartSimulation}
            style={{
              background: "rgba(0,102,255,0.12)",
              border: "1px solid rgba(0,102,255,0.3)",
              color: "#60A5FA",
              padding: "6px 14px",
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <RotateCcw size={12} /> Re-run Simulation
          </button>

          <button
            onClick={handleFastForward}
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.15)",
              color: "white",
              padding: "6px 14px",
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Zap size={12} /> Fast Forward
          </button>
        </div>
      </div>

      {/* Stages Vertical Timeline */}
      <div style={{ padding: "28px", display: "flex", flexDirection: "column", gap: 0 }}>
        {stagesData.map((s, i) => {
          let status: "passed" | "failed" | "running" | "pending";
          if (i < activeStageIndex) {
            status = i === 3 ? "failed" : "passed";
          } else if (i === activeStageIndex) {
            status = isSimulating ? "running" : (i === 3 ? "failed" : "passed");
          } else {
            status = "pending";
          }

          const isExpanded = expandedStage === i;

          return (
            <div
              key={i}
              style={{
                display: "flex",
                gap: 20,
                paddingBottom: i < stagesData.length - 1 ? 28 : 12,
                position: "relative",
              }}
              role="listitem"
              aria-label={`Stage ${s.stage}: ${s.label} — ${status}`}
            >
              {/* Connector */}
              {i < stagesData.length - 1 && (
                <div
                  style={{
                    position: "absolute",
                    left: 20,
                    top: 42,
                    bottom: 0,
                    width: 2,
                    background: status === "passed"
                      ? "rgba(76, 175, 80, 0.4)"
                      : status === "running"
                      ? "rgba(0, 102, 255, 0.4)"
                      : "rgba(255, 255, 255, 0.08)",
                  }}
                  aria-hidden
                />
              )}

              {/* Stage Dot / Badge */}
              <div
                style={{
                  width: 42,
                  height: 42,
                  borderRadius: "50%",
                  background: `${stageColors[status]}18`,
                  border: `2px solid ${stageColors[status]}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  fontWeight: 900,
                  fontSize: 14,
                  color: stageColors[status],
                  fontFamily: "JetBrains Mono, monospace",
                  boxShadow: status === "running" ? `0 0 20px ${stageColors[status]}60` : "none",
                  animation: status === "running" ? "pulse 1.5s infinite" : "none",
                }}
                aria-hidden
              >
                {status === "running" ? "⏳" : s.stage}
              </div>

              {/* Stage Content */}
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8, marginBottom: 4 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontWeight: 700, fontSize: 15, color: "white" }}>
                      Stage {s.stage}: {s.label}
                    </span>
                    {s.severity && (
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 800,
                          color: "#F44336",
                          background: "rgba(244,67,54,0.15)",
                          border: "1px solid rgba(244,67,54,0.3)",
                          borderRadius: 50,
                          padding: "2px 8px",
                        }}
                      >
                        {s.severity} SEVERITY
                      </span>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <span style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: "var(--color-text-muted)" }}>
                      {s.defaultTime}
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 800,
                        letterSpacing: "0.06em",
                        color: stageColors[status],
                        textTransform: "uppercase",
                      }}
                    >
                      {status}
                    </span>
                  </div>
                </div>

                <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5, margin: "0 0 8px" }}>
                  {s.detail}
                </p>

                {/* Stdout Console Logs Expandable Drawer */}
                <button
                  onClick={() => setExpandedStage(isExpanded ? null : i)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#60A5FA",
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                    padding: 0,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <TerminalIcon size={12} /> {isExpanded ? "Hide console stdout ▲" : "View console stdout ▼"}
                </button>

                {isExpanded && (
                  <pre
                    style={{
                      background: "rgba(0, 0, 0, 0.45)",
                      border: "1px solid rgba(255,255,255,0.06)",
                      borderRadius: 10,
                      padding: "12px 16px",
                      color: "#93C5FD",
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 12,
                      lineHeight: 1.6,
                      marginTop: 8,
                      overflowX: "auto",
                    }}
                  >
                    {s.logs.join("\n")}
                  </pre>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Live Event Log Stream (C33 Core Requirement) */}
      <div
        style={{
          borderTop: "1px solid rgba(255,255,255,0.08)",
          background: "rgba(0,0,0,0.35)",
          padding: "20px 28px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em" }}>
            REAL-TIME EVENT TICKER LOG
          </span>
          <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
            {eventLogs.length} events logged
          </span>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            maxHeight: 160,
            overflowY: "auto",
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 12,
          }}
        >
          {eventLogs.slice(-6).map((log, lIdx) => (
            <div key={lIdx} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              <span style={{ color: "var(--color-text-muted)", flexShrink: 0 }}>[{log.time}]</span>
              <span
                style={{
                  color: log.type === "pass" ? "#81C784" : log.type === "fail" ? "#EF5350" : log.type === "warn" ? "#FFB74D" : "#93C5FD",
                }}
              >
                {log.text}
              </span>
            </div>
          ))}
        </div>
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

