"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
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
  Globe,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Info
} from "lucide-react";
import { mockApi, Contract } from "@/lib/mockApi";
import { backendClient } from "@/lib/backendClient";

export default function ContractSubmitPage() {
  const params = useParams();
  const router = useRouter();
  const contractId = (params?.id as string) || "pct_099e77";

  const [contract, setContract] = useState<Contract | null>(null);
  const [repoUrl, setRepoUrl] = useState("https://github.com/freelancer/pactpal-storefront");
  const [commitSha, setCommitSha] = useState("a1b8c9d4e5f67890123456789abcdef012345678");
  const [branch, setBranch] = useState("main");
  const [deployUrl, setDeployUrl] = useState("https://preview.pactpal-storefront.vercel.app");
  const [notes, setNotes] = useState("All features implemented according to checklist. Run `npm test` and `npm run build` inside sandbox.");
  
  // Simulation flag for testing Late Submissions
  const [simulateLate, setSimulateLate] = useState(false);

  const [checks, setChecks] = useState({
    testsPassing: true,
    noHardcodedResponses: true,
    responsiveChecked: true,
    cleanLinter: true,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pipelineStage, setPipelineStage] = useState<string | null>(null);

  useEffect(() => {
    async function loadSubmitData() {
      try {
        const live = await backendClient.getContract(contractId);
        if (live) {
          setContract(live as unknown as Contract);
          if (live.repo_url) setRepoUrl(live.repo_url);
          return;
        }
      } catch {}

      const loaded = mockApi.getContract(contractId) || mockApi.getContracts()[0];
      if (loaded) {
        setContract(loaded);
        if (loaded.repo_url) setRepoUrl(loaded.repo_url);
        if (loaded.commit_sha) setCommitSha(loaded.commit_sha);
      }
    }
    loadSubmitData();
  }, [contractId]);

  if (!contract) {
    return (
      <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
        <Navbar />
        <div style={{ maxWidth: 840, margin: "140px auto", textAlign: "center", color: "white" }}>
          <h2>Loading submission portal...</h2>
        </div>
      </main>
    );
  }

  // Calculate actual deadline vs current time
  const deadlineDate = new Date(contract.deadline);
  const isPastDeadline = simulateLate || Date.now() > deadlineDate.getTime();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const stages = [
      "Recording submission intake & timestamping...",
      "Cloning git repository into isolated gVisor sandbox container...",
      "Executing Stage A: Dependency installation & container security checks...",
      "Executing Stage B: Automated unit and integration test runner (npm test)...",
      "Executing Stage C: AST cheat-scan for mock hardcoded bypasses...",
      "Executing Stage D: Headless visual diff against Figma design...",
      "Submitting verification intake to AI Referee engine...",
    ];

    let current = 0;
    setPipelineStage(stages[0]);

    const interval = setInterval(() => {
      current++;
      if (current < stages.length) {
        setPipelineStage(stages[current]);
      } else {
        clearInterval(interval);
        
        // Save submission into Supabase DB + mockApi state contract
        backendClient.submitDeliverable({
          contract_id: contract.id,
          repo_url: repoUrl,
          commit_sha: commitSha,
          branch: branch,
          deploy_url: deployUrl,
          build_notes: notes,
        });

        // If late simulation was toggled, mark the newly saved submission as late
        if (simulateLate) {
          const fresh = mockApi.getContract(contract.id);
          if (fresh && fresh.submission) {
            fresh.submission.is_late = true;
          }
        }

        setTimeout(() => {
          router.push(`/contracts/${contract.id}?submitted=true`);
        }, 1000);
      }
    }, 800);
  };

  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      <div style={{ maxWidth: 880, margin: "0 auto", padding: "110px 24px 80px" }}>
        
        {/* Back Link */}
        <Link
          href={`/contracts/${contract.id}`}
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
          <ArrowLeft size={16} /> Back to Contract Overview ({contract.id})
        </Link>

        {/* Header Block */}
        <div style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 12 }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "5px 12px",
                borderRadius: 50,
                background: "rgba(0,102,255,0.12)",
                border: "1px solid rgba(0,102,255,0.3)",
                fontSize: 12,
                fontWeight: 700,
                color: "#60A5FA",
                letterSpacing: "0.06em",
              }}
            >
              <ShieldCheck size={14} />
              C25 • SELLER SUBMISSION & VERIFICATION INTAKE
            </div>

            {/* Test Toggle for Late Flag */}
            <button
              type="button"
              onClick={() => setSimulateLate(!simulateLate)}
              style={{
                background: simulateLate ? "rgba(244, 67, 54, 0.2)" : "rgba(255, 255, 255, 0.05)",
                border: `1px solid ${simulateLate ? "rgba(244, 67, 54, 0.5)" : "rgba(255, 255, 255, 0.15)"}`,
                color: simulateLate ? "#EF5350" : "var(--color-text-secondary)",
                borderRadius: 20,
                padding: "4px 12px",
                fontSize: 12,
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              {simulateLate ? "Simulating: Late Submission" : "Simulate: Test Late Flag"}
            </button>
          </div>

          <h1 style={{ fontSize: "clamp(26px, 4vw, 36px)", fontWeight: 900, color: "white", marginBottom: 8 }}>
            Submit Deliverables for AI Verification
          </h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: 15, lineHeight: 1.6 }}>
            Contract: <strong style={{ color: "white" }}>{contract.title}</strong>
          </p>
        </div>

        {/* Real-time Late Flag Status Callout (C25 Core Requirement) */}
        <div
          style={{
            background: isPastDeadline ? "rgba(244, 67, 54, 0.08)" : "rgba(76, 175, 80, 0.08)",
            border: `1px solid ${isPastDeadline ? "rgba(244, 67, 54, 0.35)" : "rgba(76, 175, 80, 0.35)"}`,
            borderRadius: 18,
            padding: "20px 24px",
            marginBottom: 28,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            {isPastDeadline ? (
              <AlertTriangle size={24} color="#EF5350" />
            ) : (
              <CheckCircle2 size={24} color="#81C784" />
            )}
            <div>
              <div style={{ fontSize: 15, fontWeight: 800, color: isPastDeadline ? "#EF5350" : "#81C784" }}>
                {isPastDeadline ? "LATE SUBMISSION DETECTED" : "ON-TIME SUBMISSION"}
              </div>
              <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 2 }}>
                Agreed Deadline: <strong style={{ color: "white" }}>{deadlineDate.toLocaleDateString(undefined, { weekday: "short", year: "numeric", month: "short", day: "numeric" })}</strong>
                {isPastDeadline ? " (Late flag will be permanently recorded against this submission)." : " (Submission arrives before the agreed milestone deadline)."}
              </div>
            </div>
          </div>

          <span
            style={{
              padding: "4px 12px",
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 800,
              fontFamily: "JetBrains Mono, monospace",
              background: isPastDeadline ? "rgba(244, 67, 54, 0.15)" : "rgba(76, 175, 80, 0.15)",
              color: isPastDeadline ? "#EF5350" : "#81C784",
              border: `1px solid ${isPastDeadline ? "rgba(244, 67, 54, 0.3)" : "rgba(76, 175, 80, 0.3)"}`,
            }}
          >
            {isPastDeadline ? "FLAG: LATE" : "FLAG: ON_TIME"}
          </span>
        </div>

        {/* Modal / Submission Form */}
        <form onSubmit={handleSubmit}>
          <div
            style={{
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: 24,
              padding: "32px",
              display: "flex",
              flexDirection: "column",
              gap: 24,
              marginBottom: 28,
            }}
          >
            {/* Git Repo & Branch */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
              <div>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", marginBottom: 8 }}>
                  <GitBranch size={14} color="#60A5FA" />
                  GIT REPOSITORY URL (REQUIRED)
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://github.com/org/repo"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    borderRadius: 12,
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    color: "white",
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 14,
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", marginBottom: 8 }}>
                  <FileCode size={14} color="#34D399" />
                  BRANCH (DEFAULT: main)
                </label>
                <input
                  type="text"
                  required
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    borderRadius: 12,
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    color: "white",
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 14,
                    outline: "none",
                  }}
                />
              </div>
            </div>

            {/* Commit SHA */}
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", marginBottom: 8 }}>
                <Terminal size={14} color="#FBBF24" />
                EXACT COMMIT SHA (FOR IMMUTABLE CONTAINER VERIFICATION)
              </label>
              <input
                type="text"
                required
                placeholder="40-character hex sha"
                value={commitSha}
                onChange={(e) => setCommitSha(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "white",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 14,
                  outline: "none",
                }}
              />
              <span style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 6, display: "block" }}>
                The verification sandbox pins this exact git SHA to ensure test suites cannot be modified post-submission.
              </span>
            </div>

            {/* Live Preview URL */}
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", marginBottom: 8 }}>
                <Globe size={14} color="#60A5FA" />
                LIVE PREVIEW / DEPLOYMENT URL (OPTIONAL)
              </label>
              <input
                type="url"
                placeholder="https://preview.yourdomain.com"
                value={deployUrl}
                onChange={(e) => setDeployUrl(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "white",
                  fontSize: 14,
                  outline: "none",
                }}
              />
            </div>

            {/* Build Notes (C25 Core Requirement) */}
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", marginBottom: 8 }}>
                <Info size={14} color="#A78BFA" />
                BUILD NOTE & REPRODUCTION INSTRUCTIONS (REQUIRED)
              </label>
              <textarea
                rows={3}
                required
                placeholder="e.g. Run `npm install` then `npm test`. Port 3000 serves the Next.js app. Docker container requires NODE_ENV=test."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  borderRadius: 12,
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "white",
                  fontSize: 14,
                  outline: "none",
                  resize: "vertical",
                  lineHeight: 1.5,
                }}
              />
            </div>

            {/* Pre-submission checklist */}
            <div>
              <span style={{ display: "block", fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em", marginBottom: 10 }}>
                PRE-SUBMISSION VERIFICATION GUARANTEES
              </span>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  { key: "testsPassing", label: "Automated unit tests execute and pass with 0 errors" },
                  { key: "noHardcodedResponses", label: "No hardcoded return values designed to fake API responses" },
                  { key: "responsiveChecked", label: "Deliverable matches Figma design breakpoints" },
                  { key: "cleanLinter", label: "TypeScript builds cleanly without unhandled syntax exceptions" },
                ].map((item) => (
                  <label
                    key={item.key}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: "rgba(255,255,255,0.02)",
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
                      style={{ accentColor: "#0066FF", width: 16, height: 16 }}
                    />
                    {item.label}
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Progress / Pipeline Execution Feedback */}
          {isSubmitting && (
            <div
              style={{
                padding: "20px 24px",
                marginBottom: 24,
                borderRadius: 16,
                border: "1px solid #0066FF",
                background: "rgba(0,102,255,0.1)",
                display: "flex",
                alignItems: "center",
                gap: 16,
              }}
            >
              <Loader2 size={24} color="#60A5FA" className="spin" />
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "white", marginBottom: 2 }}>
                  AI REFEREE INTAKE PIPELINE ACTIVE
                </div>
                <div style={{ fontSize: 13, color: "#93C5FD", fontFamily: "JetBrains Mono, monospace" }}>
                  {pipelineStage}
                </div>
              </div>
            </div>
          )}

          {/* Submit Action Row */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 14 }}>
            <Link
              href={`/contracts/${contract.id}`}
              style={{
                padding: "12px 24px",
                borderRadius: 50,
                border: "1px solid rgba(255,255,255,0.15)",
                color: "var(--color-text-secondary)",
                textDecoration: "none",
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                border: "none",
                borderRadius: 50,
                color: "white",
                padding: "14px 32px",
                fontSize: 15,
                fontWeight: 700,
                cursor: isSubmitting ? "not-allowed" : "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 10,
                boxShadow: "0 0 25px rgba(0,102,255,0.4)",
                opacity: isSubmitting ? 0.7 : 1,
              }}
            >
              <Sparkles size={16} />
              {isSubmitting ? "Dispatching to AI Referee..." : "Dispatch Submission to AI Referee (C25) →"}
            </button>
          </div>
        </form>

      </div>
      <Footer />
    </main>
  );
}
