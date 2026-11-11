"use client";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ArrowRight, CheckCircle, Clock, Shield } from "lucide-react";
import Link from "next/link";

const steps = [
  { icon: "📋", title: "Post your project", desc: "Describe your requirements, set features with weighted acceptance tests." },
  { icon: "🔒", title: "Fund the escrow", desc: "Authorize payment via PayPal — money is held, not charged yet." },
  { icon: "🤖", title: "AI verifies the work", desc: "Our Referee runs 6 stages of automated verification on delivery." },
  { icon: "💸", title: "Pay for what passes", desc: "Passed features release automatically. Failed features are refunded." },
];

const categories = [
  { name: "Website Design", icon: "🌐", count: "12,400+ freelancers" },
  { name: "Mobile Apps", icon: "📱", count: "8,200+ freelancers" },
  { name: "AI & Automation", icon: "🤖", count: "5,100+ freelancers" },
  { name: "Brand & UI Design", icon: "🎨", count: "9,800+ freelancers" },
  { name: "API Development", icon: "⚡", count: "7,300+ freelancers" },
  { name: "Data & Analytics", icon: "📊", count: "4,600+ freelancers" },
];

export default function HirePage() {
  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      {/* Hero */}
      <section
        style={{
          padding: "160px 24px 100px",
          maxWidth: 1280,
          margin: "0 auto",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "30%",
            left: "60%",
            width: 500,
            height: 500,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(0,102,255,0.12) 0%, transparent 70%)",
            filter: "blur(80px)",
            pointerEvents: "none",
          }}
          aria-hidden
        />

        <div style={{ maxWidth: 740 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "rgba(0,102,255,0.1)",
              border: "1px solid rgba(0,102,255,0.3)",
              borderRadius: 50,
              padding: "6px 16px",
              fontSize: 12,
              fontWeight: 700,
              color: "#60A5FA",
              letterSpacing: "0.08em",
              textTransform: "uppercase" as const,
              marginBottom: 32,
            }}
          >
            <Shield size={12} aria-hidden /> For Hirers
          </div>

          <h1
            style={{
              fontSize: "clamp(44px, 7vw, 88px)",
              fontWeight: 900,
              letterSpacing: "-0.03em",
              lineHeight: 1.05,
              color: "white",
              marginBottom: 24,
            }}
          >
            Pay only for{" "}
            <span className="gradient-text">work that passes.</span>
          </h1>

          <p
            style={{
              fontSize: 20,
              color: "var(--color-text-secondary)",
              lineHeight: 1.65,
              marginBottom: 48,
              maxWidth: 560,
            }}
          >
            No more chargebacks. No more "almost done." PactPal locks your money,
            an AI referee checks the deliverables, and you pay for exactly what
            meets your acceptance tests.
          </p>

          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
            <Link
              href="/hire/create"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                color: "white",
                borderRadius: 50,
                padding: "16px 32px",
                fontSize: 16,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 0 30px rgba(0,102,255,0.4)",
                transition: "all 0.3s ease",
              }}
              aria-label="Create a contract with the wizard"
            >
              Create Contract Wizard <ArrowRight size={18} aria-hidden />
            </Link>

            <Link
              href="/dashboard/hirer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "rgba(0,102,255,0.12)",
                border: "1px solid rgba(0,102,255,0.3)",
                color: "#60A5FA",
                borderRadius: 50,
                padding: "16px 28px",
                fontSize: 15,
                fontWeight: 600,
                textDecoration: "none",
                transition: "all 0.2s",
              }}
            >
              Hirer Dashboard (Active Contracts) 📋
            </Link>

            <Link
              href="#how"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                color: "var(--color-text-secondary)",
                fontSize: 14,
                textDecoration: "none",
                padding: "8px 12px",
              }}
            >
              See how it works ↓
            </Link>
          </div>
        </div>
      </section>

      {/* How it works for hirers */}
      <section
        id="how"
        style={{ padding: "80px 24px 120px", maxWidth: 1280, margin: "0 auto" }}
        aria-labelledby="hirer-how-heading"
      >
        <h2
          id="hirer-how-heading"
          style={{
            fontSize: "clamp(32px, 4vw, 52px)",
            fontWeight: 900,
            letterSpacing: "-0.025em",
            color: "white",
            marginBottom: 56,
            textAlign: "center",
          }}
        >
          Simple. Transparent. <span className="gradient-text">Bulletproof.</span>
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 20,
          }}
          role="list"
        >
          {steps.map((step, i) => (
            <div
              key={i}
              role="listitem"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.07)",
                borderRadius: 24,
                padding: "32px 28px",
              }}
            >
              <div
                style={{
                  fontSize: 36,
                  marginBottom: 20,
                  display: "block",
                  lineHeight: 1,
                }}
                aria-hidden
              >
                {step.icon}
              </div>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.1em",
                  color: "var(--color-text-muted)",
                  marginBottom: 8,
                  fontFamily: "JetBrains Mono, monospace",
                }}
                aria-hidden
              >
                STEP 0{i + 1}
              </div>
              <h3 style={{ fontSize: 20, fontWeight: 700, color: "white", marginBottom: 10 }}>
                {step.title}
              </h3>
              <p style={{ fontSize: 14, color: "var(--color-text-secondary)", lineHeight: 1.65 }}>
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Category grid */}
      <section
        style={{
          padding: "0 24px 120px",
          maxWidth: 1280,
          margin: "0 auto",
        }}
        aria-labelledby="hirer-categories-heading"
      >
        <h2
          id="hirer-categories-heading"
          style={{
            fontSize: "clamp(28px, 3.5vw, 44px)",
            fontWeight: 900,
            letterSpacing: "-0.02em",
            color: "white",
            marginBottom: 40,
          }}
        >
          Browse talent by category
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 16,
          }}
          role="list"
        >
          {categories.map((cat) => (
            <Link
              key={cat.name}
              href={`/hire/category/${cat.name.toLowerCase().replace(/\s+/g, "-")}`}
              role="listitem"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.07)",
                borderRadius: 16,
                padding: "20px 20px",
                textDecoration: "none",
                transition: "all 0.25s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(0,102,255,0.3)";
                e.currentTarget.style.background = "rgba(0,102,255,0.06)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)";
                e.currentTarget.style.background = "rgba(255,255,255,0.03)";
              }}
              aria-label={`Browse ${cat.name}`}
            >
              <span style={{ fontSize: 28 }} aria-hidden>{cat.icon}</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15, color: "white" }}>{cat.name}</div>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 2 }}>{cat.count}</div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <Footer />
    </main>
  );
}

