"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Search, Sun, Moon, ChevronDown, Menu, X, Bell, Shield, CheckCircle, AlertTriangle, FileText, Calendar, LogOut, User } from "lucide-react";
import { getCurrentUser, signOutUser, UserProfile } from "@/lib/supabase";

export default function Navbar() {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(3);

  useEffect(() => {
    setCurrentUser(getCurrentUser());
    const onAuth = () => setCurrentUser(getCurrentUser());
    window.addEventListener("pactpal_auth_change", onAuth);
    window.addEventListener("storage", onAuth);
    return () => {
      window.removeEventListener("pactpal_auth_change", onAuth);
      window.removeEventListener("storage", onAuth);
    };
  }, []);

  const notifications = [
    {
      id: "notif_01",
      icon: <CheckCircle size={15} color="#34D399" />,
      title: "Settlement Disbursed & Receipt Sealed",
      desc: "Contract pct_settled_04 concluded with 80% payout. SHA-256 receipt generated.",
      href: "/contracts/pct_settled_04/receipt",
      time: "10m ago",
    },
    {
      id: "notif_02",
      icon: <AlertTriangle size={15} color="#FBBF24" />,
      title: "Dispute Mediation Active",
      desc: "AST scan flagged Feature 2 on pct_099e77. Review checklist & arbitration chat.",
      href: "/contracts/pct_099e77/dispute",
      time: "1h ago",
    },
    {
      id: "notif_03",
      icon: <Calendar size={15} color="#60A5FA" />,
      title: "Scheduler Timeline Updated",
      desc: "5 multi-contract assignments updated across buyer and seller schedules.",
      href: "/schedule",
      time: "2h ago",
    },
  ];

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav
      aria-label="Main navigation"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        padding: "0 32px",
        height: "64px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: scrolled
          ? "rgba(7, 11, 22, 0.85)"
          : "rgba(7, 11, 22, 0.4)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: scrolled
          ? "1px solid rgba(255,255,255,0.08)"
          : "1px solid transparent",
        transition: "all 0.3s ease",
      }}
    >
      {/* Logo */}
      <Link href="/" style={{ display: "flex", alignItems: "center", gap: "10px", textDecoration: "none" }}>
        <div
          style={{
            width: 36,
            height: 36,
            background: "linear-gradient(135deg, #0066FF, #7A5CFF)",
            borderRadius: "10px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 18,
            boxShadow: "0 0 20px rgba(0,102,255,0.4)",
          }}
          aria-hidden
        >
          ⚖
        </div>
        <span style={{ fontWeight: 800, fontSize: 20, color: "white", letterSpacing: "-0.5px" }}>
          PactPal
        </span>
      </Link>

      {/* Desktop nav links */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "32px",
          fontSize: 15,
          fontWeight: 500,
          color: "var(--color-text-secondary)",
        }}
        className="hidden-mobile"
      >
        {/* Hire Dropdown */}
        <div 
          style={{ position: "relative" }}
          onMouseEnter={() => setActiveDropdown("hire")}
          onMouseLeave={() => setActiveDropdown(null)}
        >
          <Link
            href="/hire"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              color: activeDropdown === "hire" ? "white" : "var(--color-text-secondary)",
              fontSize: 15,
              fontWeight: 500,
              textDecoration: "none",
              padding: "12px 0",
              transition: "color 0.2s",
            }}
          >
            Hire <ChevronDown size={14} />
          </Link>

          {activeDropdown === "hire" && (
            <div
              className="glass-card"
              style={{
                position: "absolute",
                top: "100%",
                left: -12,
                minWidth: 260,
                padding: "10px",
                background: "rgba(12, 18, 34, 0.98)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 14,
                boxShadow: "0 20px 40px rgba(0,0,0,0.6)",
                display: "flex",
                flexDirection: "column",
                gap: 4,
                zIndex: 110,
              }}
            >
              <Link
                href="/hire/create"
                onClick={() => setActiveDropdown(null)}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  textDecoration: "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                  transition: "background 0.2s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0,102,255,0.12)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div style={{ fontWeight: 700, fontSize: 14, color: "white", display: "flex", justifyContent: "space-between" }}>
                  Create Contract <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "rgba(0,102,255,0.2)", color: "#60A5FA" }}>Wizard</span>
                </div>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Set up milestones, acceptance tests &amp; weights</div>
              </Link>

              <Link
                href="/dashboard/hirer"
                onClick={() => setActiveDropdown(null)}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  textDecoration: "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                  transition: "background 0.2s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0,102,255,0.12)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div style={{ fontWeight: 700, fontSize: 14, color: "white", display: "flex", justifyContent: "space-between" }}>
                  Hirer Dashboard <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "rgba(76,175,80,0.15)", color: "var(--color-success)" }}>Active</span>
                </div>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>View escrow balance &amp; active contracts</div>
              </Link>

              <Link
                href="/hire"
                onClick={() => setActiveDropdown(null)}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  textDecoration: "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                  transition: "background 0.2s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div style={{ fontWeight: 600, fontSize: 13, color: "var(--color-text-secondary)" }}>Hirer Overview</div>
                <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>How hiring &amp; escrow work on PactPal</div>
              </Link>
            </div>
          )}
        </div>

        {/* Find Work Dropdown */}
        <div 
          style={{ position: "relative" }}
          onMouseEnter={() => setActiveDropdown("work")}
          onMouseLeave={() => setActiveDropdown(null)}
        >
          <Link
            href="/work"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              color: activeDropdown === "work" ? "white" : "var(--color-text-secondary)",
              fontSize: 15,
              fontWeight: 500,
              textDecoration: "none",
              padding: "12px 0",
              transition: "color 0.2s",
            }}
          >
            Find Work <ChevronDown size={14} />
          </Link>

          {activeDropdown === "work" && (
            <div
              className="glass-card"
              style={{
                position: "absolute",
                top: "100%",
                left: -12,
                minWidth: 260,
                padding: "10px",
                background: "rgba(12, 18, 34, 0.98)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 14,
                boxShadow: "0 20px 40px rgba(0,0,0,0.6)",
                display: "flex",
                flexDirection: "column",
                gap: 4,
                zIndex: 110,
              }}
            >
              <Link
                href="/dashboard/freelancer"
                onClick={() => setActiveDropdown(null)}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  textDecoration: "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                  transition: "background 0.2s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,152,0,0.12)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div style={{ fontWeight: 700, fontSize: 14, color: "white", display: "flex", justifyContent: "space-between" }}>
                  Freelancer Dashboard <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "rgba(255,152,0,0.2)", color: "#FF9800" }}>Earnings</span>
                </div>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>View assigned contracts &amp; next payout</div>
              </Link>

              <Link
                href="/work"
                onClick={() => setActiveDropdown(null)}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  textDecoration: "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                  transition: "background 0.2s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div style={{ fontWeight: 600, fontSize: 13, color: "var(--color-text-secondary)" }}>Browse Escrow Jobs</div>
                <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>Explore pre-funded freelancer listings</div>
              </Link>
            </div>
          )}
        </div>

        <Link
          href="/referee"
          style={{
            color: "var(--color-text-secondary)",
            fontSize: 15,
            fontWeight: 500,
            textDecoration: "none",
            padding: "4px 0",
            transition: "color 0.2s",
          }}
          onMouseEnter={(e) => ((e.currentTarget.style.color = "white"))}
          onMouseLeave={(e) => ((e.currentTarget.style.color = "var(--color-text-secondary)"))}
        >
          How the Referee Works
        </Link>

        <Link
          href="/pricing"
          style={{
            color: "var(--color-text-secondary)",
            fontSize: 15,
            fontWeight: 500,
            textDecoration: "none",
            padding: "4px 0",
            transition: "color 0.2s",
          }}
          onMouseEnter={(e) => ((e.currentTarget.style.color = "white"))}
          onMouseLeave={(e) => ((e.currentTarget.style.color = "var(--color-text-secondary)"))}
        >
          Pricing
        </Link>

        {/* Schedule Multi-Contract View (C57) */}
        <Link
          href="/schedule"
          style={{
            color: "var(--color-text-secondary)",
            fontSize: 15,
            fontWeight: 500,
            textDecoration: "none",
            padding: "4px 0",
            display: "flex",
            alignItems: "center",
            gap: 5,
            transition: "color 0.2s",
          }}
          onMouseEnter={(e) => ((e.currentTarget.style.color = "white"))}
          onMouseLeave={(e) => ((e.currentTarget.style.color = "var(--color-text-secondary)"))}
        >
          <Calendar size={14} color="#00A3E0" />
          Schedule
        </Link>
      </div>

      {/* Right side */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", position: "relative" }}>
        {/* C55: Notification Center Bell */}
        <div style={{ position: "relative" }}>
          <button
            onClick={() => {
              setNotificationsOpen(!notificationsOpen);
              setUnreadCount(0);
            }}
            style={{
              width: 38,
              height: 38,
              borderRadius: "10px",
              background: notificationsOpen ? "rgba(0,102,255,0.2)" : "rgba(255,255,255,0.05)",
              border: notificationsOpen ? "1px solid #0066FF" : "1px solid rgba(255,255,255,0.08)",
              color: "white",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              position: "relative",
              transition: "all 0.2s ease",
            }}
            title="Notifications (C55)"
            aria-label="View notifications"
          >
            <Bell size={17} color={notificationsOpen ? "#60A5FA" : "var(--color-text-secondary)"} />
            {unreadCount > 0 && (
              <span
                style={{
                  position: "absolute",
                  top: -2,
                  right: -2,
                  width: 17,
                  height: 17,
                  borderRadius: "50%",
                  background: "#EF4444",
                  color: "white",
                  fontSize: 10,
                  fontWeight: 800,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  border: "2px solid #070B16",
                }}
              >
                {unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown Window */}
          {notificationsOpen && (
            <div
              className="glass-card"
              style={{
                position: "absolute",
                top: "calc(100% + 10px)",
                right: 0,
                width: 340,
                background: "rgba(12, 18, 34, 0.98)",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 16,
                boxShadow: "0 20px 50px rgba(0,0,0,0.6)",
                padding: "16px",
                zIndex: 150,
                display: "flex",
                flexDirection: "column",
                gap: 10,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 10, borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                <strong style={{ fontSize: 13, color: "white" }}>Activity Notifications</strong>
                <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>Live Escrow Webhooks</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 280, overflowY: "auto" }}>
                {notifications.map((n) => (
                  <Link
                    key={n.id}
                    href={n.href}
                    onClick={() => setNotificationsOpen(false)}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 10,
                      padding: "10px",
                      borderRadius: 10,
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.05)",
                      textDecoration: "none",
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "rgba(0,102,255,0.1)";
                      e.currentTarget.style.borderColor = "rgba(0,102,255,0.3)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.05)";
                    }}
                  >
                    <div style={{ marginTop: 2 }}>{n.icon}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "white" }}>{n.title}</div>
                      <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 2 }}>{n.desc}</div>
                      <div style={{ fontSize: 10, color: "var(--color-text-muted)", marginTop: 4 }}>{n.time}</div>
                    </div>
                  </Link>
                ))}
              </div>

              <Link
                href="/dashboard/hirer"
                onClick={() => setNotificationsOpen(false)}
                style={{
                  fontSize: 11,
                  color: "#60A5FA",
                  textAlign: "center",
                  paddingTop: 8,
                  borderTop: "1px solid rgba(255,255,255,0.06)",
                  textDecoration: "none",
                  fontWeight: 600,
                }}
              >
                View All Dashboard Activities →
              </Link>
            </div>
          )}
        </div>

        {/* Search */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "10px",
            padding: "8px 14px",
            color: "var(--color-text-muted)",
            fontSize: 14,
            cursor: "pointer",
            transition: "all 0.2s",
            minWidth: 180,
          }}
          className="search-bar"
          role="search"
          aria-label="Search contracts"
        >
          <Search size={14} />
          <span>Search…</span>
        </div>

        {currentUser ? (
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Link
              href={currentUser.role === "freelancer" ? "/dashboard/freelancer" : "/dashboard/hirer"}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.14)",
                borderRadius: 20,
                padding: "6px 14px",
                color: "white",
                textDecoration: "none",
                fontSize: 13,
                fontWeight: 600,
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(0,102,255,0.4)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.14)")}
            >
              <div
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  background: currentUser.role === "freelancer" 
                    ? "linear-gradient(135deg, #FF9800, #F57C00)" 
                    : "linear-gradient(135deg, #0066FF, #00A3E0)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 11,
                  fontWeight: 800,
                  color: "white",
                }}
              >
                {currentUser.name ? currentUser.name.charAt(0).toUpperCase() : "U"}
              </div>
              <span>{currentUser.name ? currentUser.name.split(" ")[0] : "Account"}</span>
            </Link>

            <button
              onClick={() => {
                signOutUser();
                window.location.href = "/";
              }}
              style={{
                background: "none",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: "10px",
                color: "var(--color-text-secondary)",
                padding: "8px 12px",
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
                transition: "all 0.2s",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
              aria-label="Log out"
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(239,68,68,0.4)";
                e.currentTarget.style.color = "#F87171";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)";
                e.currentTarget.style.color = "var(--color-text-secondary)";
              }}
            >
              <LogOut size={13} />
              <span>Log out</span>
            </button>
          </div>
        ) : (
          <>
            <Link
              href="/login"
              style={{
                background: "none",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: "10px",
                color: "var(--color-text-secondary)",
                padding: "8px 18px",
                fontSize: 14,
                fontWeight: 500,
                cursor: "pointer",
                transition: "all 0.2s",
                textDecoration: "none",
                display: "inline-block",
              }}
              aria-label="Log in"
              onMouseEnter={(e) => {
                (e.currentTarget.style.borderColor = "rgba(255,255,255,0.3)");
                (e.currentTarget.style.color = "white");
              }}
              onMouseLeave={(e) => {
                (e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)");
                (e.currentTarget.style.color = "var(--color-text-secondary)");
              }}
            >
              Log in
            </Link>

            <Link
              href="/signup"
              className="btn-gradient"
              style={{ padding: "9px 22px", fontSize: 14, textDecoration: "none" }}
              aria-label="Sign up for PactPal"
            >
              Sign up →
            </Link>
          </>
        )}

        {/* Mobile menu toggle */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          style={{
            background: "none",
            border: "none",
            color: "white",
            cursor: "pointer",
            display: "none",
          }}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          className="mobile-menu-btn"
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div
          style={{
            position: "absolute",
            top: "64px",
            left: 0,
            right: 0,
            background: "rgba(12, 18, 34, 0.98)",
            backdropFilter: "blur(20px)",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            padding: "16px 24px 24px",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          {[
            { label: "Hire", href: "/hire" },
            { label: "Find Work", href: "/work" },
            { label: "How the Referee Works", href: "/referee" },
            { label: "Pricing", href: "/pricing" },
            { label: "Multi-Contract Schedule", href: "/schedule" },
            { label: "Admin Console", href: "/admin" },
          ].map((item) => (
            <Link
              key={item.label}
              href={item.href}
              onClick={() => setMenuOpen(false)}
              style={{
                color: "var(--color-text-secondary)",
                fontSize: 16,
                fontWeight: 500,
                textDecoration: "none",
                padding: "8px 0",
                display: "block",
                borderBottom: "1px solid rgba(255,255,255,0.05)",
              }}
            >
              {item.label}
            </Link>
          ))}
          <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
            {currentUser ? (
              <>
                <Link
                  href={currentUser.role === "freelancer" ? "/dashboard/freelancer" : "/dashboard/hirer"}
                  onClick={() => setMenuOpen(false)}
                  style={{
                    flex: 1,
                    background: "rgba(0,102,255,0.15)",
                    border: "1px solid rgba(0,102,255,0.3)",
                    borderRadius: "10px",
                    color: "white",
                    padding: "10px",
                    textAlign: "center",
                    textDecoration: "none",
                    fontSize: 14,
                    fontWeight: 700,
                  }}
                >
                  Dashboard ({currentUser.name.split(" ")[0]})
                </Link>
                <button
                  onClick={() => {
                    signOutUser();
                    setMenuOpen(false);
                    window.location.href = "/";
                  }}
                  style={{
                    flex: 1,
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: "10px",
                    color: "var(--color-text-secondary)",
                    padding: "10px",
                    cursor: "pointer",
                    fontSize: 14,
                  }}
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  onClick={() => setMenuOpen(false)}
                  style={{
                    flex: 1,
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: "10px",
                    color: "white",
                    padding: "10px",
                    textAlign: "center",
                    textDecoration: "none",
                    fontSize: 14,
                  }}
                >
                  Log in
                </Link>
                <Link
                  href="/signup"
                  onClick={() => setMenuOpen(false)}
                  className="btn-gradient"
                  style={{ flex: 1, padding: "10px", fontSize: 14, textDecoration: "none", textAlign: "center" }}
                >
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      )}

      <style>{`
        @media (max-width: 768px) {
          .hidden-mobile { display: none !important; }
          .search-bar { display: none !important; }
          .mobile-menu-btn { display: flex !important; }
        }
      `}</style>
    </nav>
  );
}

