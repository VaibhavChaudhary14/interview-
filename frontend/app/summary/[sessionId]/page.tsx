"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import RecordingPlayback from "@/components/RecordingPlayback";

interface TranscriptEntry {
  sequence: number;
  question: string;
  answer: string;
  topic: string;
  source_chunks: string[];
  recording_id?: string;
}

interface Insights {
  questions_answered: number;
  average_answer_length_words: number;
  topics_with_thin_answers: string[];
  resume_alignment_note: string;
}

interface Report {
  session_id: string;
  role: string;
  generated_at: string;
  topics_covered: string[];
  transcript: TranscriptEntry[];
  insights: Insights;
}

const ROLE_LABELS: Record<string, string> = {
  backend_engineer: "Backend Engineer",
  ai_ml_engineer: "AI / ML Engineer",
};

const TOPIC_COLORS = [
  "#6366f1", "#22d3ee", "#a78bfa", "#f59e0b",
  "#10b981", "#f43f5e", "#3b82f6", "#8b5cf6",
];

export default function SummaryPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [openItems, setOpenItems] = useState<Set<number>>(new Set());
  const [retries, setRetries] = useState(0);

  useEffect(() => {
    let attempts = 0;
    const fetchReport = async () => {
      try {
        const res = await fetch(`/api/v1/sessions/${sessionId}/report`);
        if (res.ok) {
          setReport(await res.json());
          setLoading(false);
        } else if (res.status === 404 && attempts < 5) {
          attempts++;
          setRetries(attempts);
          setTimeout(fetchReport, 1500);
        } else {
          setLoading(false);
        }
      } catch {
        setLoading(false);
      }
    };
    fetchReport();
  }, [sessionId]);

  const toggleItem = (seq: number) => {
    setOpenItems((prev) => {
      const next = new Set(prev);
      next.has(seq) ? next.delete(seq) : next.add(seq);
      return next;
    });
  };

  /* ── Loading ───────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="animate-fade-in" style={{ textAlign: "center", padding: "4rem 1rem" }}>
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: "50%",
            background: "rgba(99,102,241,0.1)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 1.5rem",
          }}
        >
          <span className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
        </div>
        <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#e2e8f0", marginBottom: "0.5rem" }}>
          Generating your report…
        </h2>
        <p style={{ color: "#64748b", fontSize: "0.875rem" }}>
          Analysing your answers and computing insights
          {retries > 0 && ` (attempt ${retries + 1})`}
        </p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="animate-fade-in" style={{ textAlign: "center", padding: "4rem 1rem" }}>
        <p style={{ color: "#64748b" }}>Report not available yet.</p>
        <Link href="/" className="btn-secondary" style={{ marginTop: "1.5rem", display: "inline-flex" }}>
          ← Start New Interview
        </Link>
      </div>
    );
  }

  const roleLabel = ROLE_LABELS[report.role] || report.role;
  const generatedAt = new Date(report.generated_at).toLocaleString();
  const answeredPct =
    report.transcript.length > 0
      ? Math.round((report.insights.questions_answered / report.transcript.length) * 100)
      : 0;
  const thinCount = report.insights.topics_with_thin_answers.length;

  return (
    <div>
      {/* ── Hero header ────────────────────────────────────── */}
      <div
        className="animate-fade-in"
        style={{ textAlign: "center", padding: "2rem 0 1.5rem" }}
      >
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: 20,
            background: "linear-gradient(135deg, #6366f1, #22d3ee)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 1.25rem",
            boxShadow: "0 0 40px rgba(99,102,241,0.4)",
          }}
        >
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none">
            <path d="M9 12l2 2 4-4" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" stroke="white" strokeWidth="2" />
          </svg>
        </div>
        <h1
          style={{
            fontSize: "clamp(1.5rem, 4vw, 2.25rem)",
            fontWeight: 800,
            color: "#e2e8f0",
            letterSpacing: "-0.02em",
            marginBottom: "0.5rem",
          }}
        >
          Interview Complete
        </h1>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", justifyContent: "center" }}>
          <span className="badge badge-primary">{roleLabel}</span>
          <span style={{ color: "#334155" }}>·</span>
          <span style={{ fontSize: "0.8125rem", color: "#64748b" }}>{generatedAt}</span>
        </div>
      </div>

      {/* ── Stats Row ─────────────────────────────────────── */}
      <div
        className="animate-fade-in"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: "0.875rem",
          marginBottom: "1.25rem",
          animationDelay: "0.05s",
        }}
      >
        <div className="stat-card">
          <div className="stat-value">{report.insights.questions_answered}</div>
          <div className="stat-label">Questions Answered</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{report.insights.average_answer_length_words}</div>
          <div className="stat-label">Avg Words per Answer</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{report.topics_covered.length}</div>
          <div className="stat-label">Topics Covered</div>
        </div>
        <div className="stat-card">
          <div
            className="stat-value"
            style={{
              background: thinCount === 0
                ? "linear-gradient(135deg, #22c55e, #16a34a)"
                : "linear-gradient(135deg, #f59e0b, #d97706)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            {thinCount === 0 ? "✓" : thinCount}
          </div>
          <div className="stat-label">
            {thinCount === 0 ? "All answers solid" : "Thin answer topics"}
          </div>
        </div>
      </div>

      {/* ── Topics Covered ────────────────────────────────── */}
      <div
        className="card animate-fade-in"
        style={{ marginBottom: "1.25rem", animationDelay: "0.1s" }}
      >
        <SectionHeader icon="🧭" label="Topics Covered" />
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "1rem" }}>
          {report.topics_covered.map((topic, i) => (
            <span
              key={topic}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.375rem",
                padding: "0.35rem 0.875rem",
                fontSize: "0.8125rem",
                fontWeight: 600,
                borderRadius: 9999,
                background: `${TOPIC_COLORS[i % TOPIC_COLORS.length]}18`,
                color: TOPIC_COLORS[i % TOPIC_COLORS.length],
                border: `1px solid ${TOPIC_COLORS[i % TOPIC_COLORS.length]}30`,
              }}
            >
              {topic}
            </span>
          ))}
        </div>
      </div>

      {/* ── Insights Card ─────────────────────────────────── */}
      <div
        className="card animate-fade-in"
        style={{ marginBottom: "1.25rem", animationDelay: "0.15s" }}
      >
        <SectionHeader icon="💡" label="Key Insights" />
        <div style={{ marginTop: "1rem" }}>
          {/* Completion bar */}
          <div style={{ marginBottom: "1.25rem" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "0.8125rem",
                color: "#64748b",
                marginBottom: "0.5rem",
              }}
            >
              <span>Completion rate</span>
              <span style={{ color: "#818cf8", fontWeight: 600 }}>{answeredPct}%</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${answeredPct}%` }} />
            </div>
          </div>

          {/* Thin topics */}
          {thinCount > 0 && (
            <div className="alert-info" style={{ marginBottom: "1rem", fontSize: "0.8125rem" }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
                <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" stroke="#818cf8" strokeWidth="2" />
                <line x1="12" y1="16" x2="12" y2="12" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" />
                <line x1="12" y1="8" x2="12.01" y2="8" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <span>
                Topics with thin answers:{" "}
                <strong>{report.insights.topics_with_thin_answers.join(", ")}</strong>
              </span>
            </div>
          )}

          {/* Alignment note */}
          <div
            style={{
              padding: "1rem 1.25rem",
              background: "rgba(255,255,255,0.02)",
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
              Resume Alignment
            </p>
            <p style={{ fontSize: "0.875rem", color: "#94a3b8", lineHeight: 1.6 }}>
              {report.insights.resume_alignment_note}
            </p>
          </div>
        </div>
      </div>

      {/* ── Transcript ────────────────────────────────────── */}
      <div
        className="card animate-fade-in"
        style={{ marginBottom: "1.5rem", animationDelay: "0.2s" }}
      >
        <SectionHeader icon="📋" label="Full Transcript" />
        <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.625rem" }}>
          {report.transcript.map((entry, i) => {
            const isOpen = openItems.has(entry.sequence);
            const hasAnswer = entry.answer && entry.answer.trim();
            const wordCount = hasAnswer ? entry.answer.trim().split(/\s+/).length : 0;
            const topicColor = TOPIC_COLORS[i % TOPIC_COLORS.length];

            return (
              <div key={entry.sequence} className="transcript-item">
                {/* Header (always visible, clickable) */}
                <button
                  onClick={() => toggleItem(entry.sequence)}
                  className="transcript-header"
                  style={{
                    width: "100%",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                  id={`transcript-q-${entry.sequence}`}
                >
                  {/* Sequence badge */}
                  <span
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: "50%",
                      background: `${topicColor}20`,
                      border: `1px solid ${topicColor}40`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      color: topicColor,
                      flexShrink: 0,
                    }}
                  >
                    {entry.sequence}
                  </span>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span
                      style={{
                        display: "inline-flex",
                        padding: "0.15rem 0.5rem",
                        fontSize: "0.6875rem",
                        fontWeight: 700,
                        borderRadius: 6,
                        background: `${topicColor}15`,
                        color: topicColor,
                        marginBottom: "0.25rem",
                        textTransform: "capitalize",
                      }}
                    >
                      {entry.topic}
                    </span>
                    <p
                      style={{
                        fontSize: "0.875rem",
                        fontWeight: 500,
                        color: "#cbd5e1",
                        lineHeight: 1.5,
                        overflow: "hidden",
                        display: "-webkit-box",
                        WebkitLineClamp: isOpen ? 999 : 2,
                        WebkitBoxOrient: "vertical",
                      }}
                    >
                      {entry.question}
                    </p>
                  </div>

                  {/* Word count + chevron */}
                  <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", flexShrink: 0 }}>
                    {wordCount > 0 && (
                      <span style={{ fontSize: "0.7rem", color: "#475569", fontWeight: 500 }}>
                        {wordCount}w
                      </span>
                    )}
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      style={{
                        transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
                        transition: "transform 0.2s",
                        color: "#475569",
                      }}
                    >
                      <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                </button>

                {/* Body (expandable) */}
                {isOpen && (
                  <div className="transcript-body animate-fade-in-scale">
                    {hasAnswer ? (
                      <p style={{ fontSize: "0.875rem", color: "#94a3b8", lineHeight: 1.7 }}>
                        {entry.answer}
                      </p>
                    ) : (
                      <p style={{ fontSize: "0.875rem", color: "#334155", fontStyle: "italic" }}>
                        (no answer recorded)
                      </p>
                    )}
                    {entry.recording_id && (
                      <div style={{ marginTop: "1rem", marginBottom: "1rem", display: "grid", gridTemplateColumns: "1fr", gap: "1rem" }}>
                        <RecordingPlayback
                          sessionId={sessionId}
                          recordingId={entry.recording_id}
                          questionSequence={entry.sequence}
                        />
                        <div style={{
                          padding: "1rem",
                          background: "rgba(255,255,255,0.01)",
                          border: "1px dashed rgba(255,255,255,0.06)",
                          borderRadius: "0.5rem"
                        }}>
                          <p style={{ fontSize: "0.75rem", color: "#6366f1", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
                            🎙️ Delivery Coaching Insights (Placeholder)
                          </p>
                          <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
                            <div>
                              <p style={{ fontSize: "0.6875rem", color: "#475569" }}>Speaking Pace</p>
                              <p style={{ fontSize: "0.875rem", color: "#cbd5e1", fontWeight: 600 }}>-- WPM</p>
                            </div>
                            <div>
                              <p style={{ fontSize: "0.6875rem", color: "#475569" }}>Filler Words</p>
                              <p style={{ fontSize: "0.875rem", color: "#cbd5e1", fontWeight: 600 }}>-- detected</p>
                            </div>
                            <div>
                              <p style={{ fontSize: "0.6875rem", color: "#475569" }}>Long Pauses</p>
                              <p style={{ fontSize: "0.875rem", color: "#cbd5e1", fontWeight: 600 }}>-- pauses</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    {entry.source_chunks && entry.source_chunks.length > 0 && (
                      <div style={{ marginTop: "0.75rem" }}>
                        <p style={{ fontSize: "0.6875rem", color: "#334155", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.375rem" }}>
                          Knowledge Base Sources
                        </p>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                          {entry.source_chunks.map((c) => (
                            <span key={c} className="skill-chip" style={{ fontSize: "0.625rem" }}>
                              {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── CTA ───────────────────────────────────────────── */}
      <div
        className="animate-fade-in"
        style={{ textAlign: "center", animationDelay: "0.25s" }}
      >
        <Link
          href="/"
          id="new-interview-btn"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.875rem 2rem",
            fontSize: "0.9375rem",
            fontWeight: 600,
            color: "#fff",
            background: "linear-gradient(135deg, #6366f1, #8b5cf6, #22d3ee)",
            borderRadius: 12,
            textDecoration: "none",
            boxShadow: "0 4px 20px rgba(99,102,241,0.4)",
            transition: "opacity 0.2s, transform 0.2s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.opacity = "0.9";
            (e.currentTarget as HTMLElement).style.transform = "translateY(-1px)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.opacity = "1";
            (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
          }}
        >
          ← Start New Interview
        </Link>
      </div>
    </div>
  );
}

function SectionHeader({ icon, label }: { icon: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
      <span style={{ fontSize: "1.125rem" }}>{icon}</span>
      <h2
        style={{
          fontSize: "1rem",
          fontWeight: 700,
          color: "#e2e8f0",
          letterSpacing: "-0.01em",
        }}
      >
        {label}
      </h2>
    </div>
  );
}
