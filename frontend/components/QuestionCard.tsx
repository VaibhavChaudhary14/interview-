"use client";

import { useState, useEffect } from "react";
import { useAnswerInput } from "@/hooks/useAnswerInput";

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
  sessionId: string;
  audioAllowed: boolean;
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

export default function QuestionCard({
  question,
  onAnswer,
  disabled,
  sessionId,
  audioAllowed,
}: Props) {
  const [answer, setAnswer] = useState("");
  const [localAudioAllowed, setLocalAudioAllowed] = useState(audioAllowed);
  const [transcribing, setTranscribing] = useState(false);
  const [uiError, setUiError] = useState<string | null>(null);

  const wordCount = answer.trim() ? answer.trim().split(/\s+/).length : 0;
  const topicStyle = getTopicStyle(question.topic);

  const {
    isRecording,
    startRecording,
    stopRecording,
    uploadRecording,
    error: micError,
  } = useAnswerInput({
    sessionId,
    questionId: question.question_id,
    audioAllowed: localAudioAllowed,
  });

  // Automatically degrade to text-only mode on mic permissions/access errors
  useEffect(() => {
    if (micError) {
      setUiError(micError);
      setLocalAudioAllowed(false);
    }
  }, [micError]);

  const handleSubmit = () => {
    if (!answer.trim()) return;
    onAnswer(answer.trim());
    setAnswer("");
    setUiError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && e.ctrlKey) handleSubmit();
  };

  const handleStopAndTranscribe = async () => {
    setTranscribing(true);
    setUiError(null);
    try {
      const audioBlob = await stopRecording();
      if (!audioBlob) {
        throw new Error("No audio recorded.");
      }
      const uploadRes = await uploadRecording(audioBlob);
      if (uploadRes) {
        if (uploadRes.status === "pending") {
          // Keep transcribing true while we poll the webhook status
          const interval = setInterval(async () => {
            try {
              const statusRes = await fetch(
                `/api/v1/sessions/${sessionId}/answers/${question.question_id}/transcript-status`
              );
              if (statusRes.ok) {
                const statusData = await statusRes.json();
                if (statusData.status === "completed") {
                  clearInterval(interval);
                  setAnswer(statusData.transcript || "");
                  setTranscribing(false);
                } else if (statusData.status === "error") {
                  clearInterval(interval);
                  setTranscribing(false);
                  setUiError("Transcription failed. You can type your answer instead.");
                  setLocalAudioAllowed(false);
                }
              }
            } catch (err) {
              // keep polling
            }
          }, 3000);
        } else if (uploadRes.status === "completed" && uploadRes.transcript) {
          setAnswer(uploadRes.transcript);
          setTranscribing(false);
        } else {
          throw new Error(uploadRes.message || "Transcription failed.");
        }
      } else {
        throw new Error("Upload failed.");
      }
    } catch (e: any) {
      setTranscribing(false);
      const msg = (e.message || "").toLowerCase();
      if (msg.includes("rate limit") || msg.includes("429")) {
        setUiError("Too many people practicing right now. Please try again in 5 minutes.");
      } else if (msg.includes("api key") || msg.includes("key missing")) {
        setUiError("Service temporarily unavailable. Your recording was saved—we'll transcribe it in the background.");
      } else {
        setUiError("Couldn't process your audio recording. Switching to manual typing fallback.");
      }
      setLocalAudioAllowed(false);
    }
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

        {/* Runtime notifications / warnings */}
        {uiError && (
          <div className="alert-error" style={{ marginBottom: "1rem", fontSize: "0.8125rem" }}>
            <span style={{ marginRight: "0.5rem" }}>⚠️</span>
            {uiError}
          </div>
        )}

        {/* Voice Input Section */}
        {localAudioAllowed ? (
          <div style={{ marginBottom: "1.5rem" }}>
            {transcribing ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "2rem",
                  background: "rgba(255,255,255,0.02)",
                  border: "1px dashed rgba(99,102,241,0.25)",
                  borderRadius: "0.75rem",
                  gap: "0.875rem",
                }}
              >
                <span className="spinner" style={{ width: 24, height: 24 }} />
                <p style={{ fontSize: "0.875rem", color: "#a5b4fc", fontWeight: 500 }}>
                  Converting your response to text using Whisper...
                </p>
              </div>
            ) : isRecording ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "2rem",
                  background: "rgba(239,68,68,0.03)",
                  border: "1px solid rgba(239,68,68,0.15)",
                  borderRadius: "0.75rem",
                  gap: "1.25rem",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span className="pulse-dot" style={{ width: 10, height: 10, background: "#ef4444", borderRadius: "50%" }} />
                  <span style={{ fontSize: "0.875rem", color: "#ef4444", fontWeight: 700, letterSpacing: "0.05em" }}>
                    RECORDING VOICE RESPONSE
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleStopAndTranscribe}
                  disabled={disabled}
                  style={{
                    padding: "0.75rem 1.5rem",
                    background: "#ef4444",
                    color: "white",
                    fontWeight: 600,
                    borderRadius: "0.5rem",
                    border: "none",
                    cursor: "pointer",
                    boxShadow: "0 0 16px rgba(239,68,68,0.4)",
                  }}
                >
                  Stop Recording & Transcribe
                </button>
              </div>
            ) : (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "2rem",
                  background: "rgba(255,255,255,0.02)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  borderRadius: "0.75rem",
                  gap: "1.25rem",
                }}
              >
                <p style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
                  Conduct this question by speaking your answer.
                </p>
                <div style={{ display: "flex", gap: "1rem" }}>
                  <button
                    type="button"
                    onClick={startRecording}
                    disabled={disabled}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.5rem",
                      padding: "0.75rem 1.5rem",
                      background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                      color: "white",
                      fontWeight: 600,
                      borderRadius: "0.5rem",
                      border: "none",
                      cursor: "pointer",
                      boxShadow: "0 0 16px rgba(99,102,241,0.4)",
                    }}
                  >
                    🎤 Start Voice Input
                  </button>
                  <button
                    type="button"
                    onClick={() => setLocalAudioAllowed(false)}
                    style={{
                      padding: "0.75rem 1.5rem",
                      background: "none",
                      border: "1px solid rgba(255,255,255,0.1)",
                      color: "#94a3b8",
                      borderRadius: "0.5rem",
                      cursor: "pointer",
                    }}
                  >
                    Type response instead
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : null}

        {/* Text Input / Review Area */}
        {(!localAudioAllowed || answer.trim() !== "") && (
          <div style={{ position: "relative", marginTop: "1rem" }}>
            {localAudioAllowed && answer.trim() !== "" && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                <span style={{ fontSize: "0.75rem", color: "#a5b4fc", fontWeight: 600 }}>
                  ✨ Review and edit your voice transcription below:
                </span>
                <button
                  type="button"
                  onClick={() => { setAnswer(""); setUiError(null); }}
                  style={{ fontSize: "0.75rem", color: "#64748b", background: "none", border: "none", cursor: "pointer" }}
                >
                  Re-record
                </button>
              </div>
            )}
            {!localAudioAllowed && audioAllowed && (
              <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "0.5rem" }}>
                <button
                  type="button"
                  onClick={() => setLocalAudioAllowed(true)}
                  style={{
                    fontSize: "0.75rem",
                    color: "#a5b4fc",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    fontWeight: 600,
                  }}
                >
                  🎤 Switch back to voice response
                </button>
              </div>
            )}
            <textarea
              id={`answer-input-${question.question_id}`}
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={localAudioAllowed ? "Your transcribed text will appear here. You can edit it." : "Type your answer here... (Ctrl+Enter to submit)"}
              rows={6}
              className="input-field"
              disabled={disabled || transcribing}
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
        )}

        {/* Submit button */}
        {(!localAudioAllowed || answer.trim() !== "") && (
          <button
            id={`submit-answer-btn-${question.question_id}`}
            onClick={handleSubmit}
            disabled={disabled || !answer.trim() || transcribing}
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
        )}
      </div>
    </div>
  );
}
