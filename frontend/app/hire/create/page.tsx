"use client";
import { useState } from "react";
import Navbar from "@/components/Navbar";
import { CheckCircle, Circle, ArrowRight, ArrowLeft } from "lucide-react";

type Feature = { name: string; weight: number; test: string };

type FormState = {
  title: string;
  description: string;
  buyerEmail: string;
  sellerEmail: string;
  deadline: string;
  totalAmount: string;
  currency: string;
};

const STEPS = ["Basic Info", "Feature Checklist", "Escrow Settings", "Review"];

export default function CreateContractPage() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    title: "",
    description: "",
    buyerEmail: "",
    sellerEmail: "",
    deadline: "",
    totalAmount: "",
    currency: "USD",
  });
  const [features, setFeatures] = useState<Feature[]>([
    { name: "Landing page", weight: 25, test: "All sections render, CTA links work" },
    { name: "Login system", weight: 20, test: "Login/logout with JWT, session persists" },
    { name: "Dashboard", weight: 30, test: "Data loads, charts render, responsive" },
    { name: "Payment flow", weight: 25, test: "Checkout completes, invoice sent" },
  ]);
  const totalWeight = features.reduce((s, f) => s + f.weight, 0);
  const weightOk = totalWeight === 100;

  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      <div
        style={{
          maxWidth: 760,
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
            padding: "40px 40px",
          }}
          role="main"
          aria-label={`Step ${step + 1}: ${STEPS[step]}`}
        >
          {step === 0 && (
            <StepBasicInfo form={form} setForm={setForm} />
          )}
          {step === 1 && (
            <StepFeatures
              features={features}
              setFeatures={setFeatures}
              totalWeight={totalWeight}
              weightOk={weightOk}
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
              marginTop: 40,
              paddingTop: 24,
              borderTop: "1px solid rgba(255,255,255,0.07)",
            }}
          >
            <button
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
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

            {step < STEPS.length - 1 ? (
              <button
                onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                  border: "none",
                  borderRadius: 50,
                  color: "white",
                  padding: "12px 28px",
                  fontSize: 15,
                  fontWeight: 700,
                  cursor: "pointer",
                  boxShadow: "0 0 20px rgba(0,102,255,0.4)",
                }}
                aria-label="Next step"
              >
                Next <ArrowRight size={16} aria-hidden />
              </button>
            ) : (
              <button
                disabled={!weightOk}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  background: weightOk
                    ? "linear-gradient(135deg, #4CAF50, #81C784)"
                    : "rgba(255,255,255,0.1)",
                  border: "none",
                  borderRadius: 50,
                  color: "white",
                  padding: "12px 32px",
                  fontSize: 15,
                  fontWeight: 700,
                  cursor: weightOk ? "pointer" : "not-allowed",
                  opacity: weightOk ? 1 : 0.5,
                  boxShadow: weightOk ? "0 0 20px rgba(76,175,80,0.4)" : "none",
                }}
                aria-label="Submit contract"
                aria-disabled={!weightOk}
              >
                🔒 Submit & Fund Escrow
              </button>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

/* ---- Sub-steps ---- */

function FormGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <label style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", letterSpacing: "0.04em" }}>
        {label}
      </label>
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


function StepBasicInfo({ form, setForm }: { form: { title: string; description: string; buyerEmail: string; sellerEmail: string; deadline: string; totalAmount: string; currency: string }; setForm: React.Dispatch<React.SetStateAction<{ title: string; description: string; buyerEmail: string; sellerEmail: string; deadline: string; totalAmount: string; currency: string }>> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h2 style={{ fontSize: 24, fontWeight: 800, color: "white", marginBottom: 6 }}>Basic info</h2>
        <p style={{ fontSize: 14, color: "var(--color-text-muted)" }}>Tell both parties what this pact is about.</p>
      </div>
      <FormGroup label="Contract title">
        <input
          style={inputStyle}
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          placeholder="e.g. E-commerce website build"
          aria-label="Contract title"
        />
      </FormGroup>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <FormGroup label="Buyer email">
          <input style={inputStyle} value={form.buyerEmail} onChange={(e) => setForm({ ...form, buyerEmail: e.target.value })} placeholder="buyer@email.com" aria-label="Buyer email" />
        </FormGroup>
        <FormGroup label="Seller email">
          <input style={inputStyle} value={form.sellerEmail} onChange={(e) => setForm({ ...form, sellerEmail: e.target.value })} placeholder="seller@email.com" aria-label="Seller email" />
        </FormGroup>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <FormGroup label="Deadline">
          <input type="date" style={inputStyle} value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} aria-label="Contract deadline" />
        </FormGroup>
        <FormGroup label="Total amount (USD)">
          <input style={inputStyle} value={form.totalAmount} onChange={(e) => setForm({ ...form, totalAmount: e.target.value })} placeholder="1500" aria-label="Total contract amount in USD" />
        </FormGroup>
      </div>
      <FormGroup label="Description">
        <textarea
          style={{ ...inputStyle, minHeight: 100, resize: "vertical" }}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          placeholder="Brief overview of the work to be done..."
          aria-label="Contract description"
        />
      </FormGroup>
    </div>
  );
}

function StepFeatures({ features, setFeatures, totalWeight, weightOk }: {
  features: Feature[];
  setFeatures: (f: Feature[]) => void;
  totalWeight: number;
  weightOk: boolean;
}) {
  const updateFeature = (i: number, field: keyof Feature, value: string | number) => {
    const updated = [...features];
    (updated[i] as Record<string, string | number>)[field] = value;
    setFeatures(updated);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 800, color: "white", marginBottom: 6 }}>Feature checklist</h2>
          <p style={{ fontSize: 14, color: "var(--color-text-muted)" }}>Weights must add to exactly 100%. These define proportional payouts.</p>
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

      {features.map((f, i) => (
        <div
          key={i}
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 16,
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
          role="group"
          aria-label={`Feature ${i + 1}: ${f.name}`}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr 100px", gap: 12 }}>
            <input
              style={inputStyle}
              value={f.name}
              onChange={(e) => updateFeature(i, "name", e.target.value)}
              placeholder="Feature name"
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
          </div>
          <input
            style={inputStyle}
            value={f.test}
            onChange={(e) => updateFeature(i, "test", e.target.value)}
            placeholder="Acceptance test (what must be true for this to pass?)"
            aria-label={`Feature ${i + 1} acceptance test`}
          />
        </div>
      ))}

      <button
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
        }}
        aria-label="Add feature"
      >
        + Add feature
      </button>
    </div>
  );
}

function StepEscrow({ form, setForm }: { form: { title: string; description: string; buyerEmail: string; sellerEmail: string; deadline: string; totalAmount: string; currency: string }; setForm: React.Dispatch<React.SetStateAction<{ title: string; description: string; buyerEmail: string; sellerEmail: string; deadline: string; totalAmount: string; currency: string }>> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h2 style={{ fontSize: 24, fontWeight: 800, color: "white", marginBottom: 6 }}>Escrow settings</h2>
        <p style={{ fontSize: 14, color: "var(--color-text-muted)" }}>PayPal authorization holds the funds — no premature charges.</p>
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
            PayPal 29-day authorization
          </div>
          <div style={{ fontSize: 14, color: "var(--color-text-secondary)", lineHeight: 1.6, maxWidth: 400 }}>
            Funds are authorized (not captured) for 29 days. The money is reserved in the
            buyer's PayPal account but not transferred until features are verified.
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
          ["Amount to authorize", form.totalAmount ? `$${form.totalAmount}` : "$0.00"],
          ["Authorization method", "PayPal Orders API (AUTHORIZE intent)"],
          ["Hold duration", "29 days"],
          ["Release trigger", "AI Referee verification complete"],
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
        }}
        role="note"
      >
        🔐 PactPal never stores your PayPal credentials. Authorization happens via PayPal&apos;s secure OAuth flow.
      </div>
    </div>
  );
}

function StepReview({ form, features, totalWeight, weightOk }: {
  form: Record<string, string>;
  features: Feature[];
  totalWeight: number;
  weightOk: boolean;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <h2 style={{ fontSize: 24, fontWeight: 800, color: "white", marginBottom: 6 }}>Review & submit</h2>
        <p style={{ fontSize: 14, color: "var(--color-text-muted)" }}>Once submitted, both parties must sign before escrow is funded.</p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {[
          ["Title", form.title || "—"],
          ["Buyer", form.buyerEmail || "—"],
          ["Seller", form.sellerEmail || "—"],
          ["Deadline", form.deadline || "—"],
          ["Total amount", form.totalAmount ? `$${form.totalAmount} USD` : "—"],
        ].map(([k, v]) => (
          <div
            key={k}
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 14,
              paddingBottom: 12,
              borderBottom: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <span style={{ color: "var(--color-text-muted)" }}>{k}</span>
            <span style={{ fontWeight: 600, color: "white" }}>{v}</span>
          </div>
        ))}
      </div>

      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text-muted)", marginBottom: 10, letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Feature breakdown
        </div>
        {features.map((f, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "10px 0",
              borderBottom: "1px solid rgba(255,255,255,0.05)",
              fontSize: 14,
            }}
          >
            <span style={{ color: "var(--color-text-secondary)" }}>{f.name || `Feature ${i + 1}`}</span>
            <span style={{ fontWeight: 700, color: "white", fontFamily: "JetBrains Mono, monospace" }}>{f.weight}%</span>
          </div>
        ))}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            paddingTop: 12,
            gap: 8,
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Total:</span>
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
