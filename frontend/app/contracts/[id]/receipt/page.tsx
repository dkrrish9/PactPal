"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import {
  ArrowLeft,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  Download,
  ExternalLink,
  Clock,
  Layers,
  FileText,
  DollarSign,
  AlertTriangle,
  GitBranch,
  Terminal,
  Zap,
  RefreshCw,
  Lock,
  Search
} from "lucide-react";
import { mockApi, Contract, ProofOfWorkReceipt } from "@/lib/mockApi";

export default function ReceiptPage() {
  const params = useParams();
  const router = useRouter();
  const rawId = (params?.id as string) || "pct_099e77";

  const [contract, setContract] = useState<Contract | null>(null);
  const [receipt, setReceipt] = useState<ProofOfWorkReceipt | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);
  const [tamperSimulation, setTamperSimulation] = useState(false);
  const [activeTab, setActiveTab] = useState<"summary" | "features" | "evidence" | "json">("summary");

  useEffect(() => {
    const c = mockApi.getContract(rawId) || mockApi.getContracts()[0];
    setContract(c);
    const r = mockApi.getReceipt(c?.id || rawId);
    setReceipt(r);
  }, [rawId]);

  if (!contract || !receipt) {
    return (
      <div style={{ minHeight: "100vh", background: "var(--color-bg)", color: "white", padding: 60, textAlign: "center" }}>
        Loading Proof-of-Work Receipt...
      </div>
    );
  }

  const isSettled = contract.status === "SETTLED" || receipt.status === "SETTLED";
  const { financial_dispatch, deliverable, verification_metrics, features, evidence_links, tamper_check } = receipt;

  const originalHash = receipt.receipt_hash;
  const simulatedTamperedHash = "0x7d81efb9423c10a448bc9024d8f5a61099882211bb3344cc556677889900aabb";
  const displayHash = tamperSimulation ? simulatedTamperedHash : originalHash;

  const handleCopyHash = () => {
    navigator.clipboard.writeText(displayHash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const handleDownloadJson = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(receipt, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `PactPal_Receipt_${contract.id}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleSimulateSettlement = () => {
    mockApi.settleContract(contract.id);
    const updated = mockApi.getContract(contract.id);
    setContract(updated);
    setReceipt(mockApi.getReceipt(contract.id));
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

      <main style={{ maxWidth: 1040, margin: "0 auto", padding: "100px 24px 80px" }}>
        {/* Breadcrumb & Navigation */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
          <Link
            href={`/contracts/${contract.id}`}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              color: "var(--color-text-secondary)",
              textDecoration: "none",
              fontSize: 14,
              transition: "color 0.15s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "white")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--color-text-secondary)")}
          >
            <ArrowLeft size={16} />
            Back to Contract Dashboard
          </Link>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {contract.id !== "pct_settled_04" && (
              <Link
                href="/contracts/pct_settled_04/receipt"
                style={{
                  fontSize: 12,
                  padding: "6px 12px",
                  borderRadius: 8,
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#93C5FD",
                  textDecoration: "none",
                }}
              >
                View Native Settled Demo (pct_settled_04) →
              </Link>
            )}
            <button
              onClick={handleDownloadJson}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 7,
                padding: "8px 14px",
                borderRadius: 9,
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.12)",
                color: "white",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <Download size={14} />
              Export JSON Certificate
            </button>
          </div>
        </div>

        {/* Not settled alert banner with 1-click settle button */}
        {contract.status !== "SETTLED" && (
          <div
            style={{
              padding: "16px 20px",
              borderRadius: 14,
              background: "rgba(255,152,0,0.1)",
              border: "1px solid rgba(255,152,0,0.3)",
              marginBottom: 24,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 12,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <AlertTriangle size={20} color="#F59E0B" />
              <div>
                <strong style={{ color: "#FBBF24", fontSize: 14 }}>Contract Currently in {contract.status}</strong>
                <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--color-text-secondary)" }}>
                  Previewing the generated receipt. Click to execute final payout settlement and seal immutable status.
                </p>
              </div>
            </div>
            <button
              onClick={handleSimulateSettlement}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                background: "#0066FF",
                border: "none",
                color: "white",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Mark Settled & Seal Receipt (C45)
            </button>
          </div>
        )}

        {/* Primary Receipt Certificate Header */}
        <div
          style={{
            background: "linear-gradient(135deg, rgba(122,92,255,0.15) 0%, rgba(0,102,255,0.1) 100%)",
            border: "1px solid rgba(122,92,255,0.35)",
            borderRadius: 24,
            padding: "32px",
            marginBottom: 32,
            boxShadow: "0 0 60px rgba(122,92,255,0.12)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Subtle watermark in background */}
          <div
            style={{
              position: "absolute",
              right: -20,
              bottom: -25,
              fontSize: 160,
              fontWeight: 900,
              color: "rgba(255,255,255,0.02)",
              pointerEvents: "none",
              userSelect: "none",
            }}
          >
            PACTPAL
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 20 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "4px 12px",
                    borderRadius: 999,
                    background: "rgba(16,185,129,0.15)",
                    border: "1px solid rgba(16,185,129,0.4)",
                    color: "#34D399",
                    fontSize: 12,
                    fontWeight: 700,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                  }}
                >
                  <ShieldCheck size={14} />
                  STAGE 6 · PROOF-OF-WORK RECEIPT SEALED
                </span>
                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                  Certificate ID: <strong style={{ color: "white" }}>{receipt.id}</strong>
                </span>
              </div>

              <h1 style={{ fontSize: 28, fontWeight: 800, margin: "0 0 8px 0", letterSpacing: "-0.02em" }}>
                Cryptographic Settlement Receipt
              </h1>
              <p style={{ color: "var(--color-text-secondary)", fontSize: 14, margin: 0, maxWidth: 640 }}>
                Autonomous AI-refereed verification completed for <strong style={{ color: "white" }}>{contract.title}</strong>. Funds disbursed proportionately via PayPal Escrow Rails.
              </p>
            </div>

            {/* Overall Verification Score Badge */}
            <div
              style={{
                background: "rgba(0,0,0,0.3)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 16,
                padding: "16px 24px",
                textAlign: "center",
                minWidth: 150,
              }}
            >
              <div style={{ fontSize: 11, color: "var(--color-text-muted)", textTransform: "uppercase", fontWeight: 700, marginBottom: 4 }}>
                Verification Score
              </div>
              <div style={{ fontSize: 32, fontWeight: 800, color: "#60A5FA", fontFamily: "JetBrains Mono, monospace" }}>
                {verification_metrics.overall_score}%
              </div>
              <div style={{ fontSize: 11, color: "#34D399", fontWeight: 600 }}>
                {verification_metrics.test_suite_status} ({verification_metrics.tests_passed}/{verification_metrics.tests_total} Tests)
              </div>
            </div>
          </div>
        </div>

        {/* Four Core Requirements Grid (Summary, Hash, Timestamps, Evidence Links) */}

        {/* 1. FINANCIAL SUMMARY & SETTLEMENT DISPATCH */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <DollarSign size={20} color="#60A5FA" />
            <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>
              1. Settlement Financial Dispatch Summary
            </h2>
          </div>

          <div
            style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 20,
              padding: "26px",
            }}
          >
            {/* Top financial metric cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 24 }}>
              <div style={{ background: "rgba(255,255,255,0.03)", padding: "16px 20px", borderRadius: 14, border: "1px solid rgba(255,255,255,0.06)" }}>
                <span style={{ fontSize: 12, color: "var(--color-text-muted)", fontWeight: 600 }}>Total Escrow Held</span>
                <div style={{ fontSize: 26, fontWeight: 800, color: "white", fontFamily: "JetBrains Mono, monospace", marginTop: 4 }}>
                  ${financial_dispatch.total_amount.toLocaleString()}.00
                </div>
                <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{financial_dispatch.currency} · 100% Locked</span>
              </div>

              <div style={{ background: "rgba(16,185,129,0.08)", padding: "16px 20px", borderRadius: 14, border: "1px solid rgba(16,185,129,0.25)" }}>
                <span style={{ fontSize: 12, color: "#6EE7B7", fontWeight: 600 }}>Disbursed to Freelancer</span>
                <div style={{ fontSize: 26, fontWeight: 800, color: "#10B981", fontFamily: "JetBrains Mono, monospace", marginTop: 4 }}>
                  +${financial_dispatch.seller_payout_amount.toLocaleString()}.00
                </div>
                <span style={{ fontSize: 11, color: "#A7F3D0" }}>{financial_dispatch.passed_weight_percent}% Passed Weight Capture</span>
              </div>

              <div style={{ background: "rgba(244,67,54,0.08)", padding: "16px 20px", borderRadius: 14, border: "1px solid rgba(244,67,54,0.25)" }}>
                <span style={{ fontSize: 12, color: "#FCA5A5", fontWeight: 600 }}>Refunded to Hirer</span>
                <div style={{ fontSize: 26, fontWeight: 800, color: "#F87171", fontFamily: "JetBrains Mono, monospace", marginTop: 4 }}>
                  ${financial_dispatch.buyer_refund_amount.toLocaleString()}.00
                </div>
                <span style={{ fontSize: 11, color: "#FECACA" }}>{financial_dispatch.failed_weight_percent}% Unverified Escrow Void</span>
              </div>
            </div>

            {/* Dual visual progress bar */}
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, fontWeight: 600, marginBottom: 8 }}>
                <span style={{ color: "#34D399" }}>
                  Freelancer Payout: {financial_dispatch.passed_weight_percent}% (${financial_dispatch.seller_payout_amount})
                </span>
                <span style={{ color: "#F87171" }}>
                  Hirer Refund: {financial_dispatch.failed_weight_percent}% (${financial_dispatch.buyer_refund_amount})
                </span>
              </div>
              <div style={{ width: "100%", height: 18, borderRadius: 9, background: "rgba(255,255,255,0.06)", overflow: "hidden", display: "flex" }}>
                <div
                  style={{
                    width: `${financial_dispatch.passed_weight_percent}%`,
                    background: "linear-gradient(90deg, #10B981, #00A3E0)",
                    transition: "width 0.4s ease",
                  }}
                  title="Seller Payout Share"
                />
                <div
                  style={{
                    width: `${financial_dispatch.failed_weight_percent}%`,
                    background: "rgba(244,67,54,0.75)",
                    transition: "width 0.4s ease",
                  }}
                  title="Hirer Refund Share"
                />
              </div>
            </div>

            {/* Feature Checklist Ledger Table */}
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, textAlign: "left" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", color: "var(--color-text-muted)", fontSize: 11, textTransform: "uppercase" }}>
                    <th style={{ padding: "10px 12px" }}>Feature Milestone</th>
                    <th style={{ padding: "10px 12px" }}>Weight</th>
                    <th style={{ padding: "10px 12px" }}>Verdict</th>
                    <th style={{ padding: "10px 12px" }}>Evidence Summary</th>
                    <th style={{ padding: "10px 12px", textAlign: "right" }}>Settled Sum</th>
                  </tr>
                </thead>
                <tbody>
                  {features.map((f, i) => (
                    <tr key={f.id || i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={{ padding: "14px 12px", fontWeight: 600, color: "white" }}>
                        {f.title}
                      </td>
                      <td style={{ padding: "14px 12px", fontFamily: "JetBrains Mono, monospace", color: "var(--color-text-muted)" }}>
                        {f.price_weight}%
                      </td>
                      <td style={{ padding: "14px 12px" }}>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 5,
                            padding: "3px 8px",
                            borderRadius: 6,
                            fontSize: 11,
                            fontWeight: 700,
                            background: f.status === "PASSED" ? "rgba(16,185,129,0.15)" : "rgba(244,67,54,0.15)",
                            color: f.status === "PASSED" ? "#34D399" : "#F87171",
                          }}
                        >
                          {f.status === "PASSED" ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                          {f.status}
                        </span>
                      </td>
                      <td style={{ padding: "14px 12px", color: "var(--color-text-secondary)", fontSize: 12 }}>
                        {f.evidence || (f.status === "PASSED" ? "Verified against acceptance test" : "Test failed during container run")}
                      </td>
                      <td style={{ padding: "14px 12px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", fontWeight: 700 }}>
                        {f.status === "PASSED" ? (
                          <span style={{ color: "#34D399" }}>+${f.allocated_amount}.00</span>
                        ) : (
                          <span style={{ color: "var(--color-text-muted)" }}>$0.00 (Refunded)</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* 2. CRYPTOGRAPHIC SHA-256 HASH & PROOF-OF-WORK FINGERPRINT */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Lock size={20} color="#A78BFA" />
              <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>
                2. Cryptographic Proof-of-Work SHA-256 Fingerprint
              </h2>
            </div>

            <button
              onClick={() => setTamperSimulation(!tamperSimulation)}
              style={{
                fontSize: 12,
                padding: "6px 12px",
                borderRadius: 8,
                background: tamperSimulation ? "rgba(244,67,54,0.15)" : "rgba(122,92,255,0.15)",
                border: `1px solid ${tamperSimulation ? "rgba(244,67,54,0.4)" : "rgba(122,92,255,0.4)"}`,
                color: tamperSimulation ? "#F87171" : "#C084FC",
                cursor: "pointer",
                fontWeight: 600,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
              title="Test C44 rule: changing 1 character changes the entire hash"
            >
              <RefreshCw size={12} />
              {tamperSimulation ? "Reset to Genuine Canonical Hash" : "Simulate Tamper (Change 1 Char)"}
            </button>
          </div>

          <div
            style={{
              background: "rgba(0,0,0,0.45)",
              border: `1px solid ${tamperSimulation ? "rgba(244,67,54,0.4)" : "rgba(122,92,255,0.3)"}`,
              borderRadius: 20,
              padding: "24px",
              boxShadow: tamperSimulation ? "0 0 30px rgba(244,67,54,0.15)" : "0 0 30px rgba(122,92,255,0.08)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                SHA-256 Digest (Attached to PayPal Payout Batch Note)
              </span>
              <span
                style={{
                  fontSize: 11,
                  padding: "2px 8px",
                  borderRadius: 6,
                  fontWeight: 700,
                  background: tamperSimulation ? "rgba(244,67,54,0.2)" : "rgba(16,185,129,0.15)",
                  color: tamperSimulation ? "#F87171" : "#34D399",
                }}
              >
                {tamperSimulation ? "TAMPER DETECTED: INVALID DIGEST" : "✓ CANONICAL DIGEST VERIFIED"}
              </span>
            </div>

            {/* The Hash Code Box */}
            <div
              style={{
                background: "rgba(0,0,0,0.6)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 12,
                padding: "16px 20px",
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 14,
                color: tamperSimulation ? "#F87171" : "#A78BFA",
                wordBreak: "break-all",
                lineHeight: 1.6,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 16,
              }}
            >
              <span>{displayHash}</span>
              <button
                onClick={handleCopyHash}
                style={{
                  background: "rgba(255,255,255,0.08)",
                  border: "none",
                  borderRadius: 8,
                  padding: "8px 14px",
                  color: "white",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                }}
              >
                {copiedHash ? <Check size={14} color="#34D399" /> : <Copy size={14} />}
                {copiedHash ? "Copied!" : "Copy Hash"}
              </button>
            </div>

            {/* Provenance Metadata details */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14, marginTop: 18, fontSize: 12 }}>
              <div>
                <span style={{ color: "var(--color-text-muted)" }}>Referee Engine:</span>
                <div style={{ color: "white", fontWeight: 600, fontFamily: "JetBrains Mono, monospace", marginTop: 2 }}>
                  {tamper_check.referee_engine}
                </div>
              </div>
              <div>
                <span style={{ color: "var(--color-text-muted)" }}>PayPal Batch Ref:</span>
                <div style={{ color: "#60A5FA", fontWeight: 600, fontFamily: "JetBrains Mono, monospace", marginTop: 2 }}>
                  {financial_dispatch.paypal_payout_batch_id}
                </div>
              </div>
              <div>
                <span style={{ color: "var(--color-text-muted)" }}>Algorithm:</span>
                <div style={{ color: "white", fontWeight: 600, fontFamily: "JetBrains Mono, monospace", marginTop: 2 }}>
                  {tamper_check.algorithm} (HMAC Salt Locked)
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 3. AUDIT TIMESTAMPS & PROVENANCE TIMELINE */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <Clock size={20} color="#34D399" />
            <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>
              3. Verification & Settlement Timestamps
            </h2>
          </div>

          <div
            style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 20,
              padding: "24px",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {[
                {
                  label: "Contract Formally Created",
                  time: contract.created_at,
                  desc: "Structured milestone weights and acceptance criteria established.",
                  icon: "📝",
                },
                {
                  label: "Dual Checklist Confirmation & PayPal Hold",
                  time: contract.seller_confirmed_at || contract.buyer_confirmed_at || contract.created_at,
                  desc: `Buyer & Seller signed terms. $${financial_dispatch.total_amount} locked in PayPal escrow hold.`,
                  icon: "🔒",
                },
                {
                  label: "Code Deliverables Pinned",
                  time: deliverable.submitted_at,
                  desc: `Git commit SHA ${deliverable.commit_sha.substring(0, 10)} pinned from ${deliverable.branch} branch.`,
                  icon: "🐙",
                },
                {
                  label: "Autonomous Referee Verification Concluded",
                  time: receipt.generated_at,
                  desc: `gVisor sandbox container passed ${verification_metrics.tests_passed}/${verification_metrics.tests_total} assertions (Coverage: ${verification_metrics.coverage_percent}%).`,
                  icon: "🔬",
                },
                {
                  label: "Settlement Disbursed & Receipt Sealed",
                  time: receipt.settled_at,
                  desc: `Final release executed. SHA-256 fingerprint attached to settlement record.`,
                  icon: "🧾",
                },
              ].map((step, idx) => {
                const formattedDate = step.time
                  ? new Date(step.time).toLocaleString([], { dateStyle: "medium", timeStyle: "medium" })
                  : "Recorded at Settlement";
                return (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 16,
                      paddingBottom: idx === 4 ? 0 : 16,
                      borderBottom: idx === 4 ? "none" : "1px solid rgba(255,255,255,0.05)",
                    }}
                  >
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: "50%",
                        background: "rgba(255,255,255,0.05)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 16,
                        flexShrink: 0,
                      }}
                    >
                      {step.icon}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 6 }}>
                        <span style={{ fontSize: 14, fontWeight: 700, color: "white" }}>
                          {step.label}
                        </span>
                        <span style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: "#60A5FA" }}>
                          {formattedDate}
                        </span>
                      </div>
                      <p style={{ fontSize: 12, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>
                        {step.desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* 4. EVIDENCE LINKS */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <ExternalLink size={20} color="#F59E0B" />
            <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>
              4. Evidence Links & Proof Artifacts
            </h2>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: 16,
            }}
          >
            {/* GitHub Deliverable Commit */}
            <a
              href={evidence_links.github_commit_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                textDecoration: "none",
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16,
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(0,102,255,0.4)";
                e.currentTarget.style.background = "rgba(0,102,255,0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                e.currentTarget.style.background = "rgba(255,255,255,0.02)";
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#60A5FA" }}>🐙 GitHub Repository & Commit</span>
                <ExternalLink size={14} color="var(--color-text-muted)" />
              </div>
              <strong style={{ color: "white", fontSize: 14 }}>
                {deliverable.repo_url.replace("https://github.com/", "")}
              </strong>
              <div style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: "var(--color-text-muted)" }}>
                SHA: {deliverable.commit_sha.substring(0, 16)}...
              </div>
            </a>

            {/* Verification Suite Report */}
            <Link
              href={evidence_links.verification_report_url}
              style={{
                textDecoration: "none",
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16,
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(122,92,255,0.4)";
                e.currentTarget.style.background = "rgba(122,92,255,0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                e.currentTarget.style.background = "rgba(255,255,255,0.02)";
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#C084FC" }}>🔬 Full Verification Report</span>
                <ExternalLink size={14} color="var(--color-text-muted)" />
              </div>
              <strong style={{ color: "white", fontSize: 14 }}>
                Inspect Test Suite, AST Scan & Visual Slider
              </strong>
              <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                Per-feature pass/fail logs, assertion counts, and cheat scan findings.
              </div>
            </Link>

            {/* Headless Browser Visual Diff */}
            <Link
              href={evidence_links.visual_diff_url}
              style={{
                textDecoration: "none",
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16,
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(16,185,129,0.4)";
                e.currentTarget.style.background = "rgba(16,185,129,0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                e.currentTarget.style.background = "rgba(255,255,255,0.02)";
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#34D399" }}>🎨 Visual Comparison Evidence</span>
                <ExternalLink size={14} color="var(--color-text-muted)" />
              </div>
              <strong style={{ color: "white", fontSize: 14 }}>
                Figma vs Headless Chromium Split Slider
              </strong>
              <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                Similarity Score: {verification_metrics.visual_similarity_score}% (Threshold: 90%)
              </div>
            </Link>

            {/* PayPal Sandbox Reference */}
            <a
              href={evidence_links.paypal_transaction_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                textDecoration: "none",
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16,
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(245,158,11,0.4)";
                e.currentTarget.style.background = "rgba(245,158,11,0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                e.currentTarget.style.background = "rgba(255,255,255,0.02)";
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#FBBF24" }}>💳 PayPal Sandbox Rail Reference</span>
                <ExternalLink size={14} color="var(--color-text-muted)" />
              </div>
              <strong style={{ color: "white", fontSize: 14 }}>
                Order ID: {financial_dispatch.paypal_order_id}
              </strong>
              <div style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: "var(--color-text-muted)" }}>
                Capture Ref: {financial_dispatch.paypal_capture_id}
              </div>
            </a>
          </div>
        </section>

        {/* Back to Overview Footer CTA */}
        <div style={{ textAlign: "center", marginTop: 40, borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 28 }}>
          <Link
            href={`/contracts/${contract.id}`}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "12px 24px",
              borderRadius: 12,
              background: "linear-gradient(135deg, #0066FF, #00A3E0)",
              color: "white",
              fontWeight: 700,
              fontSize: 14,
              textDecoration: "none",
            }}
          >
            Return to Contract Dashboard →
          </Link>
        </div>
      </main>
    </div>
  );
}

