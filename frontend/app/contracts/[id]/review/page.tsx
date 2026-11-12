"use client";
import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { mockApi, Contract, Feature } from "@/lib/mockApi";
import { backendClient } from "@/lib/backendClient";
import { getCurrentUser } from "@/lib/supabase";
import { 
  ShieldCheck, 
  CheckCircle2, 
  Clock, 
  ArrowRight, 
  ExternalLink, 
  Calendar, 
  DollarSign, 
  User, 
  Palette, 
  RotateCcw, 
  Lock, 
  Unlock, 
  AlertTriangle,
  Sparkles,
  FileSignature
} from "lucide-react";

function isUserHirer(c: Contract | null, user: any): boolean {
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

export default function ContractReviewPage() {
  const params = useParams();
  const router = useRouter();
  const contractId = (params?.id as string) || "pct_review_02";

  const [contract, setContract] = useState<Contract | null>(null);
  const [role, setRole] = useState<"SELLER" | "BUYER">("SELLER");
  const [checkedFeatures, setCheckedFeatures] = useState<Record<string, boolean>>({});
  const [isCounterModalOpen, setIsCounterModalOpen] = useState(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  // Counter offer state
  const [counterPrice, setCounterPrice] = useState<number>(0);
  const [counterDeadline, setCounterDeadline] = useState<string>("");
  const [counterNote, setCounterNote] = useState<string>("");
  const [featureWeights, setFeatureWeights] = useState<Record<string, number>>({});

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const live = await backendClient.getContract(contractId);
        if (live && isMounted) {
          setContract(live as unknown as Contract);
          setCounterPrice(live.total_amount);
          setCounterDeadline(live.deadline.split("T")[0]);
          const initialChecks: Record<string, boolean> = {};
          const initialWeights: Record<string, number> = {};
          const locked = Boolean(live.is_locked || (live as any).checklist_locked || (live as any).seller_confirmed_at);
          (live.features || []).forEach((f: any) => {
            initialChecks[f.id] = locked;
            initialWeights[f.id] = f.price_weight;
          });
          setCheckedFeatures(initialChecks);
          setFeatureWeights(initialWeights);
          return;
        }
      } catch {
        // Fallback
      }

      const loaded = mockApi.getContract(contractId) || mockApi.getContracts()[0];
      if (loaded && isMounted) {
        setContract(loaded);
        setCounterPrice(loaded.total_amount);
        setCounterDeadline(loaded.deadline.split("T")[0]);
        const initialChecks: Record<string, boolean> = {};
        const initialWeights: Record<string, number> = {};
        loaded.features.forEach((f) => {
          initialChecks[f.id] = loaded.checklist_locked || Boolean(loaded.seller_confirmed_at);
          initialWeights[f.id] = f.price_weight;
        });
        setCheckedFeatures(initialChecks);
        setFeatureWeights(initialWeights);
      }
    }
    loadData();
    return () => { isMounted = false; };
  }, [contractId]);

  useEffect(() => {
    const user = getCurrentUser();
    if (contract && user) {
      const isHirer = isUserHirer(contract, user);
      setRole(isHirer ? "BUYER" : "SELLER");
    }
  }, [contract]);

  if (!contract) {
    return (
      <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
        <Navbar />
        <div style={{ maxWidth: 800, margin: "140px auto", textAlign: "center", color: "white" }}>
          <h2>Loading contract review...</h2>
        </div>
      </main>
    );
  }

  const isLocked = Boolean(contract.is_locked || (contract as any).checklist_locked || (contract.buyer_confirmed_at && contract.seller_confirmed_at));
  const allItemsChecked = (contract.features || []).every((f) => checkedFeatures[f.id]);
  const totalWeight = Object.values(featureWeights).reduce((a, b) => a + b, 0);

  const handleToggleCheck = (featId: string) => {
    if (isLocked) return;
    setCheckedFeatures((prev) => ({
      ...prev,
      [featId]: !prev[featId],
    }));
  };

  const handleAcceptAndSign = async () => {
    const user = getCurrentUser();
    if (role === "SELLER") {
      const updated = await backendClient.applyToContract(contract.id, {
        id: user?.id,
        name: user?.name,
        email: user?.email,
      });
      if (updated) {
        setContract({ ...updated });
      }
      setSuccessToast("Agreement terms confirmed! Opening contract dashboard...");
      setTimeout(() => router.push(`/contracts/${contract.id}`), 800);
    } else {
      const updated = await backendClient.approveAndSignContract(contract.id, {
        id: user?.id,
        name: user?.name,
        email: user?.email,
      });
      if (updated) {
        setContract({ ...updated });
        setSuccessToast("Freelancer approved & contract dual-signed! Redirecting to PayPal Escrow authorization...");
        setTimeout(() => router.push(`/contracts/${contract.id}/fund`), 800);
      }
    }
  };

  const handleConfirmRole = async () => {
    const user = getCurrentUser();
    if (role === "SELLER") {
      const updated = await backendClient.applyToContract(contract.id, {
        id: user?.id,
        name: user?.name,
        email: user?.email,
      });
      if (updated) {
        setContract({ ...updated });
      }
      setSuccessToast("Agreement terms confirmed! Opening contract dashboard...");
      setTimeout(() => router.push(`/contracts/${contract.id}`), 800);
    } else {
      const updated = await backendClient.approveAndSignContract(contract.id, {
        id: user?.id,
        name: user?.name,
        email: user?.email,
      });
      if (updated) {
        setContract({ ...updated });
        setSuccessToast("Freelancer approved & contract signed by both parties! Moving to dashboard...");
        setTimeout(() => router.push(`/contracts/${contract.id}`), 800);
      }
    }
  };

  const handleOpenCounterModal = () => {
    setCounterPrice(contract.total_amount);
    setCounterDeadline(contract.deadline.split("T")[0]);
    setCounterNote("");
    setIsCounterModalOpen(true);
  };

  const handleSubmitCounter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (totalWeight !== 100) {
      alert("Feature weights must total exactly 100% before submitting counter.");
      return;
    }

    const updatedFeatures: Feature[] = contract.features.map((f) => ({
      ...f,
      price_weight: featureWeights[f.id] ?? f.price_weight,
      allocated_amount: (counterPrice * (featureWeights[f.id] ?? f.price_weight)) / 100,
    }));

    const updated = await backendClient.counterContract(contract.id, {
      proposed_by: role,
      total_amount: Number(counterPrice),
      deadline: new Date(counterDeadline).toISOString(),
      note: counterNote || "Proposed adjusted terms and feature weight distribution.",
      features: updatedFeatures,
    });

    if (updated) {
      setContract({ ...updated });
      setIsCounterModalOpen(false);
      setSuccessToast("Counter-offer submitted successfully! Status updated to In Review.");
      setTimeout(() => setSuccessToast(null), 5000);
    }
  };

  const handleAcceptCounter = async () => {
    const updated = await backendClient.acceptCounter(contract.id, role);
    if (updated) {
      setContract({ ...updated });
      setSuccessToast("Counter-offer accepted! Contract is now SIGNED.");
      setTimeout(() => setSuccessToast(null), 5000);
    }
  };

  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      <div style={{ maxWidth: 1080, margin: "0 auto", padding: "110px 24px 80px" }}>
        
        {/* Breadcrumb & Navigation */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
          <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
            <Link href={role === "BUYER" ? "/dashboard/hirer" : "/dashboard/freelancer"} style={{ color: "#60A5FA", textDecoration: "none" }}>
              {role === "BUYER" ? "Hirer Dashboard" : "Freelancer Dashboard"}
            </Link>
            {" / "}
            <Link href={`/contracts/${contract.id}`} style={{ color: "#60A5FA", textDecoration: "none" }}>{contract.id}</Link>
            {" / "}
            <span style={{ color: "white" }}>
              {role === "BUYER" ? "Hirer Review & Approval" : "Freelancer Review & Confirmation"}
            </span>
          </div>

          {/* Locked Role Badge (Viewing identity strictly bound to login) */}
          <div>
            {role === "BUYER" ? (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  background: "rgba(0,102,255,0.12)",
                  border: "1px solid rgba(0,102,255,0.35)",
                  borderRadius: 30,
                  padding: "6px 16px",
                  fontSize: 12,
                  fontWeight: 700,
                  color: "#60A5FA",
                }}
              >
                Viewing as Hirer
              </div>
            ) : (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  background: "rgba(255,152,0,0.12)",
                  border: "1px solid rgba(255,152,0,0.35)",
                  borderRadius: 30,
                  padding: "6px 16px",
                  fontSize: 12,
                  fontWeight: 700,
                  color: "#FF9800",
                }}
              >
                Viewing as Freelancer
              </div>
            )}
          </div>
        </div>

        {/* Success Toast Notification */}
        {successToast && (
          <div
            style={{
              marginBottom: 24,
              padding: "16px 20px",
              background: "rgba(76, 175, 80, 0.15)",
              border: "1px solid rgba(76, 175, 80, 0.4)",
              borderRadius: 14,
              color: "#81C784",
              display: "flex",
              alignItems: "center",
              gap: 12,
              fontWeight: 600,
              fontSize: 14,
              animation: "fadeIn 0.3s ease",
            }}
          >
            <CheckCircle2 size={18} />
            <span>{successToast}</span>
          </div>
        )}

        {/* Header Block */}
        <div
          style={{
            background: "rgba(255, 255, 255, 0.03)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: 24,
            padding: "32px",
            marginBottom: 28,
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                <span
                  style={{
                    background: contract.status === "SIGNED" ? "rgba(122, 92, 255, 0.15)" : "rgba(0, 163, 224, 0.15)",
                    border: `1px solid ${contract.status === "SIGNED" ? "rgba(122, 92, 255, 0.4)" : "rgba(0, 163, 224, 0.4)"}`,
                    color: contract.status === "SIGNED" ? "#A78BFA" : "#38BDF8",
                    padding: "4px 12px",
                    borderRadius: 50,
                    fontSize: 12,
                    fontWeight: 700,
                    letterSpacing: "0.06em",
                  }}
                >
                  {contract.status}
                </span>
                <span style={{ fontSize: 12, color: "var(--color-text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                  CONTRACT ID: {contract.id}
                </span>
              </div>
              <h1 style={{ fontSize: "clamp(26px, 4vw, 36px)", fontWeight: 900, color: "white", marginBottom: 10 }}>
                {contract.title}
              </h1>
              <p style={{ fontSize: 15, color: "var(--color-text-secondary)", maxWidth: 700, lineHeight: 1.6 }}>
                {contract.description}
              </p>
            </div>

            {/* Total Budget Card */}
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
                ESCROW HOLD VALUE
              </div>
              <div style={{ fontSize: 32, fontWeight: 900, color: "white", fontFamily: "JetBrains Mono, monospace" }}>
                ${contract.total_amount.toLocaleString()} <span style={{ fontSize: 14, color: "#60A5FA" }}>USD</span>
              </div>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4 }}>
                100% Protected via PayPal Escrow
              </div>
            </div>
          </div>

          {/* Quick Details Strip */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 16,
              marginTop: 24,
              paddingTop: 24,
              borderTop: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--color-text-muted)", marginBottom: 4 }}>HIRER</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "white", display: "flex", alignItems: "center", gap: 6 }}>
                <User size={14} color="#60A5FA" /> {contract.buyer_name || contract.buyer_email}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--color-text-muted)", marginBottom: 4 }}>FREELANCER</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "white", display: "flex", alignItems: "center", gap: 6 }}>
                <User size={14} color="#34D399" /> {contract.seller_name || contract.seller_email || "Open for Application"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--color-text-muted)", marginBottom: 4 }}>DELIVERY DEADLINE</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "white", display: "flex", alignItems: "center", gap: 6 }}>
                <Calendar size={14} color="#FBBF24" /> {new Date(contract.deadline).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
              </div>
            </div>
            {contract.figma_url && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--color-text-muted)", marginBottom: 4 }}>DESIGN SPECIFICATION</div>
                <a
                  href={contract.figma_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "#60A5FA",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    textDecoration: "none",
                  }}
                >
                  <Palette size={14} /> Open Figma Design <ExternalLink size={12} />
                </a>
              </div>
            )}
          </div>
        </div>

        {/* Dual Confirmation Status (& ) */}
        <div
          style={{
            background: "rgba(255, 255, 255, 0.02)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: 20,
            padding: "24px 28px",
            marginBottom: 28,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18, flexWrap: "wrap", gap: 10 }}>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 800, color: "white", display: "flex", alignItems: "center", gap: 8 }}>
                Dual Confirmation Status
                {isLocked ? (
                  <span style={{ fontSize: 11, background: "rgba(76,175,80,0.15)", color: "#81C784", padding: "3px 10px", borderRadius: 20, display: "inline-flex", alignItems: "center", gap: 4 }}>
                    <Lock size={12} /> Checklist Locked
                  </span>
                ) : (
                  <span style={{ fontSize: 11, background: "rgba(255,152,0,0.15)", color: "#FFB74D", padding: "3px 10px", borderRadius: 20, display: "inline-flex", alignItems: "center", gap: 4 }}>
                    <Unlock size={12} /> Unlocked (Counter Open)
                  </span>
                )}
              </h2>
              <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 2 }}>
                Both parties must timestamp and confirm the priced checklist before funding.
              </p>
            </div>

            {/* Quick Confirm button for current viewing role */}
            {!isLocked && (
              <button
                onClick={handleConfirmRole}
                style={{
                  background: role === "BUYER" ? "rgba(0,102,255,0.12)" : "rgba(255,152,0,0.12)",
                  border: role === "BUYER" ? "1px solid rgba(0,102,255,0.3)" : "1px solid rgba(255,152,0,0.3)",
                  color: "white",
                  padding: "8px 18px",
                  borderRadius: 30,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <FileSignature size={14} color={role === "BUYER" ? "#60A5FA" : "#FF9800"} />
                {role === "BUYER" ? "Approve & Sign as Hirer" : "Confirm as Freelancer"}
              </button>
            )}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
            {/* Hirer Confirmation Box */}
            <div
              style={{
                background: contract.buyer_confirmed_at ? "rgba(76, 175, 80, 0.06)" : "rgba(255, 255, 255, 0.02)",
                border: `1px solid ${contract.buyer_confirmed_at ? "rgba(76, 175, 80, 0.3)" : "rgba(255, 255, 255, 0.07)"}`,
                borderRadius: 14,
                padding: "16px 20px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                {contract.buyer_confirmed_at ? <CheckCircle2 size={16} color="#81C784" /> : <Clock size={16} color="#FFB74D" />}
                <span style={{ fontSize: 13, fontWeight: 700, color: contract.buyer_confirmed_at ? "#81C784" : "#FFB74D" }}>
                  {contract.buyer_confirmed_at ? "Hirer Confirmed" : "Pending Hirer Approval"}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                {contract.buyer_confirmed_at
                  ? `Timestamped: ${new Date(contract.buyer_confirmed_at).toLocaleString()}`
                  : "Awaiting formal checklist approval from hirer"}
              </div>
            </div>

            {/* Freelancer Confirmation Box */}
            <div
              style={{
                background: contract.seller_confirmed_at ? "rgba(76, 175, 80, 0.06)" : "rgba(255, 255, 255, 0.02)",
                border: `1px solid ${contract.seller_confirmed_at ? "rgba(76, 175, 80, 0.3)" : "rgba(255, 255, 255, 0.07)"}`,
                borderRadius: 14,
                padding: "16px 20px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                {contract.seller_confirmed_at ? <CheckCircle2 size={16} color="#81C784" /> : <Clock size={16} color="#FFB74D" />}
                <span style={{ fontSize: 13, fontWeight: 700, color: contract.seller_confirmed_at ? "#81C784" : "#FFB74D" }}>
                  {contract.seller_confirmed_at ? "Freelancer Confirmed" : "Pending Freelancer Application"}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                {contract.seller_confirmed_at
                  ? `Timestamped: ${new Date(contract.seller_confirmed_at).toLocaleString()}`
                  : "Awaiting freelancer checklist acceptance or counter"}
              </div>
            </div>
          </div>
        </div>

        {/* Active Counter-Offer Banner (if any) */}
        {contract.counter_offer && (
          <div
            style={{
              background: "rgba(255, 152, 0, 0.08)",
              border: "1px solid rgba(255, 152, 0, 0.3)",
              borderRadius: 20,
              padding: "24px 28px",
              marginBottom: 28,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <AlertTriangle size={18} color="#FFB74D" />
                  <span style={{ fontSize: 14, fontWeight: 800, color: "#FFB74D", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Active Counter-Offer from {contract.counter_offer.proposed_by === "SELLER" ? "Freelancer" : "Hirer"}
                  </span>
                </div>
                <div style={{ fontSize: 16, fontWeight: 700, color: "white", marginBottom: 4 }}>
                  Proposed Budget: ${contract.counter_offer.total_amount.toLocaleString()} USD | Deadline: {new Date(contract.counter_offer.deadline).toLocaleDateString()}
                </div>
                <p style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                  "{contract.counter_offer.note}"
                </p>
              </div>

              {/* Counter acceptance actions */}
              {role !== contract.counter_offer.proposed_by && (
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <button
                    onClick={handleAcceptCounter}
                    style={{
                      background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                      color: "white",
                      border: "none",
                      borderRadius: 30,
                      padding: "10px 22px",
                      fontSize: 14,
                      fontWeight: 700,
                      cursor: "pointer",
                      boxShadow: "0 0 20px rgba(0,102,255,0.4)",
                    }}
                  >
                    Accept Counter Terms →
                  </button>
                  <button
                    onClick={handleOpenCounterModal}
                    style={{
                      background: "rgba(255,255,255,0.06)",
                      border: "1px solid rgba(255,255,255,0.15)",
                      color: "white",
                      borderRadius: 30,
                      padding: "10px 20px",
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Re-Counter
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Priced Feature Checklist */}
        <div
          style={{
            background: "rgba(255, 255, 255, 0.03)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: 24,
            padding: "32px",
            marginBottom: 32,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
            <div>
              <h2 style={{ fontSize: 22, fontWeight: 900, color: "white", display: "flex", alignItems: "center", gap: 10 }}>
                 Priced Deliverable Checklist
              </h2>
              <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginTop: 4 }}>
                Each feature has a dedicated acceptance test and escrow weight. Funds release automatically upon passing.
              </p>
            </div>

            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              {Object.values(checkedFeatures).filter(Boolean).length} of {contract.features.length} items checked
            </div>
          </div>

          {/* Feature Cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {contract.features.map((feat, idx) => {
              const isChecked = checkedFeatures[feat.id] ?? false;
              return (
                <div
                  key={feat.id}
                  onClick={() => handleToggleCheck(feat.id)}
                  style={{
                    background: isChecked ? "rgba(0, 102, 255, 0.06)" : "rgba(255, 255, 255, 0.02)",
                    border: `1px solid ${isChecked ? "rgba(0, 102, 255, 0.3)" : "rgba(255, 255, 255, 0.06)"}`,
                    borderRadius: 18,
                    padding: "20px 24px",
                    cursor: isLocked ? "default" : "pointer",
                    transition: "all 0.2s ease",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
                    {/* Checkbox */}
                    <div
                      style={{
                        marginTop: 4,
                        width: 22,
                        height: 22,
                        borderRadius: 6,
                        border: `2px solid ${isChecked ? "#60A5FA" : "rgba(255,255,255,0.3)"}`,
                        background: isChecked ? "#0066FF" : "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "white",
                        fontSize: 14,
                        fontWeight: 900,
                        flexShrink: 0,
                        transition: "all 0.2s",
                      }}
                    >
                      {isChecked && "✓"}
                    </div>

                    {/* Content */}
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 10, marginBottom: 8 }}>
                        <div>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", fontFamily: "JetBrains Mono, monospace", marginRight: 8 }}>
                            FEATURE 0{idx + 1}
                          </span>
                          <span style={{ fontSize: 16, fontWeight: 800, color: "white" }}>
                            {feat.title}
                          </span>
                        </div>

                        {/* Weight & Allocated Amount */}
                        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                          <span
                            style={{
                              background: "rgba(0,102,255,0.15)",
                              color: "#60A5FA",
                              fontSize: 12,
                              fontWeight: 700,
                              padding: "3px 10px",
                              borderRadius: 50,
                            }}
                          >
                            {feat.price_weight}% weight
                          </span>
                          <span style={{ fontSize: 16, fontWeight: 900, color: "white", fontFamily: "JetBrains Mono, monospace" }}>
                            ${feat.allocated_amount.toLocaleString()} USD
                          </span>
                        </div>
                      </div>

                      {/* Plain-Language Acceptance Test Box */}
                      <div
                        style={{
                          background: "rgba(0,0,0,0.25)",
                          border: "1px solid rgba(255,255,255,0.06)",
                          borderRadius: 10,
                          padding: "10px 14px",
                          marginTop: 6,
                        }}
                      >
                        <div style={{ fontSize: 11, fontWeight: 700, color: "#60A5FA", marginBottom: 3, letterSpacing: "0.05em" }}>
                          ACCEPTANCE CRITERIA / TEST
                        </div>
                        <div style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                          {feat.acceptance_test}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Bar (Core Requirements) */}
        <div
          style={{
            background: "rgba(12, 18, 34, 0.95)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            borderRadius: 24,
            padding: "24px 32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 20,
            boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
          }}
        >
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: "white" }}>
              {contract.status === "SIGNED"
                ? "Contract Signed by Both Parties"
                : isLocked
                ? "Checklist Confirmed & Locked"
                : "Ready to confirm or negotiate terms?"}
            </div>
            <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 2 }}>
              {contract.status === "SIGNED"
                ? "Proceed to the funding step to lock escrow funds via PayPal authorization hold."
                : "Both parties can review the terms as outlined or counter with modified price and deadline."}
            </div>
          </div>

          <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
            {contract.status === "SIGNED" ? (
              <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                {role === "BUYER" ? (
                  <Link
                    href={`/contracts/${contract.id}/fund`}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                      background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                      color: "white",
                      borderRadius: 50,
                      padding: "14px 32px",
                      fontSize: 15,
                      fontWeight: 700,
                      textDecoration: "none",
                      boxShadow: "0 0 25px rgba(0,102,255,0.4)",
                    }}
                  >
                    Proceed to PayPal Funding (${contract.total_amount.toLocaleString()}) <ArrowRight size={16} />
                  </Link>
                ) : (
                  <>
                    <div
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 8,
                        background: "rgba(255,152,0,0.12)",
                        border: "1px solid rgba(255,152,0,0.35)",
                        color: "#FFB74D",
                        borderRadius: 50,
                        padding: "12px 24px",
                        fontSize: 14,
                        fontWeight: 700,
                      }}
                    >
                      <Clock size={16} /> Terms Signed · Awaiting Hirer&apos;s PayPal Escrow Deposit
                    </div>
                    <Link
                      href={`/contracts/${contract.id}`}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 8,
                        background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                        color: "white",
                        borderRadius: 50,
                        padding: "12px 24px",
                        fontSize: 14,
                        fontWeight: 700,
                        textDecoration: "none",
                        boxShadow: "0 0 20px rgba(0,102,255,0.4)",
                      }}
                    >
                      Open Contract Dashboard →
                    </Link>
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
                      Go to Freelancer Dashboard →
                    </Link>
                  </>
                )}
              </div>
            ) : (
              <>
                {/* Propose Counter Terms */}
                <button
                  onClick={handleOpenCounterModal}
                  style={{
                    background: "rgba(255, 255, 255, 0.05)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    color: "white",
                    borderRadius: 50,
                    padding: "14px 28px",
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    transition: "all 0.2s",
                  }}
                >
                  <RotateCcw size={15} /> Propose Counter Terms
                </button>

                {/* Accept & Sign Checklist */}
                <button
                  onClick={handleAcceptAndSign}
                  style={{
                    background: "linear-gradient(135deg, #0066FF, #00A3E0)",
                    border: "none",
                    borderRadius: 50,
                    color: "white",
                    padding: "14px 32px",
                    fontSize: 15,
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    boxShadow: "0 0 30px rgba(0,102,255,0.45)",
                  }}
                >
                  <ShieldCheck size={18} />
                  {role === "SELLER"
                    ? contract.seller_confirmed_at
                      ? "Application Submitted (Waiting Hirer Approval)"
                      : "Confirm Terms & Apply as Freelancer"
                    : contract.seller_confirmed_at
                    ? "Approve Freelancer & Sign Contract"
                    : "Confirm & Sign as Hirer"}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Counter-Offer Modal */}
        {isCounterModalOpen && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(0,0,0,0.8)",
              backdropFilter: "blur(8px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 200,
              padding: "20px",
            }}
          >
            <div
              style={{
                background: "rgba(15, 23, 42, 0.98)",
                border: "1px solid rgba(255,255,255,0.15)",
                borderRadius: 24,
                padding: "36px",
                maxWidth: 640,
                width: "100%",
                maxHeight: "90vh",
                overflowY: "auto",
                boxShadow: "0 25px 60px rgba(0,0,0,0.8)",
              }}
            >
              <h2 style={{ fontSize: 24, fontWeight: 900, color: "white", marginBottom: 8, display: "flex", alignItems: "center", gap: 10 }}>
                <RotateCcw size={22} color="#60A5FA" /> Propose Counter Terms
              </h2>
              <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginBottom: 24 }}>
                Adjust total budget, delivery deadline, or re-allocate milestone weights.
              </p>

              <form onSubmit={handleSubmitCounter}>
                {/* Proposed Budget */}
                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 6 }}>
                    PROPOSED TOTAL BUDGET (USD)
                  </label>
                  <div style={{ position: "relative" }}>
                    <span style={{ position: "absolute", left: 14, top: 14, color: "var(--color-text-muted)" }}>$</span>
                    <input
                      type="number"
                      value={counterPrice}
                      onChange={(e) => setCounterPrice(Number(e.target.value))}
                      min={100}
                      step={50}
                      required
                      style={{
                        width: "100%",
                        padding: "12px 14px 12px 30px",
                        background: "rgba(255,255,255,0.05)",
                        border: "1px solid rgba(255,255,255,0.12)",
                        borderRadius: 12,
                        color: "white",
                        fontSize: 16,
                        fontFamily: "JetBrains Mono, monospace",
                        fontWeight: 700,
                      }}
                    />
                  </div>
                </div>

                {/* Proposed Deadline */}
                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 6 }}>
                    PROPOSED DELIVERY DEADLINE
                  </label>
                  <input
                    type="date"
                    value={counterDeadline}
                    onChange={(e) => setCounterDeadline(e.target.value)}
                    required
                    style={{
                      width: "100%",
                      padding: "12px 14px",
                      background: "rgba(255,255,255,0.05)",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: 12,
                      color: "white",
                      fontSize: 15,
                    }}
                  />
                </div>

                {/* Feature Weights Re-allocation */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <label style={{ fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)" }}>
                      ADJUST FEATURE WEIGHTS (TOTAL MUST BE 100%)
                    </label>
                    <span
                      style={{
                        fontSize: 13,
                        fontWeight: 800,
                        color: totalWeight === 100 ? "#81C784" : "#F87171",
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                    >
                      Sum: {totalWeight}%
                    </span>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {contract.features.map((feat) => (
                      <div
                        key={feat.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 12,
                          background: "rgba(255,255,255,0.02)",
                          padding: "10px 14px",
                          borderRadius: 10,
                        }}
                      >
                        <span style={{ fontSize: 13, color: "white", flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {feat.title}
                        </span>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <input
                            type="number"
                            min={1}
                            max={100}
                            value={featureWeights[feat.id] ?? feat.price_weight}
                            onChange={(e) =>
                              setFeatureWeights((prev) => ({
                                ...prev,
                                [feat.id]: Number(e.target.value),
                              }))
                            }
                            style={{
                              width: 60,
                              padding: "6px 8px",
                              background: "rgba(255,255,255,0.05)",
                              border: "1px solid rgba(255,255,255,0.15)",
                              borderRadius: 8,
                              color: "white",
                              fontSize: 14,
                              textAlign: "center",
                              fontFamily: "JetBrains Mono, monospace",
                            }}
                          />
                          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Reason / Notes */}
                <div style={{ marginBottom: 28 }}>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 6 }}>
                    JUSTIFICATION / NOTES FOR OTHER PARTY
                  </label>
                  <textarea
                    rows={3}
                    value={counterNote}
                    onChange={(e) => setCounterNote(e.target.value)}
                    placeholder="e.g. Added 5 days to ensure 100% test coverage on the authentication suite."
                    style={{
                      width: "100%",
                      padding: "12px 14px",
                      background: "rgba(255,255,255,0.05)",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: 12,
                      color: "white",
                      fontSize: 14,
                      resize: "vertical",
                    }}
                  />
                </div>

                {/* Modal Buttons */}
                <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
                  <button
                    type="button"
                    onClick={() => setIsCounterModalOpen(false)}
                    style={{
                      background: "transparent",
                      border: "1px solid rgba(255,255,255,0.15)",
                      color: "white",
                      borderRadius: 30,
                      padding: "10px 20px",
                      fontSize: 14,
                      cursor: "pointer",
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={totalWeight !== 100}
                    style={{
                      background: totalWeight === 100 ? "linear-gradient(135deg, #0066FF, #00A3E0)" : "rgba(255,255,255,0.1)",
                      border: "none",
                      color: totalWeight === 100 ? "white" : "rgba(255,255,255,0.4)",
                      borderRadius: 30,
                      padding: "10px 24px",
                      fontSize: 14,
                      fontWeight: 700,
                      cursor: totalWeight === 100 ? "pointer" : "not-allowed",
                    }}
                  >
                    Submit Counter Terms
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

      </div>
      <Footer />
    </main>
  );
}

