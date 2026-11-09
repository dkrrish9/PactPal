"use client";
import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { 
  GitBranch, 
  Terminal, 
  Palette, 
  CheckSquare, 
  ShieldCheck, 
  ArrowLeft, 
  Sparkles,
  Loader2,
  FileCode,
  Globe
} from "lucide-react";

export default function ContractSubmitPage() {
  const params = useParams();
  const router = useRouter();
  const contractId = (params?.id as string) || "pct_099e77";

  const [repoUrl, setRepoUrl] = useState("https://github.com/freelancer/pactpal-storefront");
  const [commitSha, setCommitSha] = useState("a1b8c9d4e5f67890123456789abcdef012345678");
  const [branch, setBranch] = useState("main");
  const [deployUrl, setDeployUrl] = useState("https://preview.pactpal-storefront.vercel.app");
  const [figmaUrl, setFigmaUrl] = useState("https://figma.com/design/pactpal-specs-v2");
  const [notes, setNotes] = useState("All 5 features implemented according to checklist. Run `npm test` and `npm run build` inside sandbox.");
  const [checks, setChecks] = useState({
    testsPassing: true,
    noHardcodedResponses: true,
    responsiveChecked: true,
    cleanLinter: true,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pipelineStage, setPipelineStage] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const stages = [
      "Cloning repository into isolated microVM container...",
      "Running Stage A: Dependency isolation and container sandbox verification...",
      "Running Stage B: Test runner execution (npm test)...",
      "Running Stage C: AST static analysis for hardcoded mocks...",
      "Running Stage D: Headless Chrome visual diff against Figma design...",
      "Stage E: Integrity check complete. Generating cryptographic receipt...",
    ];

    let current = 0;
    setPipelineStage(stages[0]);

    const interval = setInterval(() => {
      current++;
      if (current < stages.length) {
        setPipelineStage(stages[current]);
      } else {
        clearInterval(interval);
        setTimeout(() => {
          router.push(`/contracts/${contractId}?submitted=true`);
        }, 1200);
      }
    }, 900);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        color: "white",
        fontFamily: "Inter, sans-serif",
        paddingTop: 88,
        paddingBottom: 80,
      }}
    >
      <div style={{ maxWidth: 840, margin: "0 auto", padding: "0 24px" }}>
        
        {/* Back Link */}
        <Link
          href={`/contracts/${contractId}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            color: "var(--color-text-secondary)",
            textDecoration: "none",
            fontSize: 14,
            marginBottom: 24,
          }}
        >
          <ArrowLeft size={16} /> Back to Contract Overview
        </Link>

        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 10px",
              borderRadius: 8,
              background: "rgba(255,152,0,0.12)",
              border: "1px solid rgba(255,152,0,0.3)",
              fontSize: 12,
              fontWeight: 700,
              color: "var(--color-accent)",
              letterSpacing: "0.06em",
              marginBottom: 12,
            }}
          >
            <ShieldCheck size={14} />
            STAGE 4 &bull; AI REFEREE SUBMISSION GATEWAY
          </div>
          <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.02em", marginBottom: 8 }}>
            Submit Deliverables for Verification
          </h1>
          <p style={{ color: "var(--color-text-muted)", fontSize: 15, lineHeight: 1.6 }}>
            The AI Referee will boot your code in an isolated gVisor container, execute automated test suites, scan AST for mock bypasses, and compare visual screenshots with the hirer&apos;s Figma design.
          </p>
        </div>

        {/* Modal / Submission Form */}
        <form onSubmit={handleSubmit}>
          <div className="glass-card" style={{ padding: "32px", display: "flex", flexDirection: "column", gap: 24, marginBottom: 24 }}>
            
            {/* Git Repo & Branch */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 8 }}>
                  <GitBranch size={14} color="var(--color-primary)" />
                  GIT REPOSITORY URL
                </label>
                <input
                  type="text"
                  required
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    borderRadius: 10,
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    color: "white",
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 13,
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 8 }}>
                  <FileCode size={14} color="var(--color-secondary)" />
                  BRANCH
                </label>
                <input
                  type="text"
                  required
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    borderRadius: 10,
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    color: "white",
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 13,
                    outline: "none",
                  }}
                />
              </div>
            </div>

            {/* Commit SHA */}
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 8 }}>
                <Terminal size={14} color="var(--color-accent)" />
                EXACT COMMIT SHA (FOR IMMUTABLE TESTING)
              </label>
              <input
                type="text"
                required
                value={commitSha}
                onChange={(e) => setCommitSha(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "white",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 13,
                  outline: "none",
                }}
              />
              <span style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 4, display: "block" }}>
                The container will pin and verify this exact git object hash to prevent race conditions or post-submission modifications.
              </span>
            </div>

            {/* Live Preview & Figma URL */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 8 }}>
                  <Globe size={14} color="#60A5FA" />
                  LIVE PREVIEW / DEPLOY URL
                </label>
                <input
                  type="url"
                  value={deployUrl}
                  onChange={(e) => setDeployUrl(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    borderRadius: 10,
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    color: "white",
                    fontSize: 13,
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 8 }}>
                  <Palette size={14} color="#F24E1E" />
                  FIGMA DESIGN REFERENCE
                </label>
                <input
                  type="url"
                  value={figmaUrl}
                  onChange={(e) => setFigmaUrl(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    borderRadius: 10,
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    color: "white",
                    fontSize: 13,
                    outline: "none",
                  }}
                />
              </div>
            </div>

            {/* Verification Checklist */}
            <div>
              <span style={{ display: "block", fontSize: 13, fontWeight: 700, color: "var(--color-text-secondary)", letterSpacing: "0.06em", marginBottom: 12 }}>
                PRE-SUBMISSION VERIFICATION GUARANTEES
              </span>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  { key: "testsPassing", label: "Automated test suite (unit + integration) passes locally with 0 errors" },
                  { key: "noHardcodedResponses", label: "No stubbed or hardcoded mock constants simulating backend API endpoints" },
                  { key: "responsiveChecked", label: "Responsive layout validated against mobile (390px) and desktop (1440px) breakpoints" },
                  { key: "cleanLinter", label: "Clean build with zero TypeScript and linting warnings" },
                ].map((item) => (
                  <label
                    key={item.key}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "10px 14px",
                      borderRadius: 8,
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.06)",
                      cursor: "pointer",
                      fontSize: 13,
                      color: "var(--color-text-secondary)",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checks[item.key as keyof typeof checks]}
                      onChange={(e) => setChecks({ ...checks, [item.key]: e.target.checked })}
                      style={{ accentColor: "var(--color-primary)", width: 16, height: 16 }}
                    />
                    {item.label}
                  </label>
                ))}
              </div>
            </div>

            {/* Build Notes */}
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: 8 }}>
                SANDBOX INSTRUCTIONS & REPRODUCTION NOTES
              </label>
              <textarea
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "white",
                  fontSize: 13,
                  outline: "none",
                  resize: "vertical",
                }}
              />
            </div>
          </div>

          {/* Progress / Pipeline Execution Feedback */}
          {isSubmitting && (
            <div
              className="glass-card"
              style={{
                padding: "20px 24px",
                marginBottom: 24,
                border: "1px solid var(--color-primary)",
                background: "rgba(0,102,255,0.08)",
                display: "flex",
                alignItems: "center",
                gap: 16,
              }}
            >
              <Loader2 size={24} color="var(--color-primary)" className="animate-spin" />
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "white", marginBottom: 2 }}>
                  AI REFEREE SANDBOX PIPELINE ACTIVE
                </div>
                <div style={{ fontSize: 13, color: "#93C5FD", fontFamily: "JetBrains Mono, monospace" }}>
                  {pipelineStage}
                </div>
              </div>
            </div>
          )}

          {/* Submit Action Row */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Link
              href={`/contracts/${contractId}`}
              style={{
                padding: "12px 20px",
                borderRadius: 10,
                border: "1px solid rgba(255,255,255,0.12)",
                color: "var(--color-text-secondary)",
                textDecoration: "none",
                fontSize: 14,
              }}
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-gradient"
              style={{
                padding: "14px 28px",
                fontSize: 15,
                fontWeight: 700,
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                cursor: isSubmitting ? "not-allowed" : "pointer",
                opacity: isSubmitting ? 0.7 : 1,
              }}
            >
              <Sparkles size={16} />
              {isSubmitting ? "Evaluating Deliverable..." : "Dispatch to AI Referee →"}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}
