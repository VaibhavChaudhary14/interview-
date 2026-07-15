"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface RoleFamily {
  slug: string;
  name: string;
  description: string;
  has_kb: boolean;
}

const DIFFICULTIES = [
  { value: "beginner", label: "Beginner", color: "from-emerald-500 to-teal-500" },
  { value: "intermediate", label: "Intermediate", color: "from-blue-500 to-indigo-500" },
  { value: "advanced", label: "Advanced", color: "from-violet-500 to-purple-600" },
] as const;

export default function BrowsePage() {
  const [families, setFamilies] = useState<RoleFamily[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetch("/api/v1/role-families")
      .then((r) => r.json())
      .then((data) => setFamilies(data.families))
      .catch(() => setError("Failed to load role families. Please try again."))
      .finally(() => setLoading(false));
  }, []);

  async function startSession(roleName: string, difficulty: string) {
    const key = `${roleName}-${difficulty}`;
    setStarting(key);
    try {
      const res = await fetch("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role: roleName,
          difficulty,
          mode: "self_prep",
        }),
      });
      if (!res.ok) throw new Error(`Session creation failed (${res.status})`);
      const session = await res.json();
      router.push(`/interview/${session.session_id}`);
    } catch (e) {
      setError("Couldn't start session. Please try again.");
      setStarting(null);
    }
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-primary)" }}>
      <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "48px 24px" }}>
        {/* Header */}
        <div style={{ marginBottom: "40px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "12px" }}>
            <span style={{ fontSize: "28px" }}>🎯</span>
            <h1 style={{
              fontSize: "clamp(22px, 4vw, 32px)",
              fontWeight: 700,
              background: "linear-gradient(135deg, #a78bfa, #60a5fa)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              margin: 0,
            }}>
              Browse Interview Practice
            </h1>
          </div>
          <p style={{ color: "var(--text-secondary)", fontSize: "16px", margin: 0, lineHeight: 1.6 }}>
            Pick a role and difficulty to start practicing.{" "}
            <a
              href="/"
              style={{ color: "#a78bfa", textDecoration: "underline", fontWeight: 500 }}
            >
              Type a custom role directly
            </a>{" "}
            if yours isn't listed — we'll match it to the closest fit.
          </p>
        </div>

        {/* Difficulty legend */}
        <div style={{
          display: "flex",
          gap: "16px",
          marginBottom: "32px",
          flexWrap: "wrap",
        }}>
          {DIFFICULTIES.map((d) => (
            <div
              key={d.value}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "13px",
                color: "var(--text-secondary)",
              }}
            >
              <div style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                background: `linear-gradient(135deg, ${d.value === "beginner" ? "#10b981, #14b8a6" : d.value === "intermediate" ? "#3b82f6, #6366f1" : "#8b5cf6, #7c3aed"})`,
              }} />
              {d.label}
            </div>
          ))}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--text-secondary)" }}>
            <span style={{
              background: "rgba(34, 197, 94, 0.15)",
              color: "#22c55e",
              fontSize: "11px",
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: "12px",
              border: "1px solid rgba(34, 197, 94, 0.3)",
            }}>Popular</span>
            = RAG-grounded questions
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div style={{
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "12px",
            padding: "16px",
            color: "#f87171",
            marginBottom: "24px",
          }}>
            {error}
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "20px" }}>
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "16px",
                  padding: "24px",
                  animation: "pulse 2s infinite",
                }}
              >
                <div style={{ height: "20px", background: "rgba(255,255,255,0.05)", borderRadius: "8px", marginBottom: "12px" }} />
                <div style={{ height: "40px", background: "rgba(255,255,255,0.03)", borderRadius: "8px", marginBottom: "20px" }} />
                <div style={{ display: "flex", gap: "8px" }}>
                  {[1,2,3].map(j => (
                    <div key={j} style={{ height: "34px", flex: 1, background: "rgba(255,255,255,0.05)", borderRadius: "8px" }} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Role families grid */}
        {!loading && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "20px" }}>
            {families.map((family) => (
              <div
                key={family.slug}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "16px",
                  padding: "24px",
                  transition: "border-color 0.2s, box-shadow 0.2s",
                  cursor: "default",
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(167,139,250,0.4)";
                  (e.currentTarget as HTMLDivElement).style.boxShadow = "0 4px 24px rgba(167,139,250,0.08)";
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border-color)";
                  (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
                }}
              >
                {/* Card header */}
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "10px" }}>
                  <h2 style={{
                    fontSize: "16px",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                    margin: 0,
                    lineHeight: 1.3,
                  }}>
                    {family.name}
                  </h2>
                  {family.has_kb && (
                    <span style={{
                      background: "rgba(34, 197, 94, 0.15)",
                      color: "#22c55e",
                      fontSize: "11px",
                      fontWeight: 600,
                      padding: "3px 10px",
                      borderRadius: "12px",
                      border: "1px solid rgba(34, 197, 94, 0.3)",
                      whiteSpace: "nowrap",
                      marginLeft: "8px",
                      flexShrink: 0,
                    }}>
                      ⭐ Popular
                    </span>
                  )}
                </div>

                {/* Description */}
                <p style={{
                  fontSize: "13px",
                  color: "var(--text-secondary)",
                  lineHeight: 1.6,
                  margin: "0 0 20px 0",
                  display: "-webkit-box",
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: "vertical",
                  overflow: "hidden",
                }}>
                  {family.description}
                </p>

                {/* Difficulty buttons */}
                <div style={{ display: "flex", gap: "8px" }}>
                  {DIFFICULTIES.map((d) => {
                    const key = `${family.name}-${d.value}`;
                    const isStarting = starting === key;
                    return (
                      <button
                        key={d.value}
                        id={`browse-${family.slug}-${d.value}`}
                        disabled={!!starting}
                        onClick={() => startSession(family.name, d.value)}
                        style={{
                          flex: 1,
                          padding: "8px 4px",
                          borderRadius: "8px",
                          border: "1px solid var(--border-color)",
                          background: isStarting
                            ? `linear-gradient(135deg, ${d.value === "beginner" ? "#10b981, #14b8a6" : d.value === "intermediate" ? "#3b82f6, #6366f1" : "#8b5cf6, #7c3aed"})`
                            : "transparent",
                          color: isStarting ? "#fff" : "var(--text-secondary)",
                          fontSize: "12px",
                          fontWeight: 500,
                          cursor: starting ? "not-allowed" : "pointer",
                          transition: "all 0.18s",
                          opacity: starting && !isStarting ? 0.5 : 1,
                        }}
                        onMouseEnter={e => {
                          if (!starting) {
                            (e.currentTarget as HTMLButtonElement).style.background = `linear-gradient(135deg, ${d.value === "beginner" ? "#10b981, #14b8a6" : d.value === "intermediate" ? "#3b82f6, #6366f1" : "#8b5cf6, #7c3aed"})`;
                            (e.currentTarget as HTMLButtonElement).style.color = "#fff";
                            (e.currentTarget as HTMLButtonElement).style.borderColor = "transparent";
                          }
                        }}
                        onMouseLeave={e => {
                          if (!starting) {
                            (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                            (e.currentTarget as HTMLButtonElement).style.color = "var(--text-secondary)";
                            (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border-color)";
                          }
                        }}
                      >
                        {isStarting ? "Starting…" : d.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
