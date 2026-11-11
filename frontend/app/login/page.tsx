"use client";
import { useState } from "react";
import Link from "next/link";
import { signInUser, signInWithGoogle } from "@/lib/supabase";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGoogleSignIn() {
    setError("");
    setLoading(true);
    try {
      const { error: googleError } = await signInWithGoogle();
      if (googleError) {
        setError(googleError.message || "Failed to sign in with Google.");
        setLoading(false);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to initiate Google sign-in.");
      setLoading(false);
    }
  }

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

          {/* Divider */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "24px 0" }}>
            <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }} />
            <span style={{ color: "var(--color-text-muted)", fontSize: 13 }}>or continue with</span>
            <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }} />
          </div>

          {/* Google Sign In Button (Requirement 1 & 3) */}
          <button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={loading}
            style={{
              width: "100%",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 12,
              padding: "13px 16px",
              color: "white",
              fontSize: 15,
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              transition: "all 0.2s",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
              boxShadow: "0 2px 10px rgba(0,0,0,0.2)",
            }}
            aria-label="Continue with Google"
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(0,102,255,0.6)";
              e.currentTarget.style.background = "rgba(0,102,255,0.1)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)";
              e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>{loading ? "Connecting to Google…" : "Continue with Google"}</span>
          </button>
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

