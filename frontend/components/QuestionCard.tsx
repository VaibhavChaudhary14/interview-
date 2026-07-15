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
  copilot_hints?: {
    outline: string[];
    keywords: string[];
  };
  reference_texts?: {
    id: string;
    text: string;
    source_doc: string;
    page: string;
  }[];
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
  "ml ops":             { bg: "rgba(249,115,22,0.10)",  text: "#fdba74", border: "rgba(249,115,22,0.2)"   },
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

  // AI Copilot features
  const [showCopilot, setShowCopilot] = useState(true);
  const [playingTTS, setPlayingTTS] = useState(false);
  const [ttsAudio, setTtsAudio] = useState<HTMLAudioElement | null>(null);

  const wordCount = answer.trim() ? answer.trim().split(/\s+/).length : 0;
  const topicStyle = getTopicStyle(question.topic);

  const {
    isRecording,
    autoStopping,
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

  // Clean up states when question changes
  useEffect(() => {
    setAnswer("");
    setUiError(null);
    if (ttsAudio) {
      ttsAudio.pause();
    }
    setPlayingTTS(false);
    setTtsAudio(null);
  }, [question.question_id]);

  // Cleanup TTS on unmount
  useEffect(() => {
    return () => {
      if (ttsAudio) {
        ttsAudio.pause();
      }
    };
  }, [ttsAudio]);

  const handleSubmit = () => {
    if (!answer.trim()) return;
    onAnswer(answer.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && e.ctrlKey) handleSubmit();
  };

  const handlePlayTTS = async () => {
    if (playingTTS) {
      if (ttsAudio) {
        ttsAudio.pause();
      }
      setPlayingTTS(false);
      setTtsAudio(null);
      return;
    }

    setPlayingTTS(true);
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: question.question_text }),
      });
      if (!res.ok) throw new Error("TTS generation failed");
      const blob = await res.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      setTtsAudio(audio);
      audio.play();
      audio.onended = () => {
        setPlayingTTS(false);
        setTtsAudio(null);
        URL.revokeObjectURL(audioUrl);
      };
    } catch (err) {
      console.error(err);
      setPlayingTTS(false);
    }
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
    <div style={{ display: "grid", gridTemplateColumns: showCopilot ? "1fr 380px" : "1fr", gap: "1.5rem", alignItems: "start" }}>
      <style>{`
        @keyframes activeWave {
          0%, 100% { transform: scaleY(0.35); }
          50% { transform: scaleY(1.3); }
        }
        @keyframes pulseAlert {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; }
        }
        .visualizer-bar {
          display: inline-block;
          width: 4px;
          height: 36px;
          background: linear-gradient(to top, var(--color-primary), var(--color-accent));
          border-radius: 2px;
          margin: 0 3px;
          transform-origin: center;
          animation: activeWave 1.2s ease-in-out infinite;
        }
        .recording-visualizer-bar {
          display: inline-block;
          width: 4px;
          height: 36px;
          background: linear-gradient(to top, #ef4444, #fca5a5);
          border-radius: 2px;
          margin: 0 3px;
          transform-origin: center;
          animation: activeWave 0.8s ease-in-out infinite;
        }
        .pulse-dot {
          animation: pulseAlert 1.5s infinite;
        }
      `}</style>

      {/* ── Main Interview Panel ─────────────────────────── */}
      <div
        className="card card-glow animate-fade-in"
        style={{ padding: 0, overflow: "hidden" }}
      >
        {/* ── Card Header ─────────────────────────────── */}
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
              <p style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 500 }}>
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

          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            {question.is_final_question && (
              <span className="badge badge-warning" style={{ fontSize: "0.7rem" }}>
                🏁 Final Question
              </span>
            )}
            <button
              type="button"
              onClick={() => setShowCopilot(!showCopilot)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.375rem",
                padding: "0.375rem 0.75rem",
                background: showCopilot ? "rgba(99,102,241,0.15)" : "none",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                color: showCopilot ? "#a5b4fc" : "#64748b",
                fontSize: "0.75rem",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              🤖 {showCopilot ? "Hide Copilot" : "Show Copilot"}
            </button>
          </div>
        </div>

        {/* ── Card Body ───────────────────────────────── */}
        <div style={{ padding: "1.75rem" }}>
          {/* Question text */}
          <p
            style={{
              fontSize: "1.125rem",
              fontWeight: 500,
              color: "#e2e8f0",
              lineHeight: 1.7,
              marginBottom: "1.5rem",
            }}
          >
            {question.question_text}
          </p>

          {/* Runtime notifications / warnings */}
          {uiError && (
            <div className="alert-error" style={{ marginBottom: "1.25rem", fontSize: "0.8125rem" }}>
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
                  <div style={{ display: "flex", alignItems: "center", height: "30px", marginBottom: "0.25rem" }}>
                    {[...Array(6)].map((_, i) => (
                      <div
                        key={i}
                        className="visualizer-bar"
                        style={{ animationDelay: `${i * 0.15}s`, height: "20px" }}
                      />
                    ))}
                  </div>
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
                    background: autoStopping
                      ? "rgba(251,191,36,0.04)"
                      : "rgba(239,68,68,0.03)",
                    border: `1px solid ${autoStopping ? "rgba(251,191,36,0.2)" : "rgba(239,68,68,0.15)"}`,
                    borderRadius: "0.75rem",
                    gap: "1.25rem",
                    transition: "background 0.3s, border-color 0.3s",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span
                      className="pulse-dot"
                      style={{
                        width: 10,
                        height: 10,
                        background: autoStopping ? "#fbbf24" : "#ef4444",
                        borderRadius: "50%",
                        transition: "background 0.3s",
                      }}
                    />
                    <span
                      style={{
                        fontSize: "0.875rem",
                        color: autoStopping ? "#fbbf24" : "#ef4444",
                        fontWeight: 700,
                        letterSpacing: "0.05em",
                        transition: "color 0.3s",
                      }}
                    >
                      {autoStopping ? "FINISHING UP…" : "RECORDING VOICE RESPONSE"}
                    </span>
                  </div>
                  {autoStopping && (
                    <p style={{ fontSize: "0.75rem", color: "#94a3b8", margin: 0, textAlign: "center" }}>
                      Silence detected — stopping in a moment. Keep talking to continue.
                    </p>
                  )}
                  {/* Soundwave animation */}
                  <div style={{ display: "flex", alignItems: "center", height: "40px" }}>
                    {[...Array(12)].map((_, i) => (
                      <div
                        key={i}
                        className="recording-visualizer-bar"
                        style={{
                          animationDelay: `${(i % 4) * 0.15 + 0.1}s`,
                          height: `${14 + (i % 3) * 8}px`,
                          opacity: autoStopping ? 0.4 : 1,
                          transition: "opacity 0.3s",
                        }}
                      />
                    ))}
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
                placeholder={localAudioAllowed ? "Your transcribed text will appear here. You can edit it before submitting." : "Type your answer here... (Ctrl+Enter to submit)"}
                rows={7}
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
              style={{ marginTop: "1.25rem" }}
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

      {/* ── Right side: AI Copilot Coach Panel ─────────────────── */}
      {showCopilot && (
        <div
          className="card card-glow animate-fade-in"
          style={{
            padding: "1.5rem",
            position: "sticky",
            top: "80px",
            background: "rgba(22,25,38,0.9)",
            backdropFilter: "blur(8px)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {/* Header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <div
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #22d3ee, #8b5cf6)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 0 10px rgba(34,211,238,0.3)",
                }}
              >
                <span style={{ fontSize: "0.75rem" }}>🤖</span>
              </div>
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "#f8fafc", margin: 0 }}>AI Copilot Coach</h3>
            </div>
            <span
              className="badge badge-accent"
              style={{
                fontSize: "0.625rem",
                padding: "0.15rem 0.5rem",
                background: "rgba(34,211,238,0.08)",
                border: "1px solid rgba(34,211,238,0.2)",
              }}
            >
              <span className="pulse-dot" style={{ width: 6, height: 6, background: "#22d3ee", borderRadius: "50%", marginRight: 4, display: "inline-block" }} />
              ACTIVE HELP
            </span>
          </div>

          {/* TTS Player section */}
          <div
            style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.05)",
              borderRadius: "8px",
              padding: "0.75rem 0.875rem",
              marginBottom: "1.25rem",
            }}
          >
            <p style={{ fontSize: "0.6875rem", color: "#64748b", fontWeight: 600, letterSpacing: "0.05em", marginBottom: "0.5rem", textTransform: "uppercase" }}>
              Voice Reader
            </p>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <button
                type="button"
                onClick={handlePlayTTS}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  padding: "0.45rem 0.875rem",
                  background: playingTTS ? "rgba(239,68,68,0.15)" : "rgba(34,211,238,0.1)",
                  border: playingTTS ? "1px solid rgba(239,68,68,0.3)" : "1px solid rgba(34,211,238,0.3)",
                  borderRadius: "6px",
                  color: playingTTS ? "#fca5a5" : "#67e8f9",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
              >
                {playingTTS ? "⏹ Stop Speech" : "🔊 Read Aloud"}
              </button>
              {playingTTS && (
                <div style={{ display: "flex", gap: "2px", height: "14px", alignItems: "center" }}>
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      style={{
                        width: "2px",
                        height: "100%",
                        background: "#22d3ee",
                        borderRadius: "1px",
                        animation: "activeWave 1s ease-in-out infinite",
                        animationDelay: `${i * 0.15}s`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Suggested Outline Section */}
          {question.copilot_hints?.outline && question.copilot_hints.outline.length > 0 && (
            <div style={{ marginBottom: "1.25rem" }}>
              <h4 style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: "0.625rem", borderLeft: "2px solid #8b5cf6", paddingLeft: "0.5rem" }}>
                Recommended Outline
              </h4>
              <ul style={{ paddingLeft: "1.15rem", margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {question.copilot_hints.outline.map((point, idx) => (
                  <li key={idx} style={{ fontSize: "0.75rem", color: "#cbd5e1", lineHeight: 1.45 }}>
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Interactive Keywords Checklist */}
          {question.copilot_hints?.keywords && question.copilot_hints.keywords.length > 0 && (
            <div style={{ marginBottom: "1.25rem" }}>
              <h4 style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: "0.625rem", borderLeft: "2px solid #22d3ee", paddingLeft: "0.5rem" }}>
                Keywords Checklist
              </h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                {question.copilot_hints.keywords.map((kw, idx) => {
                  const isCovered = answer.toLowerCase().includes(kw.toLowerCase());
                  return (
                    <span
                      key={idx}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        padding: "0.25rem 0.5rem",
                        borderRadius: "4px",
                        fontSize: "0.6875rem",
                        fontWeight: 600,
                        border: isCovered ? "1px solid rgba(34,197,94,0.3)" : "1px solid rgba(255,255,255,0.05)",
                        background: isCovered ? "rgba(34,197,94,0.12)" : "rgba(255,255,255,0.01)",
                        color: isCovered ? "#86efac" : "#64748b",
                        transition: "all 0.25s ease",
                        boxShadow: isCovered ? "0 0 8px rgba(34,197,94,0.15)" : "none",
                      }}
                    >
                      {isCovered ? "✓ " : "○ "}
                      {kw}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* RAG Reference Materials */}
          {question.reference_texts && question.reference_texts.length > 0 && (
            <div>
              <h4 style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: "0.625rem", borderLeft: "2px solid #6366f1", paddingLeft: "0.5rem" }}>
                Knowledge References
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {question.reference_texts.map((ref, idx) => (
                  <details
                    key={idx}
                    style={{
                      background: "rgba(255,255,255,0.01)",
                      border: "1px solid rgba(255,255,255,0.04)",
                      borderRadius: "6px",
                      padding: "0.5rem",
                      cursor: "pointer",
                    }}
                  >
                    <summary style={{ fontSize: "0.7rem", color: "#818cf8", fontWeight: 600, outline: "none", userSelect: "none" }}>
                      📄 {ref.source_doc} (p. {ref.page})
                    </summary>
                    <p
                      style={{
                        fontSize: "0.6875rem",
                        color: "#94a3b8",
                        lineHeight: 1.45,
                        marginTop: "0.375rem",
                        borderTop: "1px dashed rgba(255,255,255,0.04)",
                        paddingTop: "0.375rem",
                        whiteSpace: "pre-line",
                        cursor: "text",
                      }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {ref.text}
                    </p>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
