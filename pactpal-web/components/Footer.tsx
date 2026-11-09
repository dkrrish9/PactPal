"use client";

const footerCols = [
  {
    title: "Product",
    links: ["How it works", "Pricing", "Security", "API Docs", "Changelog"],
  },
  {
    title: "Hire",
    links: ["Website Design", "Mobile Apps", "AI & Automation", "Brand Design", "Post a Project"],
  },
  {
    title: "Find Work",
    links: ["Browse Jobs", "Freelancer Dashboard", "Skills Tests", "Reputation", "Withdraw Earnings"],
  },
  {
    title: "Company",
    links: ["About PactPal", "Blog", "Careers", "Press", "Contact"],
  },
  {
    title: "Legal",
    links: ["Terms of Service", "Privacy Policy", "Cookie Policy", "Escrow Agreement", "DMCA"],
  },
];

export default function Footer() {
  return (
    <footer
      style={{
        borderTop: "1px solid rgba(255,255,255,0.06)",
        padding: "80px 24px 40px",
        position: "relative",
        overflow: "hidden",
      }}
      aria-label="Site footer"
    >
      {/* Huge faded wordmark behind */}
      <div
        style={{
          position: "absolute",
          bottom: -40,
          left: "50%",
          transform: "translateX(-50%)",
          fontSize: "clamp(100px, 20vw, 220px)",
          fontWeight: 900,
          color: "rgba(255,255,255,0.025)",
          letterSpacing: "-0.04em",
          userSelect: "none",
          pointerEvents: "none",
          whiteSpace: "nowrap",
        }}
        aria-hidden
      >
        PactPal
      </div>

      <div style={{ maxWidth: 1280, margin: "0 auto", position: "relative", zIndex: 1 }}>
        {/* Top row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.5fr repeat(4, 1fr)",
            gap: "40px",
            marginBottom: "60px",
          }}
        >
          {/* Brand */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  background: "linear-gradient(135deg, #0066FF, #7A5CFF)",
                  borderRadius: "9px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 16,
                }}
                aria-hidden
              >
                ⚖
              </div>
              <span style={{ fontWeight: 800, fontSize: 18, color: "white" }}>PactPal</span>
            </div>
            <p
              style={{
                fontSize: 14,
                color: "var(--color-text-muted)",
                lineHeight: 1.65,
                maxWidth: 240,
                marginBottom: "24px",
              }}
            >
              The AI-refereed escrow marketplace. No more ghosting. No more
              chargebacks.
            </p>

            {/* Social icons */}
            <div style={{ display: "flex", gap: "10px" }}>
              {["𝕏", "in", "gh", "📧"].map((icon, i) => (
                <button
                  key={i}
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "10px",
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    color: "var(--color-text-muted)",
                    fontSize: 14,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "all 0.2s",
                  }}
                  aria-label={["Twitter/X", "LinkedIn", "GitHub", "Email"][i]}
                  onMouseEnter={(e) => {
                    (e.currentTarget.style.borderColor = "rgba(0,102,255,0.4)");
                    (e.currentTarget.style.color = "white");
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)");
                    (e.currentTarget.style.color = "var(--color-text-muted)");
                  }}
                >
                  {icon}
                </button>
              ))}
            </div>
          </div>

          {/* Link columns */}
          {footerCols.map((col) => (
            <nav key={col.title} aria-label={col.title}>
              <h3
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "white",
                  marginBottom: "16px",
                }}
              >
                {col.title}
              </h3>
              <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "10px" }}>
                {col.links.map((link) => (
                  <li key={link}>
                    <a
                      href="#"
                      style={{
                        fontSize: 14,
                        color: "var(--color-text-muted)",
                        textDecoration: "none",
                        transition: "color 0.2s",
                      }}
                      onMouseEnter={(e) => ((e.currentTarget.style.color = "white"))}
                      onMouseLeave={(e) =>
                        ((e.currentTarget.style.color = "var(--color-text-muted)"))
                      }
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        {/* Bottom bar */}
        <div
          style={{
            borderTop: "1px solid rgba(255,255,255,0.06)",
            paddingTop: "24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <p style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
            © 2026 PactPal. All rights reserved.
          </p>
          <p
            style={{
              fontSize: 12,
              color: "rgba(124,137,168,0.6)",
              maxWidth: 500,
              textAlign: "right",
            }}
          >
            Escrow demo environment. Production use requires licensed payment partners.
          </p>
        </div>
      </div>

      <style>{`
        @media (max-width: 1024px) {
          [style*="repeat(4, 1fr)"] {
            grid-template-columns: repeat(3, 1fr) !important;
          }
        }
        @media (max-width: 600px) {
          [style*="repeat(4, 1fr)"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </footer>
  );
}

