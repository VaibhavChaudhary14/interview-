"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import QuestionCard from "@/components/QuestionCard";
import ProgressBar from "@/components/ProgressBar";
import ConsentModal from "@/components/ConsentModal";

interface Question {
  question_id: string;
  sequence: number;
  topic: string;
  question_text: string;
  source_chunks: string[];
  is_final_question: boolean;
}

interface SessionStatus {
  session_id: string;
  status: string;
  role: string;
  questions_asked: number;
  max_questions: number;
  report_available: boolean;
}

const ROLE_LABELS: Record<string, string> = {
  backend_engineer: "Backend Engineer",
  ai_ml_engineer: "AI / ML Engineer",
};

export default function InterviewPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [question, setQuestion] = useState<Question | null>(null);
  const [sessionStatus, setSessionStatus] = useState<SessionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [transitioning, setTransitioning] = useState(false);

  const [consentChecked, setConsentChecked] = useState(false);
  const [audioAllowed, setAudioAllowed] = useState(false);
  const [showConsentModal, setShowConsentModal] = useState(false);

  const fetchSessionStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}`);
      if (res.ok) setSessionStatus(await res.json());
    } catch { /* ignore */ }
  }, [sessionId]);

  const fetchNextQuestion = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}/next-question`);
      if (res.status === 409) {
        const data = await res.json();
        if (
          data.detail?.error_code === "ALL_QUESTIONS_ASKED" ||
          data.detail?.error_code === "SESSION_COMPLETED"
        ) {
          await endAndGoToSummary();
          return;
        }
      }
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail?.message || "Failed to fetch question");
      }
      const data = await res.json();
      setTransitioning(true);
      setTimeout(() => {
        setQuestion(data);
        setTransitioning(false);
      }, 200);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const fetchConsentStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}/consent`);
      if (res.ok) {
        const data = await res.json();
        setAudioAllowed(data.audio_recording_allowed);
        setConsentChecked(true);
        fetchNextQuestion();
      } else if (res.status === 404) {
        setShowConsentModal(true);
      } else {
        setConsentChecked(true);
        fetchNextQuestion();
      }
    } catch {
      setConsentChecked(true);
      fetchNextQuestion();
    }
  }, [sessionId, fetchNextQuestion]);

  useEffect(() => {
    fetchSessionStatus();
    fetchConsentStatus();
  }, [fetchConsentStatus, fetchSessionStatus]);

  const handleConsentResolved = (allowed: boolean) => {
    setAudioAllowed(allowed);
    setConsentChecked(true);
    setShowConsentModal(false);
    fetchNextQuestion();
  };

  const handleAnswer = async (answerText: string) => {
    if (!question) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}/answers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: question.question_id, answer_text: answerText }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail?.message || "Failed to submit answer");
      }
      const data = await res.json();
      setSessionStatus((prev) =>
        prev ? { ...prev, questions_asked: data.questions_asked, status: data.session_status } : prev
      );

      if (question.is_final_question || data.session_status === "COMPLETED" || data.questions_remaining === 0) {
        await endAndGoToSummary();
      } else {
        fetchNextQuestion();
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const endAndGoToSummary = async () => {
    try {
      await fetch(`/api/v1/sessions/${sessionId}/end`, { method: "POST" });
      await fetch(`/api/v1/sessions/${sessionId}/report`, { method: "POST" });
    } catch { /* proceed anyway */ }
    router.push(`/summary/${sessionId}`);
  };

  const handleEndEarly = async () => {
    if (!confirm("End the interview now and view your report?")) return;
    await endAndGoToSummary();
  };

  if (showConsentModal) {
    return (
      <ConsentModal
        sessionId={sessionId}
        onResolved={handleConsentResolved}
      />
    );
  }

  /* ── Loading skeleton ──────────────────────────────────── */
  if (loading && !question) {
    return (
      <div className="animate-fade-in">
        <div className="card" style={{ textAlign: "center", padding: "3rem 2rem" }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              background: "rgba(99,102,241,0.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 1.25rem",
            }}
          >
            <span className="spinner" style={{ width: 24, height: 24, borderWidth: 3 }} />
          </div>
          <p style={{ fontSize: "0.9375rem", fontWeight: 600, color: "#e2e8f0", marginBottom: "0.375rem" }}>
            Generating your question…
          </p>
          <p style={{ fontSize: "0.8125rem", color: "#64748b" }}>
            The AI is retrieving context and building your next question
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* ── Session header ─────────────────────────────────── */}
      {sessionStatus && (
        <div
          className="animate-fade-in"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "1rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
            <span className="badge badge-primary">
              {ROLE_LABELS[sessionStatus.role] || sessionStatus.role}
            </span>
            <span className="badge badge-accent">{sessionStatus.status}</span>
          </div>
          <button
            id="end-interview-btn"
            onClick={handleEndEarly}
            style={{
              fontSize: "0.8125rem",
              color: "#64748b",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "0.375rem 0.75rem",
              borderRadius: 8,
              transition: "color 0.2s, background 0.2s",
            }}
            onMouseEnter={(e) => {
              (e.target as HTMLElement).style.color = "#fca5a5";
              (e.target as HTMLElement).style.background = "rgba(239,68,68,0.08)";
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.color = "#64748b";
              (e.target as HTMLElement).style.background = "none";
            }}
          >
            End Early →
          </button>
        </div>
      )}

      {/* ── Progress bar ──────────────────────────────────── */}
      {sessionStatus && (
        <div style={{ marginBottom: "1.25rem" }}>
          <ProgressBar
            current={sessionStatus.questions_asked}
            max={sessionStatus.max_questions}
          />
        </div>
      )}

      {/* ── Error ─────────────────────────────────────────── */}
      {error && (
        <div className="alert-error animate-fade-in-scale" style={{ marginBottom: "1rem" }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
            <circle cx="12" cy="12" r="10" stroke="#f87171" strokeWidth="2" />
            <line x1="12" y1="8" x2="12" y2="12" stroke="#f87171" strokeWidth="2" strokeLinecap="round" />
            <line x1="12" y1="16" x2="12.01" y2="16" stroke="#f87171" strokeWidth="2" strokeLinecap="round" />
          </svg>
          {error}
          <button
            onClick={fetchNextQuestion}
            style={{ marginLeft: "auto", fontSize: "0.8125rem", color: "#a5b4fc", background: "none", border: "none", cursor: "pointer" }}
          >
            Retry
          </button>
        </div>
      )}

      {/* ── Question Card ─────────────────────────────────── */}
      {loading && question ? (
        /* Question transition shimmer */
        <div
          style={{
            opacity: transitioning ? 0 : 1,
            transform: transitioning ? "translateY(8px)" : "translateY(0)",
            transition: "opacity 0.3s, transform 0.3s",
          }}
        >
          <QuestionCard question={question} onAnswer={handleAnswer} disabled={submitting} sessionId={sessionId} audioAllowed={audioAllowed} />
        </div>
      ) : question ? (
        <div
          style={{
            opacity: transitioning ? 0 : 1,
            transform: transitioning ? "translateY(8px)" : "translateY(0)",
            transition: "opacity 0.3s, transform 0.3s",
          }}
        >
          <QuestionCard question={question} onAnswer={handleAnswer} disabled={submitting} sessionId={sessionId} audioAllowed={audioAllowed} />
        </div>
      ) : null}

      {/* ── Subtle "thinking" overlay when loading next question ── */}
      {loading && question && (
        <div
          style={{
            marginTop: "1rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "0.5rem",
            color: "#6366f1",
            fontSize: "0.8125rem",
          }}
        >
          <span className="spinner" style={{ width: 14, height: 14 }} />
          Preparing next question…
        </div>
      )}

    </div>
  );
}
