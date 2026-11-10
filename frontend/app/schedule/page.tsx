"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import {
  Calendar,
  Clock,
  Users,
  Shield,
  Layers,
  CheckCircle,
  AlertCircle,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Filter,
  DollarSign
} from "lucide-react";
import { mockApi, Contract, CONTRACT_STATES_META, ContractStatus } from "@/lib/mockApi";

interface ResourceSchedule {
  id: string;
  name: string;
  role: "SELLER" | "BUYER";
  avatar: string;
  specialty: string;
  activeContractsCount: number;
  totalVolume: number;
  contracts: Array<{
    contract: Contract;
    startDayPct: number;
    widthPct: number;
    dateLabel: string;
    holdExpiryPct?: number;
    deadlinePct?: number;
  }>;
}

export default function SchedulePage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [groupBy, setGroupBy] = useState<"SELLER" | "BUYER">("SELLER");
  const [zoomLevel, setZoomLevel] = useState<"Week" | "Month">("Week");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  useEffect(() => {
    setContracts(mockApi.getContracts());
  }, []);

  // Compute contract time schedules relative to timeline
  const getContractSchedule = (c: Contract) => {
    switch (c.id) {
      case "pct_settled_04":
        return { startDayPct: 2, widthPct: 22, dateLabel: "Oct 28 - Nov 08", holdExpiryPct: 28, deadlinePct: 24 };
      case "pct_099e77":
        return { startDayPct: 12, widthPct: 34, dateLabel: "Nov 01 - Nov 15", holdExpiryPct: 76, deadlinePct: 46 };
      case "pct_review_02":
        return { startDayPct: 28, widthPct: 48, dateLabel: "Nov 09 - Dec 09", holdExpiryPct: 90, deadlinePct: 76 };
      case "pct_draft_01":
        return { startDayPct: 35, widthPct: 40, dateLabel: "Nov 11 - Dec 02", holdExpiryPct: 88, deadlinePct: 75 };
      case "pct_signed_03":
        return { startDayPct: 32, widthPct: 46, dateLabel: "Nov 10 - Dec 05", holdExpiryPct: 86, deadlinePct: 78 };
      default:
        return { startDayPct: 20, widthPct: 30, dateLabel: "Nov 05 - Nov 20", holdExpiryPct: 80, deadlinePct: 50 };
    }
  };

  // Group by Sellers (Freelancers)
  const sellersMap: Record<string, ResourceSchedule> = {
    "Alex Mercer": {
      id: "res_seller_01",
      name: "Alex Mercer",
      role: "SELLER",
      avatar: "🧑‍💻",
      specialty: "Full-Stack TypeScript & Web3 Escrow",
      activeContractsCount: 3,
      totalVolume: 7800,
      contracts: [],
    },
    "Elena Rostova": {
      id: "res_seller_02",
      name: "Elena Rostova",
      role: "SELLER",
      avatar: "👩‍💻",
      specialty: "AI Multi-Agent Workflows & Python",
      activeContractsCount: 1,
      totalVolume: 2400,
      contracts: [],
    },
    "Kenji Sato": {
      id: "res_seller_03",
      name: "Kenji Sato",
      role: "SELLER",
      avatar: "🧑‍💻",
      specialty: "Mobile Checkout & Apple Pay Systems",
      activeContractsCount: 1,
      totalVolume: 2100,
      contracts: [],
    },
  };

  // Group by Buyers (Clients)
  const buyersMap: Record<string, ResourceSchedule> = {
    "Priya Sharma": {
      id: "res_buyer_01",
      name: "Priya Sharma",
      role: "BUYER",
      avatar: "👔",
      specialty: "Fintech VC & Storefront Operations",
      activeContractsCount: 3,
      totalVolume: 5400,
      contracts: [],
    },
    "Marcus Vance": {
      id: "res_buyer_02",
      name: "Marcus Vance",
      role: "BUYER",
      avatar: "👔",
      specialty: "ScaleUp Analytics Executive",
      activeContractsCount: 1,
      totalVolume: 2400,
      contracts: [],
    },
    "David Chen": {
      id: "res_buyer_03",
      name: "David Chen",
      role: "BUYER",
      avatar: "👔",
      specialty: "Crypto Ventures Managing Partner",
      activeContractsCount: 1,
      totalVolume: 4500,
      contracts: [],
    },
  };

  // Populate contracts into schedules
  contracts.forEach((c) => {
    if (statusFilter !== "ALL" && c.status !== statusFilter) return;

    const sched = getContractSchedule(c);

    // Seller
    const sellerName = c.seller_name || "Alex Mercer";
    if (sellersMap[sellerName]) {
      sellersMap[sellerName].contracts.push({ contract: c, ...sched });
    }

    // Buyer
    const buyerName = c.buyer_name || "Priya Sharma";
    if (buyersMap[buyerName]) {
      buyersMap[buyerName].contracts.push({ contract: c, ...sched });
    }
  });

  const activeResources = Object.values(groupBy === "SELLER" ? sellersMap : buyersMap);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "SETTLED":
        return "#4CAF50";
      case "FUNDED":
      case "DECISION":
        return "#FF9800";
      case "IN_PROGRESS":
      case "SUBMITTED":
      case "VERIFYING":
        return "#0066FF";
      case "SIGNED":
      case "REVIEW":
        return "#7A5CFF";
      case "DISPUTE":
        return "#EF4444";
      default:
        return "#7C89A8";
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        color: "white",
        fontFamily: "Inter, sans-serif",
      }}
    >
      <Navbar />

      <main style={{ maxWidth: 1320, margin: "0 auto", padding: "100px 24px 80px" }}>
        {/* Page Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32, flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 800,
                  letterSpacing: "0.08em",
                  padding: "3px 10px",
                  borderRadius: 999,
                  background: "rgba(122,92,255,0.18)",
                  border: "1px solid rgba(122,92,255,0.35)",
                  color: "#C084FC",
                  textTransform: "uppercase",
                }}
              >
                BRYNTUM SCHEDULER &bull; C57
              </span>
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                Multi-Contract Timeline Visualization
              </span>
            </div>
            <h1 style={{ fontSize: 32, fontWeight: 900, margin: "0 0 6px 0", letterSpacing: "-0.025em" }}>
              Buyer &amp; Seller Schedules Across Contracts
            </h1>
            <p style={{ color: "var(--color-text-secondary)", fontSize: 14, margin: 0 }}>
              Track parallel milestones, active PayPal hold expiration dates, and delivery deadlines across all parties.
            </p>
          </div>

          {/* Controls: Group By & Zoom */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            {/* Group By Toggle */}
            <div
              style={{
                display: "inline-flex",
                borderRadius: 12,
                background: "rgba(255,255,255,0.05)",
                padding: 4,
                border: "1px solid rgba(255,255,255,0.1)",
              }}
            >
              <button
                onClick={() => setGroupBy("SELLER")}
                style={{
                  padding: "8px 16px",
                  borderRadius: 9,
                  fontSize: 12,
                  fontWeight: 700,
                  border: "none",
                  cursor: "pointer",
                  background: groupBy === "SELLER" ? "#0066FF" : "transparent",
                  color: groupBy === "SELLER" ? "white" : "var(--color-text-muted)",
                  transition: "all 0.15s ease",
                }}
              >
                🧑‍💻 Freelancers (Sellers)
              </button>
              <button
                onClick={() => setGroupBy("BUYER")}
                style={{
                  padding: "8px 16px",
                  borderRadius: 9,
                  fontSize: 12,
                  fontWeight: 700,
                  border: "none",
                  cursor: "pointer",
                  background: groupBy === "BUYER" ? "#0066FF" : "transparent",
                  color: groupBy === "BUYER" ? "white" : "var(--color-text-muted)",
                  transition: "all 0.15s ease",
                }}
              >
                👔 Clients (Buyers)
              </button>
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 10,
                color: "white",
                fontSize: 12,
                fontWeight: 600,
                padding: "8px 14px",
                outline: "none",
                cursor: "pointer",
              }}
            >
              <option value="ALL" style={{ background: "#0F172A" }}>All Contract States</option>
              <option value="FUNDED" style={{ background: "#0F172A" }}>Funded (Active Hold)</option>
              <option value="IN_PROGRESS" style={{ background: "#0F172A" }}>In Progress</option>
              <option value="VERIFYING" style={{ background: "#0F172A" }}>Verifying</option>
              <option value="SETTLED" style={{ background: "#0F172A" }}>Settled</option>
              <option value="DISPUTE" style={{ background: "#0F172A" }}>Dispute</option>
            </select>
          </div>
        </div>

        {/* Bryntum Scheduler Container */}
        <div
          id="bryntum-scheduler"
          style={{
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 24,
            overflow: "hidden",
            boxShadow: "0 0 60px rgba(0,102,255,0.08)",
          }}
          role="region"
          aria-label="Bryntum Scheduler Multi-Contract View"
        >
          {/* Top Timeline Header Columns */}
          <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", borderBottom: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.02)" }}>
            <div style={{ padding: "14px 20px", fontWeight: 700, fontSize: 12, color: "var(--color-text-muted)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Resource ({groupBy === "SELLER" ? "Freelancers" : "Hirers"})
            </div>
            
            {/* Calendar Weeks header */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)", letterSpacing: "0.06em" }}>
              {["Oct 27 - Nov 02", "Nov 03 - Nov 09", "Nov 10 - Nov 16", "Nov 17 - Nov 23", "Nov 24 - Nov 30", "Dec 01 - Dec 07"].map((week, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "14px 12px",
                    borderLeft: "1px solid rgba(255,255,255,0.06)",
                    textAlign: "center",
                  }}
                >
                  {week}
                </div>
              ))}
            </div>
          </div>

          {/* Resource Rows */}
          <div style={{ display: "flex", flexDirection: "column" }}>
            {activeResources.map((res) => (
              <div
                key={res.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "300px 1fr",
                  borderBottom: "1px solid rgba(255,255,255,0.06)",
                  minHeight: 110,
                }}
              >
                {/* Left Resource Info Card */}
                <div
                  style={{
                    padding: "20px",
                    borderRight: "1px solid rgba(255,255,255,0.08)",
                    background: "rgba(255,255,255,0.01)",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <div
                      style={{
                        width: 34,
                        height: 34,
                        borderRadius: 10,
                        background: "rgba(255,255,255,0.06)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 18,
                      }}
                    >
                      {res.avatar}
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14, color: "white" }}>{res.name}</div>
                      <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{res.specialty}</div>
                    </div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--color-text-muted)", marginTop: 6, paddingTop: 6, borderTop: "1px solid rgba(255,255,255,0.04)" }}>
                    <span>{res.contracts.length} active assignments</span>
                    <span style={{ color: "#34D399", fontWeight: 600 }}>${res.totalVolume.toLocaleString()} USD</span>
                  </div>
                </div>

                {/* Right Calendar Row with Contract Time Blocks */}
                <div style={{ position: "relative", minHeight: 110, display: "flex", flexDirection: "column", justifyContent: "center", padding: "12px 0" }}>
                  {/* Background vertical dashed week guide lines */}
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      display: "grid",
                      gridTemplateColumns: "repeat(6, 1fr)",
                      pointerEvents: "none",
                    }}
                  >
                    {[0, 1, 2, 3, 4, 5].map((col) => (
                      <div
                        key={col}
                        style={{
                          borderLeft: "1px dashed rgba(255,255,255,0.03)",
                          height: "100%",
                        }}
                      />
                    ))}
                  </div>

                  {/* Vertical "TODAY" Line across scheduler */}
                  <div
                    style={{
                      position: "absolute",
                      top: 0,
                      bottom: 0,
                      left: "38%",
                      width: 2,
                      background: "#0066FF",
                      boxShadow: "0 0 10px #0066FF",
                      zIndex: 8,
                      pointerEvents: "none",
                    }}
                  />

                  {/* Contract Blocks in this Resource Row */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 10, position: "relative", zIndex: 4, padding: "0 8px" }}>
                    {res.contracts.length === 0 ? (
                      <div style={{ padding: "16px 24px", color: "var(--color-text-muted)", fontSize: 12 }}>
                        No contracts in this view.
                      </div>
                    ) : (
                      res.contracts.map((item, idx) => {
                        const statusColor = getStatusColor(item.contract.status);
                        return (
                          <div
                            key={item.contract.id || idx}
                            style={{
                              position: "relative",
                              height: 38,
                              display: "flex",
                              alignItems: "center",
                            }}
                          >
                            {/* The Scheduled Contract Block */}
                            <Link
                              href={`/contracts/${item.contract.id}`}
                              style={{
                                position: "absolute",
                                left: `${item.startDayPct}%`,
                                width: `${item.widthPct}%`,
                                height: 36,
                                borderRadius: 10,
                                background: `linear-gradient(90deg, ${statusColor}22 0%, ${statusColor}44 100%)`,
                                border: `1px solid ${statusColor}`,
                                boxShadow: `0 0 16px ${statusColor}33`,
                                color: "white",
                                padding: "0 12px",
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                                textDecoration: "none",
                                overflow: "hidden",
                                whiteSpace: "nowrap",
                                transition: "all 0.15s ease",
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.transform = "scaleY(1.08)";
                                e.currentTarget.style.zIndex = "10";
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.transform = "none";
                                e.currentTarget.style.zIndex = "4";
                              }}
                              title={`${item.contract.title} (${item.dateLabel}) · State: ${item.contract.status} · $${item.contract.total_amount}`}
                            >
                              <div
                                style={{
                                  width: 8,
                                  height: 8,
                                  borderRadius: "50%",
                                  background: statusColor,
                                  flexShrink: 0,
                                }}
                              />
                              <strong style={{ fontSize: 12, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis" }}>
                                {item.contract.title}
                              </strong>
                              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.75)", marginLeft: "auto", fontFamily: "JetBrains Mono, monospace" }}>
                                ${item.contract.total_amount}
                              </span>
                            </Link>

                            {/* 29-Day Hold Expiry Diamond Milestone */}
                            {item.holdExpiryPct && (
                              <div
                                style={{
                                  position: "absolute",
                                  left: `${item.holdExpiryPct}%`,
                                  width: 14,
                                  height: 14,
                                  background: "#FF9800",
                                  transform: "rotate(45deg)",
                                  borderRadius: 2,
                                  boxShadow: "0 0 12px rgba(255,152,0,0.8)",
                                  zIndex: 6,
                                }}
                                title="29-Day PayPal Escrow Authorization Expiry Point"
                              />
                            )}

                            {/* Delivery Deadline Diamond Milestone */}
                            {item.deadlinePct && (
                              <div
                                style={{
                                  position: "absolute",
                                  left: `${item.deadlinePct}%`,
                                  width: 14,
                                  height: 14,
                                  background: "#A855F7",
                                  transform: "rotate(45deg)",
                                  borderRadius: 2,
                                  boxShadow: "0 0 12px rgba(168,85,247,0.8)",
                                  zIndex: 6,
                                }}
                                title="Final Deliverable Submission Deadline"
                              />
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Scheduler Legend & Footer */}
          <div
            style={{
              padding: "16px 24px",
              borderTop: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255,255,255,0.02)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 12,
              fontSize: 12,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
              <span style={{ fontWeight: 700, color: "var(--color-text-muted)" }}>Schedule Legend:</span>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 10, height: 10, borderRadius: 3, background: "#4CAF50" }} />
                <span>Settled</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 10, height: 10, borderRadius: 3, background: "#0066FF" }} />
                <span>In Progress / Verifying</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 10, height: 10, borderRadius: 3, background: "#FF9800" }} />
                <span>Funded (Active Hold)</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 10, height: 10, borderRadius: 3, background: "#7A5CFF" }} />
                <span>Signing / Review</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ color: "#FF9800", fontWeight: 800 }}>◆</span>
                <span style={{ color: "#FBBF24" }}>29-Day Hold Expiry</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ color: "#A855F7", fontWeight: 800 }}>◆</span>
                <span style={{ color: "#C084FC" }}>Delivery Deadline</span>
              </div>
            </div>

            <span style={{ color: "var(--color-text-muted)", fontSize: 11 }}>
              Click any schedule bar to inspect contract details.
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}

