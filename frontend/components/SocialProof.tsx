"use client";
import { useEffect, useRef, useState } from "react";

const stats = [
  { label: "held in escrow", value: "$12M+", color: "#0066FF" },
  { label: "fair-split satisfaction", value: "98%", color: "#4CAF50" },
  { label: "avg. first bid", value: "60 sec", color: "#FF9800" },
  { label: "jobs protected", value: "25.9M+", color: "#7A5CFF" },
];

const testimonials = [
  {
    name: "Alex M.",
    role: "Freelance Developer",
    avatar: "AM",
    color: "#0066FF",
    quote:
      "I used to get burned by clients who'd dispute the work after delivery. PactPal flipped everything — now money is locked before I write a line. I haven't had a single chargeback.",
  },
  {
    name: "Priya S.",
    role: "Product Manager, Hirer",
    avatar: "PS",
    color: "#FF9800",
    quote:
      "The AI referee caught a login that was completely hardcoded. We got an 80% payout instead of paying for broken software. This is what paying for work should look like.",
  },
  {
    name: "Jordan K.",
    role: "UI/UX Designer",
    avatar: "JK",
    color: "#7A5CFF",
    quote:
      "The Figma visual diff comparison blew me away. It showed exactly where my implementation differed from the design spec. Fair, transparent, brilliant.",
  },
];

export default function SocialProof() {
  return (
    <section
      style={{
        padding: "120px 24px",
        maxWidth: 1280,
        margin: "0 auto",
      }}
      aria-labelledby="proof-heading"
    >
      {/* Stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "24px",
          marginBottom: "80px",
        }}
        role="list"
        aria-label="PactPal statistics"
      >
        {stats.map((s) => (
          <div
            key={s.label}
            role="listitem"
            style={{
              textAlign: "center",
              padding: "32px 24px",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: "20px",
            }}
          >
            <div
              style={{
                fontSize: "clamp(36px, 4vw, 52px)",
                fontWeight: 900,
                fontFamily: "JetBrains Mono, monospace",
                color: s.color,
                lineHeight: 1,
                marginBottom: "8px",
                filter: `drop-shadow(0 0 20px ${s.color}66)`,
              }}
              aria-label={`${s.value} ${s.label}`}
            >
              {s.value}
            </div>
            <div style={{ fontSize: 14, color: "var(--color-text-muted)", fontWeight: 500 }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>

      {/* Testimonials */}
      <div style={{ marginBottom: "24px", textAlign: "center" }}>
        <h2
          id="proof-heading"
          style={{
            fontSize: "clamp(28px, 3.5vw, 44px)",
            fontWeight: 900,
            letterSpacing: "-0.02em",
            color: "white",
          }}
        >
          They made a pact.{" "}
          <span className="gradient-text">Here's what happened.</span>
        </h2>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "20px",
          marginTop: "48px",
        }}
        role="list"
        aria-label="Customer testimonials"
      >
        {testimonials.map((t) => (
          <blockquote
            key={t.name}
            role="listitem"
            style={{
              background: "rgba(255,255,255,0.03)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(255,255,255,0.07)",
              borderRadius: "24px",
              padding: "32px",
              margin: 0,
              transition: "all 0.3s ease",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget.style.borderColor = `${t.color}44`);
              (e.currentTarget.style.boxShadow = `0 0 30px ${t.color}18`);
            }}
            onMouseLeave={(e) => {
              (e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)");
              (e.currentTarget.style.boxShadow = "none");
            }}
          >
            {/* Stars */}
            <div style={{ marginBottom: "16px", fontSize: 14, color: "#FF9800" }} aria-label="5 stars">
              ★★★★★
            </div>

            <p
              style={{
                fontSize: 15,
                color: "var(--color-text-secondary)",
                lineHeight: 1.7,
                marginBottom: "24px",
                fontStyle: "italic",
              }}
            >
              &ldquo;{t.quote}&rdquo;
            </p>

            <footer style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: "50%",
                  background: `${t.color}22`,
                  border: `2px solid ${t.color}44`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 13,
                  fontWeight: 700,
                  color: t.color,
                  flexShrink: 0,
                }}
                aria-hidden
              >
                {t.avatar}
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 14, color: "white" }}>{t.name}</div>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{t.role}</div>
              </div>
            </footer>
          </blockquote>
        ))}
      </div>
    </section>
  );
}

