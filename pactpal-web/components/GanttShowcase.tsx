"use client";

const tasks = [
  { name: "Landing page", weight: "25%", status: "passed", due: "Nov 12", width: 55, start: 5 },
  { name: "Login system", weight: "20%", status: "failed", due: "Nov 15", width: 40, start: 20 },
  { name: "Dashboard", weight: "30%", status: "passed", due: "Nov 18", width: 50, start: 30 },
  { name: "Payment flow", weight: "15%", status: "verifying", due: "Nov 20", width: 35, start: 50 },
  { name: "API integration", weight: "5%", status: "pending", due: "Nov 22", width: 25, start: 65 },
  { name: "Responsive layout", weight: "5%", status: "pending", due: "Nov 25", width: 20, start: 72 },
];

const statusColors: Record<string, string> = {
  passed: "#4CAF50",
  failed: "#F44336",
  verifying: "#0066FF",
  pending: "#7C89A8",
};

const statusIcons: Record<string, string> = {
  passed: "✓",
  failed: "✗",
  verifying: "⟳",
  pending: "○",
};

const statusLabels: Record<string, string> = {
  passed: "Passed",
  failed: "Failed",
  verifying: "Verifying",
  pending: "Pending",
};

export default function GanttShowcase() {
  return (
    <section
      style={{ padding: "120px 24px", maxWidth: 1280, margin: "0 auto" }}
      aria-labelledby="gantt-heading"
    >
      {/* Header */}
      <div style={{ marginBottom: "48px", textAlign: "center" }}>
        <p
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "var(--color-text-muted)",
            marginBottom: "16px",
          }}
        >
          Bryntum Gantt integration
        </p>
        <h2
          id="gantt-heading"
          style={{
            fontSize: "clamp(32px, 4vw, 52px)",
            fontWeight: 900,
            letterSpacing: "-0.025em",
            color: "white",
          }}
        >
          Every contract, one{" "}
          <span className="gradient-text">glanceable timeline.</span>
        </h2>
      </div>

      {/* Gantt container — matches #bryntum-gantt placeholder */}
      <div
        id="bryntum-gantt"
        style={{
          background: "rgba(255,255,255,0.03)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "24px",
          overflow: "hidden",
          minHeight: "500px",
          boxShadow: "0 0 60px rgba(0,102,255,0.08)",
        }}
        role="region"
        aria-label="Contract Gantt timeline"
      >
        {/* Toolbar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "16px 24px",
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div style={{ fontWeight: 700, fontSize: 15, color: "white" }}>
            Contract: E-commerce Platform v2
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            {["Day", "Week", "Month"].map((z) => (
              <button
                key={z}
                style={{
                  background: z === "Week" ? "rgba(0,102,255,0.15)" : "rgba(255,255,255,0.05)",
                  border: `1px solid ${z === "Week" ? "rgba(0,102,255,0.4)" : "rgba(255,255,255,0.08)"}`,
                  borderRadius: "8px",
                  color: z === "Week" ? "#60A5FA" : "var(--color-text-muted)",
                  padding: "6px 14px",
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: "pointer",
                }}
                aria-pressed={z === "Week"}
                aria-label={`Zoom to ${z} view`}
              >
                {z}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {["All", "Passed", "Failed", "Pending"].map((f) => (
              <button
                key={f}
                style={{
                  background: f === "All" ? "rgba(255,255,255,0.08)" : "transparent",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: "50px",
                  color: "var(--color-text-secondary)",
                  padding: "5px 14px",
                  fontSize: 12,
                  cursor: "pointer",
                }}
                aria-label={`Filter: ${f}`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Grid */}
        <div style={{ display: "flex", minHeight: "400px" }}>
          {/* Task list panel */}
          <div
            style={{
              width: 320,
              borderRight: "1px solid rgba(255,255,255,0.07)",
              flexShrink: 0,
            }}
            role="columnheader"
          >
            {/* Column headers */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 56px 80px 70px",
                padding: "10px 16px",
                borderBottom: "1px solid rgba(255,255,255,0.07)",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.08em",
                color: "var(--color-text-muted)",
                textTransform: "uppercase",
              }}
              aria-hidden
            >
              <span>Feature</span>
              <span style={{ textAlign: "center" }}>Wt.</span>
              <span style={{ textAlign: "center" }}>Status</span>
              <span style={{ textAlign: "right" }}>Due</span>
            </div>

            {/* Task rows */}
            {tasks.map((task, i) => (
              <div
                key={i}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 56px 80px 70px",
                  padding: "14px 16px",
                  borderBottom: "1px solid rgba(255,255,255,0.04)",
                  alignItems: "center",
                  transition: "background 0.2s",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => ((e.currentTarget.style.background = "rgba(0,102,255,0.06)"))}
                onMouseLeave={(e) => ((e.currentTarget.style.background = "transparent"))}
                role="row"
                aria-label={`${task.name}, ${task.status}, due ${task.due}`}
              >
                <span style={{ fontSize: 13, color: "white", fontWeight: 500 }}>{task.name}</span>
                <span
                  className="mono"
                  style={{
                    fontSize: 12,
                    color: "var(--color-text-muted)",
                    textAlign: "center",
                    background: "rgba(255,255,255,0.05)",
                    borderRadius: "6px",
                    padding: "2px 6px",
                  }}
                >
                  {task.weight}
                </span>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "5px",
                    background: `${statusColors[task.status]}15`,
                    border: `1px solid ${statusColors[task.status]}30`,
                    borderRadius: "50px",
                    padding: "2px 10px",
                    fontSize: 11,
                    fontWeight: 600,
                    color: statusColors[task.status],
                    justifySelf: "center",
                  }}
                  aria-label={`Status: ${statusLabels[task.status]}`}
                >
                  <span aria-hidden>{statusIcons[task.status]}</span>
                  <span>{statusLabels[task.status]}</span>
                </div>
                <span style={{ fontSize: 12, color: "var(--color-text-muted)", textAlign: "right" }}>
                  {task.due}
                </span>
              </div>
            ))}
          </div>

          {/* Timeline panel */}
          <div
            style={{ flex: 1, padding: "0 16px", position: "relative", overflowX: "auto" }}
            role="presentation"
            aria-label="Gantt timeline bars"
          >
            {/* Week headers */}
            <div
              style={{
                display: "flex",
                height: 36,
                borderBottom: "1px solid rgba(255,255,255,0.07)",
                fontSize: 11,
                color: "var(--color-text-muted)",
                fontWeight: 600,
              }}
              aria-hidden
            >
              {["Nov 10", "Nov 12", "Nov 14", "Nov 16", "Nov 18", "Nov 20", "Nov 22", "Nov 24", "Nov 26"].map(
                (d) => (
                  <div
                    key={d}
                    style={{
                      flex: 1,
                      display: "flex",
                      alignItems: "center",
                      paddingLeft: "4px",
                      borderLeft: "1px solid rgba(255,255,255,0.04)",
                    }}
                  >
                    {d}
                  </div>
                )
              )}
            </div>

            {/* Today line */}
            <div
              style={{
                position: "absolute",
                top: 36,
                bottom: 0,
                left: "12%",
                width: 2,
                background: "linear-gradient(to bottom, #0066FF, transparent)",
                zIndex: 2,
              }}
              role="presentation"
              aria-label="Today line"
            >
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: "50%",
                  transform: "translateX(-50%)",
                  background: "#0066FF",
                  color: "white",
                  fontSize: 10,
                  fontWeight: 700,
                  padding: "2px 8px",
                  borderRadius: "50px",
                  whiteSpace: "nowrap",
                }}
              >
                TODAY
              </div>
            </div>

            {/* Task bars */}
            {tasks.map((task, i) => (
              <div
                key={i}
                style={{
                  height: 48,
                  display: "flex",
                  alignItems: "center",
                  borderBottom: "1px solid rgba(255,255,255,0.04)",
                  position: "relative",
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    left: `${task.start}%`,
                    width: `${task.width}%`,
                    height: 28,
                    borderRadius: "8px",
                    background: `linear-gradient(90deg, ${statusColors[task.status]}, ${statusColors[task.status]}bb)`,
                    boxShadow: `0 0 12px ${statusColors[task.status]}44`,
                    display: "flex",
                    alignItems: "center",
                    paddingLeft: "10px",
                    fontSize: 12,
                    fontWeight: 600,
                    color: "white",
                    overflow: "hidden",
                    cursor: "pointer",
                    transition: "opacity 0.2s",
                  }}
                  role="presentation"
                  title={`${task.name} — ${statusLabels[task.status]}`}
                  onMouseEnter={(e) => ((e.currentTarget.style.opacity = "0.85"))}
                  onMouseLeave={(e) => ((e.currentTarget.style.opacity = "1"))}
                >
                  <span aria-hidden>{statusIcons[task.status]}</span>
                  <span style={{ marginLeft: "6px", whiteSpace: "nowrap" }}>{task.name}</span>
                </div>
              </div>
            ))}

            {/* Milestone: Escrow expires */}
            <div
              style={{
                position: "absolute",
                top: 36,
                left: "75%",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                zIndex: 3,
              }}
              role="presentation"
              aria-label="Escrow hold expires milestone"
            >
              <div
                style={{
                  width: 16,
                  height: 16,
                  background: "#FF9800",
                  transform: "rotate(45deg)",
                  boxShadow: "0 0 12px rgba(255,152,0,0.6)",
                  marginBottom: "4px",
                }}
                aria-hidden
              />
              <div
                style={{
                  background: "rgba(255,152,0,0.15)",
                  border: "1px solid rgba(255,152,0,0.3)",
                  borderRadius: "50px",
                  padding: "2px 10px",
                  fontSize: 10,
                  color: "#FF9800",
                  fontWeight: 700,
                  whiteSpace: "nowrap",
                }}
              >
                12d left
              </div>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div
          style={{
            display: "flex",
            gap: "24px",
            padding: "14px 24px",
            borderTop: "1px solid rgba(255,255,255,0.07)",
            flexWrap: "wrap",
          }}
          role="legend"
          aria-label="Gantt status legend"
        >
          {Object.entries(statusColors).map(([status, color]) => (
            <div key={status} style={{ display: "flex", alignItems: "center", gap: "7px", fontSize: 12 }}>
              <div
                style={{
                  width: 24,
                  height: 10,
                  borderRadius: 3,
                  background: color,
                  boxShadow: `0 0 6px ${color}66`,
                }}
                aria-hidden
              />
              <span style={{ color: "var(--color-text-muted)" }}>
                <span aria-hidden>{statusIcons[status]}</span> {statusLabels[status]}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

