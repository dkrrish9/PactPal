"use client";
import { ArrowRight } from "lucide-react";

export default function DualCTAFinale() {
  return (
    <section
      style={{
        padding: "120px 24px",
        position: "relative",
        overflow: "hidden",
        textAlign: "center",
      }}
      aria-labelledby="finale-heading"
    >
      {/* Background gradient band */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(135deg, rgba(0,102,255,0.08) 0%, rgba(122,92,255,0.06) 50%, rgba(255,152,0,0.06) 100%)",
          borderTop: "1px solid rgba(255,255,255,0.06)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
        aria-hidden
      />
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: 700,
          height: 400,
          background:
            "radial-gradient(ellipse, rgba(0,102,255,0.12) 0%, transparent 70%)",
          filter: "blur(80px)",
          pointerEvents: "none",
        }}
        aria-hidden
      />

      <div style={{ position: "relative", zIndex: 1, maxWidth: 800, margin: "0 auto" }}>
        <p
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "var(--color-text-muted)",
            marginBottom: "24px",
          }}
        >
          Enough trust exercises
        </p>

        <h2
          id="finale-heading"
          style={{
            fontSize: "clamp(48px, 7vw, 88px)",
            fontWeight: 900,
            letterSpacing: "-0.03em",
            color: "white",
            lineHeight: 1.05,
            marginBottom: "20px",
          }}
        >
          Ready to make a pact?
        </h2>

        <p
          style={{
            fontSize: 20,
            color: "var(--color-text-secondary)",
            marginBottom: "52px",
            lineHeight: 1.6,
          }}
        >
          Money held. Work verified. Everyone paid.
        </p>

        <div
          style={{
            display: "flex",
            gap: "16px",
            justifyContent: "center",
            flexWrap: "wrap",
          }}
        >
          <a
            href="/hire"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "white",
              color: "#070B16",
              borderRadius: "50px",
              padding: "16px 32px",
              fontSize: 16,
              fontWeight: 700,
              textDecoration: "none",
              transition: "all 0.3s ease",
              boxShadow: "0 0 30px rgba(255,255,255,0.2)",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget.style.transform = "translateY(-2px)");
              (e.currentTarget.style.boxShadow = "0 10px 40px rgba(255,255,255,0.3)");
            }}
            onMouseLeave={(e) => {
              (e.currentTarget.style.transform = "none");
              (e.currentTarget.style.boxShadow = "0 0 30px rgba(255,255,255,0.2)");
            }}
            aria-label="Hire a freelancer"
          >
            Hire a Freelancer <ArrowRight size={18} aria-hidden />
          </a>

          <a
            href="/work"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "linear-gradient(135deg, #0066FF, #00A3E0)",
              color: "white",
              borderRadius: "50px",
              padding: "16px 32px",
              fontSize: 16,
              fontWeight: 700,
              textDecoration: "none",
              transition: "all 0.3s ease",
              boxShadow: "0 0 30px rgba(0,102,255,0.4)",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget.style.transform = "translateY(-2px)");
              (e.currentTarget.style.boxShadow = "0 10px 40px rgba(0,102,255,0.5)");
            }}
            onMouseLeave={(e) => {
              (e.currentTarget.style.transform = "none");
              (e.currentTarget.style.boxShadow = "0 0 30px rgba(0,102,255,0.4)");
            }}
            aria-label="Earn money freelancing"
          >
            Earn Money Freelancing <ArrowRight size={18} aria-hidden />
          </a>
        </div>
      </div>
    </section>
  );
}

