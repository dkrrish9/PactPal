"use client";

import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ArrowRight, Code } from "lucide-react";
import Link from "next/link";
import { getCurrentUser, UserProfile, toUUID } from "@/lib/supabase";
import { mockApi, Contract } from "@/lib/mockApi";
import { backendClient } from "@/lib/backendClient";

const perks = [
  { icon: "🔒", title: "Get paid before you start", desc: "Money is locked in escrow the moment you accept a contract. No more chasing invoices." },
  { icon: "", title: "Crystal-clear requirements", desc: "Every contract has weighted acceptance tests. You know exactly what 'done' looks like." },
  { icon: "", title: "Fair partial payouts", desc: "Built 3 of 4 features? Get paid for 3 of 4. No all-or-nothing drama." },
  { icon: "", title: "Proof-of-work receipt", desc: "Every job ends with a signed SHA-256 receipt you can share with any future client." },
];

const fallbackJobs = [
  { id: "mock_1", title: "Full-stack e-commerce build", budget: "$2,400", skills: ["Next.js", "Stripe", "PostgreSQL"], days: 30, bids: 4 },
  { id: "mock_2", title: "iOS fitness tracking app", budget: "$1,800", skills: ["Swift", "HealthKit", "Firebase"], days: 21, bids: 7 },
  { id: "mock_3", title: "AI chatbot integration", budget: "$900", skills: ["Python", "OpenAI", "FastAPI"], days: 10, bids: 2 },
  { id: "mock_4", title: "Brand identity design", budget: "$600", skills: ["Figma", "Illustrator"], days: 7, bids: 9 },
  { id: "mock_5", title: "Data scraping pipeline", budget: "$450", skills: ["Python", "Scrapy", "MongoDB"], days: 5, bids: 3 },
  { id: "mock_6", title: "Shopify store customization", budget: "$350", skills: ["Liquid", "JavaScript"], days: 4, bids: 6 },
];

function isUserBuyer(c: Contract, user: UserProfile | null): boolean {
  if (!user) return false;
  const userEmail = (user.email || "").trim().toLowerCase();
  const userName = (user.name || "").trim().toLowerCase();
  const userId = user.id || "";
  const userUuid = toUUID(userId);

  const buyerEmail = (c.buyer_email || "").trim().toLowerCase();
  const buyerName = (c.buyer_name || "").trim().toLowerCase();
  const buyerId = c.buyer_id || "";

  if (userId && (buyerId === userId || buyerId === userUuid)) return true;
  if (userEmail && buyerEmail && buyerEmail === userEmail) return true;
  if (userName && buyerName && (userName.includes(buyerName) || buyerName.includes(userName))) return true;
  return false;
}

function formatContract(contract: Contract) {
  const deadline = new Date(contract.deadline);
  const now = new Date();
  const days = Math.max(0, Math.ceil((deadline.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));
  return {
    id: contract.id,
    title: contract.title,
    budget: `$${contract.total_amount.toLocaleString()}`,
    days,
    bids: Math.floor(Math.random() * 10) + 1,
    skills: contract.features?.map((f) => f.title) ?? [],
  };
}

export default function WorkPage() {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loaded, setLoaded] = useState(false);

  const fetchWorkContracts = async () => {
    const user = getCurrentUser();
    setCurrentUser(user);

    try {
      const allContracts = await backendClient.getContracts();
      const available = allContracts.filter((c) => !isUserBuyer(c, user));
      setContracts(available);
    } catch (err) {
      console.error("Failed to load work contracts from Supabase:", err);
      const all = mockApi.getContracts();
      setContracts(all.filter((c) => !isUserBuyer(c, user)));
    } finally {
      setLoaded(true);
    }
  };

  useEffect(() => {
    fetchWorkContracts();

    const handleUpdate = () => fetchWorkContracts();
    window.addEventListener("pactpal_contract_created", handleUpdate);
    window.addEventListener("pactpal_contract_updated", handleUpdate);
    window.addEventListener("pactpal_auth_change", handleUpdate);

    return () => {
      window.removeEventListener("pactpal_contract_created", handleUpdate);
      window.removeEventListener("pactpal_contract_updated", handleUpdate);
      window.removeEventListener("pactpal_auth_change", handleUpdate);
    };
  }, []);

  const jobItems = loaded && contracts.length > 0 ? contracts.map(formatContract) : fallbackJobs;

  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />

      {/* Hero */}
      <section style={{ padding: "160px 24px 100px", maxWidth: 1280, margin: "0 auto", position: "relative" }}>
        <div
          style={{
            position: "absolute",
            top: "30%",
            right: "10%",
            width: 500,
            height: 500,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(255,152,0,0.12) 0%, transparent 70%)",
            filter: "blur(80px)",
            pointerEvents: "none",
          }}
          aria-hidden
        />
        <div style={{ maxWidth: 740 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "rgba(255,152,0,0.1)",
              border: "1px solid rgba(255,152,0,0.3)",
              borderRadius: 50,
              padding: "6px 16px",
              fontSize: 12,
              fontWeight: 700,
              color: "#FF9800",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: 32,
            }}
          >
            <Code size={12} aria-hidden /> For Freelancers
          </div>
          <h1
            style={{
              fontSize: "clamp(44px, 7vw, 88px)",
              fontWeight: 900,
              letterSpacing: "-0.03em",
              lineHeight: 1.05,
              color: "white",
              marginBottom: 24,
            }}
          >
            Money locked.<br />
            <span className="gradient-text-orange">Work verified.</span><br />
            You paid.
          </h1>
          <p
            style={{
              fontSize: 20,
              color: "var(--color-text-secondary)",
              lineHeight: 1.65,
              marginBottom: 48,
              maxWidth: 560,
            }}
          >
            No more ghosting. No more scope creep without pay. PactPal holds the client’s money before you write a single line. Build it, submit it, collect exactly what you earned.
          </p>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <Link
              href="#jobs"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "linear-gradient(135deg, #FF9800, #FF6B00)",
                color: "white",
                borderRadius: 50,
                padding: "16px 32px",
                fontSize: 16,
                fontWeight: 700,
                textDecoration: "none",
                boxShadow: "0 0 30px rgba(255,152,0,0.4)",
              }}
              aria-label="Browse open jobs"
            >
              Browse Jobs <ArrowRight size={18} aria-hidden />
            </Link>
            <Link
              href="/signup"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "white",
                borderRadius: 50,
                padding: "16px 32px",
                fontSize: 16,
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              Get Started
            </Link>
          </div>
        </div>
      </section>

      {/* Perks */}
      <section style={{ padding: "0 24px 100px", maxWidth: 1280, margin: "0 auto" }} aria-labelledby="perks-heading">
        <h2 id="perks-heading" style={{ fontSize: "clamp(28px, 3.5vw, 44px)", fontWeight: 900, color: "white", marginBottom: 40, textAlign: "center" }}>
          Why PactPal?
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 20 }} role="list">
          {perks.map((p, i) => (
            <div key={i} role="listitem" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 24, padding: "32px 28px" }}>
              <div style={{ fontSize: 36, marginBottom: 20, lineHeight: 1 }} aria-hidden>{p.icon}</div>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: "white", marginBottom: 10 }}>{p.title}</h3>
              <p style={{ fontSize: 14, color: "var(--color-text-secondary)", lineHeight: 1.65 }}>{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Job feed */}
      <section id="jobs" style={{ padding: "0 24px 120px", maxWidth: 1280, margin: "0 auto" }} aria-labelledby="jobs-heading">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32, flexWrap: "wrap", gap: 12 }}>
          <h2 id="jobs-heading" style={{ fontSize: "clamp(24px, 3vw, 36px)", fontWeight: 900, letterSpacing: "-0.02em", color: "white" }}>
            Open projects
          </h2>
          <div style={{ display: "flex", gap: 8 }}>
            {["All", "Design", "Dev", "AI", "Data"].map((f) => (
              <button
                key={f}
                style={{
                  background: f === "All" ? "rgba(255,152,0,0.15)" : "rgba(255,255,255,0.05)",
                  border: `1px solid ${f === "All" ? "rgba(255,152,0,0.4)" : "rgba(255,255,255,0.08)"}`,
                  borderRadius: 50,
                  color: f === "All" ? "#FF9800" : "var(--color-text-secondary)",
                  padding: "6px 16px",
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: "pointer",
                }}
                aria-label={`Filter: ${f}`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }} role="list" aria-label="Job listings">
          {jobItems.map((job, i) => {
            const contractHref = job.id.startsWith("pct_") ? `/contracts/${job.id}/review` : `/contracts/pct_099e77/review`;
            return (
              <Link
                key={job.id || i}
                href={contractHref}
                role="listitem"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.07)",
                  borderRadius: 16,
                  padding: "20px 24px",
                  textDecoration: "none",
                  transition: "all 0.25s ease",
                  flexWrap: "wrap",
                  gap: 16,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255,152,0,0.3)";
                  e.currentTarget.style.background = "rgba(255,152,0,0.04)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)";
                  e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                }}
                aria-label={`${job.title}, budget ${job.budget}`}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 16, color: "white", marginBottom: 8 }}>{job.title}</div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {job.skills.map((s) => (
                      <span
                        key={s}
                        style={{
                          background: "rgba(255,255,255,0.06)",
                          border: "1px solid rgba(255,255,255,0.08)",
                          borderRadius: 50,
                          padding: "2px 12px",
                          fontSize: 12,
                          color: "var(--color-text-muted)",
                        }}
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 24, alignItems: "center", flexShrink: 0 }}>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: "#FF9800", fontFamily: "JetBrains Mono, monospace" }}>
                      {job.budget}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{job.days}d · {job.bids} bids</div>
                  </div>
                  <div
                    style={{
                      background: "linear-gradient(135deg, #FF9800, #FF6B00)",
                      color: "white",
                      borderRadius: 10,
                      padding: "8px 16px",
                      fontSize: 13,
                      fontWeight: 700,
                    }}
                  >
                    View Project
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      <Footer />
    </main>
  );
}
