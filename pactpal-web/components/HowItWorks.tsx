"use client";
import { useState } from "react";
import { CheckCircle, Circle } from "lucide-react";

const steps = [
  {
    num: "01",
    title: "Sign the pact",
    desc: "Define features with weighted acceptance tests that add to 100%.",
    mock: <ChecklistMock />,
  },
  {
    num: "02",
    title: "Freeze the funds",
    desc: "PayPal authorization locks the money. 29-day hold begins.",
    mock: <EscrowMock />,
  },
  {
    num: "03",
    title: "Build & negotiate",
    desc: "AI prices scope changes in real time — no guesswork.",
    mock: <ChatMock />,
  },
  {
    num: "04",
    title: "Submit & verify",
    desc: "6-stage AI verification: build, tests, cheat scan, visual diff.",
    mock: <VerifyMock />,
  },
  {
    num: "05",
    title: "Smart settlement",
    desc: "Passed features pay out instantly. Failed features refunded.",
    mock: <SettlementMock />,
  },
  {
    num: "06",
    title: "Receipt",
    desc: "SHA-256 proof-of-work. Tamper-evident, permanent.",
    mock: <ReceiptMock />,
  },
];

export default function HowItWorks() {
  const [active, setActive] = useState(0);

  return (
    <section
      style={{
        padding: "120px 24px",
        maxWidth: 1280,
        margin: "0 auto",
      }}
      aria-labelledby="how-heading"
    >
      {/* Header */}
      <div style={{ marginBottom: "72px", textAlign: "center" }}>
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
          How it works
        </p>
        <h2
          id="how-heading"
          style={{
            fontSize: "clamp(36px, 5vw, 60px)",
            fontWeight: 900,
            letterSpacing: "-0.025em",
            color: "white",
          }}
        >
          Six steps.{" "}
          <span className="gradient-text">Zero trust required.</span>
        </h2>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "60px",
          alignItems: "start",
        }}
      >
        {/* Step list */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }} role="tablist" aria-label="How it works steps">
          {steps.map((step, i) => (
            <button
              key={i}
              role="tab"
              aria-selected={active === i}
              aria-controls={`step-panel-${i}`}
              id={`step-tab-${i}`}
              onClick={() => setActive(i)}
              style={{
                background: active === i ? "rgba(0,102,255,0.08)" : "transparent",
                border: active === i
                  ? "1px solid rgba(0,102,255,0.25)"
                  : "1px solid transparent",
                borderRadius: "16px",
                padding: "20px 24px",
                textAlign: "left",
                cursor: "pointer",
                transition: "all 0.25s ease",
                display: "flex",
                gap: "20px",
                alignItems: "flex-start",
              }}
            >
              {/* Progress dot */}
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: active === i ? "rgba(0,102,255,0.2)" : "rgba(255,255,255,0.05)",
                  border: `2px solid ${active === i ? "#0066FF" : "rgba(255,255,255,0.1)"}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  transition: "all 0.3s",
                }}
                aria-hidden
              >
                {i < active ? (
                  <CheckCircle size={16} color="#4CAF50" />
                ) : (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: active === i ? "#0066FF" : "var(--color-text-muted)",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {step.num}
                  </span>
                )}
              </div>

              <div>
                <div
                  style={{
                    fontWeight: 700,
                    fontSize: 16,
                    color: active === i ? "white" : "var(--color-text-secondary)",
                    marginBottom: "4px",
                    transition: "color 0.2s",
                  }}
                >
                  {step.title}
                </div>
                <div
                  style={{
                    fontSize: 14,
                    color: "var(--color-text-muted)",
                    lineHeight: 1.5,
                  }}
                >
                  {step.desc}
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Mock panel */}
        <div
          id={`step-panel-${active}`}
          role="tabpanel"
          aria-labelledby={`step-tab-${active}`}
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "24px",
            padding: "32px",
            minHeight: 380,
            position: "sticky",
            top: "88px",
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", color: "var(--color-text-muted)", marginBottom: "20px" }}>
            STEP {steps[active].num} — {steps[active].title.toUpperCase()}
          </div>
          {steps[active].mock}
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          [style*="grid-template-columns: 1fr 1fr"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </section>
  );
}

function ChecklistMock() {
  const features = [
    { name: "Landing page", weight: 25 },
    { name: "Login system", weight: 20 },
    { name: "Dashboard", weight: 30 },
    { name: "Payment flow", weight: 25 },
  ];
  const total = features.reduce((s, f) => s + f.weight, 0);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {features.map((f) => (
        <div
          key={f.name}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.07)",
            borderRadius: "12px",
            padding: "14px 16px",
          }}
        >
          <span style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>{f.name}</span>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                height: 6,
                width: 80,
                background: "rgba(255,255,255,0.08)",
                borderRadius: 3,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${f.weight}%`,
                  background: "linear-gradient(90deg, #0066FF, #00A3E0)",
                  borderRadius: 3,
                }}
              />
            </div>
            <span
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "white",
                fontFamily: "JetBrains Mono, monospace",
                width: 32,
                textAlign: "right",
              }}
            >
              {f.weight}%
            </span>
          </div>
        </div>
      ))}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          paddingTop: "12px",
          gap: "8px",
          alignItems: "center",
        }}
      >
        <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Total:</span>
        <span
          style={{
            fontSize: 18,
            fontWeight: 800,
            color: total === 100 ? "#4CAF50" : "#F44336",
            fontFamily: "JetBrains Mono, monospace",
          }}
        >
          {total}%
        </span>
        {total === 100 && <CheckCircle size={18} color="#4CAF50" />}
      </div>
    </div>
  );
}

function EscrowMock() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "20px", paddingTop: "16px" }}>
      {/* Countdown ring */}
      <div
        style={{
          width: 140,
          height: 140,
          borderRadius: "50%",
          border: "4px solid rgba(255,152,0,0.2)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          boxShadow: "0 0 40px rgba(255,152,0,0.3)",
        }}
        aria-label="29-day countdown ring"
      >
        <svg
          style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}
          viewBox="0 0 140 140"
          aria-hidden
        >
          <circle
            cx="70" cy="70" r="66"
            fill="none"
            stroke="#FF9800"
            strokeWidth="4"
            strokeDasharray="414"
            strokeDashoffset="100"
            strokeLinecap="round"
            transform="rotate(-90 70 70)"
            style={{ opacity: 0.8 }}
          />
        </svg>
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 36,
              fontWeight: 900,
              color: "#FF9800",
              fontFamily: "JetBrains Mono, monospace",
              lineHeight: 1,
            }}
          >
            29
          </div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: "4px" }}>days left</div>
        </div>
      </div>

      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 24, fontWeight: 800, color: "white" }}>$1,500.00 held</div>
        <div style={{ fontSize: 14, color: "var(--color-text-muted)", marginTop: "4px" }}>
          PayPal authorization active
        </div>
      </div>

      <div
        style={{
          background: "rgba(255,152,0,0.08)",
          border: "1px solid rgba(255,152,0,0.2)",
          borderRadius: "12px",
          padding: "12px 20px",
          fontSize: 13,
          color: "#FF9800",
          fontWeight: 600,
        }}
        role="status"
      >
        🔒 Funds secured via PayPal AUTHORIZE intent
      </div>
    </div>
  );
}

function ChatMock() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      {[
        { from: "Buyer", msg: "Can you add dark mode too?", type: "user" },
        { from: "AI Referee", msg: "Dark mode estimated: +$120, +3 days. Approve?", type: "ai" },
        { from: "Seller", msg: "I can do it for $100, 2 days.", type: "user" },
        { from: "AI Referee", msg: "Counter accepted. New hold: +$100 authorized.", type: "ai" },
      ].map((m, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: m.type === "ai" ? "flex-start" : "flex-end",
          }}
        >
          <span
            style={{
              fontSize: 11,
              color: "var(--color-text-muted)",
              marginBottom: "4px",
              fontWeight: 600,
            }}
          >
            {m.from}
          </span>
          <div
            style={{
              background: m.type === "ai"
                ? "rgba(0,102,255,0.08)"
                : "rgba(255,255,255,0.05)",
              border: m.type === "ai"
                ? "1px solid rgba(0,102,255,0.25)"
                : "1px solid rgba(255,255,255,0.08)",
              borderRadius: "12px",
              padding: "10px 14px",
              fontSize: 14,
              color: m.type === "ai" ? "#60A5FA" : "var(--color-text-secondary)",
              maxWidth: "80%",
              boxShadow: m.type === "ai" ? "0 0 20px rgba(0,102,255,0.1)" : "none",
            }}
          >
            {m.msg}
          </div>
        </div>
      ))}
    </div>
  );
}

function VerifyMock() {
  const stages = [
    { label: "A: Git clone & intake", status: "passed" },
    { label: "B: Clean build", status: "passed" },
    { label: "C: Test suite", status: "passed" },
    { label: "D: Cheat scan", status: "failed", note: "Hardcoded response (HIGH)" },
    { label: "E: Figma visual diff", status: "running" },
    { label: "F: QA report", status: "pending" },
  ];
  const colors: Record<string, string> = {
    passed: "#4CAF50",
    failed: "#F44336",
    running: "#0066FF",
    pending: "#7C89A8",
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {stages.map((s, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            background: "rgba(255,255,255,0.03)",
            border: `1px solid ${colors[s.status]}22`,
            borderRadius: "10px",
            padding: "10px 14px",
          }}
          role="status"
          aria-label={`Stage ${s.label}: ${s.status}`}
        >
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: colors[s.status],
              boxShadow: `0 0 8px ${colors[s.status]}`,
              flexShrink: 0,
            }}
            aria-hidden
          />
          <div style={{ flex: 1 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>{s.label}</span>
            {s.note && (
              <span
                style={{
                  marginLeft: "8px",
                  fontSize: 11,
                  color: "#F44336",
                  fontWeight: 600,
                }}
              >
                ⚠ {s.note}
              </span>
            )}
          </div>
          <span
            className={s.status === "running" ? "shimmer" : ""}
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: colors[s.status],
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}
          >
            {s.status}
          </span>
        </div>
      ))}
    </div>
  );
}

function SettlementMock() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
          <span style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>Paid to freelancer</span>
          <span style={{ fontSize: 16, fontWeight: 700, color: "#4CAF50" }}>$1,200</span>
        </div>
        <div
          style={{
            height: 12,
            background: "rgba(255,255,255,0.08)",
            borderRadius: 6,
            overflow: "hidden",
          }}
          role="progressbar"
          aria-valuenow={80}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="80% paid"
        >
          <div
            style={{
              height: "100%",
              width: "80%",
              background: "linear-gradient(90deg, #4CAF50, #81C784)",
              borderRadius: 6,
            }}
          />
        </div>
      </div>

      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
          <span style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>Refunded to buyer</span>
          <span style={{ fontSize: 16, fontWeight: 700, color: "#F44336" }}>$300</span>
        </div>
        <div
          style={{
            height: 12,
            background: "rgba(255,255,255,0.08)",
            borderRadius: 6,
            overflow: "hidden",
          }}
          role="progressbar"
          aria-valuenow={20}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="20% refunded"
        >
          <div
            style={{
              height: "100%",
              width: "20%",
              background: "linear-gradient(90deg, #F44336, #EF9A9A)",
              borderRadius: 6,
            }}
          />
        </div>
      </div>

      <div
        style={{
          background: "rgba(76,175,80,0.08)",
          border: "1px solid rgba(76,175,80,0.2)",
          borderRadius: "12px",
          padding: "16px",
          display: "flex",
          gap: "12px",
          alignItems: "center",
        }}
        role="status"
      >
        <span style={{ fontSize: 20 }} aria-hidden>✅</span>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#4CAF50" }}>Settlement complete</div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>3 of 4 features passed — 80% released</div>
        </div>
      </div>
    </div>
  );
}

function ReceiptMock() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <div
        style={{
          background: "rgba(122,92,255,0.08)",
          border: "1px solid rgba(122,92,255,0.2)",
          borderRadius: "12px",
          padding: "16px",
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", color: "var(--color-text-muted)", marginBottom: "8px" }}>
          SHA-256 FINGERPRINT
        </div>
        <div
          className="mono"
          style={{
            fontSize: 13,
            color: "#A78BFA",
            wordBreak: "break-all",
            lineHeight: 1.5,
          }}
          role="textbox"
          aria-label="SHA-256 fingerprint"
        >
          0xa9f3e8c2d4b1...082c
        </div>
      </div>
      {[
        ["Features passed", "3 / 4"],
        ["Seller payout", "$1,200.00"],
        ["Buyer refund", "$300.00"],
        ["Visual match", "94%"],
      ].map(([k, v]) => (
        <div
          key={k}
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 14,
            borderBottom: "1px solid rgba(255,255,255,0.05)",
            paddingBottom: "12px",
          }}
        >
          <span style={{ color: "var(--color-text-muted)" }}>{k}</span>
          <span style={{ fontWeight: 600, color: "white" }}>{v}</span>
        </div>
      ))}
      <button
        style={{
          background: "none",
          border: "1px solid rgba(122,92,255,0.3)",
          borderRadius: "10px",
          color: "#A78BFA",
          padding: "10px",
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
        }}
        aria-label="View PayPal reference"
      >
        🔗 View PayPal reference
      </button>
    </div>
  );
}

