"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";

function PayPalCallbackContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const isCancel = searchParams.get("cancel") === "true";
  const [status, setStatus] = useState<"loading" | "success" | "error" | "cancelled">("loading");
  const [email, setEmail] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    if (typeof window === "undefined") return;

    if (isCancel) {
      setStatus("cancelled");
      try {
        const payload = JSON.stringify({ type: "PAYPAL_AUTH_CANCEL", timestamp: Date.now() });
        localStorage.setItem("pactpal_paypal_auth_event", payload);
        if (window.opener) {
          window.opener.postMessage({ type: "PAYPAL_AUTH_CANCEL" }, "*");
        }
      } catch {
        // ignore
      }
      setTimeout(() => {
        if (window.opener) {
          window.close();
        } else {
          window.location.href = "/signup";
        }
      }, 800);
      return;
    }

    if (!token) {
      setStatus("error");
      setErrorMessage("No PayPal authorization token detected in callback URL.");
      return;
    }

    // Call real PayPal order verification endpoint
    async function verifyOrder() {
      try {
        const res = await fetch("/api/paypal/verify-order", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        const data = await res.json();
        if (!res.ok || !data.success || !data.email) {
          throw new Error(data.message || "Failed to verify PayPal authorization.");
        }

        setEmail(data.email);
        setStatus("success");

        const authPayload = {
          type: "PAYPAL_AUTH_SUCCESS",
          email: data.email,
          payerId: data.payer_id,
          name: data.name,
          timestamp: Date.now(),
        };

        try {
          localStorage.setItem("pactpal_paypal_auth_event", JSON.stringify(authPayload));
          if (window.opener) {
            window.opener.postMessage(authPayload, "*");
          }
        } catch {
          // ignore
        }

        setTimeout(() => {
          if (window.opener) {
            window.close();
          } else {
            window.location.href = "/signup";
          }
        }, 800);
      } catch (err: unknown) {
        setStatus("error");
        setErrorMessage(err instanceof Error ? err.message : "Error verifying with PayPal Sandbox");
      }
    }

    verifyOrder();
  }, [token, isCancel]);

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#070B16",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
        fontFamily: "system-ui, -apple-system, sans-serif",
        color: "white",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 420,
          background: "#0F172A",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: 16,
          padding: "36px 28px",
          textAlign: "center",
          boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)",
        }}
      >
        {status === "loading" && (
          <div>
            <div style={{ fontSize: 44, marginBottom: 16 }}>🔄</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
              Verifying PayPal Sandbox...
            </h2>
            <p style={{ fontSize: 14, color: "#94A3B8", lineHeight: 1.5 }}>
              Connecting to PayPal to extract authenticated account details. Please wait a moment.
            </p>
          </div>
        )}

        {status === "success" && (
          <div>
            <div style={{ fontSize: 44, marginBottom: 16 }}>✅</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "#34D399", marginBottom: 8 }}>
              Authorized Successfully!
            </h2>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "rgba(16, 185, 129, 0.12)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                padding: "6px 14px",
                borderRadius: 20,
                marginBottom: 16,
              }}
            >
              <span style={{ fontSize: 13, color: "white", fontFamily: "monospace" }}>
                {email}
              </span>
              <span
                style={{
                  fontSize: 10,
                  background: "#10B981",
                  color: "#000",
                  fontWeight: 800,
                  padding: "2px 6px",
                  borderRadius: 4,
                }}
              >
                VERIFIED
              </span>
            </div>
            <p style={{ fontSize: 13, color: "#94A3B8" }}>
              Returning back to PactPal...
            </p>
          </div>
        )}

        {status === "cancelled" && (
          <div>
            <div style={{ fontSize: 44, marginBottom: 16 }}>⚠️</div>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
              PayPal Authorization Cancelled
            </h2>
            <p style={{ fontSize: 13, color: "#94A3B8" }}>
              Returning to setup...
            </p>
          </div>
        )}

        {status === "error" && (
          <div>
            <div style={{ fontSize: 44, marginBottom: 16 }}>❌</div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#EF4444", marginBottom: 8 }}>
              Verification Failed
            </h2>
            <p style={{ fontSize: 13, color: "#94A3B8", marginBottom: 20, lineHeight: 1.5 }}>
              {errorMessage}
            </p>
            <button
              onClick={() => {
                if (window.opener) {
                  window.close();
                } else {
                  window.location.href = "/signup";
                }
              }}
              style={{
                background: "#0070BA",
                border: "none",
                borderRadius: 8,
                padding: "10px 20px",
                color: "white",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Close Window
            </button>
          </div>
        )}
      </div>
    </main>
  );
}

export default function PayPalCallbackPage() {
  return (
    <Suspense
      fallback={
        <main
          style={{
            minHeight: "100vh",
            background: "#070B16",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
          }}
        >
          <div>Loading PayPal Callback...</div>
        </main>
      }
    >
      <PayPalCallbackContent />
    </Suspense>
  );
}
