"use client";
import { useState, useEffect, useRef } from "react";
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
  Sparkles,
  Send,
  Bot,
  User,
  CheckCheck,
  RefreshCw,
  Check,
  Copy
} from "lucide-react";
import { mockApi, Contract, HoldInfo, Feature, Submission, ContractStatus, CONTRACT_STATES_META, ChatMessage } from "@/lib/mockApi";
import { getCurrentUser, UserProfile, toUUID } from "@/lib/supabase";
import { backendClient } from "@/lib/backendClient";

function isUserHirer(c: Contract | null, user: UserProfile | null): boolean {
  if (!c || !user) return false;
  const userEmail = (user.email || "").trim().toLowerCase();
  const userName = (user.name || "").trim().toLowerCase();
  const userId = user.id || "";
  const userUuid = toUUID(userId);

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

  if (userId && buyerId && (userId === buyerId || userUuid === buyerId)) return true;
  if (userEmail && buyerEmail && userEmail === buyerEmail) return true;
  if (userName && buyerName && (userName === buyerName || userName.includes(buyerName) || buyerName.includes(userName))) return true;
  return false;
}

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
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [holdInfo, setHoldInfo] = useState<HoldInfo | null>(null);
  const [releaseModalOpen, setReleaseModalOpen] = useState(false);
  const [isReleased, setIsReleased] = useState(false);
  const [simulatedStatus, setSimulatedStatus] = useState<ContractStatus | null>(null);
  const [deadlineAlert, setDeadlineAlert] = useState<string | null>(null);

  useEffect(() => {
    setCurrentUser(getCurrentUser());
    let isMounted = true;

    async function loadContractData() {
      try {
        const live = await backendClient.getContract(contractId);
        if (live && isMounted) {
          setContract(live as unknown as Contract);
          setHoldInfo(mockApi.getHoldInfo(live.id));
          return;
        }
      } catch (err) {
        console.warn("Failed to load contract from Supabase:", err);
      }
      const loaded = mockApi.getContract(contractId) || mockApi.getContracts()[0];
      if (loaded && isMounted) {
        setContract(loaded);
        setHoldInfo(mockApi.getHoldInfo(loaded.id));
      }
    }

    loadContractData();

    const handleUpdate = () => loadContractData();
    window.addEventListener("pactpal_contract_updated", handleUpdate);
    return () => {
      isMounted = false;
      window.removeEventListener("pactpal_contract_updated", handleUpdate);
    };
  }, [contractId]);

  const activeContract = contract || mockApi.getContracts()[0];
  const isViewerHirer = isUserHirer(activeContract, currentUser);
  const currentStatus: ContractStatus = simulatedStatus || (isReleased ? "SETTLED" : (activeContract.status || "VERIFYING"));
  const meta = CONTRACT_STATES_META[currentStatus] || CONTRACT_STATES_META["VERIFYING"];

  const handleSimulateStatus = (status: ContractStatus) => {
    setSimulatedStatus(status);
    mockApi.updateContractStatus(activeContract.id, status);
    if (contract) {
      setContract({ ...contract, status });
    }
  };

  const handleAdminSimulateDeadline = () => {
    const res = mockApi.simulateDeadlineWatcher(activeContract.id);
    if (res) {
      setSimulatedStatus("SETTLED");
      setContract({ ...res.contract });
      setDeadlineAlert(` [DEADLINE WATCHER FIRED ] Simulated deadline elapsed! Automated final verification completed. $${res.payoutAmount} USD disbursed to freelancer, $${res.refundAmount} USD refunded to hirer. Status transitioned to SETTLED.`);
      setTimeout(() => setDeadlineAlert(null), 7000);
    }
  };

  const features = activeContract.features || [];
  const passedAmount = features
    .filter((f) => f.status.toUpperCase() === "PASSED")
    .reduce((s, f) => s + (f.allocated_amount || 0), 0);

  const daysLeft = holdInfo?.days_remaining ?? 18;

  const handleConfirmDisburse = async () => {
    await backendClient.settleContract(activeContract.id, passedAmount);
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
                Review & Counter →
              </Link>
            ) : activeContract.status === "SIGNED" ? (
              isViewerHirer ? (
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
                  Authorize Escrow Hold with PayPal →
                </Link>
              ) : (
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    background: "rgba(255,152,0,0.12)",
                    border: "1px solid rgba(255,152,0,0.35)",
                    color: "#FFB74D",
                    borderRadius: 50,
                    padding: "10px 20px",
                    fontSize: 13,
                    fontWeight: 700,
                  }}
                >
                  <Clock size={15} /> Awaiting Hirer Escrow Deposit
                </div>
              )
            ) : activeContract.status === "DISPUTE" ? (
              <Link
                href={`/contracts/${activeContract.id}/dispute`}
                style={{
                  background: "linear-gradient(135deg, #EF4444, #DC2626)",
                  borderRadius: 50,
                  color: "white",
                  padding: "12px 24px",
                  fontSize: 14,
                  fontWeight: 700,
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  boxShadow: "0 0 20px rgba(239,68,68,0.4)",
                }}
              >
                Dispute Room 
              </Link>
            ) : activeContract.status === "SETTLED" ? (
              <Link
                href={`/contracts/${activeContract.id}/receipt`}
                style={{
                  background: "linear-gradient(135deg, #10B981, #059669)",
                  borderRadius: 50,
                  color: "white",
                  padding: "12px 24px",
                  fontSize: 14,
                  fontWeight: 700,
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  boxShadow: "0 0 20px rgba(16,185,129,0.4)",
                }}
              >
                Settlement Receipt 
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
                Review Checklist 
              </Link>
            )}
          </div>
        </div>

        {/* The 10 Contract Lifecycle State Stepper (Lifecycle Management) */}
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
                Contract Lifecycle Stepper
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

              {/* Admin Simulate Deadline Button */}
              <button
                onClick={handleAdminSimulateDeadline}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "5px 12px",
                  borderRadius: 10,
                  background: "linear-gradient(135deg, rgba(245,158,11,0.2) 0%, rgba(239,68,68,0.2) 100%)",
                  border: "1px solid rgba(245,158,11,0.5)",
                  color: "#FBBF24",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                title="Admin: Simulate deadline elapsed (triggers deadline watcher, final verification & partial payout)"
              >
                <Zap size={13} color="#FBBF24" />
                Simulate Deadline (Admin Simulation)
              </button>
            </div>
          </div>

          {/* Deadline Alert Banner */}
          {deadlineAlert && (
            <div
              style={{
                marginBottom: 16,
                padding: "12px 18px",
                borderRadius: 12,
                background: "rgba(245,158,11,0.15)",
                border: "1px solid rgba(245,158,11,0.45)",
                color: "#FDE68A",
                fontSize: 13,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: 10,
              }}
            >
              <Zap size={16} color="#FBBF24" />
              <span>{deadlineAlert}</span>
            </div>
          )}

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
                <strong style={{ color: "white", fontSize: 15 }}>Freelancer Review & Checklist Confirmation</strong>
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
              Open Terms Review Page →
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
                <strong style={{ color: "white", fontSize: 15 }}>
                  {isViewerHirer ? "Escrow Funding Required" : "Awaiting Hirer's Escrow Funding"}
                </strong>
                <p style={{ color: "var(--color-text-secondary)", fontSize: 13, margin: 0 }}>
                  {isViewerHirer
                    ? "Both parties have signed! You must now authorize the 29-day PayPal hold to activate escrow."
                    : "Both parties have signed! Waiting for the hirer to authorize the 29-day PayPal escrow deposit before project work starts."}
                </p>
              </div>
            </div>
            {isViewerHirer && (
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
            )}
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
              <span style={{ fontSize: 24 }}></span>
              <div>
                <strong style={{ color: "white", fontSize: 15 }}>AI Referee Verification Results</strong>
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
              View Verification Results →
            </Link>
          </div>
        )}

        {/* Dispute Notification Banner */}
        {activeContract.status === "DISPUTE" && (
          <div
            style={{
              padding: "16px 24px",
              borderRadius: 16,
              background: "linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(245,158,11,0.1) 100%)",
              border: "1px solid rgba(239,68,68,0.4)",
              marginBottom: 24,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 24 }}></span>
              <div>
                <strong style={{ color: "white", fontSize: 15 }}>Dispute Mediation Active (Funds Stay Held)</strong>
                <p style={{ color: "var(--color-text-secondary)", fontSize: 13, margin: 0 }}>
                  Automated AST cheat scan flagged Feature 2. Review checklist, verification report, provisional receipt, and negotiation chat.
                </p>
              </div>
            </div>
            <Link
              href={`/contracts/${activeContract.id}/dispute`}
              style={{
                background: "linear-gradient(135deg, #EF4444, #F59E0B)",
                color: "white",
                padding: "10px 22px",
                borderRadius: 30,
                fontSize: 13,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 0 20px rgba(239,68,68,0.3)",
              }}
            >
              Open Dispute Room →
            </Link>
          </div>
        )}

        {/* Settled Receipt Notification Banner */}
        {activeContract.status === "SETTLED" && (
          <div
            style={{
              padding: "16px 24px",
              borderRadius: 16,
              background: "linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(0,102,255,0.1) 100%)",
              border: "1px solid rgba(16,185,129,0.4)",
              marginBottom: 24,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 24 }}></span>
              <div>
                <strong style={{ color: "white", fontSize: 15 }}>Cryptographic Settlement Receipt Sealed</strong>
                <p style={{ color: "var(--color-text-secondary)", fontSize: 13, margin: 0 }}>
                  This contract has concluded. View the full proof-of-work summary, SHA-256 hash, timestamps, and evidence links.
                </p>
              </div>
            </div>
            <Link
              href={`/contracts/${activeContract.id}/receipt`}
              style={{
                background: "linear-gradient(135deg, #10B981, #00A3E0)",
                color: "white",
                padding: "10px 22px",
                borderRadius: 30,
                fontSize: 13,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 0 20px rgba(16,185,129,0.3)",
              }}
            >
              Open Official Receipt Page →
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
          {tab === "gantt"     && <GanttTab contract={activeContract} features={features} />}
          {tab === "chat"      && <ChatTab contract={activeContract} features={features} />}
          {tab === "activity"  && <ActivityTab submission={activeContract.submission} />}
          {tab === "receipt"   && <ReceiptTab contract={activeContract} total={activeContract.total_amount} passedAmount={passedAmount} features={features} />}
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
      {/* Latest Seller Submission Card (Core Requirement) */}
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
              <span style={{ fontSize: 28 }}></span>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <h3 style={{ fontSize: 17, fontWeight: 800, color: "white", margin: 0 }}>
                    Freelancer Submission (Version {submission.version_number})
                  </h3>
                  {/* Late Flag Badge */}
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
              <span>Verification report</span>
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
              FREELANCER BUILD NOTE & VERIFICATION INSTRUCTIONS
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
              <span style={{ color: "var(--color-text-secondary)" }}>Refunded to hirer</span>
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
              <span>Verification report</span>
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

function GanttTab({
  contract,
  features = [],
}: {
  contract?: Contract | null;
  features?: Feature[];
}) {
  const activeContract = contract || mockApi.getContracts()[0];
  const contractId = activeContract?.id || "pct_099e77";

  const [zoomLevel, setZoomLevel] = useState<"Day" | "Week" | "Month">("Week");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [tasksList, setTasksList] = useState<Feature[]>(activeContract?.features || features);
  const [changeToast, setChangeToast] = useState<string | null>(null);
  const [hoveredTask, setHoveredTask] = useState<string | null>(null);

  useEffect(() => {
    const updated = mockApi.getContract(contractId);
    if (updated?.features) {
      setTasksList(updated.features);
    }
  }, [contractId]);

  const hasAcceptedChange = tasksList.some((f) => f.title.includes("Dark Mode"));

  const handleToggleScopeChange = () => {
    if (hasAcceptedChange) {
      mockApi.removeScopeChange(contractId);
      const updated = mockApi.getContract(contractId);
      setTasksList(updated?.features || []);
      setChangeToast("Simulated scope change removed from Gantt timeline.");
    } else {
      mockApi.acceptScopeChange(contractId, {
        title: "[CR-01] Dark Mode Theme Support (Accepted Change)",
        price_weight: 10,
        allocated_amount: 150,
      });
      const updated = mockApi.getContract(contractId);
      setTasksList(updated?.features || []);
      setChangeToast("✓ Scope change accepted! Task '[CR-01] Dark Mode Theme Support' automatically appeared in Bryntum Gantt.");
    }
    setTimeout(() => setChangeToast(null), 5000);
  };

  const filteredTasks = tasksList.filter((t) => {
    if (statusFilter === "ALL") return true;
    if (statusFilter === "PASSED") return t.status === "PASSED";
    if (statusFilter === "FAILED") return t.status === "FAILED";
    if (statusFilter === "PENDING") return t.status === "PENDING";
    return true;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "PASSED":
        return "#4CAF50";
      case "FAILED":
        return "#F44336";
      case "VERIFYING":
      case "IN_PROGRESS":
        return "#0066FF";
      default:
        return "#7C89A8";
    }
  };

  // Schedule task widths and start offsets for Gantt rendering
  const taskScheduleMap: Record<string, { startPct: number; widthPct: number; days: string }> = {
    feat_01: { startPct: 4, widthPct: 24, days: "Nov 01 - Nov 07" },
    feat_02: { startPct: 20, widthPct: 22, days: "Nov 05 - Nov 11" },
    feat_03: { startPct: 36, widthPct: 28, days: "Nov 09 - Nov 17" },
    feat_04: { startPct: 56, widthPct: 26, days: "Nov 14 - Nov 21" },
  };

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 24,
        overflow: "hidden",
        minHeight: 560,
        boxShadow: "0 0 60px rgba(0,102,255,0.06)",
        fontFamily: "Inter, sans-serif",
      }}
      id="bryntum-gantt"
      role="region"
      aria-label="Bryntum Gantt Chart with status colors, hold-expiry and deadline milestones"
    >
      {/* Scope Change Alert Toast */}
      {changeToast && (
        <div
          style={{
            padding: "12px 20px",
            background: "linear-gradient(135deg, rgba(16,185,129,0.2) 0%, rgba(0,102,255,0.15) 100%)",
            borderBottom: "1px solid rgba(16,185,129,0.35)",
            color: "#A7F3D0",
            fontSize: 13,
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <Sparkles size={16} color="#34D399" />
          <span>{changeToast}</span>
        </div>
      )}

      {/* Bryntum Gantt Toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "18px 24px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          background: "rgba(255,255,255,0.015)",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Clock size={16} color="#00A3E0" />
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "white", margin: 0 }}>
              Bryntum Gantt Timeline
            </h3>
            <span
              style={{
                fontSize: 11,
                padding: "2px 8px",
                borderRadius: 999,
                background: "rgba(0,102,255,0.15)",
                color: "#60A5FA",
                border: "1px solid rgba(0,102,255,0.3)",
                fontWeight: 600,
              }}
            >
              #bryntum-gantt · </span>
          </div>
          <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: "3px 0 0" }}>
            Feature milestone tasks, 29-day hold expiry, and delivery deadline
          </p>
        </div>

        {/* Action Controls & Change Request Simulator (Done When) */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          {/* Zoom controls */}
          <div
            style={{
              display: "inline-flex",
              borderRadius: 8,
              background: "rgba(255,255,255,0.04)",
              padding: 2,
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            {(["Day", "Week", "Month"] as const).map((z) => (
              <button
                key={z}
                onClick={() => setZoomLevel(z)}
                style={{
                  padding: "4px 10px",
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 600,
                  border: "none",
                  cursor: "pointer",
                  background: zoomLevel === z ? "#0066FF" : "transparent",
                  color: zoomLevel === z ? "white" : "var(--color-text-muted)",
                }}
              >
                {z}
              </button>
            ))}
          </div>

          {/* Status filter pills */}
          <div style={{ display: "flex", gap: 5 }}>
            {[
              { id: "ALL", label: "All" },
              { id: "PASSED", label: "Passed (Green)" },
              { id: "FAILED", label: "Failed (Red)" },
              { id: "PENDING", label: "Pending" },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setStatusFilter(f.id)}
                style={{
                  padding: "4px 9px",
                  borderRadius: 999,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: "pointer",
                  border: statusFilter === f.id ? "1px solid #00A3E0" : "1px solid rgba(255,255,255,0.08)",
                  background: statusFilter === f.id ? "rgba(0,163,224,0.18)" : "rgba(255,255,255,0.03)",
                  color: statusFilter === f.id ? "white" : "var(--color-text-muted)",
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Requirement: Accept Change Request -> New task appears automatically */}
          <button
            onClick={handleToggleScopeChange}
            style={{
              padding: "6px 14px",
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: hasAcceptedChange
                ? "rgba(16,185,129,0.18)"
                : "linear-gradient(135deg, #FF9800, #F57C00)",
              border: hasAcceptedChange ? "1px solid rgba(16,185,129,0.4)" : "none",
              color: hasAcceptedChange ? "#34D399" : "white",
              boxShadow: hasAcceptedChange ? "none" : "0 0 16px rgba(255,152,0,0.3)",
              transition: "all 0.2s ease",
            }}
            title=": Simulate an accepted mini-agreement change request to see new task appear automatically in Gantt"
          >
            {hasAcceptedChange ? (
              <>
                <CheckCircle size={13} color="#34D399" />
                <span>Scope Change #1 Accepted (Click to Reset)</span>
              </>
            ) : (
              <>
                <Zap size={13} />
                <span>Accept Scope Change #1 (+10% Task)</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Gantt Dual-Pane Grid Layout (Task Table Left, Timeline Right) */}
      <div style={{ display: "grid", gridTemplateColumns: "330px 1fr", minHeight: 440 }}>
        {/* Left Column: Task Checklist Columns */}
        <div style={{ borderRight: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.01)" }}>
          {/* Table Header */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 50px 60px 70px",
              padding: "12px 16px",
              borderBottom: "1px solid rgba(255,255,255,0.08)",
              fontSize: 11,
              fontWeight: 700,
              color: "var(--color-text-muted)",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}
          >
            <div>Task Name</div>
            <div style={{ textAlign: "right" }}>Wt</div>
            <div style={{ textAlign: "right" }}>Amt</div>
            <div style={{ textAlign: "right" }}>Status</div>
          </div>

          {/* Task Rows */}
          <div style={{ display: "flex", flexDirection: "column" }}>
            {filteredTasks.map((t, idx) => {
              const isAcceptedChange = t.title.includes("Dark Mode");
              return (
                <div
                  key={t.id || idx}
                  onMouseEnter={() => setHoveredTask(t.id)}
                  onMouseLeave={() => setHoveredTask(null)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 50px 60px 70px",
                    padding: "14px 16px",
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                    fontSize: 12,
                    background: hoveredTask === t.id
                      ? "rgba(0,102,255,0.08)"
                      : isAcceptedChange
                      ? "rgba(255,152,0,0.06)"
                      : "transparent",
                    transition: "background 0.15s ease",
                    alignItems: "center",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 7, overflow: "hidden" }}>
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: getStatusColor(t.status),
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        fontWeight: 600,
                        color: isAcceptedChange ? "#FDBA74" : "white",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                      title={t.title}
                    >
                      {t.title}
                    </span>
                  </div>
                  <div style={{ textAlign: "right", color: "var(--color-text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                    {t.price_weight}%
                  </div>
                  <div style={{ textAlign: "right", color: "white", fontFamily: "JetBrains Mono, monospace", fontWeight: 600 }}>
                    ${t.allocated_amount}
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        padding: "2px 6px",
                        borderRadius: 4,
                        background: `${getStatusColor(t.status)}22`,
                        color: getStatusColor(t.status),
                        border: `1px solid ${getStatusColor(t.status)}55`,
                      }}
                    >
                      {t.status}
                    </span>
                  </div>
                </div>
              );
            })}

            {/* Hold-Expiry Milestone Row in Table */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 50px 60px 70px",
                padding: "14px 16px",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
                fontSize: 12,
                background: "rgba(255,152,0,0.04)",
                alignItems: "center",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#FBBF24", fontWeight: 700 }}>
                <span>◆</span>
                <span>29-Day PayPal Hold Expiry</span>
              </div>
              <div style={{ textAlign: "right", color: "var(--color-text-muted)" }}>-</div>
              <div style={{ textAlign: "right", color: "#FBBF24", fontFamily: "JetBrains Mono, monospace", fontSize: 11 }}>Hold</div>
              <div style={{ textAlign: "right" }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: "#FBBF24", padding: "2px 6px", borderRadius: 4, background: "rgba(255,152,0,0.15)" }}>
                  MILESTONE
                </span>
              </div>
            </div>

            {/* Deadline Milestone Row in Table */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 50px 60px 70px",
                padding: "14px 16px",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
                fontSize: 12,
                background: "rgba(168,85,247,0.04)",
                alignItems: "center",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#C084FC", fontWeight: 700 }}>
                <span>◆</span>
                <span>Final Deliverable Deadline</span>
              </div>
              <div style={{ textAlign: "right", color: "var(--color-text-muted)" }}>-</div>
              <div style={{ textAlign: "right", color: "#C084FC", fontFamily: "JetBrains Mono, monospace", fontSize: 11 }}>Due</div>
              <div style={{ textAlign: "right" }}>
                <span style={{ fontSize: 10, fontWeight: 700, color: "#C084FC", padding: "2px 6px", borderRadius: 4, background: "rgba(168,85,247,0.15)" }}>
                  DEADLINE
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Bryntum Timeline Calendar Grid */}
        <div style={{ display: "flex", flexDirection: "column", position: "relative", overflowX: "auto" }}>
          {/* Timeline Date Header Scale */}
          <div
            style={{
              height: 40,
              borderBottom: "1px solid rgba(255,255,255,0.08)",
              display: "grid",
              gridTemplateColumns: "repeat(6, 1fr)",
              background: "rgba(255,255,255,0.02)",
              fontSize: 11,
              fontWeight: 700,
              color: "var(--color-text-muted)",
              letterSpacing: "0.06em",
            }}
          >
            {["Nov 01 - 05", "Nov 06 - 10", "Nov 11 - 15", "Nov 16 - 20", "Nov 21 - 25", "Nov 26 - 30"].map((w, i) => (
              <div
                key={i}
                style={{
                  padding: "10px 12px",
                  borderRight: i < 5 ? "1px solid rgba(255,255,255,0.05)" : "none",
                }}
              >
                {w}
              </div>
            ))}
          </div>

          {/* Timeline Grid Body */}
          <div style={{ flex: 1, position: "relative", minHeight: 380 }}>
            {/* Background vertical grid columns */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "grid",
                gridTemplateColumns: "repeat(6, 1fr)",
                pointerEvents: "none",
              }}
            >
              {[0, 1, 2, 3, 4, 5].map((c) => (
                <div
                  key={c}
                  style={{
                    borderRight: c < 5 ? "1px dashed rgba(255,255,255,0.04)" : "none",
                    height: "100%",
                  }}
                />
              ))}
            </div>

            {/* Vertical "TODAY" Line */}
            <div
              style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                left: "42%",
                width: 2,
                background: "#0066FF",
                boxShadow: "0 0 12px #0066FF",
                zIndex: 10,
                pointerEvents: "none",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: -20,
                  left: "50%",
                  transform: "translateX(-50%)",
                  background: "#0066FF",
                  color: "white",
                  fontSize: 9,
                  fontWeight: 800,
                  padding: "1px 6px",
                  borderRadius: 999,
                  letterSpacing: "0.05em",
                }}
              >
                TODAY
              </div>
            </div>

            {/* Task Gantt Bars */}
            <div style={{ display: "flex", flexDirection: "column", position: "relative", zIndex: 2 }}>
              {filteredTasks.map((t, idx) => {
                const isAcceptedChange = t.title.includes("Dark Mode");
                const defaultSchedule = taskScheduleMap[t.id] || {
                  startPct: 40 + idx * 8,
                  widthPct: 22,
                  days: "Nov 15 - Nov 22",
                };
                const schedule = isAcceptedChange
                  ? { startPct: 62, widthPct: 24, days: "Nov 18 - Nov 24" }
                  : defaultSchedule;

                return (
                  <div
                    key={t.id || idx}
                    onMouseEnter={() => setHoveredTask(t.id)}
                    onMouseLeave={() => setHoveredTask(null)}
                    style={{
                      height: 48,
                      position: "relative",
                      display: "flex",
                      alignItems: "center",
                      borderBottom: "1px solid rgba(255,255,255,0.04)",
                    }}
                  >
                    {/* Gantt Bar */}
                    <div
                      style={{
                        position: "absolute",
                        left: `${schedule.startPct}%`,
                        width: `${schedule.widthPct}%`,
                        height: 28,
                        borderRadius: 8,
                        background: getStatusColor(t.status),
                        boxShadow: `0 0 16px ${getStatusColor(t.status)}55`,
                        display: "flex",
                        alignItems: "center",
                        padding: "0 12px",
                        color: "white",
                        fontSize: 11,
                        fontWeight: 700,
                        cursor: "pointer",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        transform: hoveredTask === t.id ? "scaleY(1.08)" : "none",
                        transition: "all 0.15s ease",
                      }}
                      title={`${t.title} (${t.price_weight}% · $${t.allocated_amount}) · Status: ${t.status}`}
                    >
                      <span style={{ marginRight: 6 }}>
                        {t.status === "PASSED" ? "✓" : t.status === "FAILED" ? "✗" : "○"}
                      </span>
                      <span>{t.title}</span>
                      <span style={{ marginLeft: "auto", opacity: 0.85, fontSize: 10 }}>
                        {t.price_weight}%
                      </span>
                    </div>

                    {/* Dependency line connecting preceding task to this one if accepted change */}
                    {isAcceptedChange && (
                      <div
                        style={{
                          position: "absolute",
                          left: "58%",
                          top: 0,
                          width: "4%",
                          height: 24,
                          borderLeft: "2px solid #F59E0B",
                          borderBottom: "2px solid #F59E0B",
                          pointerEvents: "none",
                        }}
                      />
                    )}
                  </div>
                );
              })}

              {/* 29-Day PayPal Hold Expiry Milestone Marker */}
              <div
                style={{
                  height: 48,
                  position: "relative",
                  display: "flex",
                  alignItems: "center",
                  borderBottom: "1px solid rgba(255,255,255,0.04)",
                  background: "rgba(255,152,0,0.02)",
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    left: "92%",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    transform: "translateX(-50%)",
                    cursor: "pointer",
                  }}
                  title="29-Day PayPal Escrow Authorization Expiry Point "
                >
                  <div
                    style={{
                      width: 18,
                      height: 18,
                      background: "#FF9800",
                      transform: "rotate(45deg)",
                      boxShadow: "0 0 16px rgba(255,152,0,0.8)",
                      borderRadius: 3,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 800,
                      color: "#FBBF24",
                      whiteSpace: "nowrap",
                      background: "rgba(0,0,0,0.6)",
                      padding: "2px 8px",
                      borderRadius: 6,
                      border: "1px solid rgba(255,152,0,0.3)",
                    }}
                  >
                    ◆ 29-Day Hold Expiry
                  </span>
                </div>
              </div>

              {/* Final Delivery Deadline Milestone Marker */}
              <div
                style={{
                  height: 48,
                  position: "relative",
                  display: "flex",
                  alignItems: "center",
                  borderBottom: "1px solid rgba(255,255,255,0.04)",
                  background: "rgba(168,85,247,0.02)",
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    left: "50%",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    transform: "translateX(-50%)",
                    cursor: "pointer",
                  }}
                  title="Final Deliverable Submission Deadline "
                >
                  <div
                    style={{
                      width: 18,
                      height: 18,
                      background: "#A855F7",
                      transform: "rotate(45deg)",
                      boxShadow: "0 0 16px rgba(168,85,247,0.8)",
                      borderRadius: 3,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 800,
                      color: "#C084FC",
                      whiteSpace: "nowrap",
                      background: "rgba(0,0,0,0.6)",
                      padding: "2px 8px",
                      borderRadius: 6,
                      border: "1px solid rgba(168,85,247,0.3)",
                    }}
                  >
                    ◆ Contract Deadline
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bryntum Gantt Status Legend & Footer Bar */}
      <div
        style={{
          padding: "16px 24px",
          borderTop: "1px solid rgba(255,255,255,0.08)",
          background: "rgba(255,255,255,0.015)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
          fontSize: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <span style={{ fontWeight: 700, color: "var(--color-text-muted)" }}>Legend:</span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: "#4CAF50" }} />
            <span style={{ color: "white" }}>Passed</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: "#F44336" }} />
            <span style={{ color: "white" }}>Failed</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: "#0066FF" }} />
            <span style={{ color: "white" }}>In Progress</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: "#7C89A8" }} />
            <span style={{ color: "var(--color-text-muted)" }}>Pending</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ color: "#FF9800", fontWeight: 800 }}>◆</span>
            <span style={{ color: "#FBBF24" }}>Hold Expiry (29-Day)</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ color: "#A855F7", fontWeight: 800 }}>◆</span>
            <span style={{ color: "#C084FC" }}>Deadline</span>
          </div>
        </div>

        <div style={{ color: "var(--color-text-muted)", fontSize: 11 }}>
          Live Gantt state synced with contract: <code style={{ color: "#60A5FA" }}>{contractId}</code>
        </div>
      </div>
    </div>
  );
}

function ChatTab({ 
  contract, 
  features = [] 
}: { 
  contract?: Contract | null; 
  features?: Feature[];
}) {
  const activeContract = contract || mockApi.getContracts()[0];
  const contractId = activeContract?.id || "pct_099e77";
  const displayFeatures = features.length > 0 ? features : (activeContract?.features || []);

  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [roleFilter, setRoleFilter] = useState<"ALL" | "BUYER" | "SELLER" | "AI_REFEREE">("ALL");
  const [isAiThinking, setIsAiThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCurrentUser(getCurrentUser());
  }, []);

  const isViewerHirer = isUserHirer(activeContract, currentUser);
  const mySenderRole: "BUYER" | "SELLER" = isViewerHirer ? "BUYER" : "SELLER";
  const mySenderName = isViewerHirer
    ? (currentUser?.name || activeContract?.buyer_name || "Hirer")
    : (currentUser?.name || activeContract?.seller_name || "Freelancer");

  // Load persisted messages from Supabase DB with mockApi fallback
  useEffect(() => {
    let isMounted = true;
    async function loadChatMessages() {
      try {
        const live = await backendClient.getMessages(contractId);
        if (live && live.length > 0 && isMounted) {
          setMessages(live);
          return;
        }
      } catch (err) {
        console.warn("Failed to load messages from backend:", err);
      }
      if (isMounted) {
        setMessages(mockApi.getMessages(contractId));
      }
    }
    loadChatMessages();
    return () => { isMounted = false; };
  }, [contractId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAiThinking]);

  const handleSendMessage = async (contentToSend?: string) => {
    const text = (contentToSend || inputText).trim();
    if (!text) return;

    if (!contentToSend) setInputText("");

    const newMsg = await backendClient.sendMessage(contractId, {
      sender_type: mySenderRole,
      sender_name: mySenderName,
      content: text,
      sender_id: currentUser?.id,
    });

    setMessages((prev) => [...prev, newMsg]);

    // Simulate smart AI Referee response if a user triggers scope, weight, or terms discussion
    const lower = text.toLowerCase();
    if (
      lower.includes("scope") ||
      lower.includes("weight") ||
      lower.includes("price") ||
      lower.includes("counter") ||
      lower.includes("deadline") ||
      lower.includes("test") ||
      lower.includes("add") ||
      lower.includes("change")
    ) {
      setIsAiThinking(true);
      setTimeout(async () => {
        const aiMsg = await backendClient.sendMessage(contractId, {
          sender_type: "AI_REFEREE",
          sender_name: "AI Referee",
          content: `AI Referee Analysis: Scope alteration noted for "${activeContract?.title}". In accordance with PactPal arbitration rules, any modification to milestone weights or deadline requires dual-party confirmation before funding hold adjustment.`,
          metadata: { action: "SCOPE_ADVISORY" },
        });
        setMessages((prev) => [...prev, aiMsg]);
        setIsAiThinking(false);
      }, 900);
    }
  };

  const handleResetChat = async () => {
    await backendClient.resetMessages(contractId);
    setMessages(mockApi.getMessages(contractId));
  };

  const filteredMessages = messages.filter((m) => {
    if (roleFilter === "ALL") return true;
    return m.sender_type === roleFilter;
  });

  const buyerCount = messages.filter((m) => m.sender_type === "BUYER").length;
  const sellerCount = messages.filter((m) => m.sender_type === "SELLER").length;
  const aiCount = messages.filter((m) => m.sender_type === "AI_REFEREE").length;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 20, minHeight: 620 }}>
      {/* Left panel: Context & Features */}
      <div
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 20,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
        role="complementary"
        aria-label="Negotiation scope overview"
      >
        <div style={{ padding: "18px 20px", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: "#60A5FA", textTransform: "uppercase" }}>
              Negotiation Scope
            </span>
            <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, background: "rgba(255,255,255,0.06)", color: "var(--color-text-muted)" }}>
              {activeContract?.id}
            </span>
          </div>
          <h4 style={{ fontSize: 15, fontWeight: 700, color: "white", margin: 0 }}>
            {activeContract?.title}
          </h4>
          <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4, marginBottom: 0 }}>
            Total Value: <strong style={{ color: "white" }}>${activeContract?.total_amount?.toLocaleString()} {activeContract?.currency || "USD"}</strong>
          </p>
        </div>

        {/* Parties involved */}
        <div style={{ padding: "14px 20px", borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.01)" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 8, textTransform: "uppercase" }}>
            Parties at the Table
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#3B82F6" }} />
              <span style={{ color: "white", fontWeight: 600 }}>{activeContract?.buyer_name || "Priya Sharma"}</span>
              <span style={{ color: "var(--color-text-muted)", fontSize: 11 }}>(Hirer)</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#10B981" }} />
              <span style={{ color: "white", fontWeight: 600 }}>{activeContract?.seller_name || "Alex Mercer"}</span>
              <span style={{ color: "var(--color-text-muted)", fontSize: 11 }}>(Freelancer)</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#A855F7" }} />
              <span style={{ color: "white", fontWeight: 600 }}>AI Referee</span>
              <span style={{ color: "var(--color-text-muted)", fontSize: 11 }}>(Autonomous Arbiter)</span>
            </div>
          </div>
        </div>

        {/* Feature click-to-discuss list */}
        <div style={{ flex: 1, overflowY: "auto", padding: "12px 14px" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", padding: "4px 6px 8px 6px", textTransform: "uppercase" }}>
            Contract Milestones (Click to Discuss)
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {displayFeatures.map((f, i) => {
              const title = f.title || (f as any).name;
              const weight = f.price_weight ?? (f as any).weight;
              const amount = f.allocated_amount ?? (f as any).amount;
              return (
                <div
                  key={f.id || i}
                  onClick={() => {
                    setInputText(`Regarding "${title}": `);
                  }}
                  style={{
                    padding: "10px 12px",
                    borderRadius: 12,
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "rgba(0,102,255,0.1)";
                    e.currentTarget.style.borderColor = "rgba(0,102,255,0.3)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                    e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)";
                  }}
                  title="Click to draft a message about this feature"
                >
                  <div style={{ fontSize: 12, fontWeight: 600, color: "white", marginBottom: 4 }}>
                    {title}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--color-text-muted)" }}>
                    <span>{weight}% weight</span>
                    <span style={{ color: "#10B981", fontWeight: 600 }}>${amount}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Reset button footer */}
        <div style={{ padding: "14px 18px", borderTop: "1px solid rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.01)" }}>
          <button
            onClick={handleResetChat}
            style={{
              width: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              padding: "8px 12px",
              borderRadius: 10,
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              color: "var(--color-text-muted)",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
            }}
            title="Reset messages to default seed history"
          >
            <RefreshCw size={13} />
            Reset Chat to Default
          </button>
        </div>
      </div>

      {/* Right panel: Full Negotiation Timeline & Active Chat */}
      <div
        style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 20,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
        role="log"
        aria-label="Negotiation chat stream"
        aria-live="polite"
      >
        {/* Chat Header & Filters */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            background: "rgba(255,255,255,0.015)",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <MessageSquare size={17} color="#60A5FA" />
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "white", margin: 0 }}>
                Negotiation Chat & Audit History
              </h3>
              <span
                style={{
                  fontSize: 11,
                  padding: "2px 8px",
                  borderRadius: 999,
                  background: "rgba(16,185,129,0.15)",
                  color: "#10B981",
                  border: "1px solid rgba(16,185,129,0.3)",
                  fontWeight: 600,
                }}
              >
                ● Live & Persisted
              </span>
            </div>
            <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: "4px 0 0 0" }}>
              Full audit trail between AI Referee, Hirer, and Freelancer
            </p>
          </div>

          {/* Filter Pills */}
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 11, color: "var(--color-text-muted)", marginRight: 4 }}>Filter:</span>
            {[
              { id: "ALL", label: `All (${messages.length})` },
              { id: "AI_REFEREE", label: `AI (${aiCount})` },
              { id: "BUYER", label: `Hirer (${buyerCount})` },
              { id: "SELLER", label: `Freelancer (${sellerCount})` },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setRoleFilter(f.id as any)}
                style={{
                  padding: "4px 10px",
                  borderRadius: 999,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: "pointer",
                  border: roleFilter === f.id ? "1px solid #3B82F6" : "1px solid rgba(255,255,255,0.08)",
                  background: roleFilter === f.id ? "rgba(59,130,246,0.2)" : "rgba(255,255,255,0.03)",
                  color: roleFilter === f.id ? "white" : "var(--color-text-muted)",
                  transition: "all 0.15s ease",
                }}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Message Stream */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: 18,
            maxHeight: "460px",
          }}
        >
          {filteredMessages.length === 0 ? (
            <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--color-text-muted)", fontSize: 13 }}>
              No messages found for this filter.
            </div>
          ) : (
            filteredMessages.map((m) => {
              const isAi = m.sender_type === "AI_REFEREE";
              const isBuyer = m.sender_type === "BUYER";
              const isSeller = m.sender_type === "SELLER";

              const timeStr = m.sent_at
                ? new Date(m.sent_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                : "Just now";

              return (
                <div
                  key={m.id}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: isBuyer ? "flex-end" : "flex-start",
                    width: "100%",
                  }}
                >
                  {/* Sender Header info */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      marginBottom: 6,
                      flexDirection: isBuyer ? "row-reverse" : "row",
                    }}
                  >
                    {/* Avatar Icon */}
                    <div
                      style={{
                        width: 26,
                        height: 26,
                        borderRadius: "50%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: isAi
                          ? "linear-gradient(135deg, #7A5CFF, #0066FF)"
                          : isBuyer
                          ? "rgba(59,130,246,0.2)"
                          : "rgba(16,185,129,0.2)",
                        border: `1px solid ${
                          isAi ? "#7A5CFF" : isBuyer ? "rgba(59,130,246,0.4)" : "rgba(16,185,129,0.4)"
                        }`,
                      }}
                    >
                      {isAi ? <Bot size={14} color="white" /> : <User size={14} color={isBuyer ? "#60A5FA" : "#34D399"} />}
                    </div>

                    {/* Sender Name */}
                    <span style={{ fontSize: 12, fontWeight: 700, color: "white" }}>
                      {m.sender_name || (isAi ? "AI Referee" : isBuyer ? "Hirer" : "Freelancer")}
                    </span>

                    {/* Role Pill */}
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        letterSpacing: "0.04em",
                        padding: "1px 7px",
                        borderRadius: 6,
                        textTransform: "uppercase",
                        background: isAi
                          ? "rgba(122,92,255,0.18)"
                          : isBuyer
                          ? "rgba(59,130,246,0.18)"
                          : "rgba(16,185,129,0.18)",
                        color: isAi ? "#C084FC" : isBuyer ? "#93C5FD" : "#6EE7B7",
                        border: `1px solid ${
                          isAi ? "rgba(122,92,255,0.3)" : isBuyer ? "rgba(59,130,246,0.3)" : "rgba(16,185,129,0.3)"
                        }`,
                      }}
                    >
                      {isAi ? "Referee" : isBuyer ? "Hirer" : "Freelancer"}
                    </span>

                    {/* Timestamp */}
                    <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                      {timeStr}
                    </span>
                  </div>

                  {/* Message Bubble */}
                  <div
                    style={{
                      maxWidth: isAi ? "86%" : "78%",
                      padding: "14px 18px",
                      borderRadius: isAi ? 16 : isBuyer ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
                      background: isAi
                        ? "linear-gradient(135deg, rgba(122,92,255,0.12) 0%, rgba(0,102,255,0.06) 100%)"
                        : isBuyer
                        ? "rgba(0,102,255,0.14)"
                        : "rgba(255,255,255,0.05)",
                      border: isAi
                        ? "1px solid rgba(122,92,255,0.35)"
                        : isBuyer
                        ? "1px solid rgba(0,102,255,0.3)"
                        : "1px solid rgba(255,255,255,0.1)",
                      boxShadow: isAi ? "0 4px 24px rgba(122,92,255,0.1)" : "none",
                      color: isAi ? "#E0E7FF" : "white",
                      fontSize: 13.5,
                      lineHeight: 1.6,
                    }}
                  >
                    {m.content}

                    {/* Special Metadata Cards */}
                    {m.metadata && (
                      <div
                        style={{
                          marginTop: 10,
                          padding: "10px 14px",
                          borderRadius: 10,
                          fontSize: 12,
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          background:
                            m.metadata.action === "COUNTER_OFFER"
                              ? "rgba(255,152,0,0.12)"
                              : m.metadata.action === "ACCEPT_TERMS"
                              ? "rgba(16,185,129,0.15)"
                              : m.metadata.action === "VERDICT_SUMMARY"
                              ? "rgba(122,92,255,0.18)"
                              : "rgba(0,163,224,0.12)",
                          border: `1px solid ${
                            m.metadata.action === "COUNTER_OFFER"
                              ? "rgba(255,152,0,0.3)"
                              : m.metadata.action === "ACCEPT_TERMS"
                              ? "rgba(16,185,129,0.3)"
                              : m.metadata.action === "VERDICT_SUMMARY"
                              ? "rgba(122,92,255,0.35)"
                              : "rgba(0,163,224,0.25)"
                          }`,
                          color:
                            m.metadata.action === "COUNTER_OFFER"
                              ? "#FDBA74"
                              : m.metadata.action === "ACCEPT_TERMS"
                              ? "#86EFAC"
                              : m.metadata.action === "VERDICT_SUMMARY"
                              ? "#D8B4FE"
                              : "#93C5FD",
                        }}
                      >
                        {m.metadata.action === "ACCEPT_TERMS" && <CheckCheck size={16} />}
                        {m.metadata.action === "COUNTER_OFFER" && <Scale size={16} />}
                        {m.metadata.action === "VERDICT_SUMMARY" && <ShieldCheck size={16} />}
                        {m.metadata.action === "SCOPE_ADVISORY" && <Sparkles size={16} />}
                        <div>
                          <strong>
                            {m.metadata.action === "COUNTER_OFFER" && "Terms Adjustment: Counter-Offer Filed"}
                            {m.metadata.action === "ACCEPT_TERMS" && "Dual Acceptance Confirmed"}
                            {m.metadata.action === "VERDICT_SUMMARY" && "Escrow Settlement Allocation"}
                            {m.metadata.action === "SCOPE_ADVISORY" && "Official Scope Advisory Notice"}
                          </strong>
                          {m.metadata.proposed_amount && (
                            <span style={{ marginLeft: 8, opacity: 0.9 }}>
                              · Amount: ${m.metadata.proposed_amount.toLocaleString()} USD
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {isAiThinking && (
            <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 14px", borderRadius: 12, background: "rgba(122,92,255,0.1)", border: "1px solid rgba(122,92,255,0.25)", width: "fit-content" }}>
              <Bot size={16} color="#C084FC" className="animate-spin" />
              <span style={{ fontSize: 12, color: "#D8B4FE" }}>AI Referee is analyzing scope & agreement terms...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick mediation prompt suggestions */}
        <div
          style={{
            padding: "8px 20px",
            background: "rgba(255,255,255,0.015)",
            borderTop: "1px solid rgba(255,255,255,0.06)",
            display: "flex",
            alignItems: "center",
            gap: 8,
            overflowX: "auto",
          }}
        >
          <span style={{ fontSize: 11, color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
            Suggested:
          </span>
          {(isViewerHirer
            ? [
                "Can you add dark mode support as well?",
                "Please verify milestone acceptance criteria details.",
                "Let me know when the code is ready for test verification.",
              ]
            : [
                "I can deliver dark mode for $100 and 2 extra days.",
                "Milestone implementation is ready for verification.",
                "Currently working on test coverage for the authentication flow.",
              ]
          ).map((s, idx) => (
            <button
              key={idx}
              onClick={() => {
                setInputText(s);
              }}
              style={{
                whiteSpace: "nowrap",
                fontSize: 11,
                padding: "4px 10px",
                borderRadius: 999,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                color: "var(--color-text-secondary)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(0,102,255,0.4)";
                e.currentTarget.style.color = "white";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                e.currentTarget.style.color = "var(--color-text-secondary)";
              }}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Send Input Bar & Sender Identity */}
        <div
          style={{
            padding: "16px 20px",
            borderTop: "1px solid rgba(255,255,255,0.08)",
            background: "rgba(255,255,255,0.02)",
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          {/* Identity badge & Hirer-only Escrow key */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-muted)" }}>
                Chatting as:
              </span>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  borderRadius: 20,
                  background: isViewerHirer ? "rgba(0,102,255,0.12)" : "rgba(16,185,129,0.12)",
                  border: `1px solid ${isViewerHirer ? "rgba(0,102,255,0.3)" : "rgba(16,185,129,0.3)"}`,
                  padding: "4px 14px",
                  fontSize: 12,
                  fontWeight: 700,
                  color: isViewerHirer ? "#60A5FA" : "#34D399",
                }}
              >
                <span>{isViewerHirer ? "" : ""}</span>
                <span>{mySenderName} ({isViewerHirer ? "Hirer" : "Freelancer"})</span>
              </div>
            </div>

            {/* Escrow Key: STRICTLY visible to Hirer only */}
            {isViewerHirer && (
              <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                Escrow Key: <code style={{ color: "#60A5FA" }}>pactpal_chat_v1_{contractId}</code>
              </span>
            )}
          </div>

          {/* Form input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            style={{ display: "flex", gap: 10 }}
          >
            <input
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={`Type a negotiation message as ${mySenderName}...`}
              style={{
                flex: 1,
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 12,
                color: "white",
                fontSize: 14,
                padding: "12px 16px",
                outline: "none",
                fontFamily: "Inter, sans-serif",
              }}
              aria-label="Negotiation chat input"
            />
            <button
              type="submit"
              disabled={!inputText.trim()}
              style={{
                background: inputText.trim()
                  ? "linear-gradient(135deg, #0066FF, #00A3E0)"
                  : "rgba(255,255,255,0.06)",
                border: "none",
                borderRadius: 12,
                color: inputText.trim() ? "white" : "rgba(255,255,255,0.3)",
                padding: "12px 22px",
                fontSize: 14,
                fontWeight: 700,
                cursor: inputText.trim() ? "pointer" : "not-allowed",
                display: "flex",
                alignItems: "center",
                gap: 8,
                transition: "all 0.2s ease",
              }}
            >
              <span>Send</span>
              <Send size={15} />
            </button>
          </form>
        </div>
      </div>

      <style>{`
        @media (max-width: 860px) {
          [style*="grid-template-columns: 300px 1fr"] {
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
            Live Verification Pipeline — Stages A to F
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

      {/* Live Event Log Stream (Lifecycle Management) */}
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
  contract,
  total,
  passedAmount,
  features,
}: {
  contract?: Contract | null;
  total: number;
  passedAmount: number;
  features: Feature[];
}) {
  const activeContract = contract || mockApi.getContracts()[0];
  const receipt = mockApi.getReceipt(activeContract?.id || "pct_099e77");
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(receipt.receipt_hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const passedCount = features.filter((f) => (f.status || "").toLowerCase() === "passed").length;
  const sellerPayout = passedAmount > 0 ? passedAmount : receipt.financial_dispatch.seller_payout_amount;
  const buyerRefund = total - sellerPayout;

  return (
    <div style={{ maxWidth: 760, margin: "0 auto" }}>
      <div
        style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 24,
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
            padding: "24px 30px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", color: "var(--color-text-muted)", marginBottom: 4 }}>
              PROOF-OF-WORK RECEIPT
            </div>
            <div style={{ fontSize: 19, fontWeight: 800, color: "white" }}>
              PactPal Cryptographic Verification Certificate
            </div>
          </div>
          <div
            style={{
              background: "rgba(76,175,80,0.15)",
              border: "1px solid rgba(76,175,80,0.4)",
              borderRadius: 50,
              padding: "6px 16px",
              fontSize: 12,
              fontWeight: 700,
              color: "#4CAF50",
              display: "flex",
              alignItems: "center",
              gap: 7,
            }}
          >
            <CheckCircle size={14} aria-hidden /> Immutable Record
          </div>
        </div>

        <div style={{ padding: "26px 30px", display: "flex", flexDirection: "column", gap: 20 }}>
          {/* SHA-256 Hash box */}
          <div
            style={{
              background: "rgba(0,0,0,0.4)",
              border: "1px solid rgba(122,92,255,0.25)",
              borderRadius: 14,
              padding: "16px 20px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: "var(--color-text-muted)" }}>
                SHA-256 FINGERPRINT (HMAC LATCHED)
              </span>
              <span style={{ fontSize: 11, color: "#34D399", fontWeight: 600 }}>
                ✓ Attached to PayPal Note
              </span>
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
              {receipt.receipt_hash}
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
              <button
                onClick={handleCopy}
                style={{
                  background: "rgba(122,92,255,0.15)",
                  border: "1px solid rgba(122,92,255,0.3)",
                  borderRadius: 8,
                  color: "#C084FC",
                  padding: "6px 14px",
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                }}
                aria-label="Copy SHA-256 fingerprint to clipboard"
              >
                {copied ? <Check size={13} color="#34D399" /> : <Copy size={13} />}
                {copied ? "Copied to Clipboard!" : "Copy Hash"}
              </button>
            </div>
          </div>

          {/* Summary metadata rows */}
          {[
            ["Contract ID", activeContract.id],
            ["Contract Title", activeContract.title],
            ["Settlement Timestamp", new Date(receipt.settled_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })],
            ["Hirer", activeContract.buyer_name || "Priya Sharma"],
            ["Freelancer", activeContract.seller_name || "Alex Mercer"],
            ["Total Held in Escrow", `$${total.toLocaleString()}.00 USD`],
            ["Features Passed", `${passedCount} of ${features.length} milestones verified`],
            ["Freelancer Disbursal", `$${sellerPayout.toLocaleString()}.00 USD`],
            ["Hirer Refund", `$${buyerRefund.toLocaleString()}.00 USD`],
            ["Test Assertions", `${receipt.verification_metrics.tests_passed}/${receipt.verification_metrics.tests_total} Passed (${receipt.verification_metrics.coverage_percent}% Coverage)`],
            ["Visual Match Avg", `${receipt.verification_metrics.visual_similarity_score}% (Threshold: 90%)`],
            ["PayPal Batch ID", receipt.financial_dispatch.paypal_payout_batch_id],
          ].map(([k, v]) => (
            <div
              key={k}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                fontSize: 13.5,
                paddingBottom: 12,
                borderBottom: "1px solid rgba(255,255,255,0.05)",
              }}
            >
              <span style={{ color: "var(--color-text-muted)" }}>{k}</span>
              <span style={{ fontWeight: 600, color: "white", fontFamily: ["Total Held in Escrow", "Freelancer Disbursal", "Hirer Refund", "Contract ID", "PayPal Batch ID"].includes(k) ? "JetBrains Mono, monospace" : "Inter, sans-serif" }}>
                {v}
              </span>
            </div>
          ))}

          {/* Direct link to dedicated standalone receipt page */}
          <Link
            href={`/contracts/${activeContract.id}/receipt`}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              background: "linear-gradient(135deg, #0066FF, #00A3E0)",
              borderRadius: 12,
              color: "white",
              padding: "14px",
              fontSize: 14,
              fontWeight: 700,
              textDecoration: "none",
              boxShadow: "0 0 20px rgba(0,102,255,0.3)",
              marginTop: 6,
            }}
          >
            Open Dedicated Proof-of-Work Receipt Page →
          </Link>

          {/* PayPal link */}
          <a
            href={receipt.evidence_links.paypal_transaction_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 12,
              color: "var(--color-text-secondary)",
              padding: "12px",
              fontSize: 13,
              fontWeight: 600,
              textDecoration: "none",
            }}
            aria-label="View PayPal transaction reference"
          >
            🔗 View PayPal Reference · {receipt.financial_dispatch.paypal_order_id}
          </a>
        </div>
      </div>
    </div>
  );
}

