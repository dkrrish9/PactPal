"use client";
import { useEffect, useRef } from "react";
import { Shield, Code, ArrowRight } from "lucide-react";

const floatingCards = [
  {
    label: "Mobile app design",
    amount: "$1,500",
    days: "20 days",
    pct: "100%",
    color: "#0066FF",
  },
  {
    label: "Landing page build",
    amount: "$500",
    days: "6 days",
    pct: "80%",
    color: "#FF9800",
  },
  {
    label: "API integration",
    amount: "$900",
    days: "11 days",
    receipt: "#A9F3",
    color: "#7A5CFF",
  },
];

export default function HeroSection() {
  return (
    <section
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "120px 24px 80px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background glows */}
      <div
        style={{
          position: "absolute",
          top: "10%",
          left: "15%",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(0,102,255,0.15) 0%, transparent 70%)",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
        aria-hidden
      />
      <div
        style={{
          position: "absolute",
          top: "20%",
          right: "10%",
          width: 400,
          height: 400,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255,152,0,0.12) 0%, transparent 70%)",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
        aria-hidden
      />
      <div
        style={{
          position: "absolute",
          bottom: "10%",
          left: "50%",
          transform: "translateX(-50%)",
          width: 600,
          height: 300,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(122,92,255,0.08) 0%, transparent 70%)",
          filter: "blur(80px)",
          pointerEvents: "none",
        }}
        aria-hidden
      />

      {/* Grid overlay */}
      <div
        className="grid-overlay"
        style={{ position: "absolute", inset: 0, opacity: 0.6, pointerEvents: "none" }}
        aria-hidden
      />

      {/* Pill label */}
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          background: "rgba(0,102,255,0.1)",
          border: "1px solid rgba(0,102,255,0.3)",
          borderRadius: "50px",
          padding: "6px 16px",
          marginBottom: "32px",
          fontSize: 13,
          fontWeight: 600,
          color: "#60A5FA",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
        role="banner"
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "#4CAF50",
            display: "inline-block",
            boxShadow: "0 0 8px #4CAF50",
          }}
          aria-hidden
        />
        AI-refereed escrow for freelancers, live now
      </div>

      {/* H1 */}
      <h1
        style={{
          fontSize: "clamp(52px, 8vw, 96px)",
          fontWeight: 900,
          lineHeight: 1.05,
          letterSpacing: "-0.03em",
          textAlign: "center",
          maxWidth: 900,
          marginBottom: "24px",
          color: "white",
        }}
      >
        Freelance without the{" "}
        <span className="gradient-text">fear.</span>
      </h1>

      {/* Subhead */}
      <p
        style={{
          fontSize: "clamp(16px, 2vw, 20px)",
          color: "var(--color-text-secondary)",
          textAlign: "center",
          maxWidth: 620,
          lineHeight: 1.65,
          marginBottom: "56px",
        }}
      >
        PactPal locks the buyer's money, an AI Referee tests the delivered work, and
        the seller gets paid for exactly what passes. Every decision comes with a
        tamper-proof receipt.
      </p>

      {/* Live ticker pill */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          background: "rgba(0,102,255,0.08)",
          border: "1px solid rgba(0,102,255,0.2)",
          borderRadius: "50px",
          padding: "8px 20px",
          marginBottom: "32px",
          fontSize: 14,
          fontWeight: 600,
          color: "#60A5FA",
        }}
        aria-live="polite"
        aria-label="Live escrow status"
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "#4CAF50",
            display: "inline-block",
            boxShadow: "0 0 8px #4CAF50",
          }}
          aria-hidden
        />
        <span style={{ color: "white" }}>LIVE</span>
        <span style={{ color: "var(--color-text-muted)" }}>·</span>
        <span>$1,500 held</span>
        <span style={{ color: "var(--color-text-muted)" }}>·</span>
        <span>3 of 4 checks passed</span>
        <span style={{ color: "var(--color-text-muted)" }}>·</span>
        <span style={{ color: "#FF9800" }}>Releasing $1,125</span>
      </div>

      {/* THE TWO DOORS */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: "20px",
          maxWidth: 780,
          width: "100%",
          marginBottom: "60px",
        }}
        role="navigation"
        aria-label="Choose your role"
      >
        {/* Hirer card */}
        <TwoDoorCard
          label="01 / HIRING"
          title="I'm hiring"
          description="Post a project, fund the escrow, pay only for work that passes."
          cta="Hire a Freelancer"
          glowColor="rgba(0, 102, 255, 0.35)"
          borderGlow="rgba(0, 102, 255, 0.4)"
          ctaColor="#0066FF"
          icon={<Shield size={28} color="#0066FF" aria-hidden />}
          href="/hire"
        />

        {/* Freelancer card */}
        <TwoDoorCard
          label="02 / BUILDING"
          title="I'm a freelancer"
          description="Get paid on time, every time, with money locked before you write a line."
          cta="Find paid work"
          glowColor="rgba(255, 152, 0, 0.3)"
          borderGlow="rgba(255, 152, 0, 0.35)"
          ctaColor="#FF9800"
          icon={<Code size={28} color="#FF9800" aria-hidden />}
          href="/work"
        />
      </div>

      {/* Trust row */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "center",
          gap: "32px",
          color: "var(--color-text-muted)",
          fontSize: 14,
          fontWeight: 500,
        }}
        aria-label="Trust indicators"
      >
        {[
          { icon: "🔐", label: "Funds held via PayPal" },
          { icon: "🛡️", label: "Verified in isolated containers" },
          { icon: "🧾", label: "Tamper-evident receipts" },
        ].map((item) => (
          <div
            key={item.label}
            style={{ display: "flex", alignItems: "center", gap: "8px" }}
          >
            <span role="img" aria-hidden>{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </div>

      {/* Floating mini-cards */}
      {floatingCards.map((card, i) => (
        <FloatingCard key={i} card={card} index={i} />
      ))}

      <style>{`
        @media (max-width: 600px) {
          [role="navigation"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </section>
  );
}

function TwoDoorCard({
  label, title, description, cta, glowColor, borderGlow, ctaColor, icon, href,
}: {
  label: string;
  title: string;
  description: string;
  cta: string;
  glowColor: string;
  borderGlow: string;
  ctaColor: string;
  icon: React.ReactNode;
  href: string;
}) {
  return (
    <a
      href={href}
      style={{
        display: "block",
        textDecoration: "none",
        background: "rgba(255,255,255,0.03)",
        backdropFilter: "blur(20px)",
        border: `1px solid rgba(255,255,255,0.08)`,
        borderRadius: "24px",
        padding: "32px",
        transition: "all 0.35s cubic-bezier(0.4, 0, 0.2, 1)",
        cursor: "pointer",
        position: "relative",
        overflow: "hidden",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget.style.borderColor = borderGlow);
        (e.currentTarget.style.boxShadow = `0 0 60px ${glowColor}, 0 20px 60px rgba(0,0,0,0.3)`);
        (e.currentTarget.style.transform = "translateY(-4px) rotateX(2deg)");
      }}
      onMouseLeave={(e) => {
        (e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)");
        (e.currentTarget.style.boxShadow = "none");
        (e.currentTarget.style.transform = "none");
      }}
      aria-label={title}
    >
      {/* Inner glow */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "2px",
          background: `linear-gradient(90deg, transparent, ${ctaColor}, transparent)`,
          opacity: 0.6,
        }}
        aria-hidden
      />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px" }}>
        {icon}
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.1em",
            color: "var(--color-text-muted)",
          }}
        >
          {label}
        </span>
      </div>

      <h2
        style={{
          fontSize: "clamp(28px, 3vw, 36px)",
          fontWeight: 800,
          letterSpacing: "-0.02em",
          marginBottom: "12px",
          color: "white",
        }}
      >
        {title}
      </h2>
      <p
        style={{
          fontSize: 15,
          color: "var(--color-text-secondary)",
          lineHeight: 1.6,
          marginBottom: "24px",
        }}
      >
        {description}
      </p>

      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          color: ctaColor,
          fontWeight: 600,
          fontSize: 15,
        }}
      >
        {cta} <ArrowRight size={16} aria-hidden />
      </span>
    </a>
  );
}

function FloatingCard({ card, index }: { card: (typeof floatingCards)[0]; index: number }) {
  const positions = [
    { top: "22%", right: "4%", rotate: "5deg" },
    { top: "60%", right: "2%", rotate: "-3deg" },
    { top: "30%", left: "2%", rotate: "4deg" },
  ];
  const pos = positions[index % positions.length];

  return (
    <div
      style={{
        position: "absolute",
        ...pos,
        background: "rgba(255,255,255,0.04)",
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: "16px",
        padding: "14px 18px",
        fontSize: 13,
        color: "var(--color-text-secondary)",
        maxWidth: 220,
        transform: `rotate(${pos.rotate})`,
        boxShadow: `0 0 30px ${card.color}22`,
        display: "flex",
        flexDirection: "column",
        gap: "6px",
        pointerEvents: "none",
      }}
      aria-hidden
    >
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: card.color,
          boxShadow: `0 0 8px ${card.color}`,
          marginBottom: "2px",
        }}
      />
      <div style={{ fontWeight: 700, color: "white", fontSize: 14 }}>{card.label}</div>
      <div style={{ display: "flex", gap: "10px" }}>
        <span style={{ color: card.color, fontWeight: 600 }}>{card.amount}</span>
        <span>·</span>
        <span>{card.days ?? card.receipt}</span>
        {card.pct && (
          <>
            <span>·</span>
            <span style={{ color: "#4CAF50" }}>{card.pct} verified</span>
          </>
        )}
      </div>
    </div>
  );
}

