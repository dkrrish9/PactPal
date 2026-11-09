"use client";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Link from "next/link";
import { CheckCircle, ArrowRight } from "lucide-react";

const plans = [
  {
    name: "Freelancer",
    tagline: "For individuals who build.",
    price: "Free",
    priceSub: "to get started",
    color: "#FF9800",
    glow: "rgba(255,152,0,0.2)",
    border: "rgba(255,152,0,0.3)",
    cta: "Start freelancing",
    href: "/work",
    features: [
      "Unlimited bid proposals",
      "5% PactPal fee on earnings",
      "AI Referee verification",
      "Proof-of-work receipts",
      "Negotiation chat",
      "Payout within 24h of release",
    ],
  },
  {
    name: "Hirer",
    tagline: "For teams who ship.",
    price: "Free",
    priceSub: "to post a project",
    color: "#0066FF",
    glow: "rgba(0,102,255,0.2)",
    border: "rgba(0,102,255,0.4)",
    featured: true,
    cta: "Post your first project",
    href: "/hire",
    features: [
      "Unlimited project posts",
      "3% platform fee on contracts",
      "PayPal escrow authorization",
      "29-day hold protection",
      "Bryntum Gantt timeline",
      "Partial release controls",
      "Dispute resolution support",
    ],
  },
  {
    name: "Enterprise",
    tagline: "For agencies & large teams.",
    price: "Custom",
    priceSub: "contact us",
    color: "#7A5CFF",
    glow: "rgba(122,92,255,0.2)",
    border: "rgba(122,92,255,0.3)",
    cta: "Talk to us",
    href: "mailto:enterprise@pactpal.io",
    features: [
      "Everything in Hirer",
      "Custom escrow limits",
      "SLA & priority support",
      "API access",
      "Dedicated account manager",
      "White-label receipt branding",
      "Audit log exports",
    ],
  },
];

const faqs = [
  {
    q: "How does the escrow actually work?",
    a: "Buyers authorize payment via PayPal's AUTHORIZE intent — money is reserved in their account but not transferred. When the AI Referee confirms features pass, we capture the authorized amount. Failed features are voided.",
  },
  {
    q: "What happens if I disagree with the AI's decision?",
    a: "You can open a Dispute within a 48-hour grace window. Our team reviews the evidence and the AI reasoning chain, and can override the decision. Every step is logged and tamper-evident.",
  },
  {
    q: "What is the 29-day hold?",
    a: "PayPal authorization holds expire after 29 days. PactPal requires all verification and settlement to happen within that window. For longer projects, we create milestone sub-contracts with their own holds.",
  },
  {
    q: "Can I see the AI Referee's reasoning?",
    a: "Yes. Every decision comes with a detailed log showing each stage (A–F), test results, cheat-scan findings, and visual match scores. Nothing is a black box.",
  },
  {
    q: "What counts as a 'failed' feature?",
    a: "A feature fails if it doesn't pass its stated acceptance test, if the cheat scanner finds hardcoded responses or mocks, or if the visual diff falls below the agreed similarity threshold.",
  },
];

export default function PricingPage() {
  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      {/* Hero */}
      <section style={{ padding: "140px 24px 80px", textAlign: "center", position: "relative" }}>
        <div
          style={{
            position: "absolute",
            top: "30%",
            left: "50%",
            transform: "translateX(-50%)",
            width: 600,
            height: 400,
            background: "radial-gradient(ellipse, rgba(0,102,255,0.1) 0%, transparent 70%)",
            filter: "blur(80px)",
            pointerEvents: "none",
          }}
          aria-hidden
        />
        <p
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.12em",
            textTransform: "uppercase" as const,
            color: "var(--color-text-muted)",
            marginBottom: 20,
          }}
        >
          Pricing
        </p>
        <h1
          style={{
            fontSize: "clamp(44px, 7vw, 80px)",
            fontWeight: 900,
            letterSpacing: "-0.03em",
            color: "white",
            lineHeight: 1.05,
            marginBottom: 20,
          }}
        >
          Simple fees.{" "}
          <span className="gradient-text">No surprises.</span>
        </h1>
        <p
          style={{
            fontSize: 20,
            color: "var(--color-text-secondary)",
            maxWidth: 520,
            margin: "0 auto 60px",
            lineHeight: 1.6,
          }}
        >
          You only pay when value is delivered. The AI Referee makes sure you never
          pay for work that doesn&apos;t pass.
        </p>
      </section>

      {/* Plans */}
      <section
        style={{ padding: "0 24px 120px", maxWidth: 1100, margin: "0 auto" }}
        aria-labelledby="plans-heading"
      >
        <h2 id="plans-heading" className="sr-only">Pricing plans</h2>
        <div
          style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}
          role="list"
        >
          {plans.map((plan) => (
            <article
              key={plan.name}
              role="listitem"
              style={{
                background: plan.featured
                  ? "rgba(0,102,255,0.06)"
                  : "rgba(255,255,255,0.03)",
                border: `1px solid ${plan.border}`,
                borderRadius: 28,
                padding: "36px 32px",
                position: "relative",
                boxShadow: plan.featured ? `0 0 60px ${plan.glow}` : "none",
                transition: "all 0.3s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = `0 0 60px ${plan.glow}`;
                e.currentTarget.style.transform = "translateY(-4px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = plan.featured
                  ? `0 0 60px ${plan.glow}`
                  : "none";
                e.currentTarget.style.transform = "none";
              }}
              aria-label={`${plan.name} plan: ${plan.price}`}
            >
              {plan.featured && (
                <div
                  style={{
                    position: "absolute",
                    top: -14,
                    left: "50%",
                    transform: "translateX(-50%)",
                    background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                    borderRadius: 50,
                    padding: "5px 18px",
                    fontSize: 11,
                    fontWeight: 700,
                    color: "white",
                    letterSpacing: "0.08em",
                    whiteSpace: "nowrap",
                  }}
                >
                  MOST POPULAR
                </div>
              )}

              {/* Top glow line */}
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 2,
                  background: `linear-gradient(90deg, transparent, ${plan.color}, transparent)`,
                  borderRadius: "28px 28px 0 0",
                  opacity: 0.8,
                }}
                aria-hidden
              />

              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase" as const,
                  color: plan.color,
                  marginBottom: 12,
                }}
              >
                {plan.name}
              </div>
              <div
                style={{
                  fontSize: 15,
                  color: "var(--color-text-secondary)",
                  marginBottom: 24,
                }}
              >
                {plan.tagline}
              </div>

              <div style={{ marginBottom: 32 }}>
                <span
                  style={{
                    fontSize: 52,
                    fontWeight: 900,
                    color: "white",
                    fontFamily: "JetBrains Mono, monospace",
                    letterSpacing: "-0.03em",
                    lineHeight: 1,
                  }}
                >
                  {plan.price}
                </span>
                <div
                  style={{
                    fontSize: 13,
                    color: "var(--color-text-muted)",
                    marginTop: 4,
                  }}
                >
                  {plan.priceSub}
                </div>
              </div>

              <Link
                href={plan.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  background: plan.featured
                    ? `linear-gradient(135deg, ${plan.color}, #00A3E0)`
                    : `${plan.color}18`,
                  border: `1px solid ${plan.color}44`,
                  borderRadius: 50,
                  color: plan.featured ? "white" : plan.color,
                  padding: "13px 24px",
                  fontSize: 15,
                  fontWeight: 700,
                  textDecoration: "none",
                  marginBottom: 32,
                  transition: "all 0.2s ease",
                  boxShadow: plan.featured
                    ? `0 0 20px ${plan.color}44`
                    : "none",
                }}
                aria-label={`${plan.cta} — ${plan.name} plan`}
              >
                {plan.cta} <ArrowRight size={16} aria-hidden />
              </Link>

              <ul
                style={{
                  listStyle: "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
                aria-label={`${plan.name} plan features`}
              >
                {plan.features.map((f) => (
                  <li
                    key={f}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      fontSize: 14,
                      color: "var(--color-text-secondary)",
                    }}
                  >
                    <CheckCircle
                      size={16}
                      color={plan.color}
                      style={{ flexShrink: 0 }}
                      aria-hidden
                    />
                    {f}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>

        <style>{`
          @media (max-width: 900px) {
            [style*="repeat(3, 1fr)"] {
              grid-template-columns: 1fr !important;
            }
          }
          .sr-only {
            position: absolute; width: 1px; height: 1px;
            overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap;
          }
        `}</style>
      </section>

      {/* Fee calculator hint */}
      <section
        style={{
          padding: "0 24px 120px",
          maxWidth: 700,
          margin: "0 auto",
          textAlign: "center",
        }}
        aria-labelledby="fee-heading"
      >
        <div
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 24,
            padding: "40px",
          }}
        >
          <h2
            id="fee-heading"
            style={{
              fontSize: 28,
              fontWeight: 800,
              color: "white",
              marginBottom: 12,
            }}
          >
            What does PactPal actually cost?
          </h2>
          <p
            style={{
              fontSize: 15,
              color: "var(--color-text-secondary)",
              lineHeight: 1.7,
              marginBottom: 28,
            }}
          >
            On a <strong style={{ color: "white" }}>$1,500</strong> contract where{" "}
            <strong style={{ color: "#4CAF50" }}>3 of 4 features pass</strong>:
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 12, textAlign: "left" }}>
            {[
              ["Freelancer earns (80%)", "$1,200", "#4CAF50"],
              ["PactPal fee (5%)", "−$60", "#FF9800"],
              ["Freelancer net", "$1,140", "white"],
              ["Buyer refund (20%)", "$300", "#0066FF"],
              ["Buyer platform fee (3%)", "−$45", "#FF9800"],
            ].map(([label, val, color]) => (
              <div
                key={label}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 15,
                  paddingBottom: 12,
                  borderBottom: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                <span style={{ color: "var(--color-text-secondary)" }}>{label}</span>
                <span
                  style={{
                    fontWeight: 700,
                    color,
                    fontFamily: "JetBrains Mono, monospace",
                  }}
                >
                  {val}
                </span>
              </div>
            ))}
          </div>
          <p
            style={{
              marginTop: 20,
              fontSize: 13,
              color: "var(--color-text-muted)",
              fontStyle: "italic",
            }}
          >
            Fees are only charged on successful, verified payouts. No subscription. No hidden charges.
          </p>
        </div>
      </section>

      {/* FAQ */}
      <section
        style={{ padding: "0 24px 120px", maxWidth: 760, margin: "0 auto" }}
        aria-labelledby="faq-heading"
      >
        <h2
          id="faq-heading"
          style={{
            fontSize: "clamp(28px, 3.5vw, 44px)",
            fontWeight: 900,
            letterSpacing: "-0.02em",
            color: "white",
            marginBottom: 48,
            textAlign: "center",
          }}
        >
          Frequently asked questions
        </h2>
        <div
          style={{ display: "flex", flexDirection: "column", gap: 16 }}
          role="list"
          aria-label="Frequently asked questions"
        >
          {faqs.map((faq, i) => (
            <details
              key={i}
              role="listitem"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16,
                padding: "20px 24px",
                cursor: "pointer",
              }}
            >
              <summary
                style={{
                  fontWeight: 700,
                  fontSize: 16,
                  color: "white",
                  listStyle: "none",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                }}
                aria-expanded="false"
              >
                {faq.q}
                <span
                  style={{
                    color: "var(--color-text-muted)",
                    fontSize: 20,
                    flexShrink: 0,
                  }}
                  aria-hidden
                >
                  +
                </span>
              </summary>
              <p
                style={{
                  fontSize: 15,
                  color: "var(--color-text-secondary)",
                  lineHeight: 1.7,
                  marginTop: 14,
                  borderTop: "1px solid rgba(255,255,255,0.06)",
                  paddingTop: 14,
                }}
              >
                {faq.a}
              </p>
            </details>
          ))}
        </div>
      </section>

      <Footer />
    </main>
  );
}

