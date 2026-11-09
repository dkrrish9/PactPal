"use client";
import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { 
  ArrowLeft, 
  CheckCircle2, 
  XCircle, 
  FileText, 
  DollarSign, 
  ShieldCheck, 
  Download, 
  Share2,
  ExternalLink,
  Layers,
  ArrowRight
} from "lucide-react";

export default function SettlementSummaryPage() {
  const params = useParams();
  const contractId = (params?.id as string) || "pct_099e77";

  const totalEscrow = 1500;
  const passedAmount = 1200; // 80%
  const refundedAmount = 300; // 20%
  const shaHash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

  const [copied, setCopied] = useState(false);

  const handleCopyHash = () => {
    navigator.clipboard.writeText(shaHash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const features = [
    { name: "Auth & OAuth Login with NextAuth", weight: 20, status: "PASSED", payout: 300, score: "100%" },
    { name: "Bryntum Gantt Timeline Integration", weight: 30, status: "PASSED", payout: 450, score: "98%" },
    { name: "PayPal Escrow Webhook Listeners", weight: 30, status: "PASSED", payout: 450, score: "100%" },
    { name: "Real-time Notification Service", weight: 20, status: "FAILED", payout: 0, score: "42% (Mock returned)" },
  ];

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
      <div style={{ maxWidth: 960, margin: "0 auto", padding: "0 24px" }}>
        
        {/* Navigation */}
        <Link
          href={`/contracts/${contractId}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            color: "var(--color-text-secondary)",
            textDecoration: "none",
            fontSize: 14,
            marginBottom: 24,
          }}
        >
          <ArrowLeft size={16} /> Back to Contract Overview
        </Link>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32, flexWrap: "wrap", gap: 16 }}>
          <div>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "4px 10px",
                borderRadius: 8,
                background: "rgba(76,175,80,0.12)",
                border: "1px solid rgba(76,175,80,0.3)",
                fontSize: 12,
                fontWeight: 700,
                color: "var(--color-success)",
                letterSpacing: "0.06em",
                marginBottom: 12,
              }}
            >
              <ShieldCheck size={14} />
              STAGE 6 &bull; SMART SETTLEMENT EXECUTED
            </div>
            <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.02em", marginBottom: 8 }}>
              Final Settlement Summary
            </h1>
            <p style={{ color: "var(--color-text-muted)", fontSize: 15 }}>
              Contract <span style={{ fontFamily: "JetBrains Mono, monospace", color: "white" }}>{contractId}</span> has concluded with a rule-based prorated release.
            </p>
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={handleCopyHash}
              style={{
                padding: "10px 16px",
                borderRadius: 10,
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.12)",
                color: "white",
                fontSize: 14,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Share2 size={15} />
              {copied ? "Copied Hash!" : "Share Receipt"}
            </button>
            <button
              className="btn-gradient"
              style={{
                padding: "10px 18px",
                fontSize: 14,
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Download size={15} />
              Export PDF
            </button>
          </div>
        </div>

        {/* Settlement Split Banner */}
        <div className="glass-card" style={{ padding: "32px", marginBottom: 32 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
            <div>
              <span style={{ fontSize: 13, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em" }}>
                TOTAL ESCROW DISBURSED
              </span>
              <div style={{ fontSize: 36, fontWeight: 800, fontFamily: "JetBrains Mono, monospace" }}>
                ${totalEscrow.toLocaleString()}.00
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Settlement Ratio</span>
              <div style={{ fontSize: 20, fontWeight: 700, color: "var(--color-success)" }}>
                80% Paid &bull; 20% Refunded
              </div>
            </div>
          </div>

          {/* Visual Dual Progress Bar */}
          <div style={{ width: "100%", height: 28, borderRadius: 14, background: "rgba(255,255,255,0.08)", overflow: "hidden", display: "flex", marginBottom: 16, border: "1px solid rgba(255,255,255,0.1)" }}>
            <div
              style={{
                width: "80%",
                background: "linear-gradient(90deg, #4CAF50, #00A3E0)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                fontWeight: 700,
                color: "white",
                letterSpacing: "0.04em",
              }}
            >
              FREELANCER PAYOUT: $1,200.00
            </div>
            <div
              style={{
                width: "20%",
                background: "rgba(244,67,54,0.75)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 11,
                fontWeight: 700,
                color: "white",
                letterSpacing: "0.04em",
              }}
            >
              REFUND: $300.00
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 24, paddingTop: 20, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
            <div style={{ background: "rgba(76,175,80,0.08)", padding: "16px 20px", borderRadius: 12, border: "1px solid rgba(76,175,80,0.2)" }}>
              <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 4 }}>Disbursed to Freelancer</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: "var(--color-success)", fontFamily: "JetBrains Mono, monospace" }}>
                +${passedAmount}.00
              </div>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4 }}>
                Instant PayPal payout transaction ref: <span style={{ fontFamily: "JetBrains Mono, monospace" }}>PP-TX-991204</span>
              </div>
            </div>

            <div style={{ background: "rgba(244,67,54,0.08)", padding: "16px 20px", borderRadius: 12, border: "1px solid rgba(244,67,54,0.2)" }}>
              <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 4 }}>Returned to Hirer</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: "#F87171", fontFamily: "JetBrains Mono, monospace" }}>
                ${refundedAmount}.00
              </div>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4 }}>
                Escrow hold authorization unblocked back to primary card.
              </div>
            </div>
          </div>
        </div>

        {/* Feature-by-Feature Settlement Breakdown */}
        <div className="glass-card" style={{ padding: "28px", marginBottom: 32 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
            <Layers size={18} color="var(--color-primary)" />
            Feature-Level Settlement Ledger
          </h2>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "var(--color-text-muted)", fontSize: 12 }}>
                  <th style={{ padding: "12px 14px" }}>DELIVERABLE MILESTONE</th>
                  <th style={{ padding: "12px 14px" }}>WEIGHT</th>
                  <th style={{ padding: "12px 14px" }}>VERIFICATION SCORE</th>
                  <th style={{ padding: "12px 14px" }}>STATUS</th>
                  <th style={{ padding: "12px 14px", textAlign: "right" }}>SETTLED SUM</th>
                </tr>
              </thead>
              <tbody>
                {features.map((f, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                    <td style={{ padding: "16px 14px", fontWeight: 600 }}>{f.name}</td>
                    <td style={{ padding: "16px 14px", color: "var(--color-text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                      {f.weight}%
                    </td>
                    <td style={{ padding: "16px 14px", fontSize: 13, color: f.status === "PASSED" ? "var(--color-text-secondary)" : "#FCA5A5" }}>
                      {f.score}
                    </td>
                    <td style={{ padding: "16px 14px" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "4px 8px",
                          borderRadius: 6,
                          fontSize: 12,
                          fontWeight: 700,
                          background: f.status === "PASSED" ? "rgba(76,175,80,0.15)" : "rgba(244,67,54,0.15)",
                          color: f.status === "PASSED" ? "var(--color-success)" : "var(--color-danger)",
                        }}
                      >
                        {f.status === "PASSED" ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                        {f.status}
                      </span>
                    </td>
                    <td style={{ padding: "16px 14px", textAlign: "right", fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>
                      {f.status === "PASSED" ? `$${f.payout}.00` : "$0.00 (Refunded)"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Cryptographic Proof of Settlement */}
        <div className="glass-card" style={{ padding: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <FileText size={18} color="var(--color-secondary)" />
            <h2 style={{ fontSize: 16, fontWeight: 700, letterSpacing: "0.04em" }}>
              CRYPTOGRAPHIC SETTLEMENT RECEIPT (SHA-256)
            </h2>
          </div>
          <div
            style={{
              background: "rgba(0,0,0,0.4)",
              borderRadius: 10,
              padding: "16px 20px",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 12,
              color: "#94A3B8",
              lineHeight: 1.8,
              border: "1px solid rgba(255,255,255,0.06)",
              wordBreak: "break-all",
            }}
          >
            <div><strong>HASH:</strong> {shaHash}</div>
            <div><strong>TIMESTAMP:</strong> 2026-11-09T18:42:15.109Z</div>
            <div><strong>REFEREE_ENGINE:</strong> PactPal-Referee-v2.4-gVisor-isolated</div>
            <div><strong>PAYPAL_SETTLEMENT_BATCH:</strong> BATCH_8941_RELEASE_ESCROW</div>
            <div style={{ color: "var(--color-success)", marginTop: 8 }}>
              &gt; STATUS: IMMUTABLE & TAMPER-EVIDENT RECORD SECURED
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

