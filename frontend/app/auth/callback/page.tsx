"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase, setCurrentUser, UserProfile } from "@/lib/supabase";
import Link from "next/link";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let mounted = true;

    async function handleAuthCallback() {
      try {
        // 1. Check for error parameters in URL hash or search query
        if (typeof window !== "undefined") {
          const hashParams = new URLSearchParams(window.location.hash.substring(1));
          const queryParams = new URLSearchParams(window.location.search);
          const errorDescription =
            hashParams.get("error_description") || queryParams.get("error_description");
          const error = hashParams.get("error") || queryParams.get("error");

          if (error || errorDescription) {
            if (mounted) {
              setStatus("error");
              setErrorMessage(errorDescription || error || "Google authentication was cancelled or failed.");
            }
            return;
          }
        }

        // 2. Fetch session from Supabase
        const { data: { session }, error } = await supabase.auth.getSession();

        if (error) {
          if (mounted) {
            setStatus("error");
            setErrorMessage(error.message);
          }
          return;
        }

        if (session && session.user) {
          if (mounted) {
            const user = session.user;
            const userMeta = user.user_metadata || {};
            const role = userMeta.role === "freelancer" ? "freelancer" : "hirer";

            const profile: UserProfile = {
              id: user.id,
              name: userMeta.full_name || userMeta.name || user.email?.split("@")[0] || "User",
              email: user.email || "",
              role: role,
              avatar_url: userMeta.avatar_url,
              access_token: session.access_token,
              created_at: user.created_at,
              is_demo: false,
            };

            setCurrentUser(profile);
            setStatus("success");
            router.replace(role === "freelancer" ? "/dashboard/freelancer" : "/dashboard/hirer");
          }
          return;
        }

        // 3. Fallback listener in case token hash is still processing
        const { data: authListener } = supabase.auth.onAuthStateChange((event, newSession) => {
          if (newSession && newSession.user && mounted) {
            const user = newSession.user;
            const userMeta = user.user_metadata || {};
            const role = userMeta.role === "freelancer" ? "freelancer" : "hirer";

            const profile: UserProfile = {
              id: user.id,
              name: userMeta.full_name || userMeta.name || user.email?.split("@")[0] || "User",
              email: user.email || "",
              role: role,
              avatar_url: userMeta.avatar_url,
              access_token: newSession.access_token,
              created_at: user.created_at,
              is_demo: false,
            };

            setCurrentUser(profile);
            setStatus("success");
            router.replace(role === "freelancer" ? "/dashboard/freelancer" : "/dashboard/hirer");
          }
        });

        const timer = setTimeout(() => {
          if (mounted && status === "loading") {
            router.replace("/dashboard/hirer");
          }
        }, 4000);

        return () => {
          authListener.subscription.unsubscribe();
          clearTimeout(timer);
        };
      } catch (err: any) {
        if (mounted) {
          setStatus("error");
          setErrorMessage(err?.message || "Unexpected authentication error");
        }
      }
    }

    handleAuthCallback();

    return () => {
      mounted = false;
    };
  }, [router, status]);

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "80px 24px",
      }}
    >
      <div
        className="glass-card"
        style={{
          width: "100%",
          maxWidth: 440,
          padding: "40px 36px",
          textAlign: "center",
        }}
      >
        {status === "loading" && (
          <div>
            <div
              style={{
                width: 48,
                height: 48,
                margin: "0 auto 20px",
                border: "3px solid rgba(0, 102, 255, 0.2)",
                borderTopColor: "var(--color-primary, #0066FF)",
                borderRadius: "50%",
                animation: "spin 1s linear infinite",
              }}
            />
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "white", marginBottom: 8 }}>
              Signing in with Google…
            </h2>
            <p style={{ color: "var(--color-text-muted)", fontSize: 14 }}>
              Connecting your Supabase account to PactPal
            </p>
          </div>
        )}

        {status === "success" && (
          <div>
            <div
              style={{
                width: 48,
                height: 48,
                margin: "0 auto 20px",
                borderRadius: "50%",
                background: "rgba(34, 197, 94, 0.15)",
                color: "#22c55e",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 24,
                fontWeight: "bold",
              }}
            >
              ✓
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "white", marginBottom: 8 }}>
              Authenticated!
            </h2>
            <p style={{ color: "var(--color-text-muted)", fontSize: 14 }}>
              Redirecting you to your dashboard…
            </p>
          </div>
        )}

        {status === "error" && (
          <div>
            <div
              style={{
                width: 48,
                height: 48,
                margin: "0 auto 20px",
                borderRadius: "50%",
                background: "rgba(239, 68, 68, 0.15)",
                color: "#ef4444",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 24,
                fontWeight: "bold",
              }}
            >
              ✕
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "white", marginBottom: 8 }}>
              Sign-In Failed
            </h2>
            <p style={{ color: "#ef4444", fontSize: 14, marginBottom: 24 }}>
              {errorMessage || "Unable to complete Google authentication."}
            </p>
            <Link
              href="/login"
              className="btn-gradient"
              style={{
                display: "inline-block",
                padding: "10px 24px",
                textDecoration: "none",
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Back to Login
            </Link>
          </div>
        )}
      </div>

      <style jsx global>{`
        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </main>
  );
}

