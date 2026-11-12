"use client";
import { useState, useEffect, Suspense } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { mockApi, Contract, HoldInfo } from "@/lib/mockApi";
import { backendClient } from "@/lib/backendClient";
import { getCurrentUser, UserProfile } from "@/lib/supabase";
import { 
  ShieldCheck, 
  Lock, 
  Clock, 
  ArrowRight, 
  CheckCircle2, 
  AlertCircle, 
  Calendar, 
  DollarSign, 
  Info,
  ExternalLink,
  RefreshCw,
  User
} from "lucide-react";

function isUserHirer(c: Contract | null, user: UserProfile | null): boolean {
  if (!c || !user) return false;
  const userEmail = (user.email || "").trim().toLowerCase();
  const userName = (user.name || "").trim().toLowerCase();
  const userId = user.id || "";

  // If user is explicitly the seller/freelancer, they cannot be the hirer
  const sellerEmail = (c.seller_email || "").trim().toLowerCase();
  const sellerName = (c.seller_name || "").trim().toLowerCase();
  const sellerId = c.seller_id || "";
  if (userId && sellerId && userId === sellerId) return false;
  if (userEmail && sellerEmail && userEmail === sellerEmail) return false;
  if (userName && sellerName && userName === sellerName) return false;

  const buyerEmail = (c.buyer_email || "").trim().toLowerCase();
  const buyerName = (c.buyer_name || "").trim().toLowerCase();
  const buyerId = c.buyer_id || "";

  if (userId && buyerId && userId === buyerId) return true;
  if (userEmail && buyerEmail && userEmail === buyerEmail) return true;
  if (userName && buyerName && (userName === buyerName || userName.includes(buyerName) || buyerName.includes(userName))) return true;
  return false;
}

export default function ContractFundPage() {
  return (
    <Suspense
      fallback={
        <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
          <Navbar />
          <div style={{ maxWidth: 800, margin: "140px auto", textAlign: "center", color: "white" }}>
            <h2 style={{ fontSize: 22, fontWeight: 700 }}>Loading escrow funding details...</h2>
          </div>
          <Footer />
        </main>
      }
    >
      <ContractFundContent />
    </Suspense>
  );
}

function ContractFundContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const contractId = (params?.id as string) || "pct_signed_03";

  const [contract, setContract] = useState<Contract | null>(null);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [holdInfo, setHoldInfo] = useState<HoldInfo | null>(null);
  const [isAuthorizing, setIsAuthorizing] = useState(false);
  const [authSuccess, setAuthSuccess] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [timeRemaining, setTimeRemaining] = useState<{
    days: number;
    hours: number;
    minutes: number;
    seconds: number;
  }>({ days: 29, hours: 0, minutes: 0, seconds: 0 });

  useEffect(() => {
    const user = getCurrentUser();
    setCurrentUser(user);

    async function loadFundData() {
      try {
        const live = await backendClient.getContract(contractId);
        if (live) {
          setContract(live as unknown as Contract);
          const hold = mockApi.getHoldInfo(live.id);
          setHoldInfo(hold);
          if (live.status === "FUNDED" && hold) {
            setAuthSuccess(true);
          }
          return;
        }
      } catch {}

      const loaded = mockApi.getContract(contractId) || mockApi.getContracts()[0];
      if (loaded) {
        setContract(loaded);
        const hold = mockApi.getHoldInfo(loaded.id);
        setHoldInfo(hold);
        if (loaded.status === "FUNDED" && hold) {
          setAuthSuccess(true);
        }
      }
    }
    loadFundData();
  }, [contractId]);

  // Complete official authorization hold with PayPal order token
  const completeAuthorization = async (orderId: string) => {
    setIsAuthorizing(true);
    setAuthError(null);
    try {
      const res = await backendClient.authorizeEscrowHold({
        contract_id: contractId,
        order_id: orderId,
      });

      if (res && res.paypal_auth_id) {
        const live = await backendClient.getContract(contractId);
        if (live) {
          setContract(live as unknown as Contract);
        } else {
          setContract((prev) =>
            prev
              ? {
                  ...prev,
                  status: "FUNDED",
                  paypal_auth_id: res.paypal_auth_id,
                  paypal_order_id: orderId,
                  auth_expires_at: res.auth_expires_at,
                }
              : null
          );
        }
        const hold = mockApi.getHoldInfo(contractId);
        setHoldInfo(hold);
        setAuthSuccess(true);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute PayPal authorization hold.";
      setAuthError(msg);
    } finally {
      setIsAuthorizing(false);
    }
  };

  // Handle redirect return params from PayPal Sandbox
  useEffect(() => {
    const paypalAction = searchParams.get("paypal_action");
    const token = searchParams.get("token");

    if (paypalAction === "cancelled") {
      setAuthError("PayPal authorization hold was cancelled by payer.");
      if (typeof window !== "undefined" && window.opener) {
        try {
          window.opener.postMessage({ type: "PAYPAL_ESCROW_CANCELLED", contractId }, "*");
          window.close();
        } catch {}
      }
      return;
    }

    if (paypalAction === "approved" && token) {
      if (typeof window !== "undefined" && window.opener) {
        try {
          window.opener.postMessage({ type: "PAYPAL_ESCROW_APPROVED", orderId: token, contractId }, "*");
          window.close();
          return;
        } catch {}
      }
      // Direct redirect in same tab
      completeAuthorization(token);
      if (typeof window !== "undefined") {
        window.history.replaceState({}, "", window.location.pathname);
      }
    }
  }, [searchParams, contractId]);

  // Handle postMessage from popup window
  useEffect(() => {
    if (typeof window === "undefined") return;

    const onMessage = async (event: MessageEvent) => {
      if (event.data?.type === "PAYPAL_ESCROW_APPROVED" && event.data?.orderId) {
        await completeAuthorization(event.data.orderId);
      } else if (event.data?.type === "PAYPAL_ESCROW_CANCELLED") {
        setIsAuthorizing(false);
        setAuthError("PayPal authorization hold was cancelled.");
      }
    };

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [contractId]);

  // Live countdown ticker every 1 second
  useEffect(() => {
    const interval = setInterval(() => {
      if (!contract?.auth_expires_at) return;
      const expiresAt = new Date(contract.auth_expires_at).getTime();
      const diff = Math.max(0, expiresAt - Date.now());
      const totalSeconds = Math.floor(diff / 1000);

      setTimeRemaining({
        days: Math.floor(totalSeconds / 86400),
        hours: Math.floor((totalSeconds % 86400) / 3600),
        minutes: Math.floor((totalSeconds % 3600) / 60),
        seconds: totalSeconds % 60,
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [contract?.auth_expires_at]);

  if (!contract) {
    return (
      <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
        <Navbar />
        <div style={{ maxWidth: 800, margin: "140px auto", textAlign: "center", color: "white" }}>
          <h2>Loading escrow funding details...</h2>
        </div>
      </main>
    );
  }

  const handlePayPalApprove = async () => {
    if (!contract) return;
    setIsAuthorizing(true);
    setAuthError(null);

    try {
      const origin = typeof window !== "undefined" ? window.location.origin : "";
      const holdRes = await backendClient.createEscrowHold({
        contract_id: contract.id,
        amount: contract.total_amount,
        currency: contract.currency || "USD",
        title: contract.title,
        origin,
      });

      if (!holdRes.approve_url) {
        throw new Error("Did not receive a valid PayPal approval URL.");
      }

      // Open official PayPal Sandbox popup
      const popupWidth = 600;
      const popupHeight = 720;
      const left = window.screenX + (window.outerWidth - popupWidth) / 2;
      const top = window.screenY + (window.outerHeight - popupHeight) / 2;

      const popup = window.open(
        holdRes.approve_url,
        "PayPalEscrowPopup",
        `width=${popupWidth},height=${popupHeight},left=${left},top=${top},status=no,toolbar=no,menubar=no`
      );

      if (!popup || popup.closed || typeof popup.closed === "undefined") {
        // Fallback to direct redirect if popup blocked
        window.location.href = holdRes.approve_url;
      } else {
        const timer = setInterval(() => {
          if (!popup || popup.closed) {
            clearInterval(timer);
            setTimeout(() => {
              setIsAuthorizing((prev) => (authSuccess ? false : prev));
            }, 1200);
          }
        }, 800);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to initiate PayPal escrow authorization.";
      setAuthError(msg);
      setIsAuthorizing(false);
    }
  };

  const isFunded = contract.status === "FUNDED" || authSuccess;
  const isHirer = isUserHirer(contract, currentUser);
  const expiryDate = contract.auth_expires_at 
    ? new Date(contract.auth_expires_at).toLocaleDateString(undefined, { 
        weekday: "short", 
        year: "numeric", 
        month: "short", 
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      })
    : new Date(Date.now() + 29 * 86400000).toLocaleDateString(undefined, {
        weekday: "short", 
        year: "numeric", 
        month: "short", 
        day: "numeric"
      });

  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      <div style={{ maxWidth: 960, margin: "0 auto", padding: "110px 24px 80px" }}>
        
        {/* Breadcrumb */}
        <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 24 }}>
          <Link href={isHirer ? "/dashboard/hirer" : "/dashboard/freelancer"} style={{ color: "#60A5FA", textDecoration: "none" }}>
            {isHirer ? "Hirer Dashboard" : "Freelancer Dashboard"}
          </Link>
          {" / "}
          <Link href={`/contracts/${contract.id}`} style={{ color: "#60A5FA", textDecoration: "none" }}>{contract.id}</Link>
          {" / "}
          <span style={{ color: "white" }}>{isHirer ? "Authorize Escrow Hold" : "Escrow Funding Status"}</span>
        </div>

        {/* Success Banner if Funded */}
        {isFunded && (
          <div
            style={{
              marginBottom: 28,
              padding: "20px 24px",
              background: "rgba(76, 175, 80, 0.12)",
              border: "1px solid rgba(76, 175, 80, 0.4)",
              borderRadius: 18,
              color: "#81C784",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <CheckCircle2 size={24} color="#81C784" />
              <div>
                <div style={{ fontSize: 16, fontWeight: 800, color: "white" }}>
                  Escrow Payment Successfully Authorized!
                </div>
                <div style={{ fontSize: 13, color: "#A5D6A7", marginTop: 2 }}>
                  PayPal Authorization ID: <strong style={{ fontFamily: "JetBrains Mono, monospace" }}>{contract.paypal_auth_id || "AUTH_99B87A65"}</strong>. Funds are locked in escrow.
                </div>
              </div>
            </div>

            <Link
              href={`/contracts/${contract.id}`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                color: "white",
                borderRadius: 30,
                padding: "10px 22px",
                fontSize: 14,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 0 20px rgba(0,102,255,0.4)",
              }}
            >
              Open Live Dashboard <ArrowRight size={15} />
            </Link>
          </div>
        )}

        {/* Main Funding Card */}
        <div
          style={{
            background: "rgba(255, 255, 255, 0.03)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: 24,
            padding: "36px",
            marginBottom: 32,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16, marginBottom: 28 }}>
            <div>
              <span
                style={{
                  background: isFunded ? "rgba(76, 175, 80, 0.15)" : "rgba(255, 152, 0, 0.15)",
                  border: `1px solid ${isFunded ? "rgba(76, 175, 80, 0.4)" : "rgba(255, 152, 0, 0.4)"}`,
                  color: isFunded ? "#81C784" : "#FFB74D",
                  padding: "4px 14px",
                  borderRadius: 50,
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: "0.06em",
                  display: "inline-block",
                  marginBottom: 10,
                }}
              >
                {isFunded ? "FUNDED & ACTIVE" : isHirer ? "PENDING AUTHORIZATION" : "AWAITING HIRER DEPOSIT"}
              </span>
              <h1 style={{ fontSize: "clamp(26px, 4vw, 36px)", fontWeight: 900, color: "white", marginBottom: 6 }}>
                {isHirer ? "Escrow Funding & Authorization Hold" : "Escrow Funding in Progress"}
              </h1>
              <p style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>
                Contract: <span style={{ color: "white", fontWeight: 600 }}>{contract.title}</span> ({contract.id})
              </p>
            </div>

            {/* Escrow Amount Pill */}
            <div
              style={{
                background: "rgba(0, 102, 255, 0.08)",
                border: "1px solid rgba(0, 102, 255, 0.25)",
                borderRadius: 20,
                padding: "20px 28px",
                textAlign: "right",
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em" }}>
                AUTHORIZED HOLD AMOUNT
              </div>
              <div style={{ fontSize: 36, fontWeight: 900, color: "white", fontFamily: "JetBrains Mono, monospace" }}>
                ${contract.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} <span style={{ fontSize: 14, color: "#60A5FA" }}>USD</span>
              </div>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4 }}>
                {isHirer ? "Funds held safely — zero upfront charges" : `Payable by Hirer: ${contract.buyer_name || contract.buyer_email}`}
              </div>
            </div>
          </div>

          {/* Real Live Countdown Ticker Grid */}
          <div
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: 20,
              padding: "28px",
              marginBottom: 32,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18, flexWrap: "wrap", gap: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Clock size={18} color="#FF9800" />
                <span style={{ fontSize: 14, fontWeight: 800, color: "white", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  PayPal Authorization 29-Day Hold Limit
                </span>
              </div>
              <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
                Expires on: <strong style={{ color: "white" }}>{expiryDate}</strong>
              </div>
            </div>

            {/* Countdown Blocks */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: 16,
                textAlign: "center",
              }}
            >
              {[
                { label: "DAYS", val: timeRemaining.days },
                { label: "HOURS", val: timeRemaining.hours },
                { label: "MINUTES", val: timeRemaining.minutes },
                { label: "SECONDS", val: timeRemaining.seconds },
              ].map((item) => (
                <div
                  key={item.label}
                  style={{
                    background: "rgba(255, 152, 0, 0.06)",
                    border: "1px solid rgba(255, 152, 0, 0.2)",
                    borderRadius: 16,
                    padding: "16px 12px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "clamp(26px, 4vw, 42px)",
                      fontWeight: 900,
                      color: "#FFB74D",
                      fontFamily: "JetBrains Mono, monospace",
                      lineHeight: 1.1,
                    }}
                  >
                    {String(item.val).padStart(2, "0")}
                  </div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.08em", marginTop: 4 }}>
                    {item.label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Freelancer Information Box: shown when freelancer is viewing an unfunded contract */}
          {!isHirer && !isFunded && (
            <div
              style={{
                background: "rgba(0, 102, 255, 0.08)",
                border: "1px solid rgba(0, 102, 255, 0.25)",
                borderRadius: 16,
                padding: "20px 24px",
                marginBottom: 28,
              }}
            >
              <div style={{ fontSize: 15, fontWeight: 700, color: "white", marginBottom: 6, display: "flex", alignItems: "center", gap: 8 }}>
                <Clock size={16} color="#60A5FA" /> Awaiting Hirer&apos;s Escrow Payment
              </div>
              <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.6 }}>
                Both parties have approved terms and dual-signed this contract. As the freelancer, you do not need to make any payment. The hirer (<strong style={{ color: "white" }}>{contract.buyer_name || contract.buyer_email}</strong>) has been prompted to authorize and hold <strong style={{ color: "#60A5FA" }}>${contract.total_amount.toLocaleString()} USD</strong> in escrow via PayPal. Once authorized, this project will automatically move to your Active Contracts and you can start development.
              </p>
            </div>
          )}

          {/* Educational Escrow Explainer */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: 18,
              marginBottom: 36,
            }}
          >
            <div
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                borderRadius: 16,
                padding: "20px",
              }}
            >
              <div style={{ fontSize: 14, fontWeight: 700, color: "white", marginBottom: 6, display: "flex", alignItems: "center", gap: 8 }}>
                <Lock size={15} color="#60A5FA" /> PayPal Authorization
              </div>
              <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                Your payment is authorized and held in escrow for up to 29 days. It is NOT transferred to the freelancer until AI verification succeeds.
              </p>
            </div>

            <div
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                borderRadius: 16,
                padding: "20px",
              }}
            >
              <div style={{ fontSize: 14, fontWeight: 700, color: "white", marginBottom: 6, display: "flex", alignItems: "center", gap: 8 }}>
                <ShieldCheck size={15} color="#34D399" /> AI Referee Protection
              </div>
              <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                When the code repository is submitted, PactPal's 6-stage referee verifies unit tests and design match. Only passing features trigger capture.
              </p>
            </div>

            <div
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                borderRadius: 16,
                padding: "20px",
              }}
            >
              <div style={{ fontSize: 14, fontWeight: 700, color: "white", marginBottom: 6, display: "flex", alignItems: "center", gap: 8 }}>
                <RefreshCw size={15} color="#FBBF24" /> Instant Refund Guarantee
              </div>
              <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                If tests fail or deliverables miss the agreed deadline, the authorization void/refund releases the money back to your account automatically.
              </p>
            </div>
          </div>

          {authError && (
            <div
              style={{
                width: "100%",
                padding: "14px 18px",
                marginBottom: 16,
                background: "rgba(239, 68, 68, 0.12)",
                border: "1px solid rgba(239, 68, 68, 0.4)",
                borderRadius: 14,
                color: "#FCA5A5",
                fontSize: 13,
                display: "flex",
                alignItems: "center",
                gap: 10,
              }}
            >
              <AlertCircle size={18} color="#EF4444" />
              <span>{authError}</span>
            </div>
          )}

          {/* Action Button: PayPal Approve (HIRER ONLY) or Waiting Indicator (FREELANCER) */}
          <div
            style={{
              paddingTop: 24,
              borderTop: "1px solid rgba(255, 255, 255, 0.08)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 16,
            }}
          >
            <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
              PactPal Escrow Sandbox · PayPal Authorization V2
            </div>

            {isFunded ? (
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <button
                  disabled
                  style={{
                    background: "rgba(76, 175, 80, 0.2)",
                    border: "1px solid rgba(76, 175, 80, 0.4)",
                    color: "#81C784",
                    borderRadius: 50,
                    padding: "14px 28px",
                    fontSize: 15,
                    fontWeight: 700,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    cursor: "default",
                  }}
                >
                  <CheckCircle2 size={18} /> Funds Authorized in Escrow
                </button>
                <Link
                  href={`/contracts/${contract.id}`}
                  style={{
                    background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                    color: "white",
                    borderRadius: 50,
                    padding: "14px 28px",
                    fontSize: 15,
                    fontWeight: 700,
                    textDecoration: "none",
                    boxShadow: "0 0 20px rgba(0,102,255,0.4)",
                  }}
                >
                  Go to Contract Dashboard →
                </Link>
              </div>
            ) : isHirer ? (
              <button
                onClick={handlePayPalApprove}
                disabled={isAuthorizing}
                style={{
                  background: isAuthorizing ? "#D97706" : "#FFC439",
                  color: "#003087",
                  border: "none",
                  borderRadius: 50,
                  padding: "16px 36px",
                  fontSize: 16,
                  fontWeight: 900,
                  cursor: isAuthorizing ? "wait" : "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 10,
                  boxShadow: "0 4px 20px rgba(255, 196, 57, 0.4)",
                  transition: "all 0.2s ease",
                }}
              >
                {isAuthorizing ? (
                  <>
                    <RefreshCw size={18} className="spin" /> Authorizing in PayPal Sandbox...
                  </>
                ) : (
                  <>
                    <span style={{ fontSize: 18, fontStyle: "italic", fontWeight: 900 }}>P</span>
                    <span>Approve with PayPal (${contract.total_amount.toLocaleString()})</span>
                  </>
                )}
              </button>
            ) : (
              <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    background: "rgba(255, 152, 0, 0.12)",
                    border: "1px solid rgba(255, 152, 0, 0.35)",
                    color: "#FFB74D",
                    borderRadius: 50,
                    padding: "12px 24px",
                    fontSize: 14,
                    fontWeight: 700,
                  }}
                >
                  <Clock size={16} /> Awaiting Hirer&apos;s PayPal Escrow Deposit
                </div>
                <Link
                  href="/dashboard/freelancer"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.15)",
                    color: "white",
                    borderRadius: 50,
                    padding: "12px 24px",
                    fontSize: 14,
                    fontWeight: 600,
                    textDecoration: "none",
                  }}
                >
                  ← Back to Freelancer Dashboard
                </Link>
              </div>
            )}
          </div>
        </div>

      </div>
      <Footer />
    </main>
  );
}

