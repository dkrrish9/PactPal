"use client";
import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import { useRouter } from "next/navigation";
import { 
  CheckCircle, 
  ArrowRight, 
  ArrowLeft, 
  Palette, 
  Trash2, 
  Plus, 
  ShieldCheck, 
  ExternalLink,
  Loader2,
  FileCode,
  Sparkles,
  AlertTriangle,
  HelpCircle
} from "lucide-react";
import { mockApi } from "@/lib/mockApi";
import { getCurrentUser } from "@/lib/supabase";

type Feature = { name: string; weight: number; test: string };

type FormState = {
  title: string;
  description: string;
  buyerEmail: string;
  sellerEmail: string;
  deadline: string;
  totalAmount: string;
  currency: string;
  figmaUrl: string;
  repoUrl: string;
};

const STEPS = ["Basic Info", "Feature Checklist", "Escrow Settings", "Review"];

export default function CreateContractPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<FormState>({
    title: "",
    description: "",
    buyerEmail: "priya@fintech.io",
    sellerEmail: "alex.dev@code.io",
    deadline: new Date(Date.now() + 14 * 86400000).toISOString().split("T")[0],
    totalAmount: "1500",
    currency: "USD",
    figmaUrl: "https://figma.com/design/sample-project-spec",
    repoUrl: "https://github.com/freelancer/pactpal-storefront",
  });

  useEffect(() => {
    const user = getCurrentUser();
    if (user && user.email) {
      setForm((prev) => ({
        ...prev,
        buyerEmail: user.email,
      }));
    }
  }, []);

  const [features, setFeatures] = useState<Feature[]>([
    { name: "Landing page", weight: 25, test: "All 12 sections render, CTA links work, mobile drawer opens" },
    { name: "Login system", weight: 20, test: "Login/logout with JWT, session persists across refresh" },
    { name: "Dashboard", weight: 30, test: "Data loads from API, Bryntum Gantt chart renders, 100% responsive" },
    { name: "Payment flow", weight: 25, test: "PayPal escrow webhook listeners respond with 200" },
  ]);

  const totalWeight = features.reduce((s, f) => s + (Number(f.weight) || 0), 0);
  const weightOk = totalWeight === 100;
  const basicInfoOk = form.title.trim() !== "" && form.buyerEmail.trim() !== "" && form.sellerEmail.trim() !== "" && form.totalAmount.trim() !== "";

  // Phase 1 / Agreement Reader Rule: Every feature must have a measurable acceptance test
  const featureIssues = features.map((f, idx) => {
    const issues: string[] = [];
    if (!f.name || f.name.trim().length === 0) {
      issues.push(`Feature #${idx + 1} needs a title`);
    }
    if (!f.test || f.test.trim().length === 0) {
      issues.push(`Feature #${idx + 1} has no acceptance test`);
    } else if (f.test.trim().length < 10) {
      issues.push(`Feature #${idx + 1} test is too short ("${f.test}"). Must specify an objective condition`);
    }
    if (Number(f.weight) <= 0) {
      issues.push(`Feature #${idx + 1} weight must be > 0%`);
    }
    return { index: idx, name: f.name || `Feature ${idx + 1}`, issues };
  });

  const allTestsMeasurable = featureIssues.every((fi) => fi.issues.length === 0);
  const canProceedFromFeatures = weightOk && allTestsMeasurable;

  const handleSubmit = async () => {
    if (!canProceedFromFeatures || !basicInfoOk) return;
    setIsSubmitting(true);

    try {
      const user = getCurrentUser();
      const created = mockApi.createContract({
        title: form.title,
        description: form.description,
        buyer_id: user?.id,
        buyer_name: user?.name,
        buyer_email: form.buyerEmail,
        seller_email: form.sellerEmail,
        total_amount: parseFloat(form.totalAmount) || 1500,
        currency: form.currency || "USD",
        deadline: new Date(form.deadline || Date.now() + 14 * 86400000).toISOString(),
        figma_url: form.figmaUrl,
        repo_url: form.repoUrl,
        features: features.map((f) => ({
          title: f.name || "Untitled Feature",
          acceptance_test: f.test || "Acceptance test passed",
          price_weight: Number(f.weight) || 0,
        })),
      });

      // Brief simulated state sync delay
      setTimeout(() => {
        router.push(`/contracts/${created.id}`);
      }, 700);
    } catch (err) {
      console.error("Failed to create contract:", err);
      setIsSubmitting(false);
    }
  };

  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      <div
        style={{
          maxWidth: 820,
          margin: "0 auto",
          padding: "120px 24px 80px",
        }}
      >
        {/* Stepper */}
        <div
          style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 48 }}
          role="navigation"
          aria-label="Contract creation progress"
        >
          {STEPS.map((label, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", flex: i < STEPS.length - 1 ? 1 : 0 }}>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    background: i < step
                      ? "#4CAF50"
                      : i === step
                      ? "linear-gradient(135deg, #0066FF, #00A3E0)"
                      : "rgba(255,255,255,0.08)",
                    border: `2px solid ${i < step ? "#4CAF50" : i === step ? "#0066FF" : "rgba(255,255,255,0.1)"}`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 13,
                    fontWeight: 700,
                    color: "white",
                    flexShrink: 0,
                    boxShadow: i === step ? "0 0 20px rgba(0,102,255,0.5)" : "none",
                    transition: "all 0.3s",
                  }}
                  aria-current={i === step ? "step" : undefined}
                  aria-label={`Step ${i + 1}: ${label}${i < step ? " (completed)" : i === step ? " (current)" : ""}`}
                >
                  {i < step ? <CheckCircle size={18} /> : i + 1}
                </div>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: i === step ? "white" : "var(--color-text-muted)",
                    whiteSpace: "nowrap",
                    letterSpacing: "0.04em",
                  }}
                >
                  {label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  style={{
                    flex: 1,
                    height: 2,
                    background: i < step
                      ? "#4CAF50"
                      : "rgba(255,255,255,0.08)",
                    marginBottom: 22,
                    marginLeft: 8,
                    marginRight: 8,
                    borderRadius: 1,
                    transition: "background 0.4s",
                  }}
                  aria-hidden
                />
              )}
            </div>
          ))}
        </div>

        {/* Step panels */}
        <div
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 28,
            padding: "40px",
          }}
          role="main"
          aria-label={`Step ${step + 1}: ${STEPS[step]}`}
        >
          {step === 0 && (
            <StepBasicInfo form={form} setForm={setForm} />
          )}
          {step === 1 && (
            <StepFeatures
              form={form}
              features={features}
              setFeatures={setFeatures}
              totalWeight={totalWeight}
              weightOk={weightOk}
              featureIssues={featureIssues}
              allTestsMeasurable={allTestsMeasurable}
            />
          )}
          {step === 2 && (
            <StepEscrow form={form} setForm={setForm} />
          )}
          {step === 3 && (
            <StepReview form={form} features={features} totalWeight={totalWeight} weightOk={weightOk} />
          )}

          {/* Navigation buttons */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: 40,
              paddingTop: 24,
              borderTop: "1px solid rgba(255,255,255,0.07)",
              flexWrap: "wrap",
              gap: 12,
            }}
          >
            <button
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0 || isSubmitting}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: "none",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 50,
                color: step === 0 ? "var(--color-text-muted)" : "white",
                padding: "12px 24px",
                fontSize: 15,
                fontWeight: 600,
                cursor: step === 0 ? "default" : "pointer",
                opacity: step === 0 ? 0.4 : 1,
              }}
              aria-label="Previous step"
            >
              <ArrowLeft size={16} aria-hidden /> Back
            </button>

            {step === 1 && (!weightOk || !allTestsMeasurable) && (
              <div
                style={{
                  fontSize: 13,
                  color: "#EF4444",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  fontFamily: "JetBrains Mono, monospace",
                }}
              >
                <span>⚠️</span> {!weightOk ? `Total is ${totalWeight}% (must equal exactly 100%)` : "All features must have objective acceptance tests"}
              </div>
            )}

            {step < STEPS.length - 1 ? (
              <button
                onClick={() => {
                  if (step === 1 && !canProceedFromFeatures) return;
                  if (step === 0 && !basicInfoOk) return;
                  setStep((s) => Math.min(STEPS.length - 1, s + 1));
                }}
                disabled={(step === 1 && !canProceedFromFeatures) || (step === 0 && !basicInfoOk)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  background:
                    (step === 1 && !canProceedFromFeatures) || (step === 0 && !basicInfoOk)
                      ? "rgba(255,255,255,0.06)"
                      : "linear-gradient(135deg, #0066FF, #00A3E0)",
                  border:
                    (step === 1 && !canProceedFromFeatures) || (step === 0 && !basicInfoOk)
                      ? "1px solid rgba(255,255,255,0.1)"
                      : "none",
                  borderRadius: 50,
                  color:
                    (step === 1 && !canProceedFromFeatures) || (step === 0 && !basicInfoOk)
                      ? "rgba(255,255,255,0.35)"
                      : "white",
                  padding: "12px 28px",
                  fontSize: 15,
                  fontWeight: 700,
                  cursor:
                    (step === 1 && !canProceedFromFeatures) || (step === 0 && !basicInfoOk)
                      ? "not-allowed"
                      : "pointer",
                  boxShadow:
                    (step === 1 && !canProceedFromFeatures) || (step === 0 && !basicInfoOk)
                      ? "none"
                      : "0 0 20px rgba(0,102,255,0.4)",
                  transition: "all 0.2s ease",
                }}
                aria-label="Next step"
                aria-disabled={(step === 1 && !canProceedFromFeatures) || (step === 0 && !basicInfoOk)}
              >
                Next <ArrowRight size={16} aria-hidden />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!weightOk || isSubmitting}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  background: weightOk && !isSubmitting
                    ? "linear-gradient(135deg, #0066FF, #00A3E0)"
                    : "rgba(255,255,255,0.1)",
                  border: "none",
                  borderRadius: 50,
                  color: "white",
                  padding: "12px 32px",
                  fontSize: 15,
                  fontWeight: 700,
                  cursor: weightOk && !isSubmitting ? "pointer" : "not-allowed",
                  opacity: weightOk && !isSubmitting ? 1 : 0.5,
                  boxShadow: weightOk && !isSubmitting ? "0 0 20px rgba(0,102,255,0.4)" : "none",
                }}
                aria-label="Submit contract"
                aria-disabled={!weightOk || isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Creating Contract...
                  </>
                ) : (
                  <>
                    🔒 Submit Contract (DRAFT) <ArrowRight size={16} />
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

/* ---- Sub-steps ---- */

function FormGroup({ label, children, optional = false }: { label: string; children: React.ReactNode; optional?: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <label style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", letterSpacing: "0.04em" }}>
          {label}
        </label>
        {optional && (
          <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>Optional</span>
        )}
      </div>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  background: "rgba(255,255,255,0.05)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 12,
  color: "white",
  fontSize: 15,
  padding: "12px 16px",
  outline: "none",
  width: "100%",
  fontFamily: "Inter, sans-serif",
};

function StepBasicInfo({ form, setForm }: { form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h2 style={{ fontSize: 24, fontWeight: 800, color: "white", marginBottom: 6 }}>Basic Info &amp; Parties</h2>
        <p style={{ fontSize: 14, color: "var(--color-text-muted)" }}>Capture project parameters, buyer/seller parties, and design references.</p>
      </div>

      <FormGroup label="Contract title">
        <input
          style={inputStyle}
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          placeholder="e.g. Next.js SaaS Storefront &amp; Bryntum Gantt UI"
          aria-label="Contract title"
        />
      </FormGroup>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <FormGroup label="Buyer email (Party A)">
          <input 
            style={inputStyle} 
            value={form.buyerEmail} 
            onChange={(e) => setForm({ ...form, buyerEmail: e.target.value })} 
            placeholder="buyer@email.com" 
            aria-label="Buyer email" 
          />
        </FormGroup>
        <FormGroup label="Seller email (Party B)">
          <input 
            style={inputStyle} 
            value={form.sellerEmail} 
            onChange={(e) => setForm({ ...form, sellerEmail: e.target.value })} 
            placeholder="seller@email.com" 
            aria-label="Seller email" 
          />
        </FormGroup>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <FormGroup label="Milestone Deadline">
          <input 
            type="date" 
            style={inputStyle} 
            value={form.deadline} 
            onChange={(e) => setForm({ ...form, deadline: e.target.value })} 
            aria-label="Contract deadline" 
          />
        </FormGroup>
        <FormGroup label="Total Escrow Price (USD)">
          <input 
            style={inputStyle} 
            value={form.totalAmount} 
            onChange={(e) => setForm({ ...form, totalAmount: e.target.value })} 
            placeholder="1500" 
            aria-label="Total contract amount in USD" 
          />
        </FormGroup>
      </div>

      {/* Captured Design Link (Figma/Design Reference) */}
      <FormGroup label="Design Reference / Figma Link">
        <div style={{ position: "relative" }}>
          <div style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--color-text-muted)" }}>
            <Palette size={16} color="#F24E1E" />
          </div>
          <input
            style={{ ...inputStyle, paddingLeft: 42 }}
            value={form.figmaUrl}
            onChange={(e) => setForm({ ...form, figmaUrl: e.target.value })}
            placeholder="https://figma.com/design/your-spec-link"
            aria-label="Design reference link"
          />
        </div>
        <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
          The AI Referee uses this design reference in Stage E for automated visual regression diffing.
        </span>
      </FormGroup>

      {/* Deliverable Repository Expectations */}
      <FormGroup label="Deliverable Repository Expectations (GitHub URL)" optional>
        <div style={{ position: "relative" }}>
          <div style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--color-text-muted)" }}>
            <FileCode size={16} color="#60A5FA" />
          </div>
          <input
            style={{ ...inputStyle, paddingLeft: 42 }}
            value={form.repoUrl}
            onChange={(e) => setForm({ ...form, repoUrl: e.target.value })}
            placeholder="https://github.com/freelancer/pactpal-storefront"
            aria-label="Target repository URL"
          />
        </div>
        <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
          The target GitHub repository where the seller will deliver commits for isolated Render container verification.
        </span>
      </FormGroup>

      <FormGroup label="Scope Description" optional>
        <textarea
          style={{ ...inputStyle, minHeight: 90, resize: "vertical" }}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          placeholder="Brief overview of features, responsive guidelines, or performance constraints..."
          aria-label="Contract description"
        />
      </FormGroup>
    </div>
  );
}

function StepFeatures({ form, features, setFeatures, totalWeight, weightOk, featureIssues, allTestsMeasurable }: {
  form: FormState;
  features: Feature[];
  setFeatures: (f: Feature[]) => void;
  totalWeight: number;
  weightOk: boolean;
  featureIssues: Array<{ index: number; name: string; issues: string[] }>;
  allTestsMeasurable: boolean;
}) {
  const totalAmountNum = parseFloat(form.totalAmount) || 0;

  const updateFeature = (i: number, field: keyof Feature, value: string | number) => {
    const updated = [...features];
    (updated[i] as Record<string, string | number>)[field] = value;
    setFeatures(updated);
  };

  const removeFeature = (idx: number) => {
    if (features.length <= 1) return;
    setFeatures(features.filter((_, i) => i !== idx));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 800, color: "white", marginBottom: 6 }}>Feature Checklist &amp; Weights</h2>
          <p style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
            Each feature must have an explicit acceptance test. Weights must total exactly 100%.
          </p>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: weightOk ? "rgba(76,175,80,0.1)" : "rgba(244,67,54,0.1)",
            border: `1px solid ${weightOk ? "rgba(76,175,80,0.3)" : "rgba(244,67,54,0.3)"}`,
            borderRadius: 50,
            padding: "8px 16px",
            fontSize: 16,
            fontWeight: 900,
            color: weightOk ? "#4CAF50" : "#F44336",
            fontFamily: "JetBrains Mono, monospace",
            transition: "all 0.3s",
          }}
          role="status"
          aria-live="polite"
          aria-label={`Total weight: ${totalWeight}%`}
        >
          {totalWeight}%
          {weightOk && <CheckCircle size={16} color="#4CAF50" aria-hidden />}
        </div>
      </div>

      {features.map((f, i) => {
        const allocatedVal = ((totalAmountNum * (Number(f.weight) || 0)) / 100).toFixed(2);
        const thisFeatureIssues = featureIssues.find((fi) => fi.index === i)?.issues || [];

        return (
          <div
            key={i}
            style={{
              background: thisFeatureIssues.length > 0 ? "rgba(244,67,54,0.04)" : "rgba(255,255,255,0.03)",
              border: `1px solid ${thisFeatureIssues.length > 0 ? "rgba(244,67,54,0.25)" : "rgba(255,255,255,0.08)"}`,
              borderRadius: 16,
              padding: "20px",
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
            role="group"
            aria-label={`Feature ${i + 1}: ${f.name}`}
          >
            <div style={{ display: "grid", gridTemplateColumns: "1fr 110px 100px auto", gap: 12, alignItems: "center" }}>
              <input
                style={inputStyle}
                value={f.name}
                onChange={(e) => updateFeature(i, "name", e.target.value)}
                placeholder="Feature title"
                aria-label={`Feature ${i + 1} name`}
              />
              <div style={{ position: "relative" }}>
                <input
                  type="number"
                  min={0}
                  max={100}
                  style={{ ...inputStyle, paddingRight: 28 }}
                  value={f.weight}
                  onChange={(e) => updateFeature(i, "weight", parseInt(e.target.value) || 0)}
                  aria-label={`Feature ${i + 1} weight percentage`}
                />
                <span
                  style={{
                    position: "absolute",
                    right: 12,
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "var(--color-text-muted)",
                    fontSize: 14,
                    pointerEvents: "none",
                  }}
                  aria-hidden
                >%</span>
              </div>

              <div style={{ textAlign: "right", fontFamily: "JetBrains Mono, monospace", fontSize: 13, color: "var(--color-secondary)", fontWeight: 700 }}>
                ${allocatedVal}
              </div>

              {features.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeFeature(i)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--color-text-muted)",
                    cursor: "pointer",
                    padding: 8,
                    borderRadius: 8,
                  }}
                  title="Remove feature"
                  aria-label="Remove feature"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>

            <input
              style={inputStyle}
              value={f.test}
              onChange={(e) => updateFeature(i, "test", e.target.value)}
              placeholder="Plain-language acceptance test (what objective condition proves this passes?)"
              aria-label={`Feature ${i + 1} acceptance test`}
            />

            {thisFeatureIssues.length > 0 && (
              <div style={{ fontSize: 12, color: "#FCA5A5", display: "flex", alignItems: "center", gap: 6 }}>
                <AlertTriangle size={13} />
                <span>{thisFeatureIssues.join("; ")}</span>
              </div>
            )}
          </div>
        );
      })}

      <button
        type="button"
        onClick={() => setFeatures([...features, { name: "", weight: 0, test: "" }])}
        style={{
          background: "rgba(255,255,255,0.05)",
          border: "1px dashed rgba(255,255,255,0.15)",
          borderRadius: 12,
          color: "var(--color-text-muted)",
          padding: "14px",
          fontSize: 14,
          fontWeight: 600,
          cursor: "pointer",
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 6,
        }}
        aria-label="Add feature"
      >
        <Plus size={16} /> Add feature milestone
      </button>

      {/* AI Agreement Reader Pre-Validation & Clarification Notice (Phase 1 & Phase 3) */}
      {(!weightOk || !allTestsMeasurable) && (
        <div
          style={{
            background: "rgba(122,92,255,0.08)",
            border: "1px solid rgba(122,92,255,0.3)",
            borderRadius: 16,
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
          role="alert"
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#C084FC", fontWeight: 700, fontSize: 14 }}>
            <Sparkles size={16} />
            <span>AI Agreement Reader Pre-Validation Notice (Zero-Trust Standard)</span>
          </div>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.5 }}>
            In accordance with PactPal escrow rules, the AI Referee never guesses requirements. Every feature must define an objective acceptance test so containerized verification in Phase 5 can evaluate it deterministically.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12.5, color: "#FCA5A5" }}>
            {!weightOk && (
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span>•</span>
                <span>Total weight is currently <strong>{totalWeight}%</strong>. Must equal exactly <strong>100%</strong> before checklist can lock.</span>
              </div>
            )}
            {featureIssues.filter((fi) => fi.issues.length > 0).map((fi) => (
              <div key={fi.index} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span>•</span>
                <span><strong>{fi.name}</strong>: {fi.issues.join("; ")}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StepEscrow({ form, setForm }: { form: FormState; setForm: React.Dispatch<React.SetStateAction<FormState>> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h2 style={{ fontSize: 24, fontWeight: 800, color: "white", marginBottom: 6 }}>Escrow Authorization Terms</h2>
        <p style={{ fontSize: 14, color: "var(--color-text-muted)" }}>PayPal authorization holds funds securely — no premature transfers.</p>
      </div>

      <div
        style={{
          background: "rgba(255,152,0,0.06)",
          border: "1px solid rgba(255,152,0,0.2)",
          borderRadius: 20,
          padding: "28px",
          display: "flex",
          gap: 24,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            width: 100,
            height: 100,
            borderRadius: "50%",
            border: "3px solid rgba(255,152,0,0.4)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 30px rgba(255,152,0,0.3)",
            flexShrink: 0,
          }}
          aria-label="29-day hold countdown"
        >
          <div style={{ fontSize: 28, fontWeight: 900, color: "#FF9800", fontFamily: "JetBrains Mono, monospace", lineHeight: 1 }}>29</div>
          <div style={{ fontSize: 10, color: "var(--color-text-muted)" }}>day hold</div>
        </div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "white", marginBottom: 6 }}>
            PayPal 29-day authorization hold
          </div>
          <div style={{ fontSize: 14, color: "var(--color-text-secondary)", lineHeight: 1.6, maxWidth: 440 }}>
            Funds are authorized (not captured) for 29 days. The money is reserved in the
            buyer&apos;s PayPal account but not transferred until delivered features pass AI Referee verification.
          </div>
        </div>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.07)",
          borderRadius: 16,
          padding: "20px",
        }}
      >
        {[
          ["Amount to authorize", form.totalAmount ? `$${form.totalAmount} USD` : "$0.00 USD"],
          ["Authorization method", "PayPal Orders API (AUTHORIZE intent)"],
          ["Hold duration", "29 days"],
          ["Release trigger", "AI Referee verification report complete"],
        ].map(([k, v]) => (
          <div
            key={k}
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 14,
              paddingBottom: 12,
              borderBottom: "1px solid rgba(255,255,255,0.05)",
            }}
          >
            <span style={{ color: "var(--color-text-muted)" }}>{k}</span>
            <span style={{ fontWeight: 600, color: "white" }}>{v}</span>
          </div>
        ))}
      </div>

      <div
        style={{
          background: "rgba(76,175,80,0.06)",
          border: "1px solid rgba(76,175,80,0.2)",
          borderRadius: 12,
          padding: "14px 18px",
          fontSize: 13,
          color: "#4CAF50",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
        role="note"
      >
        <ShieldCheck size={18} />
        PactPal never stores your PayPal credentials. Authorization happens via PayPal&apos;s secure sandbox authorization protocol.
      </div>
    </div>
  );
}

function StepReview({ form, features, totalWeight, weightOk }: {
  form: FormState;
  features: Feature[];
  totalWeight: number;
  weightOk: boolean;
}) {
  const totalAmountNum = parseFloat(form.totalAmount) || 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h2 style={{ fontSize: 24, fontWeight: 800, color: "white", marginBottom: 6 }}>Review &amp; Create Contract</h2>
        <p style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
          Contract will be registered in <strong style={{ color: "var(--color-text-secondary)" }}>DRAFT</strong> status and made available to the seller for acceptance.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {[
          ["Contract Title", form.title || "—"],
          ["Buyer (Party A)", form.buyerEmail || "—"],
          ["Seller (Party B)", form.sellerEmail || "—"],
          ["Milestone Deadline", form.deadline || "—"],
          ["Total Escrow Price", form.totalAmount ? `$${form.totalAmount} USD` : "—"],
          ["Design Reference", form.figmaUrl || "—"],
          ["Deliverable Repository", form.repoUrl || "—"],
        ].map(([k, v]) => (
          <div
            key={k}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: 14,
              paddingBottom: 12,
              borderBottom: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <span style={{ color: "var(--color-text-muted)" }}>{k}</span>
            <span style={{ fontWeight: 600, color: "white", textAlign: "right", maxWidth: 360, wordBreak: "break-all" }}>
              {k === "Design Reference" && v !== "—" ? (
                <a href={v} target="_blank" rel="noopener noreferrer" style={{ color: "var(--color-primary)", display: "inline-flex", alignItems: "center", gap: 4, textDecoration: "none" }}>
                  {v} <ExternalLink size={12} />
                </a>
              ) : k === "Deliverable Repository" && v !== "—" ? (
                <a href={v} target="_blank" rel="noopener noreferrer" style={{ color: "#60A5FA", display: "inline-flex", alignItems: "center", gap: 4, textDecoration: "none" }}>
                  {v} <ExternalLink size={12} />
                </a>
              ) : (
                v
              )}
            </span>
          </div>
        ))}
      </div>

      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-muted)", marginBottom: 12, letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Priced Features &amp; Acceptance Tests
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {features.map((f, i) => {
            const allocatedVal = ((totalAmountNum * (Number(f.weight) || 0)) / 100).toFixed(2);

            return (
              <div
                key={i}
                style={{
                  padding: "12px 16px",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.02)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: 600, color: "white", fontSize: 14 }}>{f.name || `Feature ${i + 1}`}</span>
                  <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                    <span style={{ fontWeight: 700, color: "var(--color-secondary)", fontFamily: "JetBrains Mono, monospace", fontSize: 13 }}>
                      ${allocatedVal}
                    </span>
                    <span style={{ fontWeight: 700, color: "white", fontFamily: "JetBrains Mono, monospace", fontSize: 13 }}>
                      {f.weight}%
                    </span>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)", fontStyle: "italic" }}>
                  Test: &ldquo;{f.test || "No acceptance test specified"}&rdquo;
                </div>
              </div>
            );
          })}
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            paddingTop: 14,
            gap: 8,
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Total Checklist Weight:</span>
          <span
            style={{
              fontSize: 20,
              fontWeight: 900,
              color: weightOk ? "#4CAF50" : "#F44336",
              fontFamily: "JetBrains Mono, monospace",
            }}
          >
            {totalWeight}%
          </span>
          {weightOk && <CheckCircle size={18} color="#4CAF50" aria-label="Weights sum to 100%" />}
        </div>
      </div>

      {!weightOk && (
        <div
          style={{
            background: "rgba(244,67,54,0.08)",
            border: "1px solid rgba(244,67,54,0.25)",
            borderRadius: 12,
            padding: "14px 18px",
            fontSize: 13,
            color: "#F44336",
          }}
          role="alert"
        >
          ⚠ Feature weights must total exactly 100% before submitting. Currently: {totalWeight}%
        </div>
      )}
    </div>
  );
}
