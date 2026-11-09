import Link from "next/link";
import Navbar from "@/components/Navbar";

export default function NotFound() {
  return (
    <main style={{ background: "var(--color-bg)", minHeight: "100vh" }}>
      <Navbar />
      <section
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "80vh",
          padding: "40px 24px",
          textAlign: "center",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: 500,
            height: 500,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(0,102,255,0.08) 0%, transparent 70%)",
            filter: "blur(60px)",
            pointerEvents: "none",
          }}
          aria-hidden
        />

        <div
          style={{
            fontSize: "clamp(96px, 20vw, 200px)",
            fontWeight: 900,
            fontFamily: "JetBrains Mono, monospace",
            lineHeight: 1,
            background: "linear-gradient(135deg, #0066FF, #7A5CFF)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            marginBottom: 24,
            opacity: 0.6,
          }}
          aria-hidden
        >
          404
        </div>

        <h1
          style={{
            fontSize: "clamp(28px, 4vw, 48px)",
            fontWeight: 900,
            letterSpacing: "-0.025em",
            color: "white",
            marginBottom: 16,
          }}
        >
          This pact doesn&apos;t exist.
        </h1>
        <p
          style={{
            fontSize: 18,
            color: "var(--color-text-secondary)",
            marginBottom: 40,
            maxWidth: 440,
            lineHeight: 1.6,
          }}
        >
          The page you&apos;re looking for has either been removed, or never existed.
          No receipt for this one.
        </p>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", justifyContent: "center" }}>
          <Link
            href="/"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "linear-gradient(135deg, #0066FF, #00A3E0)",
              color: "white",
              borderRadius: 50,
              padding: "14px 28px",
              fontSize: 15,
              fontWeight: 700,
              textDecoration: "none",
              boxShadow: "0 0 24px rgba(0,102,255,0.4)",
            }}
          >
            Go home
          </Link>
          <Link
            href="/hire"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "white",
              borderRadius: 50,
              padding: "14px 28px",
              fontSize: 15,
              fontWeight: 600,
              textDecoration: "none",
            }}
          >
            Browse projects
          </Link>
        </div>
      </section>
    </main>
  );
}

