"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { signUpUser } from "@/lib/supabase";

type Role = "hirer" | "freelancer" | null;

export default function SignupPage() {
  const [role, setRole] = useState<Role>(null);
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // PayPal Connection State
  const [connectingPayPal, setConnectingPayPal] = useState(false);
  const [paypalConnected, setPaypalConnected] = useState(false);
  const [paypalEmail, setPaypalEmail] = useState("");
  const [paypalPayerId, setPaypalPayerId] = useState("");

  // Listen for PayPal popup return via postMessage and localStorage events
  useEffect(() => {
    if (typeof window === "undefined") return;

    // Restore draft if returned via redirect
    try {
      const draft = sessionStorage.getItem("pactpal_signup_draft");
      if (draft) {
        const parsed = JSON.parse(draft);
        if (parsed.role) setRole(parsed.role);
        if (parsed.form) setForm(parsed.form);
        if (parsed.step) setStep(parsed.step);
      }
    } catch {
      // ignore
    }

    function applySuccess(email: string, payerId?: string) {
      setPaypalEmail(email);
      setPaypalPayerId(payerId || "PAYER_SANDBOX_VERIFIED");
      setPaypalConnected(true);
      setConnectingPayPal(false);
      setError("");
      try {
        sessionStorage.removeItem("pactpal_signup_draft");
        localStorage.removeItem("pactpal_paypal_auth_event");
      } catch {
        // ignore
      }
    }

    function handleMessage(event: MessageEvent) {
      if (event.data?.type === "PAYPAL_AUTH_SUCCESS" && event.data?.email) {
        applySuccess(event.data.email, event.data.payerId);
      }
      if (event.data?.type === "PAYPAL_AUTH_CANCEL") {
        setConnectingPayPal(false);
      }
    }

    function handleStorage(event: StorageEvent) {
      if (event.key === "pactpal_paypal_auth_event" && event.newValue) {
        try {
          const ev = JSON.parse(event.newValue);
          if (ev.type === "PAYPAL_AUTH_SUCCESS" && ev.email) {
            applySuccess(ev.email, ev.payerId);
          } else if (ev.type === "PAYPAL_AUTH_CANCEL") {
            setConnectingPayPal(false);
          }
        } catch {
          // ignore
        }
      }
    }

    const pollTimer = setInterval(() => {
      try {
        const stored = localStorage.getItem("pactpal_paypal_auth_event");
        if (stored) {
          const ev = JSON.parse(stored);
          if (ev.type === "PAYPAL_AUTH_SUCCESS" && ev.email) {
            applySuccess(ev.email, ev.payerId);
          } else if (ev.type === "PAYPAL_AUTH_CANCEL") {
            setConnectingPayPal(false);
            localStorage.removeItem("pactpal_paypal_auth_event");
          }
        }
      } catch {
        // ignore
      }
    }, 500);

    window.addEventListener("message", handleMessage);
    window.addEventListener("storage", handleStorage);
    return () => {
      clearInterval(pollTimer);
      window.removeEventListener("message", handleMessage);
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  async function handleConnectPayPal() {
    setError("");
    setConnectingPayPal(true);

    try {
      sessionStorage.setItem(
        "pactpal_signup_draft",
        JSON.stringify({ role, form, step: 3 })
      );
    } catch {
      // ignore
    }

    const popupWidth = 520;
    const popupHeight = 700;
    const left = window.screenX + (window.outerWidth - popupWidth) / 2;
    const top = window.screenY + (window.outerHeight - popupHeight) / 2;

    // Open popup immediately on user action to avoid popup blockers
    const popup = window.open(
      "",
      "PayPalLoginWindow",
      `width=${popupWidth},height=${popupHeight},left=${left},top=${top},status=no,toolbar=no,menubar=no`
    );

    if (popup) {
      try {
        popup.document.write(
          "<!DOCTYPE html><html><head><title>Connecting to PayPal...</title><style>body{margin:0;background:#070B16;color:white;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;text-align:center;}.spinner{font-size:36px;margin-bottom:16px;animation:spin 1s linear infinite;}@keyframes spin{100%{transform:rotate(360deg);}}</style></head><body><div><div class='spinner'>🔄</div><h3 style='margin:0 0 8px;'>Connecting to PayPal Sandbox...</h3><p style='color:#94A3B8;font-size:14px;margin:0;'>Opening official PayPal login...</p></div></body></html>"
        );
      } catch {
        // ignore
      }
    }

    try {
      const res = await fetch("/api/paypal/create-auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });

      const data = await res.json();
      if (!res.ok || !data.approve_url) {
        if (popup) popup.close();
        throw new Error(data.message || data.error || "Failed to initialize PayPal authorization.");
      }

      if (popup && !popup.closed) {
        popup.location.href = data.approve_url;
      } else {
        window.location.href = data.approve_url;
      }

      const checkClosed = setInterval(() => {
        if (!popup || popup.closed) {
          clearInterval(checkClosed);
          setTimeout(() => {
            setConnectingPayPal((prev) => {
              return prev && !paypalConnected ? false : prev;
            });
          }, 1500);
        }
      }, 800);
    } catch (err: unknown) {
      if (popup && !popup.closed) popup.close();
      setConnectingPayPal(false);
      const msg = err instanceof Error ? err.message : "Failed to open PayPal authorization.";
      setError(msg);
    }
  }

  function handleDisconnectPayPal() {
    setPaypalConnected(false);
    setPaypalEmail("");
    setPaypalPayerId("");
  }

  function handleNext() {
    if (step === 1 && !role) {
      setError("Please select a role to continue.");
      return;
    }
    if (step === 2 && (!form.name || !form.email || !form.password)) {
      setError("Please fill in all fields.");
      return;
    }
    setError("");
    if (step < 3) setStep((s) => (s + 1) as 1 | 2 | 3);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!paypalConnected) {
      setError("Please authorize PayPal before completing setup.");
      return;
    }
    setError("");
    setLoading(true);

    try {
      const res = await signUpUser({
        name: form.name,
        email: form.email,
        password: form.password,
        role: (role || "hirer") as "hirer" | "freelancer",
        paypal_email: paypalEmail,
        paypal_payer_id: paypalPayerId,
        paypal_connected: true,
      });

      if (res.error) {
        setError(res.error);
        setLoading(false);
        return;
      }

      // Persist full authenticated user profile with PayPal details
      if (typeof window !== "undefined") {
        const userProfile = {
          id: res.user?.id || `usr_${Date.now()}`,
          role: role || "hirer",
          name: form.name,
          email: form.email,
          paypal_email: paypalEmail,
          paypal_payer_id: paypalPayerId,
          paypal_connected: true,
          created_at: new Date().toISOString(),
          is_demo: false,
        };
        localStorage.setItem("pactpal_current_user", JSON.stringify(userProfile));
        window.dispatchEvent(new Event("pactpal_auth_change"));
      }

      setLoading(false);
      window.location.href = role === "hirer" ? "/dashboard/hirer" : "/dashboard/freelancer";
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create account. Please try again.";
      setError(message);
      setLoading(false);
    }
  }

  const stepLabels = ["Choose role", "Account details", "Connect PayPal"];

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "80px 24px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Glow blobs */}
      <div
        aria-hidden
        style={{
          position: "absolute",
          top: "15%",
          left: "25%",
          width: 500,
          height: 500,
          background: "radial-gradient(circle, rgba(0,102,255,0.12) 0%, transparent 70%)",
          borderRadius: "50%",
          filter: "blur(80px)",
          pointerEvents: "none",
        }}
      />
      <div
        aria-hidden
        style={{
          position: "absolute",
          bottom: "10%",
          right: "20%",
          width: 400,
          height: 400,
          background: "radial-gradient(circle, rgba(255,152,0,0.08) 0%, transparent 70%)",
          borderRadius: "50%",
          filter: "blur(80px)",
          pointerEvents: "none",
        }}
      />

      <div style={{ width: "100%", maxWidth: 520, position: "relative", zIndex: 1 }}>
        {/* Logo */}
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            textDecoration: "none",
            justifyContent: "center",
            marginBottom: 40,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              background: "linear-gradient(135deg, #0066FF, #7A5CFF)",
              borderRadius: 12,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 20,
              boxShadow: "0 0 24px rgba(0,102,255,0.4)",
            }}
          >
            ⚖
          </div>
          <span style={{ fontWeight: 800, fontSize: 22, color: "white" }}>PactPal</span>
        </Link>

        {/* Step indicator */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 0,
            marginBottom: 32,
            justifyContent: "center",
          }}
        >
          {stepLabels.map((label, i) => {
            const idx = i + 1;
            const active = step === idx;
            const done = step > idx;
            return (
              <div key={label} style={{ display: "flex", alignItems: "center" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      background: done
                        ? "var(--color-success)"
                        : active
                        ? "var(--color-primary)"
                        : "rgba(255,255,255,0.08)",
                      border: `2px solid ${done ? "var(--color-success)" : active ? "var(--color-primary)" : "rgba(255,255,255,0.15)"}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 13,
                      fontWeight: 700,
                      color: done || active ? "white" : "var(--color-text-muted)",
                      transition: "all 0.3s",
                    }}
                  >
                    {done ? "✓" : idx}
                  </div>
                  <span
                    style={{
                      fontSize: 11,
                      color: active ? "white" : "var(--color-text-muted)",
                      fontWeight: active ? 600 : 400,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {label}
                  </span>
                </div>
                {i < stepLabels.length - 1 && (
                  <div
                    style={{
                      width: 60,
                      height: 2,
                      background: done ? "var(--color-primary)" : "rgba(255,255,255,0.08)",
                      marginBottom: 20,
                      transition: "background 0.3s",
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Card */}
        <div className="glass-card" style={{ padding: "40px 36px" }}>
          {error && (
            <div
              role="alert"
              style={{
                background: "rgba(244,67,54,0.12)",
                border: "1px solid rgba(244,67,54,0.3)",
                borderRadius: 10,
                padding: "12px 16px",
                color: "#F44336",
                fontSize: 14,
                marginBottom: 20,
              }}
            >
              {error}
            </div>
          )}

          {/* Step 1: Role selection */}
          {step === 1 && (
            <div>
              <h1
                style={{
                  fontSize: 26,
                  fontWeight: 800,
                  color: "white",
                  marginBottom: 8,
                  textAlign: "center",
                }}
              >
                How will you use PactPal?
              </h1>
              <p
                style={{
                  color: "var(--color-text-muted)",
                  textAlign: "center",
                  marginBottom: 32,
                  fontSize: 15,
                }}
              >
                Choose your primary role. You can always switch later.
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {[
                  {
                    key: "hirer" as Role,
                    icon: "💼",
                    title: "I&apos;m hiring",
                    desc: "Post projects, fund escrow, pay only for work that passes.",
                    glow: "rgba(0,102,255,0.3)",
                    border: "rgba(0,102,255,0.6)",
                  },
                  {
                    key: "freelancer" as Role,
                    icon: "⌨️",
                    title: "I&apos;m a freelancer",
                    desc: "Find work, get paid on time with money locked upfront.",
                    glow: "rgba(255,152,0,0.2)",
                    border: "rgba(255,152,0,0.6)",
                  },
                ].map((opt) => (
                  <button
                    key={opt.key!}
                    onClick={() => setRole(opt.key)}
                    style={{
                      background:
                        role === opt.key
                          ? opt.key === "hirer"
                            ? "rgba(0,102,255,0.1)"
                            : "rgba(255,152,0,0.08)"
                          : "rgba(255,255,255,0.03)",
                      border: `2px solid ${role === opt.key ? opt.border : "rgba(255,255,255,0.08)"}`,
                      borderRadius: 16,
                      padding: "24px 20px",
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "all 0.2s",
                      boxShadow: role === opt.key ? `0 0 24px ${opt.glow}` : "none",
                    }}
                    aria-pressed={role === opt.key}
                    aria-label={opt.title.replace(/&apos;/g, "'")}
                  >
                    <div style={{ fontSize: 32, marginBottom: 12 }}>{opt.icon}</div>
                    <div
                      style={{
                        fontSize: 16,
                        fontWeight: 700,
                        color: "white",
                        marginBottom: 6,
                      }}
                      dangerouslySetInnerHTML={{ __html: opt.title }}
                    />
                    <div style={{ fontSize: 13, color: "var(--color-text-muted)", lineHeight: 1.5 }}>
                      {opt.desc}
                    </div>
                  </button>
                ))}
              </div>

              <button
                className="btn-gradient"
                onClick={handleNext}
                style={{ width: "100%", padding: "14px", fontSize: 16, fontWeight: 700, marginTop: 24 }}
                aria-label="Continue to account details"
              >
                Continue →
              </button>
            </div>
          )}

          {/* Step 2: Account details */}
          {step === 2 && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleNext();
              }}
            >
              <h1
                style={{
                  fontSize: 26,
                  fontWeight: 800,
                  color: "white",
                  marginBottom: 8,
                  textAlign: "center",
                }}
              >
                Create your account
              </h1>
              <p
                style={{
                  color: "var(--color-text-muted)",
                  textAlign: "center",
                  marginBottom: 32,
                  fontSize: 15,
                }}
              >
                You&apos;re signing up as a{" "}
                <span
                  style={{
                    color: role === "hirer" ? "var(--color-primary)" : "var(--color-accent)",
                    fontWeight: 600,
                  }}
                >
                  {role === "hirer" ? "Hirer" : "Freelancer"}
                </span>
                .
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {[
                  { id: "name", label: "Full name", type: "text", placeholder: "Jane Smith", key: "name" },
                  { id: "email", label: "Email", type: "email", placeholder: "you@example.com", key: "email" },
                  { id: "password", label: "Password", type: "password", placeholder: "Min 8 characters", key: "password" },
                ].map((field) => (
                  <div key={field.id}>
                    <label
                      htmlFor={field.id}
                      style={{
                        display: "block",
                        fontSize: 13,
                        fontWeight: 600,
                        color: "var(--color-text-secondary)",
                        marginBottom: 8,
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                      }}
                    >
                      {field.label}
                    </label>
                    <input
                      id={field.id}
                      type={field.type}
                      value={form[field.key as keyof typeof form]}
                      onChange={(e) => setForm({ ...form, [field.key]: e.target.value })}
                      placeholder={field.placeholder}
                      style={{
                        width: "100%",
                        background: "rgba(255,255,255,0.05)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 10,
                        padding: "12px 16px",
                        color: "white",
                        fontSize: 15,
                        outline: "none",
                        boxSizing: "border-box",
                        transition: "border-color 0.2s",
                      }}
                      onFocus={(e) => (e.currentTarget.style.borderColor = "rgba(0,102,255,0.6)")}
                      onBlur={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)")}
                    />
                  </div>
                ))}
              </div>

              <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  style={{
                    flex: 1,
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 10,
                    padding: "13px",
                    color: "var(--color-text-secondary)",
                    fontSize: 15,
                    cursor: "pointer",
                  }}
                  aria-label="Go back to role selection"
                >
                  ← Back
                </button>
                <button
                  type="submit"
                  className="btn-gradient"
                  style={{ flex: 2, padding: "13px", fontSize: 15, fontWeight: 700 }}
                  aria-label="Continue to PayPal connection"
                >
                  Continue →
                </button>
              </div>
            </form>
          )}

          {/* Step 3: Connect PayPal */}
          {step === 3 && (
            <form onSubmit={handleSubmit}>
              <h1
                style={{
                  fontSize: 26,
                  fontWeight: 800,
                  color: "white",
                  marginBottom: 8,
                  textAlign: "center",
                }}
              >
                Connect PayPal
              </h1>
              <p
                style={{
                  color: "var(--color-text-muted)",
                  textAlign: "center",
                  marginBottom: 32,
                  fontSize: 15,
                  lineHeight: 1.6,
                }}
              >
                PactPal uses PayPal to hold escrow funds securely. We&apos;ll never charge you without your explicit approval.
              </p>

              {/* PayPal connect / authorization card */}
              {!paypalConnected ? (
                <div
                  style={{
                    background: "rgba(0,112,186,0.12)",
                    border: "2px dashed rgba(0,112,186,0.4)",
                    borderRadius: 16,
                    padding: "32px",
                    textAlign: "center",
                    marginBottom: 24,
                  }}
                >
                  <div style={{ fontSize: 48, marginBottom: 16 }}>
                    {connectingPayPal ? "🔄" : "🔗"}
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: "white", marginBottom: 8 }}>
                    PayPal Authorization
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      color: "var(--color-text-muted)",
                      marginBottom: 20,
                      lineHeight: 1.6,
                    }}
                  >
                    You&apos;ll be redirected to PayPal to authorize PactPal to hold and release funds on your behalf. This is a demo environment.
                  </div>
                  <button
                    type="button"
                    onClick={handleConnectPayPal}
                    disabled={connectingPayPal}
                    style={{
                      background: connectingPayPal ? "#005ea6" : "#0070BA",
                      border: "none",
                      borderRadius: 10,
                      padding: "12px 28px",
                      color: "white",
                      fontSize: 15,
                      fontWeight: 700,
                      cursor: connectingPayPal ? "not-allowed" : "pointer",
                      transition: "opacity 0.2s",
                      boxShadow: "0 4px 14px rgba(0,112,186,0.35)",
                    }}
                    aria-label="Connect PayPal account"
                    onMouseEnter={(e) => {
                      if (!connectingPayPal) e.currentTarget.style.opacity = "0.85";
                    }}
                    onMouseLeave={(e) => {
                      if (!connectingPayPal) e.currentTarget.style.opacity = "1";
                    }}
                  >
                    {connectingPayPal ? "Connecting to PayPal Sandbox…" : "Connect PayPal →"}
                  </button>
                </div>
              ) : (
                <div
                  style={{
                    background: "rgba(16, 185, 129, 0.09)",
                    border: "2px solid rgba(16, 185, 129, 0.4)",
                    borderRadius: 16,
                    padding: "28px 24px",
                    textAlign: "center",
                    marginBottom: 24,
                    boxShadow: "0 0 20px rgba(16, 185, 129, 0.15)",
                  }}
                >
                  <div style={{ fontSize: 44, marginBottom: 12 }}>✅</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#34D399", marginBottom: 6 }}>
                    PayPal Account Authorized
                  </div>
                  <div
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                      background: "rgba(0,0,0,0.3)",
                      padding: "6px 14px",
                      borderRadius: 20,
                      border: "1px solid rgba(16, 185, 129, 0.3)",
                      marginBottom: 12,
                    }}
                  >
                    <span style={{ fontSize: 13, color: "white", fontFamily: "monospace" }}>
                      {paypalEmail}
                    </span>
                    <span
                      style={{
                        fontSize: 10,
                        background: "#10B981",
                        color: "#000",
                        fontWeight: 800,
                        padding: "2px 6px",
                        borderRadius: 4,
                        letterSpacing: "0.05em",
                      }}
                    >
                      VERIFIED
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      color: "var(--color-text-muted)",
                      lineHeight: 1.5,
                      marginBottom: 16,
                    }}
                  >
                    PactPal is authorized to handle escrow holds &amp; releases. Your account is ready!
                  </div>
                  <button
                    type="button"
                    onClick={handleDisconnectPayPal}
                    style={{
                      background: "transparent",
                      border: "1px solid rgba(255,255,255,0.18)",
                      borderRadius: 8,
                      padding: "6px 14px",
                      color: "var(--color-text-muted)",
                      fontSize: 12,
                      cursor: "pointer",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "white")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "var(--color-text-muted)")}
                  >
                    Disconnect / Re-authorize
                  </button>
                </div>
              )}

              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  background: "rgba(76,175,80,0.08)",
                  border: "1px solid rgba(76,175,80,0.2)",
                  borderRadius: 10,
                  padding: "12px 16px",
                  marginBottom: 24,
                }}
              >
                <span style={{ fontSize: 18, flexShrink: 0 }}>🔒</span>
                <span style={{ fontSize: 13, color: "var(--color-text-muted)", lineHeight: 1.6 }}>
                  Your funds are held in a PayPal-authorized escrow. PactPal cannot access or move money without both parties agreeing.
                </span>
              </div>

              <div style={{ display: "flex", gap: 12 }}>
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  style={{
                    flex: 1,
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 10,
                    padding: "13px",
                    color: "var(--color-text-secondary)",
                    fontSize: 15,
                    cursor: "pointer",
                  }}
                  aria-label="Go back to account details"
                >
                  ← Back
                </button>
                <button
                  type="submit"
                  className="btn-gradient"
                  disabled={loading}
                  style={{
                    flex: 2,
                    padding: "13px",
                    fontSize: 15,
                    fontWeight: 700,
                    opacity: loading ? 0.7 : 1,
                    cursor: loading ? "not-allowed" : "pointer",
                  }}
                  aria-label="Complete signup and go to dashboard"
                >
                  {loading ? "Creating account…" : "Complete setup →"}
                </button>
              </div>
            </form>
          )}
        </div>

        <p style={{ textAlign: "center", marginTop: 24, fontSize: 14, color: "var(--color-text-muted)" }}>
          Already have an account?{" "}
          <Link href="/login" style={{ color: "var(--color-primary)", fontWeight: 600, textDecoration: "none" }}>
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}

