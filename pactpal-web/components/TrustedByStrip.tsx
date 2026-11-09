"use client";

const logos = [
  "ARCFORM", "NORTH★STAR", "MONUMENT", "FOLD", "MERIDIAN",
  "STRATUM", "KAIROS", "NEXUS", "VELA", "CIPHER",
  "ARCFORM", "NORTH★STAR", "MONUMENT", "FOLD", "MERIDIAN",
  "STRATUM", "KAIROS", "NEXUS", "VELA", "CIPHER",
];

export default function TrustedByStrip() {
  return (
    <section
      style={{
        padding: "60px 0",
        borderTop: "1px solid rgba(255,255,255,0.05)",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        overflow: "hidden",
        position: "relative",
      }}
      aria-label="Trusted by companies worldwide"
    >
      <p
        style={{
          textAlign: "center",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: "var(--color-text-muted)",
          marginBottom: "32px",
        }}
      >
        Trusted by builders and teams worldwide
      </p>

      {/* Edge fades */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          bottom: 0,
          width: 160,
          background: "linear-gradient(to right, var(--color-bg), transparent)",
          zIndex: 2,
          pointerEvents: "none",
        }}
        aria-hidden
      />
      <div
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          bottom: 0,
          width: 160,
          background: "linear-gradient(to left, var(--color-bg), transparent)",
          zIndex: 2,
          pointerEvents: "none",
        }}
        aria-hidden
      />

      <div style={{ overflow: "hidden" }}>
        <div
          className="marquee-track"
          style={{
            display: "flex",
            gap: "60px",
            alignItems: "center",
            width: "max-content",
          }}
          aria-hidden
        >
          {logos.map((logo, i) => (
            <span
              key={i}
              style={{
                fontSize: 15,
                fontWeight: 800,
                letterSpacing: "0.08em",
                color: "rgba(124, 137, 168, 0.5)",
                whiteSpace: "nowrap",
                userSelect: "none",
              }}
            >
              {logo}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

