"use client";

const benefits = [
  {
    num: "01",
    icon: "💰",
    title: "Money locked, not promised",
    desc: "The buyer's funds are secured before the first line gets written.",
    stat: "ESCROW FUNDED",
    statVal: "$1,500.00",
    color: "#0066FF",
  },
  {
    num: "02",
    icon: "🤖",
    title: "Work checked by an AI Referee",
    desc: "Code tests, cheat detection, and pixel-level visual matching.",
    stat: "VERIFICATION",
    statVal: "6 checks running",
    color: "#00A3E0",
  },
  {
    num: "03",
    icon: "⚡",
    title: "Fair pay, automatically",
    desc: "Passed features pay out. The rest is returned. No all-or-nothing drama.",
    stat: "SMART SPLIT",
    statVal: "80% / 20%",
    color: "#FF9800",
  },
  {
    num: "04",
    icon: "🔏",
    title: "Proof you can show anyone",
    desc: "Every outcome includes a signed, tamper-evident work receipt.",
    stat: "RECEIPT",
    statVal: "0xA9F3...082C",
    color: "#7A5CFF",
  },
];

export default function BenefitCards() {
  return (
    <section
      style={{
        padding: "120px 24px",
        maxWidth: 1280,
        margin: "0 auto",
      }}
      aria-labelledby="benefits-heading"
    >
      {/* Section header */}
      <div style={{ marginBottom: "64px" }}>
        <h2
          id="benefits-heading"
          style={{
            fontSize: "clamp(36px, 5vw, 60px)",
            fontWeight: 900,
            letterSpacing: "-0.025em",
            lineHeight: 1.1,
            color: "white",
            maxWidth: 700,
          }}
        >
          Make it real.{" "}
          <span className="gradient-text-orange">Keep it fair.</span>
        </h2>
        <p
          style={{
            marginTop: "16px",
            fontSize: 18,
            color: "var(--color-text-secondary)",
            maxWidth: 480,
            lineHeight: 1.6,
          }}
        >
          No vague promises. Just funded milestones, explicit checks, and receipts
          both sides can trust.
        </p>
      </div>

      {/* Cards grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "20px",
        }}
        role="list"
      >
        {benefits.map((b) => (
          <article
            key={b.num}
            role="listitem"
            style={{
              background: "rgba(255,255,255,0.03)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(255,255,255,0.07)",
              borderRadius: "24px",
              padding: "32px",
              transition: "all 0.3s ease",
              cursor: "default",
              position: "relative",
              overflow: "hidden",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget.style.borderColor = `${b.color}44`);
              (e.currentTarget.style.boxShadow = `0 0 40px ${b.color}18`);
              (e.currentTarget.style.transform = "translateY(-3px)");
            }}
            onMouseLeave={(e) => {
              (e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)");
              (e.currentTarget.style.boxShadow = "none");
              (e.currentTarget.style.transform = "none");
            }}
            aria-label={b.title}
          >
            {/* Number */}
            <div
              style={{
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.1em",
                color: "var(--color-text-muted)",
                marginBottom: "24px",
                fontFamily: "JetBrains Mono, monospace",
              }}
              aria-hidden
            >
              {b.num}
            </div>

            {/* Icon */}
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: "16px",
                background: `${b.color}18`,
                border: `1px solid ${b.color}30`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 24,
                marginBottom: "20px",
              }}
              aria-hidden
            >
              {b.icon}
            </div>

            <h3
              style={{
                fontSize: 20,
                fontWeight: 700,
                color: "white",
                marginBottom: "10px",
                lineHeight: 1.3,
              }}
            >
              {b.title}
            </h3>
            <p
              style={{
                fontSize: 14,
                color: "var(--color-text-secondary)",
                lineHeight: 1.65,
                marginBottom: "28px",
              }}
            >
              {b.desc}
            </p>

            {/* Stat */}
            <div
              style={{
                borderTop: "1px solid rgba(255,255,255,0.07)",
                paddingTop: "16px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: "0.08em",
                  color: "var(--color-text-muted)",
                  textTransform: "uppercase",
                }}
              >
                {b.stat}
              </span>
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: b.color,
                  fontFamily: "JetBrains Mono, monospace",
                }}
                aria-label={`${b.stat}: ${b.statVal}`}
              >
                {b.statVal}
              </span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

