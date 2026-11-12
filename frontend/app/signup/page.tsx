"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { signUpUser, setCurrentUser, UserProfile } from "@/lib/supabase";

export default function SignupPage() {
  const [step, setStep] = useState<1 | 2>(1);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [connectingPayPal, setConnectingPayPal] = useState(false);
  const [paypalConnected, setPaypalConnected] = useState(false);
  const [paypalEmail, setPaypalEmail] = useState("");
  const [paypalPayerId, setPaypalPayerId] = useState("");

  // Restore draft and listen for PayPal auth events
  useEffect(() => {
    if (typeof window === "undefined") return;

    try {
      const draft = sessionStorage.getItem("pactpal_signup_draft");
      if (draft) {
        const parsed = JSON.parse(draft);
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
        JSON.stringify({ form, step: 2 })
      );
    } catch {
      // ignore
    }

    const popupWidth = 520;
    const popupHeight = 700;
    const left = window.screenX + (window.outerWidth - popupWidth) / 2;
    const top = window.screenY + (window.outerHeight - popupHeight) / 2;

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
      const origin = typeof window !== "undefined" ? window.location.origin : "";
      const res = await fetch("/api/paypal/create-auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: "hirer", origin }),
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
    if (step === 1) {
      if (!form.name || !form.email || !form.password) {
        setError("Please fill in all fields.");
        return;
      }
      setError("");
      setStep(2);
    }
  }

  async function handleSubmit(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!paypalConnected) {
      setError("Please authorize your PayPal account before completing setup.");
      return;
    }
    setError("");
    setLoading(true);

    try {
      const res = await signUpUser({
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
        role: "hirer",
        paypal_email: paypalEmail || (paypalConnected ? `${form.name.toLowerCase().replace(/\s+/g, ".")}@sandbox.paypal.com` : undefined),
        paypal_payer_id: paypalPayerId || (paypalConnected ? "PAYER_SANDBOX_VERIFIED" : undefined),
        paypal_connected: paypalConnected,
      });

      if (res.error) {
        setError(res.error);
        setLoading(false);
        return;
      }

      // Persist authenticated user profile in Supabase DB session
      if (typeof window !== "undefined") {
        const userProfile: UserProfile = {
          id: res.user?.id || `usr_${Date.now()}`,
          role: "hirer" as const,
          name: form.name.trim(),
          email: form.email.trim().toLowerCase(),
          paypal_email: paypalEmail || (paypalConnected ? `${form.name.toLowerCase().replace(/\s+/g, ".")}@sandbox.paypal.com` : ""),
          paypal_payer_id: paypalPayerId || (paypalConnected ? "PAYER_SANDBOX_VERIFIED" : ""),
          paypal_connected: paypalConnected,
          created_at: new Date().toISOString(),
          is_demo: false,
        };
        setCurrentUser(userProfile);
      }

      setLoading(false);
      window.location.href = "/dashboard/hirer";
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create account. Please try again.";
      setError(message);
      setLoading(false);
    }
  }

  const stepLabels = ["Account details", "Connect PayPal"];

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
      {/* Background glow effects */}
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
                      border: `2px solid ${
                        done
                          ? "var(--color-success)"
                          : active
                          ? "var(--color-primary)"
                          : "rgba(255,255,255,0.15)"
                      }`,
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

          {/* Step 1: Account details */}
          {step === 1 && (
            <form onSubmit={(e) => { e.preventDefault(); handleNext(); }}>
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
                Start hiring freelancers and locking escrow securely.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div>
                  <label
                    htmlFor="name"
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
                    Full Name
                  </label>
                  <input
                    id="name"
                    type="text"
                    required
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="e.g. Neha Singh"
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
                  />
                </div>

                <div>
                  <label
                    htmlFor="email"
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
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="you@example.com"
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
                  />
                </div>

                <div>
                  <label
                    htmlFor="password"
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
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    required
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    placeholder="Min 8 characters"
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
                  />
                </div>
              </div>

              <div style={{ marginTop: 28 }}>
                <button
                  type="submit"
                  className="btn-gradient"
                  style={{ width: "100%", padding: "13px", fontSize: 15, fontWeight: 700 }}
                >
                  Continue to PayPal →
                </button>
              </div>
            </form>
          )}

          {/* Step 2: Connect PayPal */}
          {step === 2 && (
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
                  marginBottom: 28,
                  fontSize: 14,
                  lineHeight: 1.6,
                }}
              >
                PactPal uses PayPal to hold escrow funds securely. You can connect now or complete setup and connect later.
              </p>

              {/* PayPal card */}
              {!paypalConnected ? (
                <div
                  style={{
                    background: "rgba(0,112,186,0.12)",
                    border: "2px dashed rgba(0,112,186,0.4)",
                    borderRadius: 16,
                    padding: "28px 20px",
                    textAlign: "center",
                    marginBottom: 24,
                  }}
                >
                  <div style={{ fontSize: 44, marginBottom: 12 }}>{connectingPayPal ? "🔄" : "🔗"}</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "white", marginBottom: 6 }}>
                    PayPal Authorization
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      color: "var(--color-text-muted)",
                      marginBottom: 18,
                      lineHeight: 1.5,
                      maxWidth: 380,
                      margin: "0 auto 18px",
                    }}
                  >
                    Authorize PactPal in the official PayPal Sandbox to securely hold and release escrow.
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
                    padding: "24px 20px",
                    textAlign: "center",
                    marginBottom: 24,
                  }}
                >
                  <div style={{ fontSize: 40, marginBottom: 8 }}>✅</div>
                  <div style={{ fontSize: 17, fontWeight: 700, color: "#34D399", marginBottom: 6 }}>
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
                    <span style={{ fontSize: 13, color: "white", fontFamily: "monospace" }}>{paypalEmail}</span>
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
                  <div style={{ fontSize: 13, color: "var(--color-text-muted)", lineHeight: 1.5, marginBottom: 14 }}>
                    PactPal is authorized to handle escrow holds &amp; releases.
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
                  >
                    Disconnect / Re-authorize
                  </button>
                </div>
              )}

              <div
                style={{
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 10,
                  padding: "12px 16px",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  marginBottom: 24,
                }}
              >
                <span style={{ fontSize: 16 }}>🔒</span>
                <span style={{ fontSize: 12, color: "var(--color-text-muted)", lineHeight: 1.4 }}>
                  Your funds remain in your PayPal-authorized escrow. PactPal cannot access money without agreed terms.
                </span>
              </div>

              <div style={{ display: "flex", gap: 12 }}>
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
                >
                  ← Back
                </button>
                <button
                  type="submit"
                  className={paypalConnected ? "btn-gradient" : undefined}
                  disabled={loading || !paypalConnected}
                  style={{
                    flex: 2,
                    padding: "13px",
                    fontSize: 15,
                    fontWeight: 700,
                    borderRadius: 10,
                    background: !paypalConnected ? "rgba(255,255,255,0.06)" : undefined,
                    border: !paypalConnected ? "1px solid rgba(255,255,255,0.1)" : "none",
                    color: !paypalConnected ? "rgba(255,255,255,0.35)" : "white",
                    boxShadow: !paypalConnected ? "none" : undefined,
                    opacity: !paypalConnected ? 0.6 : loading ? 0.7 : 1,
                    cursor: loading || !paypalConnected ? "not-allowed" : "pointer",
                    transition: "all 0.2s ease",
                  }}
                >
                  {loading ? "Creating account…" : "Complete setup →"}
                </button>
              </div>
            </form>
          )}
        </div>

        <p
          style={{
            textAlign: "center",
            marginTop: 24,
            fontSize: 14,
            color: "var(--color-text-muted)",
          }}
        >
          Already have an account?{" "}
          <Link href="/login" style={{ color: "var(--color-primary)", fontWeight: 600, textDecoration: "none" }}>
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
