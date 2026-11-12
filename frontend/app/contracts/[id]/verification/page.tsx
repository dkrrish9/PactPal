"use client";
import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Link from "next/link";
import { useParams } from "next/navigation";
import { 
  mockApi, 
  Contract, 
  VerificationReport 
} from "@/lib/mockApi";
import { backendClient } from "@/lib/backendClient";
import { 
  ShieldCheck, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Terminal, 
  GitBranch, 
  FileCode, 
  Palette, 
  ArrowLeft, 
  Copy, 
  Check, 
  Eye, 
  Columns, 
  Sliders, 
  Download,
  ExternalLink,
  Code2
} from "lucide-react";

export default function VerificationResultPage() {
  const params = useParams();
  const contractId = (params?.id as string) || "pct_099e77";

  const [contract, setContract] = useState<Contract | null>(null);
  const [report, setReport] = useState<VerificationReport | null>(null);
  const [activeDiffMode, setActiveDiffMode] = useState<"sideBySide" | "slider" | "overlay">("sideBySide");
  const [sliderPosition, setSliderPosition] = useState(50);
  const [isJsonModalOpen, setIsJsonModalOpen] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);

  useEffect(() => {
    async function loadVerificationData() {
      try {
        const liveContract = await backendClient.getContract(contractId);
        if (liveContract) {
          setContract(liveContract as unknown as Contract);
          const rep = await backendClient.getVerificationReport(liveContract.id);
          if (rep) {
            setReport(rep);
            return;
          }
        }
      } catch {}

      const loadedContract = mockApi.getContract(contractId) || mockApi.getContracts()[0];
      if (loadedContract) {
        setContract(loadedContract);
        const rep = mockApi.getVerificationReport(loadedContract.id);
        setReport(rep);
      }
    }
    loadVerificationData();
  }, [contractId]);

  if (!contract || !report) {
    return (
      <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
        <Navbar />
        <div style={{ maxWidth: 840, margin: "140px auto", textAlign: "center", color: "white" }}>
          <h2>Loading verification results...</h2>
        </div>
      </main>
    );
  }

  const perFeatures = Object.values(report.per_feature_results);
  const totalWeight = perFeatures.reduce((acc, f) => acc + f.price_weight, 0);
  const passedFeatures = perFeatures.filter((f) => f.status === "PASSED");
  const passedAmount = passedFeatures.reduce((acc, f) => acc + f.allocated_amount, 0);
  const refundedAmount = contract.total_amount - passedAmount;

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(report, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      <div style={{ maxWidth: 1160, margin: "0 auto", padding: "110px 24px 80px" }}>
        
        {/* Navigation Breadcrumb */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
          <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
            <Link href="/dashboard/hirer" style={{ color: "#60A5FA", textDecoration: "none" }}>Dashboard</Link>
            {" / "}
            <Link href={`/contracts/${contract.id}`} style={{ color: "#60A5FA", textDecoration: "none" }}>{contract.id}</Link>
            {" / "}
            <span style={{ color: "white" }}>AI Referee Verification Results (C29)</span>
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => setIsJsonModalOpen(true)}
              style={{
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.15)",
                color: "white",
                padding: "8px 16px",
                borderRadius: 24,
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                transition: "all 0.2s",
              }}
            >
              <Code2 size={14} color="#60A5FA" /> View Raw Report JSON
            </button>

            <Link
              href={`/contracts/${contract.id}`}
              style={{
                background: "rgba(0,102,255,0.12)",
                border: "1px solid rgba(0,102,255,0.3)",
                color: "#60A5FA",
                padding: "8px 16px",
                borderRadius: 24,
                fontSize: 12,
                fontWeight: 700,
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <ArrowLeft size={14} /> Back to Overview
            </Link>
          </div>
        </div>

        {/* Top Verdict Summary Header */}
        <div
          style={{
            background: "rgba(255, 255, 255, 0.03)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: 24,
            padding: "36px",
            marginBottom: 32,
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 20 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <span
                  style={{
                    background: "rgba(122, 92, 255, 0.15)",
                    border: "1px solid rgba(122, 92, 255, 0.4)",
                    color: "#A78BFA",
                    padding: "4px 12px",
                    borderRadius: 50,
                    fontSize: 12,
                    fontWeight: 700,
                    letterSpacing: "0.06em",
                  }}
                >
                  REFEREE AUDIT STAGES A–E
                </span>
                <span style={{ fontSize: 12, color: "var(--color-text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                  REPORT ID: {report.id}
                </span>
              </div>

              <h1 style={{ fontSize: "clamp(26px, 4vw, 36px)", fontWeight: 900, color: "white", marginBottom: 8 }}>
                AI Referee Verification Report
              </h1>
              <p style={{ fontSize: 15, color: "var(--color-text-secondary)", maxWidth: 640, lineHeight: 1.6 }}>
                Evaluated container sandbox run for contract <strong style={{ color: "white" }}>{contract.title}</strong> against agreed acceptance test suites and Figma design specs.
              </p>
            </div>

            {/* Score Ring & Escrow Payout Breakdown */}
            <div style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
              {/* Overall Score */}
              <div
                style={{
                  background: "rgba(0, 102, 255, 0.08)",
                  border: "1px solid rgba(0, 102, 255, 0.25)",
                  borderRadius: 20,
                  padding: "18px 24px",
                  textAlign: "center",
                  minWidth: 140,
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em" }}>
                  OVERALL SCORE
                </div>
                <div
                  style={{
                    fontSize: 40,
                    fontWeight: 900,
                    color: report.overall_score >= 75 ? "#81C784" : "#F87171",
                    fontFamily: "JetBrains Mono, monospace",
                    lineHeight: 1.1,
                    marginTop: 4,
                  }}
                >
                  {report.overall_score}%
                </div>
                <div style={{ fontSize: 11, color: "#60A5FA", fontWeight: 600, marginTop: 4 }}>
                  {passedFeatures.length} of {perFeatures.length} Passed
                </div>
              </div>

              {/* Escrow Release Card */}
              <div
                style={{
                  background: "rgba(255, 255, 255, 0.02)",
                  border: "1px solid rgba(255, 255, 255, 0.07)",
                  borderRadius: 20,
                  padding: "18px 24px",
                  minWidth: 200,
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em" }}>
                  RECOMMENDED DISBURSEMENT
                </div>
                <div style={{ fontSize: 22, fontWeight: 900, color: "#81C784", fontFamily: "JetBrains Mono, monospace", marginTop: 4 }}>
                  ${passedAmount.toLocaleString()} <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>to Seller</span>
                </div>
                <div style={{ fontSize: 14, fontWeight: 700, color: refundedAmount > 0 ? "#F87171" : "var(--color-text-muted)", fontFamily: "JetBrains Mono, monospace", marginTop: 2 }}>
                  ${refundedAmount.toLocaleString()} <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>refund to Buyer</span>
                </div>
              </div>
            </div>
          </div>

          {/* Verification Pipeline Quick Metrics Bar */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 16,
              marginTop: 24,
              paddingTop: 24,
              borderTop: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 4 }}>
                CONTAINER BUILD
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: report.build_succeeded ? "#81C784" : "#F87171", display: "flex", alignItems: "center", gap: 6 }}>
                {report.build_succeeded ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                {report.build_succeeded ? "Clean Build (0 errors)" : "Build Failed"}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 4 }}>
                UNIT TEST SUITE
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "white", display: "flex", alignItems: "center", gap: 6 }}>
                <Terminal size={14} color="#60A5FA" />
                {report.test_suite_results.passed_tests}/{report.test_suite_results.total_tests} passed ({report.test_suite_results.coverage_percent}% coverage)
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 4 }}>
                CHEAT &amp; MOCK SCAN
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: report.cheat_scan_findings.length > 0 ? "#FBBF24" : "#81C784", display: "flex", alignItems: "center", gap: 6 }}>
                <AlertTriangle size={14} color={report.cheat_scan_findings.length > 0 ? "#FBBF24" : "#81C784"} />
                {report.cheat_scan_findings.length} findings detected
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 4 }}>
                FIGMA VISUAL SIMILARITY
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: report.visual_diff_summary.passed ? "#81C784" : "#FBBF24", display: "flex", alignItems: "center", gap: 6 }}>
                <Palette size={14} color="#A78BFA" />
                {report.visual_diff_summary.similarity_score}% (Threshold: {report.visual_diff_summary.threshold}%)
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 1: PER-FEATURE VERDICT & EVIDENCE (C29 Requirement 1) */}
        <div style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <div>
              <h2 style={{ fontSize: 22, fontWeight: 900, color: "white", display: "flex", alignItems: "center", gap: 10 }}>
                📋 Per-Feature Verdicts &amp; Test Evidence
              </h2>
              <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginTop: 2 }}>
                Individual milestone pass/fail breakdown mapping directly to the shared JSON report shape.
              </p>
            </div>
            <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
              {perFeatures.length} features evaluated
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {perFeatures.map((feat, idx) => {
              const isPassed = feat.status === "PASSED";
              return (
                <div
                  key={feat.feature_id}
                  style={{
                    background: isPassed ? "rgba(76, 175, 80, 0.03)" : "rgba(244, 67, 54, 0.03)",
                    border: `1px solid ${isPassed ? "rgba(76, 175, 80, 0.25)" : "rgba(244, 67, 54, 0.25)"}`,
                    borderRadius: 18,
                    padding: "24px 28px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 14, marginBottom: 12 }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                          FEATURE 0{idx + 1}
                        </span>
                        <h3 style={{ fontSize: 17, fontWeight: 800, color: "white", margin: 0 }}>
                          {feat.feature_title}
                        </h3>
                      </div>
                      <div style={{ fontSize: 12, color: "var(--color-text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                        ID: {feat.feature_id}
                      </div>
                    </div>

                    {/* Verdict Pill & Amount */}
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <span
                        style={{
                          background: isPassed ? "rgba(76, 175, 80, 0.15)" : "rgba(244, 67, 54, 0.15)",
                          border: `1px solid ${isPassed ? "rgba(76, 175, 80, 0.4)" : "rgba(244, 67, 54, 0.4)"}`,
                          color: isPassed ? "#81C784" : "#EF5350",
                          padding: "4px 12px",
                          borderRadius: 20,
                          fontSize: 12,
                          fontWeight: 800,
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        {isPassed ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                        VERDICT: {feat.status}
                      </span>

                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: 16, fontWeight: 900, color: "white", fontFamily: "JetBrains Mono, monospace" }}>
                          ${feat.allocated_amount} USD
                        </div>
                        <div style={{ fontSize: 11, color: isPassed ? "#81C784" : "#EF5350" }}>
                          {isPassed ? "Release to seller" : "Refund to buyer"} ({feat.price_weight}%)
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Evidence Box */}
                  <div
                    style={{
                      background: "rgba(0, 0, 0, 0.25)",
                      border: "1px solid rgba(255, 255, 255, 0.06)",
                      borderRadius: 12,
                      padding: "14px 18px",
                      marginTop: 12,
                    }}
                  >
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#60A5FA", letterSpacing: "0.06em", marginBottom: 4 }}>
                      EVALUATION EVIDENCE &amp; LOG TRACE
                    </div>
                    <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5, margin: 0 }}>
                      {feat.evidence}
                    </p>

                    {feat.reason && (
                      <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid rgba(255,255,255,0.06)", fontSize: 12, color: "#EF5350" }}>
                        <strong>Failure Root Cause:</strong> {feat.reason}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* SECTION 2: SIDE-BY-SIDE VISUAL DIFF SCREENSHOTS (C29 Requirement 2) */}
        <div style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 14 }}>
            <div>
              <h2 style={{ fontSize: 22, fontWeight: 900, color: "white", display: "flex", alignItems: "center", gap: 10 }}>
                🖼️ Side-by-Side Visual Regression (Figma vs Render)
              </h2>
              <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginTop: 2 }}>
                Headless browser screenshot captured in sandbox compared directly with hirer&apos;s Figma design specification.
              </p>
            </div>

            {/* Mode Switcher */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 24,
                padding: "3px",
              }}
            >
              <button
                onClick={() => setActiveDiffMode("sideBySide")}
                style={{
                  background: activeDiffMode === "sideBySide" ? "linear-gradient(135deg, #0066FF, #00A3E0)" : "transparent",
                  color: "white",
                  border: "none",
                  borderRadius: 20,
                  padding: "6px 14px",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <Columns size={13} /> Side-by-Side
              </button>
              <button
                onClick={() => setActiveDiffMode("slider")}
                style={{
                  background: activeDiffMode === "slider" ? "linear-gradient(135deg, #0066FF, #00A3E0)" : "transparent",
                  color: "white",
                  border: "none",
                  borderRadius: 20,
                  padding: "6px 14px",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <Sliders size={13} /> Split Slider
              </button>
            </div>
          </div>

          {/* Visual Diff Viewport Container */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: 24,
              padding: "24px",
            }}
          >
            {/* Top Bar with Similarity Tag */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18, flexWrap: "wrap", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span
                  style={{
                    background: report.visual_diff_summary.passed ? "rgba(76, 175, 80, 0.15)" : "rgba(255, 152, 0, 0.15)",
                    border: `1px solid ${report.visual_diff_summary.passed ? "rgba(76, 175, 80, 0.4)" : "rgba(255, 152, 0, 0.4)"}`,
                    color: report.visual_diff_summary.passed ? "#81C784" : "#FFB74D",
                    padding: "3px 12px",
                    borderRadius: 20,
                    fontSize: 11,
                    fontWeight: 800,
                  }}
                >
                  SIMILARITY: {report.visual_diff_summary.similarity_score}% (THRESHOLD: {report.visual_diff_summary.threshold}%)
                </span>
                <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                  {report.visual_diff_summary.notes}
                </span>
              </div>
            </div>

            {/* Diff Render Display */}
            {activeDiffMode === "sideBySide" ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                {/* Left: Target Figma Specification */}
                <div
                  style={{
                    background: "rgba(0,0,0,0.4)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 16,
                    overflow: "hidden",
                  }}
                >
                  <div style={{ padding: "12px 16px", background: "rgba(255,255,255,0.04)", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: "#60A5FA" }}>
                      FIGMA DESIGN SPECIFICATION (TARGET)
                    </span>
                    <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>1440 × 900</span>
                  </div>

                  {/* Mock Wireframe Canvas Preview */}
                  <div style={{ padding: "24px", minHeight: 280, display: "flex", flexDirection: "column", gap: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ width: 80, height: 20, background: "#0066FF", borderRadius: 4 }} />
                      <div style={{ display: "flex", gap: 8 }}>
                        <div style={{ width: 40, height: 12, background: "rgba(255,255,255,0.2)", borderRadius: 2 }} />
                        <div style={{ width: 40, height: 12, background: "rgba(255,255,255,0.2)", borderRadius: 2 }} />
                      </div>
                    </div>
                    <div style={{ width: "70%", height: 32, background: "rgba(255,255,255,0.7)", borderRadius: 6, marginTop: 10 }} />
                    <div style={{ width: "90%", height: 16, background: "rgba(255,255,255,0.25)", borderRadius: 4 }} />
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginTop: 16 }}>
                      <div style={{ height: 80, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                      <div style={{ height: 80, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                      <div style={{ height: 80, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                    </div>
                  </div>
                </div>

                {/* Right: Actual Headless Browser Capture */}
                <div
                  style={{
                    background: "rgba(0,0,0,0.4)",
                    border: "1px solid rgba(255, 152, 0, 0.3)",
                    borderRadius: 16,
                    overflow: "hidden",
                  }}
                >
                  <div style={{ padding: "12px 16px", background: "rgba(255,152,0,0.06)", borderBottom: "1px solid rgba(255,152,0,0.2)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: "#FFB74D" }}>
                      HEADLESS BROWSER RENDER (ACTUAL RUNTIME)
                    </span>
                    <span style={{ fontSize: 11, color: "#EF5350", fontWeight: 700 }}>Mismatch Detected</span>
                  </div>

                  {/* Mock Wireframe Canvas Preview with Mismatch Highlight */}
                  <div style={{ padding: "24px", minHeight: 280, display: "flex", flexDirection: "column", gap: 14, position: "relative" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ width: 80, height: 20, background: "#0066FF", borderRadius: 4 }} />
                      <div style={{ display: "flex", gap: 8 }}>
                        <div style={{ width: 40, height: 12, background: "rgba(255,255,255,0.2)", borderRadius: 2 }} />
                        <div style={{ width: 40, height: 12, background: "rgba(255,255,255,0.2)", borderRadius: 2 }} />
                      </div>
                    </div>
                    {/* Visual Mismatch Highlight box */}
                    <div
                      style={{
                        border: "2px dashed #EF5350",
                        background: "rgba(244, 67, 54, 0.08)",
                        padding: "6px",
                        borderRadius: 8,
                        marginTop: 10,
                      }}
                    >
                      <div style={{ width: "85%", height: 32, background: "rgba(255,255,255,0.7)", borderRadius: 6 }} />
                      <div style={{ fontSize: 10, color: "#EF5350", fontWeight: 800, marginTop: 4 }}>
                        Δ Header font size 36px vs Figma 28px
                      </div>
                    </div>
                    <div style={{ width: "90%", height: 16, background: "rgba(255,255,255,0.25)", borderRadius: 4 }} />
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginTop: 16 }}>
                      <div style={{ height: 80, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                      <div style={{ height: 80, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                      <div style={{ height: 80, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* Split Slider Mode */
              <div>
                <div style={{ marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                    Drag slider to compare Figma Spec (left) vs Headless Output (right):
                  </span>
                  <span style={{ fontSize: 13, fontWeight: 700, color: "#60A5FA", fontFamily: "JetBrains Mono, monospace" }}>
                    {sliderPosition}% Split
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={sliderPosition}
                  onChange={(e) => setSliderPosition(Number(e.target.value))}
                  style={{ width: "100%", accentColor: "#0066FF", cursor: "ew-resize", marginBottom: 16 }}
                />

                <div
                  style={{
                    position: "relative",
                    minHeight: 280,
                    background: "rgba(0,0,0,0.4)",
                    borderRadius: 16,
                    overflow: "hidden",
                    border: "1px solid rgba(255,255,255,0.1)",
                  }}
                >
                  <div style={{ padding: "32px", width: "100%" }}>
                    <div style={{ width: `${sliderPosition}%`, borderRight: "2px solid #0066FF", height: "100%", position: "absolute", top: 0, left: 0, background: "rgba(0, 102, 255, 0.05)", pointerEvents: "none" }} />
                    <div style={{ width: "70%", height: 32, background: "rgba(255,255,255,0.8)", borderRadius: 6, marginBottom: 12 }} />
                    <div style={{ width: "90%", height: 16, background: "rgba(255,255,255,0.3)", borderRadius: 4, marginBottom: 24 }} />
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                      <div style={{ height: 80, background: "rgba(255,255,255,0.06)", borderRadius: 8 }} />
                      <div style={{ height: 80, background: "rgba(255,255,255,0.06)", borderRadius: 8 }} />
                      <div style={{ height: 80, background: "rgba(255,255,255,0.06)", borderRadius: 8 }} />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* SECTION 3: CHEAT & LOOPHOLE SCAN FINDINGS (AST Stage C) */}
        {report.cheat_scan_findings.length > 0 && (
          <div style={{ marginBottom: 40 }}>
            <h2 style={{ fontSize: 22, fontWeight: 900, color: "white", marginBottom: 6, display: "flex", alignItems: "center", gap: 10 }}>
              🛡️ AST Cheat &amp; Hardcode Scan Findings
            </h2>
            <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginBottom: 20 }}>
              Automated abstract syntax tree inspection to detect mock bypasses, skipped assertions, or hardcoded API constants.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {report.cheat_scan_findings.map((item) => (
                <div
                  key={item.finding_id}
                  style={{
                    background: item.severity === "HIGH" ? "rgba(244, 67, 54, 0.05)" : "rgba(255, 152, 0, 0.05)",
                    border: `1px solid ${item.severity === "HIGH" ? "rgba(244, 67, 54, 0.3)" : "rgba(255, 152, 0, 0.3)"}`,
                    borderRadius: 16,
                    padding: "20px 24px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span
                        style={{
                          background: item.severity === "HIGH" ? "rgba(244, 67, 54, 0.2)" : "rgba(255, 152, 0, 0.2)",
                          color: item.severity === "HIGH" ? "#EF5350" : "#FFB74D",
                          border: `1px solid ${item.severity === "HIGH" ? "#EF5350" : "#FFB74D"}`,
                          padding: "2px 10px",
                          borderRadius: 20,
                          fontSize: 11,
                          fontWeight: 800,
                        }}
                      >
                        {item.severity} SEVERITY
                      </span>
                      <span style={{ fontSize: 13, fontWeight: 700, color: "white" }}>
                        Rule: {item.rule_violated}
                      </span>
                    </div>

                    <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, color: "var(--color-text-muted)" }}>
                      {item.file_path}:{item.line_number}
                    </div>
                  </div>

                  <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5, margin: 0 }}>
                    {item.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SECTION 4: CONTAINER BUILD & SANDBOX LOGS */}
        <div
          style={{
            background: "rgba(10, 15, 29, 0.95)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: 20,
            padding: "24px 28px",
            marginBottom: 32,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", display: "flex", alignItems: "center", gap: 8 }}>
              <Terminal size={14} color="#60A5FA" />
              MICROVM SANDBOX BUILD OUTPUT
            </div>
            <span style={{ fontSize: 11, color: "#81C784", fontFamily: "JetBrains Mono, monospace" }}>
              EXIT 0 (SUCCESS)
            </span>
          </div>

          <pre
            style={{
              background: "rgba(0, 0, 0, 0.4)",
              padding: "16px",
              borderRadius: 12,
              border: "1px solid rgba(255, 255, 255, 0.05)",
              color: "#93C5FD",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 12,
              lineHeight: 1.6,
              overflowX: "auto",
              margin: 0,
            }}
          >
            {report.build_logs}
          </pre>
        </div>

        {/* Bottom Decision / Payout Actions */}
        <div
          style={{
            background: "rgba(12, 18, 34, 0.95)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            borderRadius: 24,
            padding: "24px 32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 20,
          }}
        >
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: "white" }}>
              AI Referee Evaluation Concluded
            </div>
            <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 2 }}>
              Recommended action: Release ${passedAmount.toLocaleString()} USD to seller for verified features.
            </div>
          </div>

          <div style={{ display: "flex", gap: 14 }}>
            <Link
              href={`/contracts/${contract.id}/dispute`}
              style={{
                background: "rgba(244, 67, 54, 0.1)",
                border: "1px solid rgba(244, 67, 54, 0.3)",
                color: "#EF5350",
                padding: "12px 24px",
                borderRadius: 50,
                fontSize: 14,
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              Open Dispute
            </Link>

            <Link
              href={`/contracts/${contract.id}`}
              style={{
                background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                color: "white",
                padding: "12px 28px",
                borderRadius: 50,
                fontSize: 14,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 0 25px rgba(0,102,255,0.4)",
              }}
            >
              Proceed to Decision &amp; Settlement →
            </Link>
          </div>
        </div>

        {/* RAW REPORT JSON INSPECTOR MODAL (C07 & C29 Compliance) */}
        {isJsonModalOpen && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(0,0,0,0.85)",
              backdropFilter: "blur(10px)",
              zIndex: 300,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "20px",
            }}
          >
            <div
              style={{
                background: "rgba(15, 23, 42, 0.98)",
                border: "1px solid rgba(255,255,255,0.15)",
                borderRadius: 24,
                padding: "32px",
                maxWidth: 780,
                width: "100%",
                maxHeight: "85vh",
                display: "flex",
                flexDirection: "column",
                boxShadow: "0 25px 60px rgba(0,0,0,0.8)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div>
                  <h3 style={{ fontSize: 18, fontWeight: 800, color: "white", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                    <Code2 size={18} color="#60A5FA" /> Shared Verification Report JSON (C07 / C29)
                  </h3>
                  <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 2 }}>
                    Strict implementation of shared verification report schema
                  </div>
                </div>

                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    onClick={handleCopyJson}
                    style={{
                      background: "rgba(255,255,255,0.06)",
                      border: "1px solid rgba(255,255,255,0.15)",
                      color: "white",
                      padding: "6px 14px",
                      borderRadius: 16,
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    {copiedJson ? <Check size={13} color="#81C784" /> : <Copy size={13} />}
                    {copiedJson ? "Copied!" : "Copy JSON"}
                  </button>

                  <button
                    onClick={() => setIsJsonModalOpen(false)}
                    style={{
                      background: "rgba(255,255,255,0.06)",
                      border: "none",
                      color: "white",
                      padding: "6px 12px",
                      borderRadius: 16,
                      fontSize: 12,
                      cursor: "pointer",
                    }}
                  >
                    ✕ Close
                  </button>
                </div>
              </div>

              <div style={{ flex: 1, overflowY: "auto", background: "rgba(0,0,0,0.5)", borderRadius: 12, border: "1px solid rgba(255,255,255,0.07)", padding: "16px" }}>
                <pre
                  style={{
                    color: "#93C5FD",
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 12,
                    lineHeight: 1.5,
                    margin: 0,
                  }}
                >
                  {JSON.stringify(report, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}

      </div>
      <Footer />
    </main>
  );
}

