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
  answer_id?: string;
}

interface Insights {
  questions_answered: number;
  average_answer_length_words: number;
  topics_with_thin_answers: string[];
  resume_alignment_note: string;
}

interface DeliverySummary {
  avg_wpm: number | null;
  total_filler_words: number;
  most_common_filler: string | null;
  question_with_longest_pause: { answer_id: string; pause_seconds: number } | null;
  answers_with_metrics: number;
}

interface AnswerMetrics {
  status: "ready" | "error" | "not_computed";
  wpm?: number;
  word_count?: number;
  audio_duration_seconds?: number;
  pause_count?: number;
  avg_pause_duration?: number;
  longest_pause_seconds?: number;
  filler_word_count?: number;
  filler_word_breakdown?: { unambiguous: Record<string, number>; contextual: Record<string, number> };
}

interface Report {
  session_id: string;
  role: string;
  generated_at: string;
  topics_covered: string[];
  transcript: TranscriptEntry[];
  insights: Insights;
  delivery_summary?: DeliverySummary | null;
  has_feedback?: boolean;
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
  // Per-answer metrics polled after the report loads
  const [metricsMap, setMetricsMap] = useState<Record<string, AnswerMetrics>>({});
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

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

  // Poll /metrics for every answer once the report is loaded
  useEffect(() => {
    if (!report) return;
    const sessionId_ = report.session_id;

    // Only poll metrics for answers that actually have a recording associated
    const answerIds: string[] = report.transcript
      .filter((e) => e.recording_id)
      .map((e) => e.answer_id)
      .filter((id): id is string => !!id);

    if (answerIds.length === 0) return;

    const MAX_POLLS = 15;
    const INTERVAL_MS = 2000;
    const pollCounts: Record<string, number> = {};

    const intervals: NodeJS.Timeout[] = [];

    answerIds.forEach((answerId) => {
      pollCounts[answerId] = 0;
      const id = setInterval(async () => {
        pollCounts[answerId] = (pollCounts[answerId] || 0) + 1;
        if (pollCounts[answerId] > MAX_POLLS) {
          clearInterval(id);
          return;
        }
        try {
          const res = await fetch(`/api/v1/sessions/${sessionId_}/answers/${answerId}/metrics`);
          if (!res.ok) return;
          const data: AnswerMetrics = await res.json();
          setMetricsMap((prev) => ({ ...prev, [answerId]: data }));
          if (data.status === "ready" || data.status === "error") {
            clearInterval(id);
          }
        } catch {
          // Network error — will retry
        }
      }, INTERVAL_MS);
      intervals.push(id);
    });

    return () => intervals.forEach(clearInterval);
  }, [report]);

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
    <div style={{ maxWidth: 880, margin: "0 auto" }}>
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

      {/* ── Delivery Insights ─────────────────────────────── */}
      <DeliveryInsightsCard
        sessionId={sessionId}
        transcript={report.transcript}
        metricsMap={metricsMap}
        deliverySummary={report.delivery_summary}
      />

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

      {/* ── Feedback Widget ───────────────────────────────── */}
      {report && !report.has_feedback && !feedbackSubmitted ? (
        <FeedbackWidget
          sessionId={sessionId}
          onSubmitSuccess={() => setFeedbackSubmitted(true)}
        />
      ) : feedbackSubmitted ? (
        <div className="card animate-fade-in" style={{ marginBottom: "1.5rem", padding: "1.5rem", textAlign: "center", border: "1px solid rgba(16,185,129,0.3)" }}>
          <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#10b981", marginBottom: "0.5rem" }}>
            ✓ Thank you for your feedback!
          </h3>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
            Your review helps us refine question generation and coaching insights.
          </p>
        </div>
      ) : null}

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

// ---------------------------------------------------------------------------
// Delivery Insights Card
// ---------------------------------------------------------------------------

function DeliveryInsightsCard({
  sessionId,
  transcript,
  metricsMap,
  deliverySummary,
}: {
  sessionId: string;
  transcript: TranscriptEntry[];
  metricsMap: Record<string, AnswerMetrics>;
  deliverySummary?: DeliverySummary | null;
}) {
  const readyAnswers = Object.values(metricsMap).filter((m) => m.status === "ready");
  const isComputing = readyAnswers.length < transcript.filter((e) => e.answer_id && e.recording_id).length;

  // Aggregate WPM across ready answers for the summary strip
  const avgWpm = deliverySummary?.avg_wpm ??
    (readyAnswers.length > 0
      ? Math.round(readyAnswers.reduce((s, m) => s + (m.wpm ?? 0), 0) / readyAnswers.length)
      : null);

  const totalFillers = deliverySummary?.total_filler_words ??
    readyAnswers.reduce((s, m) => s + (m.filler_word_count ?? 0), 0);

  const mostCommonFiller = deliverySummary?.most_common_filler ?? null;

  function wpmLabel(wpm: number | null): { text: string; color: string } {
    if (wpm === null) return { text: "—", color: "#64748b" };
    if (wpm < 110) return { text: `${wpm} WPM — a bit slow`, color: "#f59e0b" };
    if (wpm > 170) return { text: `${wpm} WPM — spoke quickly`, color: "#a78bfa" };
    return { text: `${wpm} WPM — good pace ✓`, color: "#22d3ee" };
  }

  const wpm = wpmLabel(avgWpm);

  return (
    <div
      className="card animate-fade-in"
      style={{ marginBottom: "1.25rem", animationDelay: "0.175s" }}
      id="delivery-insights-card"
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <SectionHeader icon="🎙️" label="Delivery Insights" />
        {isComputing && (
          <span style={{ fontSize: "0.75rem", color: "#64748b", display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <span className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
            Computing…
          </span>
        )}
      </div>

      {readyAnswers.length === 0 && isComputing ? (
        <div style={{ marginTop: "1.25rem", textAlign: "center", padding: "1.5rem 0" }}>
          <p style={{ color: "#475569", fontSize: "0.875rem" }}>
            Analysing your speaking pace and delivery patterns…
          </p>
        </div>
      ) : readyAnswers.length === 0 ? (
        <div style={{ marginTop: "1.25rem", textAlign: "center", padding: "1.5rem 0" }}>
          <p style={{ color: "#475569", fontSize: "0.875rem" }}>
            Delivery metrics unavailable for this session.
          </p>
        </div>
      ) : (
        <>
          {/* Summary strip */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
            gap: "0.875rem",
            marginTop: "1.25rem",
          }}>
            {/* WPM */}
            <div style={{
              background: "rgba(255,255,255,0.03)",
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.06)",
              padding: "0.875rem 1rem",
            }}>
              <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.375rem" }}>Speaking Pace</div>
              <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: wpm.color }}>{wpm.text}</div>
            </div>

            {/* Filler words */}
            <div style={{
              background: "rgba(255,255,255,0.03)",
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.06)",
              padding: "0.875rem 1rem",
            }}>
              <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.375rem" }}>Filler Words</div>
              <div style={{ fontSize: "0.9375rem", fontWeight: 700, color: totalFillers > 15 ? "#f59e0b" : "#22d3ee" }}>
                {totalFillers} total
                {mostCommonFiller && <span style={{ fontSize: "0.8rem", fontWeight: 400, color: "#64748b", marginLeft: "0.375rem" }}>("{mostCommonFiller}" most used)</span>}
              </div>
            </div>
          </div>

          {/* Per-question breakdown */}
          <div style={{ marginTop: "1.25rem" }}>
            <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "#475569", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.75rem" }}>Per-Answer Breakdown</p>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {transcript.map((entry, i) => {
                const m = entry.answer_id ? metricsMap[entry.answer_id] : undefined;
                const topicColor = ["#6366f1", "#22d3ee", "#a78bfa", "#f59e0b", "#10b981", "#f43f5e", "#3b82f6", "#8b5cf6"][i % 8];

                return (
                  <div key={entry.sequence} style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "0.75rem",
                    padding: "0.625rem 0.875rem",
                    background: "rgba(255,255,255,0.02)",
                    borderRadius: 8,
                    border: "1px solid rgba(255,255,255,0.04)",
                  }}>
                    <span style={{
                      width: 22, height: 22, borderRadius: "50%",
                      background: `${topicColor}20`, border: `1px solid ${topicColor}40`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "0.6875rem", fontWeight: 700, color: topicColor, flexShrink: 0, marginTop: 2,
                    }}>{entry.sequence}</span>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: "0.8125rem", color: "#94a3b8", marginBottom: "0.25rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {entry.question}
                      </p>

                      {!m || m.status === "not_computed" ? (
                        <span style={{ fontSize: "0.75rem", color: "#475569" }}>Computing…</span>
                      ) : m.status === "error" ? (
                        <span style={{ fontSize: "0.75rem", color: "#475569" }}>Metrics unavailable</span>
                      ) : (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                          {m.wpm != null && (
                            <span style={{
                              fontSize: "0.75rem", fontWeight: 600,
                              color: m.wpm < 110 ? "#f59e0b" : m.wpm > 170 ? "#a78bfa" : "#22d3ee",
                            }}>{m.wpm.toFixed(0)} WPM</span>
                          )}
                          {m.pause_count != null && (
                            <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                              {m.pause_count} pause{m.pause_count !== 1 ? "s" : ""}
                              {m.longest_pause_seconds != null && m.longest_pause_seconds >= 2
                                ? <span style={{ color: "#f59e0b", marginLeft: 3 }}>(longest {m.longest_pause_seconds.toFixed(1)}s ⚠️)</span>
                                : null}
                            </span>
                          )}
                          {m.filler_word_breakdown && (
                            <FillerBadges breakdown={m.filler_word_breakdown} />
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Coaching callout */}
          <div style={{
            marginTop: "1.25rem",
            padding: "0.75rem 1rem",
            background: "rgba(99,102,241,0.06)",
            borderRadius: 10,
            border: "1px solid rgba(99,102,241,0.15)",
          }}>
            <p style={{ fontSize: "0.8125rem", color: "#94a3b8", lineHeight: 1.6 }}>
              <strong style={{ color: "#a5b4fc" }}>💡 Tip:</strong>{" "}
              Brief pauses (under 2s) are natural and can improve clarity — only sustained gaps over 2s are worth watching.
              For filler words, aim to notice them in real-time; awareness alone usually reduces frequency over a few sessions.
            </p>
          </div>
        </>
      )}
    </div>
  );
}

function FillerBadges({
  breakdown,
}: {
  breakdown: { unambiguous: Record<string, number>; contextual: Record<string, number> };
}) {
  const unambiguous = Object.entries(breakdown.unambiguous || {}).filter(([, c]) => c > 0);
  const contextual = Object.entries(breakdown.contextual || {}).filter(([, c]) => c > 0);

  if (unambiguous.length === 0 && contextual.length === 0) {
    return <span style={{ fontSize: "0.75rem", color: "#22d3ee" }}>No fillers ✓</span>;
  }

  return (
    <span style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem", alignItems: "center" }}>
      {unambiguous.map(([word, count]) => (
        <span key={word} style={{
          fontSize: "0.6875rem", fontWeight: 600,
          padding: "0.1rem 0.375rem", borderRadius: 4,
          background: "rgba(245,158,11,0.12)", color: "#f59e0b",
          border: "1px solid rgba(245,158,11,0.25)",
        }}>"{word}" ×{count}</span>
      ))}
      {contextual.map(([word, count]) => (
        <span key={word} style={{
          fontSize: "0.6875rem", fontWeight: 600,
          padding: "0.1rem 0.375rem", borderRadius: 4,
          background: "rgba(100,116,139,0.12)", color: "#94a3b8",
          border: "1px solid rgba(100,116,139,0.2)",
        }}>"{word}" ×{count}</span>
      ))}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Feedback Widget Component
// ---------------------------------------------------------------------------

interface FeedbackWidgetProps {
  sessionId: string;
  onSubmitSuccess: () => void;
}

function FeedbackWidget({ sessionId, onSubmitSuccess }: FeedbackWidgetProps) {
  const [ratingRealistic, setRatingRealistic] = useState<number>(0);
  const [ratingFeedback, setRatingFeedback] = useState<number>(0);
  const [comments, setComments] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (ratingRealistic === 0 || ratingFeedback === 0) {
      setError("Please select a rating for both questions.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rating_realistic: ratingRealistic,
          rating_feedback: ratingFeedback,
          comments: comments.trim() || null,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail?.message || err.message || "Failed to submit feedback");
      }
      onSubmitSuccess();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card animate-fade-in" style={{ marginBottom: "1.5rem", padding: "1.5rem" }} id="feedback-widget-card">
      <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#e2e8f0", marginBottom: "0.5rem" }}>
        💬 Help us improve the AI Coach
      </h3>
      <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "1.25rem" }}>
        Your review helps us refine question realism and coaching accuracy.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {/* Rating 1 */}
        <div>
          <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#cbd5e1", marginBottom: "0.5rem" }}>
            How realistic were the interview questions?
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setRatingRealistic(star)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "1.75rem",
                  color: star <= ratingRealistic ? "#fbbf24" : "#4b5563",
                  transition: "transform 0.1s",
                  padding: 0,
                  outline: "none",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.15)")}
                onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
              >
                ★
              </button>
            ))}
          </div>
        </div>

        {/* Rating 2 */}
        <div>
          <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#cbd5e1", marginBottom: "0.5rem" }}>
            How useful was the speech coaching & filler word analysis?
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setRatingFeedback(star)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "1.75rem",
                  color: star <= ratingFeedback ? "#fbbf24" : "#4b5563",
                  transition: "transform 0.1s",
                  padding: 0,
                  outline: "none",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.15)")}
                onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
              >
                ★
              </button>
            ))}
          </div>
        </div>

        {/* Comments */}
        <div>
          <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#cbd5e1", marginBottom: "0.5rem" }}>
            Optional: Any thoughts on what we can improve?
          </div>
          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder="e.g. The questions were too easy, or filler words missed some instances of 'like'..."
            style={{
              width: "100%",
              minHeight: "75px",
              padding: "0.75rem",
              borderRadius: "6px",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.08)",
              color: "#f8fafc",
              fontSize: "0.85rem",
              outline: "none",
              resize: "vertical",
            }}
          />
        </div>

        {error && (
          <div style={{ fontSize: "0.8125rem", color: "#f87171" }}>
            ⚠️ {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="btn-primary"
          style={{ padding: "0.625rem 1.25rem", fontSize: "0.875rem", alignSelf: "flex-start", marginTop: "0.25rem" }}
        >
          {submitting ? "Submitting..." : "Submit Review"}
        </button>
      </div>
    </div>
  );
}
