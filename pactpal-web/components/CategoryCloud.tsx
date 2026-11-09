"use client";

const categories = [
  "Website Design", "React", "Python", "Logo Design", "Figma",
  "Shopify", "SEO", "Mobile Apps", "API Development", "Data Entry",
  "Copywriting", "Next.js", "Node.js", "WordPress", "UI/UX",
  "Video Editing", "Machine Learning", "Django", "Swift", "Kotlin",
  "Blockchain", "DevOps", "PostgreSQL", "Three.js", "Tailwind CSS",
  "Smart Contracts", "Flutter", "AI Agents", "TypeScript", "Vue.js",
];

const categories2 = [
  "Content Writing", "Digital Marketing", "Graphic Design", "Animation",
  "3D Modelling", "Cybersecurity", "AWS", "Docker", "Firebase",
  "React Native", "FastAPI", "Supabase", "Vercel", "Netlify",
  "Stripe Integration", "OAuth", "WebSockets", "Rust", "Go",
  "Unity", "Unreal Engine", "WebGL", "D3.js", "Pandas", "PyTorch",
  "OpenAI API", "Langchain", "Pinecone", "Redis", "Kubernetes",
];

function CategoryPill({ label }: { label: string }) {
  return (
    <button
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "50px",
        padding: "9px 18px",
        fontSize: 13,
        fontWeight: 500,
        color: "var(--color-text-secondary)",
        cursor: "pointer",
        whiteSpace: "nowrap",
        transition: "all 0.2s",
        flexShrink: 0,
      }}
      onMouseEnter={(e) => {
        (e.currentTarget.style.borderColor = "rgba(0,102,255,0.4)");
        (e.currentTarget.style.color = "#60A5FA");
        (e.currentTarget.style.background = "rgba(0,102,255,0.08)");
        (e.currentTarget.style.transform = "translateY(-1px)");
      }}
      onMouseLeave={(e) => {
        (e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)");
        (e.currentTarget.style.color = "var(--color-text-secondary)");
        (e.currentTarget.style.background = "rgba(255,255,255,0.03)");
        (e.currentTarget.style.transform = "none");
      }}
      aria-label={`Browse ${label} projects`}
    >
      {label}
    </button>
  );
}

export default function CategoryCloud() {
  return (
    <section
      style={{
        padding: "120px 0",
        overflow: "hidden",
      }}
      aria-labelledby="category-heading"
    >
      <div style={{ textAlign: "center", marginBottom: "52px", padding: "0 24px" }}>
        <h2
          id="category-heading"
          style={{
            fontSize: "clamp(28px, 4vw, 48px)",
            fontWeight: 900,
            letterSpacing: "-0.02em",
            color: "white",
            marginBottom: "8px",
          }}
        >
          Get work done in{" "}
          <span className="gradient-text">4,000+ categories</span>
        </h2>
        <p style={{ fontSize: 16, color: "var(--color-text-muted)" }}>
          If it can be built, designed, or scripted — the Referee can verify it.
        </p>
      </div>

      {/* Row 1 — left scroll */}
      <div style={{ overflow: "hidden", marginBottom: "12px" }}>
        <div
          className="marquee-track"
          style={{ display: "flex", gap: "10px", width: "max-content", padding: "0 20px" }}
          aria-hidden
        >
          {[...categories, ...categories].map((c, i) => (
            <CategoryPill key={i} label={c} />
          ))}
        </div>
      </div>

      {/* Row 2 — right scroll */}
      <div style={{ overflow: "hidden" }}>
        <div
          className="marquee-track-reverse"
          style={{ display: "flex", gap: "10px", width: "max-content", padding: "0 20px" }}
          aria-hidden
        >
          {[...categories2, ...categories2].map((c, i) => (
            <CategoryPill key={i} label={c} />
          ))}
        </div>
      </div>

      {/* Accessible fallback list (visually hidden) */}
      <div
        style={{
          position: "absolute",
          width: 1,
          height: 1,
          overflow: "hidden",
          clip: "rect(0,0,0,0)",
          whiteSpace: "nowrap",
        }}
      >
        <ul>
          {[...categories, ...categories2].map((c) => (
            <li key={c}><a href={`/category/${c.toLowerCase().replace(/\s+/g, "-")}`}>{c}</a></li>
          ))}
        </ul>
      </div>
    </section>
  );
}

