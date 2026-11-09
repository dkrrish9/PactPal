"use client";
import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { 
  ArrowLeft, 
  AlertTriangle, 
  ShieldAlert, 
  Send, 
  Upload, 
  CheckCircle2, 
  MessageSquare,
  FileCode,
  Scale,
  Clock
} from "lucide-react";

export default function DisputePage() {
  const params = useParams();
  const contractId = (params?.id as string) || "pct_099e77";

  const [evidenceText, setEvidenceText] = useState("");
  const [evidenceSubmitted, setEvidenceSubmitted] = useState(false);
  const [selectedResolution, setSelectedResolution] = useState<string | null>(null);

  const handleEvidenceSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!evidenceText) return;
    setEvidenceSubmitted(true);
    setEvidenceText("");
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

        {/* Dispute Notice Banner */}
        <div
          style={{
            padding: "24px 28px",
            borderRadius: 16,
            background: "rgba(255, 152, 0, 0.08)",
            border: "1px solid rgba(255, 152, 0, 0.3)",
            marginBottom: 32,
            display: "flex",
            gap: 20,
            alignItems: "flex-start",
          }}
        >
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: "rgba(255, 152, 0, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <AlertTriangle size={24} color="var(--color-accent)" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--color-accent)", letterSpacing: "0.08em" }}>
                ARBITRATION CASE ACTIVE
              </span>
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>&bull; Case ID: DSP-89021</span>
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>
              Dispute Mediation: Automated AST Cheat Detected
            </h1>
            <p style={{ color: "var(--color-text-secondary)", fontSize: 14, lineHeight: 1.6 }}>
              The AI Referee flagged Feature 4 (&ldquo;Real-time Notification Service&rdquo;). AST scanning discovered hardcoded mock return statements bypassing backend Redis subscriptions.
            </p>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 24, marginBottom: 32 }}>
          
          {/* Left Column: Referee Finding & Settlement Choice */}
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            
            {/* The Referee Decision Card */}
            <div className="glass-card" style={{ padding: "28px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                <Scale size={20} color="var(--color-primary)" />
                <h2 style={{ fontSize: 18, fontWeight: 800 }}>AI Referee Settlement Offer</h2>
              </div>

              <p style={{ fontSize: 14, color: "var(--color-text-secondary)", lineHeight: 1.6, marginBottom: 20 }}>
                Based on objective test runners and visual diffing, 3 of 4 features passed completely (80% weighted total). The Referee offers three resolution pathways:
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {[
                  {
                    id: "partial",
                    title: "Accept 80% Partial Settlement Now",
                    desc: "Releases $1,200.00 to the seller immediately. Refunds $300.00 back to the buyer. Zero penalty strikes.",
                    recommended: true,
                  },
                  {
                    id: "cure",
                    title: "Grant 48-Hour Cure Period",
                    desc: "Freeze settlement and allow the freelancer 48 hours to fix the Redis integration and resubmit code.",
                    recommended: false,
                  },
                  {
                    id: "escalate",
                    title: "Escalate to Human Arbitration Panel",
                    desc: "Submit case to 3-member neutral developer panel. $75 escrow arbitration deposit required.",
                    recommended: false,
                  },
                ].map((opt) => (
                  <div
                    key={opt.id}
                    onClick={() => setSelectedResolution(opt.id)}
                    style={{
                      padding: "16px 18px",
                      borderRadius: 12,
                      background: selectedResolution === opt.id ? "rgba(0,102,255,0.12)" : "rgba(255,255,255,0.03)",
                      border: selectedResolution === opt.id ? "1px solid var(--color-primary)" : "1px solid rgba(255,255,255,0.08)",
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                      <div style={{ fontWeight: 700, fontSize: 14, color: "white" }}>{opt.title}</div>
                      {opt.recommended && (
                        <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 4, background: "rgba(76,175,80,0.15)", color: "var(--color-success)" }}>
                          RECOMMENDED
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, color: "var(--color-text-muted)", lineHeight: 1.5 }}>
                      {opt.desc}
                    </div>
                  </div>
                ))}
              </div>

              {selectedResolution && (
                <div style={{ marginTop: 20 }}>
                  <Link
                    href={`/contracts/${contractId}/settlement`}
                    className="btn-gradient"
                    style={{
                      width: "100%",
                      padding: "12px",
                      display: "block",
                      textAlign: "center",
                      textDecoration: "none",
                      fontSize: 14,
                      fontWeight: 700,
                    }}
                  >
                    Confirm Resolution ({selectedResolution.toUpperCase()}) →
                  </Link>
                </div>
              )}
            </div>

            {/* AST Code Diff Inspector */}
            <div className="glass-card" style={{ padding: "24px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                <FileCode size={18} color="var(--color-danger)" />
                <h3 style={{ fontSize: 15, fontWeight: 700 }}>Referee Flagged Code Snippet</h3>
              </div>
              <div
                style={{
                  background: "rgba(0,0,0,0.4)",
                  borderRadius: 8,
                  padding: "14px",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 12,
                  border: "1px solid rgba(244,67,54,0.2)",
                  color: "#FCA5A5",
                  lineHeight: 1.6,
                }}
              >
                <div>// src/services/notifications.ts (Line 42)</div>
                <div style={{ color: "#EF4444", textDecoration: "line-through" }}>
                  - const sub = redis.subscribe(&apos;notifications&apos;);
                </div>
                <div style={{ color: "var(--color-accent)" }}>
                  + return &#123; status: 200, count: 4, mock: true &#125;; // [FLAG: Bypassed Network]
                </div>
              </div>
            </div>

          </div>

          {/* Right Column: Evidence & Communication */}
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            
            <div className="glass-card" style={{ padding: "24px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
                <MessageSquare size={18} color="var(--color-secondary)" />
                <h3 style={{ fontSize: 15, fontWeight: 700 }}>Submit Counter-Evidence</h3>
              </div>

              {evidenceSubmitted ? (
                <div
                  style={{
                    padding: "16px",
                    borderRadius: 10,
                    background: "rgba(76,175,80,0.1)",
                    border: "1px solid rgba(76,175,80,0.3)",
                    color: "var(--color-success)",
                    fontSize: 13,
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <CheckCircle2 size={16} />
                  Counter-evidence logged in SHA-256 audit docket.
                </div>
              ) : (
                <form onSubmit={handleEvidenceSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <textarea
                    rows={4}
                    value={evidenceText}
                    onChange={(e) => setEvidenceText(e.target.value)}
                    placeholder="Explain why this behavior occurred or provide alternate test reproduction steps..."
                    style={{
                      width: "100%",
                      padding: "12px",
                      borderRadius: 10,
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(255,255,255,0.1)",
                      color: "white",
                      fontSize: 13,
                      outline: "none",
                      resize: "none",
                    }}
                  />
                  <button
                    type="submit"
                    style={{
                      padding: "10px",
                      borderRadius: 8,
                      background: "rgba(255,255,255,0.08)",
                      border: "1px solid rgba(255,255,255,0.15)",
                      color: "white",
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                    }}
                  >
                    <Send size={14} /> Send to Docket
                  </button>
                </form>
              )}
            </div>

            {/* Escrow Status Summary Box */}
            <div className="glass-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <Clock size={16} color="var(--color-text-muted)" />
                <span style={{ fontSize: 13, fontWeight: 700, color: "var(--color-text-secondary)" }}>
                  29-DAY HOLD CLOCK
                </span>
              </div>
              <div style={{ fontSize: 22, fontWeight: 800, fontFamily: "JetBrains Mono, monospace", marginBottom: 6 }}>
                18 DAYS REMAINING
              </div>
              <p style={{ fontSize: 12, color: "var(--color-text-muted)", lineHeight: 1.5 }}>
                If no resolution is selected within 18 days, PactPal auto-executes the AI Referee recommendation.
              </p>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}
