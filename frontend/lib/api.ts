/**
 * Typed API client for the Candidate Screening System backend.
 * All endpoints live at /api/v1 (proxied by Next.js to the FastAPI backend).
 */

const BASE = "/api/v1";

// ── Shared ──────────────────────────────────────────────────────────────────

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = (body as any)?.detail?.message || (body as any)?.message || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return body as T;
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface Role {
  slug: string;
  label: string;
  kb_ready: boolean;
}

export interface ResumeExtracted {
  skills: string[];
  technologies: string[];
  domains: string[];
  years_experience_estimate: number;
}

export interface ResumeUploadResponse {
  resume_id: string;
  extracted: ResumeExtracted;
}

export interface SessionResponse {
  session_id: string;
  status: string;
  role: string;
  max_questions: number;
}

export interface SessionStatusResponse {
  session_id: string;
  status: string;
  role: string;
  questions_asked: number;
  max_questions: number;
  report_available: boolean;
}

export interface QuestionResponse {
  question_id: string;
  sequence: number;
  topic: string;
  question_text: string;
  source_chunks: string[];
  is_final_question: boolean;
}

export interface AnswerSubmitResponse {
  stored: boolean;
  session_status: string;
  questions_asked: number;
  questions_remaining: number;
}

export interface TranscriptEntry {
  sequence: number;
  question: string;
  answer: string;
  topic: string;
  source_chunks: string[];
}

export interface ReportInsights {
  questions_answered: number;
  average_answer_length_words: number;
  topics_with_thin_answers: string[];
  resume_alignment_note: string;
}

export interface ReportResponse {
  session_id: string;
  role: string;
  generated_at: string;
  topics_covered: string[];
  transcript: TranscriptEntry[];
  insights: ReportInsights;
}

// ── API functions ─────────────────────────────────────────────────────────────

export const api = {
  getRoles(): Promise<{ roles: Role[] }> {
    return request("/roles");
  },

  async uploadResume(file: File): Promise<ResumeUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${BASE}/resume`, { method: "POST", body: formData });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error((body as any)?.detail?.message || "Upload failed");
    return body as ResumeUploadResponse;
  },

  createSession(resumeId: string, role: string): Promise<SessionResponse> {
    return request("/sessions", {
      method: "POST",
      body: JSON.stringify({ resume_id: resumeId, role }),
    });
  },

  getSession(sessionId: string): Promise<SessionStatusResponse> {
    return request(`/sessions/${sessionId}`);
  },

  getNextQuestion(sessionId: string): Promise<QuestionResponse> {
    return request(`/sessions/${sessionId}/next-question`);
  },

  submitAnswer(sessionId: string, questionId: string, answerText: string): Promise<AnswerSubmitResponse> {
    return request(`/sessions/${sessionId}/answers`, {
      method: "POST",
      body: JSON.stringify({ question_id: questionId, answer_text: answerText }),
    });
  },

  endSession(sessionId: string): Promise<{ status: string }> {
    return request(`/sessions/${sessionId}/end`, { method: "POST" });
  },

  generateReport(sessionId: string): Promise<{ report_id: string; status: string }> {
    return request(`/sessions/${sessionId}/report`, { method: "POST" });
  },

  getReport(sessionId: string): Promise<ReportResponse> {
    return request(`/sessions/${sessionId}/report`);
  },
};
