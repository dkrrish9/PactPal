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
      const { error: googleErr } = await signInWithGoogle();
      if (googleErr) {
        setError(googleErr.message);
        setLoading(false);
      }
    } catch (err: any) {
      setError(err?.message || "Google sign-in failed.");
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
      // Redirect to Hirer dashboard after login
      window.location.href = "/dashboard/hirer";
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
          <h1
            style={{
              fontSize: 28,
              fontWeight: 800,
              color: "white",
              marginBottom: 8,
              textAlign: "center",
            }}
          >
            Welcome back
          </h1>
          <p
            style={{
              color: "var(--color-text-muted)",
              textAlign: "center",
              marginBottom: 32,
              fontSize: 15,
            }}
          >
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
                required
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
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
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

            <button
              type="submit"
              className="btn-gradient"
              disabled={loading}
              style={{
                marginTop: 8,
                padding: "13px",
                fontSize: 15,
                fontWeight: 700,
                opacity: loading ? 0.7 : 1,
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        </div>

        <p
          style={{
            textAlign: "center",
            marginTop: 24,
            fontSize: 14,
            color: "var(--color-text-muted)",
          }}
        >
          Don't have an account?{" "}
          <Link href="/signup" style={{ color: "var(--color-primary)", fontWeight: 600, textDecoration: "none" }}>
            Sign up
          </Link>
        </p>
      </div>
    </main>
  );
}
