"use client";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ArrowRight } from "lucide-react";
import Link from "next/link";

const stages = [
  {
    id: "A",
    title: "Intake & Git clone",
    color: "#0066FF",
    icon: "",
    desc: "The Referee clones the submitted repository into an isolated Render Workflow container. It records the exact commit SHA, timestamp, and repo URL — all hashed into the receipt.",
    detail: ["Git clone into ephemeral container", "Commit SHA locked to receipt", "No local environment access", "Timestamp verified against contract deadline"],
  },
  {
    id: "B",
    title: "Clean sandbox build",
    color: "#00A3E0",
    icon: "",
    desc: "Dependencies are installed fresh. The build must succeed with zero external data sources — no cached databases, no live APIs. If it fails to build, the contract cannot pass.",
    detail: ["Fresh npm / pip install", "No network access during build", "Build timeout: 10 minutes", "Output artifacts fingerprinted"],
  },
  {
    id: "C",
    title: "Automated test suite",
    color: "#7A5CFF",
    icon: "",
    desc: "The existing test suite is executed. PactPal maps each test to the feature it covers, calculating a per-feature pass rate that directly determines the payout weight.",
    detail: ["Unit + integration tests", "Per-feature test mapping", "Coverage report generated", "Flaky test detection"],
  },
  {
    id: "D",
    title: "Cheat & loophole scan",
    color: "#FF9800",
    icon: "",
    desc: "The most critical stage. The Referee scans for hardcoded responses, mock returns, environment flags that bypass real logic, and any code that would only work in test mode.",
    detail: ["Hardcoded response detection", "Mock/stub abuse scan", "Environment flag analysis", "Severity: HIGH / MED / LOW"],
  },
  {
    id: "E",
    title: "Figma visual diff",
    color: "#F44336",
    icon: "",
    desc: "If a Figma design was provided, headless browser screenshots are captured and compared pixel-by-pixel against the reference. A similarity score per screen is calculated.",
    detail: ["Headless Chromium screenshots", "Pixel-level diff computation", "Per-screen similarity %", "Annotated diff image in receipt"],
  },
  {
    id: "F",
    title: "QA multimodal report",
    color: "#4CAF50",
    icon: "",
    desc: "All results are compiled into a structured report. The AI Referee applies transparent rules to compute the final pass/fail per feature, offer amount, and negotiation options.",
    detail: ["Structured JSON report", "Per-feature pass/fail map", "Referee offer calculation", "Receipt hash generated"],
  },
];

export default function RefereePage() {
  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      {/* Hero */}
      <section
        style={{
          padding: "140px 24px 100px",
          maxWidth: 1280,
          margin: "0 auto",
          position: "relative",
          textAlign: "center",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "30%",
            left: "50%",
            transform: "translateX(-50%)",
            width: 700,
            height: 400,
            background: "radial-gradient(ellipse, rgba(0,102,255,0.12) 0%, transparent 70%)",
            filter: "blur(80px)",
            pointerEvents: "none",
          }}
          aria-hidden
        />

        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            background: "rgba(0,102,255,0.1)",
            border: "1px solid rgba(0,102,255,0.3)",
            borderRadius: 50,
            padding: "6px 18px",
            fontSize: 12,
            fontWeight: 700,
            color: "#60A5FA",
            letterSpacing: "0.08em",
            textTransform: "uppercase" as const,
            marginBottom: 32,
          }}
        >
           The AI Referee
        </div>

        <h1
          style={{
            fontSize: "clamp(44px, 7vw, 88px)",
            fontWeight: 900,
            letterSpacing: "-0.03em",
            color: "white",
            lineHeight: 1.05,
            marginBottom: 24,
          }}
        >
          Rules-based.{" "}
          <span className="gradient-text">Never a black box.</span>
        </h1>

        <p
          style={{
            fontSize: 20,
            color: "var(--color-text-secondary)",
            lineHeight: 1.65,
            maxWidth: 620,
            margin: "0 auto 56px",
          }}
        >
          The AI Referee doesn&apos;t guess. It runs six deterministic stages, logs every
          finding, and applies transparent rules to decide exactly how much to release.
          Every decision is auditable.
        </p>

        {/* Six-stage pill */}
        <div
          style={{
            display: "flex",
            gap: 8,
            justifyContent: "center",
            flexWrap: "wrap",
            marginBottom: 80,
          }}
          role="list"
          aria-label="Six verification stages"
        >
          {stages.map((s) => (
            <a
              key={s.id}
              href={`#stage-${s.id}`}
              role="listitem"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: `${s.color}12`,
                border: `1px solid ${s.color}30`,
                borderRadius: 50,
                padding: "8px 18px",
                fontSize: 13,
                fontWeight: 700,
                color: s.color,
                textDecoration: "none",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = `${s.color}22`;
                e.currentTarget.style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = `${s.color}12`;
                e.currentTarget.style.transform = "none";
              }}
              aria-label={`Stage ${s.id}: ${s.title}`}
            >
              <span aria-hidden>{s.icon}</span> Stage {s.id}: {s.title}
            </a>
          ))}
        </div>
      </section>

      {/* Stage deep-dives */}
      <section
        style={{ padding: "0 24px 80px", maxWidth: 1100, margin: "0 auto" }}
        aria-label="Detailed stage descriptions"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
          {stages.map((stage, i) => (
            <div
              key={stage.id}
              id={`stage-${stage.id}`}
              style={{
                display: "grid",
                gridTemplateColumns: i % 2 === 0 ? "1fr 1.4fr" : "1.4fr 1fr",
                gap: 32,
                alignItems: "center",
              }}
              role="article"
              aria-labelledby={`stage-${stage.id}-heading`}
            >
              {/* Text side */}
              <div style={{ order: i % 2 === 0 ? 0 : 1 }}>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 10,
                    marginBottom: 20,
                  }}
                >
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 16,
                      background: `${stage.color}18`,
                      border: `1px solid ${stage.color}44`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 24,
                    }}
                    aria-hidden
                  >
                    {stage.icon}
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        letterSpacing: "0.1em",
                        color: stage.color,
                        textTransform: "uppercase" as const,
                      }}
                    >
                      Stage {stage.id}
                    </div>
                    <h2
                      id={`stage-${stage.id}-heading`}
                      style={{
                        fontSize: 24,
                        fontWeight: 800,
                        color: "white",
                        letterSpacing: "-0.02em",
                      }}
                    >
                      {stage.title}
                    </h2>
                  </div>
                </div>

                <p
                  style={{
                    fontSize: 16,
                    color: "var(--color-text-secondary)",
                    lineHeight: 1.7,
                    marginBottom: 24,
                  }}
                >
                  {stage.desc}
                </p>

                <ul
                  style={{
                    listStyle: "none",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                  }}
                  aria-label={`Stage ${stage.id} details`}
                >
                  {stage.detail.map((d) => (
                    <li
                      key={d}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        fontSize: 14,
                        color: "var(--color-text-secondary)",
                      }}
                    >
                      <span
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          background: stage.color,
                          flexShrink: 0,
                          boxShadow: `0 0 6px ${stage.color}`,
                        }}
                        aria-hidden
                      />
                      {d}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Visual side — log terminal */}
              <div
                style={{
                  order: i % 2 === 0 ? 1 : 0,
                  background: "rgba(0,0,0,0.5)",
                  border: `1px solid ${stage.color}22`,
                  borderRadius: 20,
                  padding: "24px",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 13,
                  boxShadow: `0 0 40px ${stage.color}10`,
                }}
                role="log"
                aria-label={`Stage ${stage.id} sample output`}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 18,
                    paddingBottom: 14,
                    borderBottom: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <div style={{ display: "flex", gap: 6 }} aria-hidden>
                    {["#F44336", "#FF9800", "#4CAF50"].map((c) => (
                      <div
                        key={c}
                        style={{
                          width: 10,
                          height: 10,
                          borderRadius: "50%",
                          background: c,
                        }}
                      />
                    ))}
                  </div>
                  <span style={{ color: "var(--color-text-muted)", fontSize: 12 }}>
                    stage_{stage.id.toLowerCase()}.log
                  </span>
                  <span
                    style={{
                      marginLeft: "auto",
                      background: `${stage.color}18`,
                      border: `1px solid ${stage.color}30`,
                      borderRadius: 50,
                      padding: "2px 10px",
                      fontSize: 10,
                      fontWeight: 700,
                      color: stage.color,
                      letterSpacing: "0.06em",
                    }}
                  >
                    RUNNING
                  </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6, lineHeight: 1.6 }}>
                  {getStageLog(stage.id).map((line, j) => (
                    <div key={j} style={{ display: "flex", gap: 12 }}>
                      <span style={{ color: "rgba(124,137,168,0.5)", flexShrink: 0 }}>{line.time}</span>
                      <span style={{ color: line.color }}>{line.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              <style>{`
                @media (max-width: 768px) {
                  [style*="grid-template-columns: 1fr 1.4fr"],
                  [style*="grid-template-columns: 1.4fr 1fr"] {
                    grid-template-columns: 1fr !important;
                  }
                  [style*="order: 1"] { order: 0 !important; }
                }
              `}</style>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section
        style={{
          padding: "80px 24px 120px",
          textAlign: "center",
          borderTop: "1px solid rgba(255,255,255,0.06)",
        }}
        aria-labelledby="referee-cta-heading"
      >
        <h2
          id="referee-cta-heading"
          style={{
            fontSize: "clamp(32px, 5vw, 60px)",
            fontWeight: 900,
            letterSpacing: "-0.025em",
            color: "white",
            marginBottom: 20,
          }}
        >
          Let the Referee{" "}
          <span className="gradient-text">do the talking.</span>
        </h2>
        <p
          style={{
            fontSize: 18,
            color: "var(--color-text-secondary)",
            marginBottom: 40,
          }}
        >
          No awkward conversations. No disputed invoices. Just receipts.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <Link
            href="/hire/create"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "linear-gradient(135deg, #0066FF, #00A3E0)",
              color: "white",
              borderRadius: 50,
              padding: "16px 36px",
              fontSize: 16,
              fontWeight: 700,
              textDecoration: "none",
              boxShadow: "0 0 30px rgba(0,102,255,0.4)",
            }}
            aria-label="Start a contract"
          >
            Start a contract <ArrowRight size={18} aria-hidden />
          </Link>
        </div>
      </section>

      <Footer />
    </main>
  );
}

function getStageLog(id: string): { time: string; text: string; color: string }[] {
  const logs: Record<string, { time: string; text: string; color: string }[]> = {
    A: [
      { time: "14:30:01", text: "→ Cloning repo...", color: "#B8C2D9" },
      { time: "14:30:03", text: "✓ Cloned: github.com/alex/ecomm-v2", color: "#4CAF50" },
      { time: "14:30:03", text: "→ Locking commit SHA...", color: "#B8C2D9" },
      { time: "14:30:04", text: "✓ SHA: 4a9f2b1c8d3e (locked)", color: "#4CAF50" },
      { time: "14:30:04", text: "→ Checking submission timestamp...", color: "#B8C2D9" },
      { time: "14:30:04", text: "✓ On time. Deadline: Nov 20 23:59.", color: "#4CAF50" },
    ],
    B: [
      { time: "14:30:10", text: "→ Installing dependencies (npm ci)...", color: "#B8C2D9" },
      { time: "14:30:35", text: "✓ 847 packages installed.", color: "#4CAF50" },
      { time: "14:30:35", text: "→ Running build...", color: "#B8C2D9" },
      { time: "14:31:00", text: "✓ Build succeeded in 25s. 0 errors.", color: "#4CAF50" },
      { time: "14:31:00", text: "→ Fingerprinting output artifacts...", color: "#B8C2D9" },
      { time: "14:31:01", text: "✓ dist/ hashed: 0x7f3a2b1c...", color: "#4CAF50" },
    ],
    C: [
      { time: "14:31:05", text: "→ Running test suite (jest --ci)...", color: "#B8C2D9" },
      { time: "14:31:12", text: "✓ 42 tests passed. 0 failed.", color: "#4CAF50" },
      { time: "14:31:12", text: "→ Mapping tests to features...", color: "#B8C2D9" },
      { time: "14:31:13", text: "  Landing page  → 11/11 tests pass ✓", color: "#4CAF50" },
      { time: "14:31:13", text: "  Login system  → 7/8 tests pass !", color: "#FF9800" },
      { time: "14:31:13", text: "  Coverage: 87% overall.", color: "#B8C2D9" },
    ],
    D: [
      { time: "14:31:20", text: "→ Scanning for hardcoded responses...", color: "#B8C2D9" },
      { time: "14:31:22", text: "⚠ FOUND: /api/login returns static JWT.", color: "#F44336" },
      { time: "14:31:22", text: "  Severity: HIGH. Not real auth logic.", color: "#F44336" },
      { time: "14:31:23", text: "→ Scanning for mock/stub abuse...", color: "#B8C2D9" },
      { time: "14:31:24", text: "✓ No suspicious mocks found.", color: "#4CAF50" },
      { time: "14:31:24", text: "⚠ Feature 'Login' flagged for FAIL.", color: "#F44336" },
    ],
    E: [
      { time: "14:31:30", text: "→ Launching headless Chromium...", color: "#B8C2D9" },
      { time: "14:31:33", text: "→ Capturing screenshots (4 screens)...", color: "#B8C2D9" },
      { time: "14:31:40", text: "✓ Landing:   97.2% match ✓", color: "#4CAF50" },
      { time: "14:31:40", text: "✓ Dashboard: 94.8% match ✓", color: "#4CAF50" },
      { time: "14:31:40", text: "✗ Login:     skip (feature failed)", color: "#7C89A8" },
      { time: "14:31:41", text: "✓ Payments:  98.1% match ✓", color: "#4CAF50" },
    ],
    F: [
      { time: "14:31:45", text: "→ Compiling QA report...", color: "#B8C2D9" },
      { time: "14:31:46", text: "  Landing page:  PASSED (25%)", color: "#4CAF50" },
      { time: "14:31:46", text: "  Login system:  FAILED (20%)", color: "#F44336" },
      { time: "14:31:46", text: "  Dashboard:     PASSED (30%)", color: "#4CAF50" },
      { time: "14:31:46", text: "  Payment flow:  PASSED (25%)", color: "#4CAF50" },
      { time: "14:31:47", text: "→ Hashing receipt: SHA-256 0xa9f3...", color: "#B8C2D9" },
      { time: "14:31:47", text: "✓ Receipt sealed. Offer: 80% ($1,200).", color: "#4CAF50" },
    ],
  };
  return logs[id] ?? [];
}

