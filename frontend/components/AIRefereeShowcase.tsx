"use client";

export default function AIRefereeShowcase() {
  return (
    <section
      style={{
        background: "var(--color-surface-1)",
        borderTop: "1px solid rgba(255,255,255,0.05)",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        padding: "120px 24px",
        position: "relative",
        overflow: "hidden",
      }}
      aria-labelledby="referee-heading"
    >
      {/* Background glow */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: 600,
          height: 400,
          background: "radial-gradient(ellipse, rgba(0,102,255,0.1) 0%, transparent 70%)",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
        aria-hidden
      />

      <div style={{ maxWidth: 1280, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: "72px" }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "var(--color-text-muted)",
              marginBottom: "16px",
            }}
          >
            The AI Referee
          </p>
          <h2
            id="referee-heading"
            style={{
              fontSize: "clamp(36px, 5vw, 60px)",
              fontWeight: 900,
              letterSpacing: "-0.025em",
              color: "white",
            }}
          >
            Doesn&apos;t take sides.{" "}
            <span className="gradient-text">Takes receipts.</span>
          </h2>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "32px",
            alignItems: "start",
          }}
        >
          {/* Referee live log */}
          <div
            style={{
              background: "rgba(0,0,0,0.4)",
              border: "1px solid rgba(0,102,255,0.2)",
              borderRadius: "24px",
              padding: "28px",
              fontFamily: "JetBrains Mono, monospace",
            }}
            role="log"
            aria-label="AI Referee verification log"
            aria-live="polite"
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "20px",
              }}
            >
              <div style={{ display: "flex", gap: "6px" }} aria-hidden>
                {["#F44336", "#FF9800", "#4CAF50"].map((c) => (
                  <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />
                ))}
              </div>
              <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>referee.log</span>
            </div>

            {[
              { time: "14:32:01", text: "→ Checking Feature 1: Landing page...", color: "#B8C2D9" },
              { time: "14:32:04", text: "✓ PASSED. All acceptance tests met.", color: "#4CAF50" },
              { time: "14:32:05", text: "→ Checking Feature 2: Dashboard...", color: "#B8C2D9" },
              { time: "14:32:09", text: "✓ PASSED. Visual match 97%.", color: "#4CAF50" },
              { time: "14:32:10", text: "→ Checking Feature 3: Login...", color: "#B8C2D9" },
              { time: "14:32:14", text: "✗ FAILED. Hardcoded response detected (HIGH severity).", color: "#F44336" },
              { time: "14:32:15", text: "⚡ Cheat type: mock return, not real auth.", color: "#FF9800" },
              { time: "14:32:16", text: "→ Checking Feature 4: Payments...", color: "#B8C2D9" },
              { time: "14:32:19", text: "✓ PASSED. PayPal integration verified.", color: "#4CAF50" },
            ].map((line, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  gap: "14px",
                  marginBottom: "8px",
                  fontSize: 13,
                  lineHeight: 1.5,
                }}
              >
                <span style={{ color: "var(--color-text-muted)", flexShrink: 0 }}>{line.time}</span>
                <span style={{ color: line.color }}>{line.text}</span>
              </div>
            ))}

            <div
              style={{
                marginTop: "16px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
              aria-hidden
            >
              <span style={{ color: "#0066FF" }}>_</span>
              <div
                style={{
                  width: 8,
                  height: 16,
                  background: "#0066FF",
                  animation: "pulse 1s infinite",
                }}
              />
            </div>
          </div>

          {/* Referee offer card */}
          <div
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(0,102,255,0.2)",
              borderRadius: "24px",
              padding: "32px",
              boxShadow: "0 0 40px rgba(0,102,255,0.1)",
            }}
            role="dialog"
            aria-label="Referee settlement offer"
          >
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "rgba(0,102,255,0.1)",
                border: "1px solid rgba(0,102,255,0.3)",
                borderRadius: "50px",
                padding: "6px 14px",
                fontSize: 12,
                fontWeight: 700,
                color: "#60A5FA",
                marginBottom: "24px",
              }}
            >
              ⚖ AI Referee Decision
            </div>

            <h3
              style={{
                fontSize: 22,
                fontWeight: 800,
                color: "white",
                marginBottom: "12px",
                lineHeight: 1.3,
              }}
            >
              3 of 4 features passed.
            </h3>
            <p
              style={{
                fontSize: 15,
                color: "var(--color-text-secondary)",
                lineHeight: 1.6,
                marginBottom: "32px",
              }}
            >
              Release <strong style={{ color: "#4CAF50" }}>80% now ($1,200)</strong>, or give the
              seller a chance to fix Feature 3 and resubmit?
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <button
                style={{
                  background: "linear-gradient(135deg, #4CAF50, #81C784)",
                  border: "none",
                  borderRadius: "12px",
                  color: "white",
                  padding: "14px 20px",
                  fontSize: 15,
                  fontWeight: 700,
                  cursor: "pointer",
                  textAlign: "left",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
                aria-label="Accept 80% payout"
              >
                <span>Accept 80% — Release $1,200</span>
                <span style={{ fontSize: 20 }}>→</span>
              </button>
              <button
                style={{
                  background: "rgba(255,152,0,0.08)",
                  border: "1px solid rgba(255,152,0,0.3)",
                  borderRadius: "12px",
                  color: "#FF9800",
                  padding: "14px 20px",
                  fontSize: 15,
                  fontWeight: 600,
                  cursor: "pointer",
                  textAlign: "left",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
                aria-label="Fix and resubmit"
              >
                <span>Fix Feature 3 & resubmit</span>
                <span>↩</span>
              </button>
            </div>

            <div
              style={{
                marginTop: "24px",
                display: "flex",
                gap: "24px",
                fontSize: 12,
                color: "var(--color-text-muted)",
              }}
            >
              <span>✓ Negotiated partial release</span>
              <span>✓ Rules-based, not a black box</span>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          [style*="grid-template-columns: 1fr 1fr"] {
            grid-template-columns: 1fr !important;
          }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </section>
  );
}

