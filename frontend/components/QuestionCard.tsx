"use client";

import { useState } from "react";

interface Question {
  question_id: string;
  sequence: number;
  topic: string;
  question_text: string;
  source_chunks: string[];
  is_final_question: boolean;
}

interface Props {
  question: Question;
  onAnswer: (answer: string) => void;
  disabled: boolean;
}

const TOPIC_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  "API design":         { bg: "rgba(99,102,241,0.12)",  text: "#a5b4fc", border: "rgba(99,102,241,0.25)"  },
  databases:            { bg: "rgba(34,211,238,0.10)",  text: "#67e8f9", border: "rgba(34,211,238,0.2)"   },
  caching:              { bg: "rgba(167,139,250,0.10)", text: "#c4b5fd", border: "rgba(167,139,250,0.2)"  },
  concurrency:          { bg: "rgba(251,191,36,0.10)",  text: "#fde68a", border: "rgba(251,191,36,0.2)"   },
  "system design":      { bg: "rgba(239,68,68,0.10)",   text: "#fca5a5", border: "rgba(239,68,68,0.2)"    },
  testing:              { bg: "rgba(34,197,94,0.10)",   text: "#86efac", border: "rgba(34,197,94,0.2)"    },
  security:             { bg: "rgba(249,115,22,0.10)",  text: "#fdba74", border: "rgba(249,115,22,0.2)"   },
  performance:          { bg: "rgba(236,72,153,0.10)",  text: "#f9a8d4", border: "rgba(236,72,153,0.2)"   },
  "supervised learning":{ bg: "rgba(99,102,241,0.12)",  text: "#a5b4fc", border: "rgba(99,102,241,0.25)"  },
  "neural networks":    { bg: "rgba(139,92,246,0.12)",  text: "#c4b5fd", border: "rgba(139,92,246,0.25)"  },
  NLP:                  { bg: "rgba(34,211,238,0.10)",  text: "#67e8f9", border: "rgba(34,211,238,0.2)"   },
  "model evaluation":   { bg: "rgba(34,197,94,0.10)",   text: "#86efac", border: "rgba(34,197,94,0.2)"    },
  "feature engineering":{ bg: "rgba(251,191,36,0.10)",  text: "#fde68a", border: "rgba(251,191,36,0.2)"   },
  "deep learning":      { bg: "rgba(239,68,68,0.10)",   text: "#fca5a5", border: "rgba(239,68,68,0.2)"    },
  "ML ops":             { bg: "rgba(249,115,22,0.10)",  text: "#fdba74", border: "rgba(249,115,22,0.2)"   },
  statistics:           { bg: "rgba(167,139,250,0.10)", text: "#c4b5fd", border: "rgba(167,139,250,0.2)"  },
};

function getTopicStyle(topic: string) {
  const t = topic?.toLowerCase();
  for (const [key, style] of Object.entries(TOPIC_COLORS)) {
    if (t?.includes(key.toLowerCase())) return style;
  }
  return { bg: "rgba(99,102,241,0.12)", text: "#a5b4fc", border: "rgba(99,102,241,0.25)" };
}

export default function QuestionCard({ question, onAnswer, disabled }: Props) {
  const [answer, setAnswer] = useState("");
  const wordCount = answer.trim() ? answer.trim().split(/\s+/).length : 0;
  const topicStyle = getTopicStyle(question.topic);

  const handleSubmit = () => {
    if (!answer.trim()) return;
    onAnswer(answer.trim());
    setAnswer("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && e.ctrlKey) handleSubmit();
  };

  return (
    <div
      className="card card-glow animate-fade-in"
      style={{ padding: 0, overflow: "hidden" }}
    >
      {/* ── Question Header ─────────────────────────────── */}
      <div
        style={{
          padding: "1.25rem 1.75rem",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
          {/* Sequence circle */}
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.8125rem",
              fontWeight: 700,
              color: "white",
              flexShrink: 0,
              boxShadow: "0 0 16px rgba(99,102,241,0.4)",
            }}
          >
            {question.sequence}
          </div>
          <div>
            <p style={{ fontSize: "0.75rem", color: "#475569", fontWeight: 500 }}>
              Question {question.sequence}
            </p>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "0.15rem 0.625rem",
                fontSize: "0.7rem",
                fontWeight: 700,
                borderRadius: 9999,
                background: topicStyle.bg,
                color: topicStyle.text,
                border: `1px solid ${topicStyle.border}`,
                letterSpacing: "0.03em",
                textTransform: "capitalize",
              }}
            >
              {question.topic}
            </span>
          </div>
        </div>

        {question.is_final_question && (
          <span className="badge badge-warning">
            🏁 Final Question
          </span>
        )}
      </div>

      {/* ── Question Body ───────────────────────────────── */}
      <div style={{ padding: "1.75rem" }}>
        {/* Question text */}
        <p
          style={{
            fontSize: "1.0625rem",
            fontWeight: 500,
            color: "#e2e8f0",
            lineHeight: 1.7,
            marginBottom: "1.5rem",
          }}
        >
          {question.question_text}
        </p>

        {/* Source chunks hint */}
        {question.source_chunks && question.source_chunks.length > 0 && (
          <div
            className="alert-info"
            style={{ marginBottom: "1.25rem", fontSize: "0.75rem" }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0, marginTop: 1 }}>
              <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" stroke="#818cf8" strokeWidth="2" />
              <line x1="12" y1="16" x2="12" y2="12" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" />
              <line x1="12" y1="8" x2="12.01" y2="8" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span>
              Grounded in {question.source_chunks.length} reference chunk
              {question.source_chunks.length > 1 ? "s" : ""} from the knowledge base
            </span>
          </div>
        )}

        {/* Answer area */}
        <div style={{ position: "relative" }}>
          <textarea
            id={`answer-input-${question.question_id}`}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your answer here... (Ctrl+Enter to submit)"
            rows={6}
            className="input-field"
            disabled={disabled}
            style={{ paddingBottom: "2.5rem" }}
          />
          {/* Word counter inside textarea */}
          <span
            style={{
              position: "absolute",
              bottom: "0.75rem",
              right: "0.875rem",
              fontSize: "0.7rem",
              fontWeight: 500,
              color: wordCount > 0 ? "#6366f1" : "#334155",
              pointerEvents: "none",
              transition: "color 0.2s",
            }}
          >
            {wordCount} {wordCount === 1 ? "word" : "words"}
          </span>
        </div>

        {/* Submit button */}
        <button
          id={`submit-answer-btn-${question.question_id}`}
          onClick={handleSubmit}
          disabled={disabled || !answer.trim()}
          className="btn-primary"
          style={{ marginTop: "1rem" }}
        >
          {disabled ? (
            <><span className="spinner" style={{ width: 16, height: 16 }} /> Submitting...</>
          ) : (
            <>
              Submit Answer
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
