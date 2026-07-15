"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import ResumeUpload from "@/components/ResumeUpload";

const ROLES = [
  {
    slug: "backend_engineer",
    label: "Backend Engineer",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <rect x="2" y="3" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="2" />
        <path d="M8 21h8M12 17v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path d="M7 8l2 2-2 2M12 12h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    description: "APIs, databases, system design, concurrency, performance",
    topics: ["API Design", "Databases", "Caching", "System Design", "Security"],
    color: "#6366f1",
    gradient: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.1))",
  },
  {
    slug: "ai_ml_engineer",
    label: "AI / ML Engineer",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
        <path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
    description: "ML models, deep learning, NLP, RAG, MLOps, statistics",
    topics: ["Neural Networks", "NLP", "Model Evaluation", "Deep Learning", "MLOps"],
    color: "#22d3ee",
    gradient: "linear-gradient(135deg, rgba(34,211,238,0.15), rgba(99,102,241,0.08))",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [role, setRole] = useState<string>("");
  const [difficulty, setDifficulty] = useState<"beginner" | "intermediate" | "advanced">("intermediate");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleResumeUploaded = (id: string) => {
    setResumeId(id);
    setError("");
  };

  const handleStartInterview = async () => {
    if (!role) {
      setError("Please enter a target role first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_id: resumeId, role, difficulty }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail?.message || err.message || "Failed to create session");
      }
      const data = await res.json();
      router.push(`/interview/${data.session_id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const canStart = !!role;


  return (
    <div style={{ maxWidth: 760, margin: "0 auto" }}>
      {/* ── Hero ─────────────────────────────────────────── */}
      <div
        className="animate-fade-in"
        style={{ textAlign: "center", padding: "2.5rem 0 2rem", animationDelay: "0s" }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.375rem 1rem",
            background: "rgba(99,102,241,0.1)",
            border: "1px solid rgba(99,102,241,0.2)",
            borderRadius: 9999,
            marginBottom: "1.25rem",
          }}
        >
          <span style={{ fontSize: "0.75rem", color: "#6366f1" }}>●</span>
          <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#a5b4fc", letterSpacing: "0.04em" }}>
            POWERED BY RAG PIPELINE
          </span>
        </div>

        <h1
          style={{
            fontSize: "clamp(2rem, 5vw, 3rem)",
            fontWeight: 800,
            lineHeight: 1.15,
            letterSpacing: "-0.02em",
            marginBottom: "1rem",
          }}
        >
          <span className="gradient-text">Practice Mock Interviews</span>
          <br />
          <span style={{ color: "#e2e8f0" }}>With AI Coach</span>
        </h1>

        <p
          style={{
            fontSize: "1.0625rem",
            color: "#94a3b8",
            maxWidth: 520,
            margin: "0 auto",
            lineHeight: 1.65,
          }}
        >
          Get instant feedback on speaking speed, filler words, and technical depth. Completely free, no registration required.
        </p>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "0.5rem",
            justifyContent: "center",
            marginTop: "1.5rem",
          }}
        >
          {["100% Free Self-Prep", "Real-Time Speech Coaching", "Custom Role Generation", "Resume-Aware RAG"].map(
            (f) => (
              <span key={f} className="badge badge-primary" style={{ fontSize: "0.75rem" }}>
                ✦ {f}
              </span>
            )
          )}
        </div>
      </div>

      {/* ── Step 1: Resume Upload ─────────────────────────── */}
      <div
        className="animate-fade-in"
        style={{ marginBottom: "1.25rem", animationDelay: "0.1s" }}
      >
        <StepLabel number={1} label="Upload your resume (Optional - skip to practice without background)" done={!!resumeId} />
        <ResumeUpload onUploaded={handleResumeUploaded} />
      </div>

      {/* ── Step 2: Role Selection ────────────────────────── */}
      <div
        className="animate-fade-in"
        style={{ marginBottom: "1.25rem", animationDelay: "0.2s" }}
      >
        <StepLabel number={2} label="Enter your target role" done={!!role} />
        <div className="card" style={{ padding: "1.5rem" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <input
              type="text"
              id="role-input"
              placeholder="e.g. Growth Manager, Backend Engineer, Product Manager, Nurse..."
              value={role}
              onChange={(e) => setRole(e.target.value)}
              style={{
                width: "100%",
                padding: "0.875rem 1rem",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "0.5rem",
                color: "#f8fafc",
                fontSize: "0.9375rem",
                outline: "none",
                transition: "border-color 0.2s",
              }}
            />
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Suggestions:</span>
              {[
                "Backend Engineer",
                "Frontend Engineer",
                "Product Manager",
                "Growth Marketer",
                "AI / ML Engineer",
                "Financial Analyst",
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => setRole(s)}
                  type="button"
                  style={{
                    fontSize: "0.75rem",
                    padding: "0.25rem 0.625rem",
                    background: "rgba(99,102,241,0.08)",
                    border: "1px solid rgba(99,102,241,0.2)",
                    color: "#a5b4fc",
                    borderRadius: "9999px",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Error ─────────────────────────────────────────── */}
      {error && (
        <div className="alert-error animate-fade-in-scale" style={{ marginBottom: "1rem" }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
            <circle cx="12" cy="12" r="10" stroke="#f87171" strokeWidth="2" />
            <line x1="12" y1="8" x2="12" y2="12" stroke="#f87171" strokeWidth="2" strokeLinecap="round" />
            <line x1="12" y1="16" x2="12.01" y2="16" stroke="#f87171" strokeWidth="2" strokeLinecap="round" />
          </svg>
          {error}
        </div>
      )}

      {/* ── Step 3: Difficulty Selection ──────────────────── */}
      <div
        className="animate-fade-in"
        style={{ marginBottom: "1.25rem", animationDelay: "0.25s" }}
      >
        <StepLabel number={3} label="Choose your difficulty level" done={true} />
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.75rem" }}>
            {[
              { value: "beginner", label: "Beginner", desc: "Foundational, core theories" },
              { value: "intermediate", label: "Intermediate", desc: "Standard professional depth" },
              { value: "advanced", label: "Advanced", desc: "Complex scenarios & design" },
            ].map((d) => {
              const active = difficulty === d.value;
              return (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => setDifficulty(d.value as any)}
                  style={{
                    padding: "0.75rem",
                    borderRadius: "8px",
                    background: active
                      ? "rgba(99,102,241,0.12)"
                      : "rgba(255,255,255,0.02)",
                    border: active
                      ? "1px solid rgba(99,102,241,0.6)"
                      : "1px solid rgba(255,255,255,0.08)",
                    color: active ? "#e2e8f0" : "#94a3b8",
                    cursor: "pointer",
                    transition: "all 0.2s",
                    textAlign: "center",
                    boxShadow: active ? "0 0 12px rgba(99,102,241,0.15)" : "none",
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: "0.875rem", marginBottom: "0.25rem", color: active ? "#a5b4fc" : "#cbd5e1" }}>
                    {d.label}
                  </div>
                  <div style={{ fontSize: "0.725rem", color: active ? "#94a3b8" : "#64748b", lineHeight: 1.3 }}>
                    {d.desc}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Step 4: Start ─────────────────────────────────── */}
      <div
        className="animate-fade-in"
        style={{ animationDelay: "0.3s" }}
      >
        <StepLabel number={4} label="Begin your interview" done={false} />
        <button
          id="start-interview-btn"
          onClick={handleStartInterview}
          disabled={loading || !canStart}
          className="btn-primary"
          style={{ fontSize: "1rem", padding: "1rem" }}
        >
          {loading ? (
            <>
              <span className="spinner" />
              Setting up your session...
            </>
          ) : (
            <>
              Start Interview
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </>
          )}
        </button>

        {!canStart && !loading && (
          <p
            style={{
              textAlign: "center",
              fontSize: "0.8125rem",
              color: "#475569",
              marginTop: "0.875rem",
            }}
          >
            Enter a role to continue
          </p>
        )}
      </div>

    </div>
  );
}

function StepLabel({
  number,
  label,
  done,
}: {
  number: number;
  label: string;
  done: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.625rem",
        marginBottom: "0.75rem",
        marginTop: "0.5rem",
      }}
    >
      <div
        style={{
          width: 26,
          height: 26,
          borderRadius: "50%",
          background: done
            ? "linear-gradient(135deg, #22c55e, #16a34a)"
            : "linear-gradient(135deg, #6366f1, #8b5cf6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "0.75rem",
          fontWeight: 700,
          color: "white",
          flexShrink: 0,
          boxShadow: done
            ? "0 0 12px rgba(34,197,94,0.35)"
            : "0 0 12px rgba(99,102,241,0.35)",
          transition: "all 0.4s",
        }}
      >
        {done ? (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <path d="M20 6L9 17l-5-5" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          number
        )}
      </div>
      <span
        style={{
          fontSize: "0.875rem",
          fontWeight: 600,
          color: done ? "#86efac" : "#94a3b8",
          transition: "color 0.4s",
        }}
      >
        {label}
      </span>
    </div>
  );
}
