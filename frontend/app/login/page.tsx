"use client";
import { useState } from "react";
import Link from "next/link";
import { signInUser, DEMO_HIRER, DEMO_FREELANCER } from "@/lib/supabase";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }
    setError("");
    setLoading(true);

    try {
      const res = await signInUser({ email, password });
      if (res.error) {
        setError(res.error);
        setLoading(false);
        return;
      }

      setLoading(false);
      const targetRole = res.user?.role || "hirer";
      window.location.href = targetRole === "freelancer" ? "/dashboard/freelancer" : "/dashboard/hirer";
    } catch (err: any) {
      setError(err?.message || "Sign in failed.");
      setLoading(false);
    }
  }

  function handleQuickDemo(demoUser: typeof DEMO_HIRER) {
    setEmail(demoUser.email);
    setPassword("DemoPassword123!");
    signInUser({ email: demoUser.email, password: "DemoPassword123!" }).then((res) => {
      const targetRole = res.user?.role || "hirer";
      window.location.href = targetRole === "freelancer" ? "/dashboard/freelancer" : "/dashboard/hirer";
    });
  }

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
          top: "20%",
          left: "30%",
          width: 400,
          height: 400,
          background: "radial-gradient(circle, rgba(0,102,255,0.15) 0%, transparent 70%)",
          borderRadius: "50%",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
      />
      <div
        aria-hidden
        style={{
          position: "absolute",
          bottom: "20%",
          right: "30%",
          width: 300,
          height: 300,
          background: "radial-gradient(circle, rgba(122,92,255,0.12) 0%, transparent 70%)",
          borderRadius: "50%",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
      />

      <div style={{ width: "100%", maxWidth: 440, position: "relative", zIndex: 1 }}>
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

        {/* Card */}
        <div className="glass-card" style={{ padding: "40px 36px" }}>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "white", marginBottom: 8, textAlign: "center" }}>
            Welcome back
          </h1>
          <p style={{ color: "var(--color-text-muted)", textAlign: "center", marginBottom: 32, fontSize: 15 }}>
            Sign in to your PactPal account
          </p>

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

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
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
                onFocus={(e) => (e.currentTarget.style.borderColor = "rgba(0,102,255,0.6)")}
                onBlur={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)")}
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
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
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

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <Link
                href="/forgot-password"
                style={{ fontSize: 13, color: "var(--color-primary)", textDecoration: "none" }}
              >
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              className="btn-gradient"
              disabled={loading}
              style={{
                padding: "14px",
                fontSize: 16,
                fontWeight: 700,
                width: "100%",
                opacity: loading ? 0.7 : 1,
                cursor: loading ? "not-allowed" : "pointer",
                marginTop: 8,
              }}
              aria-label="Sign in"
            >
              {loading ? "Signing in…" : "Sign in →"}
            </button>
          </form>

          <div style={{ marginTop: 24, textAlign: "center" }}>
            <span style={{ color: "var(--color-text-muted)", fontSize: 14 }}>Don&apos;t have an account? </span>
            <Link href="/signup" style={{ color: "var(--color-primary)", fontWeight: 600, fontSize: 14, textDecoration: "none" }}>
              Sign up free
            </Link>
          </div>

          {/* Demo account quick login */}
          <div style={{ marginTop: 20, padding: "12px", background: "rgba(0,102,255,0.06)", border: "1px dashed rgba(0,102,255,0.25)", borderRadius: 12, textAlign: "center" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-primary)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
              ⚡ One-Click Demo Logins
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                onClick={() => handleQuickDemo(DEMO_HIRER)}
                style={{
                  flex: 1,
                  background: "rgba(0,102,255,0.15)",
                  border: "1px solid rgba(0,102,255,0.3)",
                  borderRadius: 8,
                  padding: "8px 10px",
                  color: "white",
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Priya (Hirer Demo)
              </button>
              <button
                type="button"
                onClick={() => handleQuickDemo(DEMO_FREELANCER)}
                style={{
                  flex: 1,
                  background: "rgba(255,152,0,0.15)",
                  border: "1px solid rgba(255,152,0,0.3)",
                  borderRadius: 8,
                  padding: "8px 10px",
                  color: "#FF9800",
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Alex (Freelancer Demo)
              </button>
            </div>
          </div>

          {/* Divider */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "24px 0" }}>
            <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }} />
            <span style={{ color: "var(--color-text-muted)", fontSize: 13 }}>or continue with</span>
            <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }} />
          </div>

          {/* OAuth placeholders */}
          <div style={{ display: "flex", gap: 12 }}>
            {["Google", "GitHub"].map((provider) => (
              <button
                key={provider}
                style={{
                  flex: 1,
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 10,
                  padding: "11px",
                  color: "var(--color-text-secondary)",
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
                aria-label={`Continue with ${provider}`}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.25)";
                  e.currentTarget.style.color = "white";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                  e.currentTarget.style.color = "var(--color-text-secondary)";
                }}
              >
                {provider}
              </button>
            ))}
          </div>
        </div>

        <p
          style={{
            textAlign: "center",
            marginTop: 24,
            fontSize: 12,
            color: "var(--color-text-muted)",
            lineHeight: 1.6,
          }}
        >
          By signing in you agree to our{" "}
          <Link href="/terms" style={{ color: "var(--color-primary)", textDecoration: "none" }}>
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/privacy" style={{ color: "var(--color-primary)", textDecoration: "none" }}>
            Privacy Policy
          </Link>
          .
        </p>
      </div>
    </main>
  );
}

