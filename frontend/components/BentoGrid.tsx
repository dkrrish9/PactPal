"use client";

const tiles = [
  {
    category: "Website Builds",
    headline: "Ship the site you sketched.",
    cta: "Post a project →",
    gradient: "linear-gradient(135deg, #0D1B4B 0%, #1a3a8a 50%, #0066FF 100%)",
    glow: "#0066FF",
    emoji: "🌐",
  },
  {
    category: "Mobile Apps",
    headline: "From napkin to App Store.",
    cta: "Post a project →",
    gradient: "linear-gradient(135deg, #2D1B00 0%, #7a3a00 50%, #FF6B00 100%)",
    glow: "#FF9800",
    emoji: "📱",
  },
  {
    category: "Brand & UI Design",
    headline: "Pixel-perfect or it doesn't pay.",
    cta: "Post a project →",
    gradient: "linear-gradient(135deg, #1A0030 0%, #4a0080 50%, #7A5CFF 100%)",
    glow: "#7A5CFF",
    emoji: "🎨",
  },
  {
    category: "AI & Automation",
    headline: "Let the bots be accountable.",
    cta: "Post a project →",
    gradient: "linear-gradient(135deg, #001A30 0%, #004a70 50%, #00A3E0 100%)",
    glow: "#00A3E0",
    emoji: "🤖",
  },
  {
    category: "Game Dev",
    headline: "Your idea. Their thumbs.",
    cta: "Post a project →",
    gradient: "linear-gradient(135deg, #0A0020 0%, #2a0060 50%, #6A0FCC 100%)",
    glow: "#9B59B6",
    emoji: "🎮",
  },
  {
    category: "Data & Scraping",
    headline: "Clean data or no invoice.",
    cta: "Post a project →",
    gradient: "linear-gradient(135deg, #001A10 0%, #004a20 50%, #4CAF50 100%)",
    glow: "#4CAF50",
    emoji: "📊",
  },
];

export default function BentoGrid() {
  return (
    <section
      style={{ padding: "120px 24px", maxWidth: 1280, margin: "0 auto" }}
      aria-labelledby="bento-heading"
    >
      {/* Header */}
      <div style={{ marginBottom: "56px" }}>
        <h2
          id="bento-heading"
          style={{
            fontSize: "clamp(36px, 5vw, 60px)",
            fontWeight: 900,
            letterSpacing: "-0.025em",
            color: "white",
            lineHeight: 1.1,
          }}
        >
          Big idea?{" "}
          <span className="gradient-text">Make a pact.</span>
        </h2>
        <p
          style={{
            marginTop: "12px",
            fontSize: 18,
            color: "var(--color-text-secondary)",
          }}
        >
          Start with a category. End with work that&apos;s actually done.
        </p>
      </div>

      {/* Bento grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "20px",
        }}
        role="list"
      >
        {tiles.map((tile, i) => (
          <BentoTile key={i} tile={tile} />
        ))}
      </div>

      <style>{`
        @media (max-width: 900px) {
          [role="list"][style*="repeat(3, 1fr)"] {
            grid-template-columns: repeat(2, 1fr) !important;
          }
        }
        @media (max-width: 600px) {
          [role="list"][style*="repeat(3, 1fr)"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </section>
  );
}

function BentoTile({ tile }: { tile: (typeof tiles)[0] }) {
  return (
    <article
      role="listitem"
      style={{
        background: tile.gradient,
        borderRadius: "24px",
        padding: "40px 32px",
        position: "relative",
        overflow: "hidden",
        cursor: "pointer",
        transition: "all 0.3s ease",
        border: "1px solid rgba(255,255,255,0.08)",
        minHeight: 260,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget.style.transform = "translateY(-4px) scale(1.01)");
        (e.currentTarget.style.boxShadow = `0 20px 60px ${tile.glow}44, 0 0 40px ${tile.glow}22`);
      }}
      onMouseLeave={(e) => {
        (e.currentTarget.style.transform = "none");
        (e.currentTarget.style.boxShadow = "none");
      }}
      aria-label={`${tile.category}: ${tile.headline}`}
    >
      {/* Glow blob inside tile */}
      <div
        style={{
          position: "absolute",
          top: "30%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: 180,
          height: 180,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${tile.glow}55 0%, transparent 70%)`,
          filter: "blur(30px)",
          pointerEvents: "none",
        }}
        aria-hidden
      />

      {/* Inner orb / abstract 3D suggestion */}
      <div
        style={{
          width: 120,
          height: 120,
          borderRadius: "50%",
          border: `1px solid ${tile.glow}44`,
          position: "absolute",
          top: "50%",
          left: "60%",
          transform: "translate(-50%, -50%)",
          boxShadow: `inset 0 0 40px ${tile.glow}22, 0 0 20px ${tile.glow}22`,
          opacity: 0.6,
        }}
        aria-hidden
      />

      <div style={{ position: "relative", zIndex: 1 }}>
        <p
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "rgba(255,255,255,0.5)",
            marginBottom: "16px",
          }}
        >
          {tile.category}
        </p>
        <h3
          style={{
            fontSize: "clamp(22px, 2.5vw, 30px)",
            fontWeight: 800,
            color: "white",
            lineHeight: 1.2,
            letterSpacing: "-0.02em",
          }}
        >
          {tile.headline}
        </h3>
      </div>

      <div style={{ position: "relative", zIndex: 1 }}>
        <span
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: `${tile.glow}`,
            filter: "brightness(1.5)",
          }}
        >
          {tile.cta}
        </span>
      </div>
    </article>
  );
}

