"use client";

interface Props {
  current: number;
  max: number;
}

export default function ProgressBar({ current, max }: Props) {
  const pct = max > 0 ? Math.min((current / max) * 100, 100) : 0;
  const steps = Array.from({ length: max }, (_, i) => i + 1);

  return (
    <div className="card animate-fade-in" style={{ padding: "1.25rem 1.75rem" }}>
      {/* Label row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.875rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"
              stroke="#6366f1"
              strokeWidth="2"
            />
            <path
              d="M12 6v6l4 2"
              stroke="#6366f1"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
          <span
            style={{ fontSize: "0.8125rem", fontWeight: 600, color: "#94a3b8" }}
          >
            Interview Progress
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
          <span
            style={{ fontSize: "1.25rem", fontWeight: 700, color: "#818cf8" }}
          >
            {current}
          </span>
          <span style={{ fontSize: "0.8125rem", color: "#475569" }}>/ {max}</span>
          <span style={{ fontSize: "0.75rem", color: "#475569", marginLeft: "0.25rem" }}>
            questions
          </span>
        </div>
      </div>

      {/* Bar */}
      <div className="progress-track" style={{ marginBottom: "0.875rem" }}>
        <div
          className="progress-fill"
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={current}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>

      {/* Step dots */}
      {max <= 12 && (
        <div
          style={{
            display: "flex",
            gap: "0.375rem",
            justifyContent: "center",
          }}
        >
          {steps.map((s) => (
            <div
              key={s}
              title={`Question ${s}`}
              style={{
                width: s <= current ? 20 : 8,
                height: 8,
                borderRadius: 9999,
                background:
                  s <= current
                    ? "linear-gradient(90deg, #6366f1, #22d3ee)"
                    : "rgba(255,255,255,0.08)",
                transition: "all 0.4s cubic-bezier(0.4,0,0.2,1)",
                flexShrink: 0,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
