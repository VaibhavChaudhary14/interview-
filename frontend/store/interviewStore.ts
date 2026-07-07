/**
 * Zustand store for interview session state.
 * Persists current session across page refreshes (server is still source of truth).
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { QuestionResponse, SessionStatusResponse } from "@/lib/api";

interface InterviewState {
  // Session metadata
  sessionId: string | null;
  role: string | null;
  resumeId: string | null;

  // Current question (in-flight, before answer submitted)
  currentQuestion: QuestionResponse | null;

  // Session status snapshot
  sessionStatus: SessionStatusResponse | null;

  // UI state
  isSubmitting: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  setSession: (sessionId: string, role: string, resumeId: string) => void;
  setCurrentQuestion: (q: QuestionResponse | null) => void;
  setSessionStatus: (s: SessionStatusResponse | null) => void;
  setSubmitting: (v: boolean) => void;
  setLoading: (v: boolean) => void;
  setError: (e: string | null) => void;
  clearSession: () => void;
}

export const useInterviewStore = create<InterviewState>()(
  persist(
    (set) => ({
      sessionId: null,
      role: null,
      resumeId: null,
      currentQuestion: null,
      sessionStatus: null,
      isSubmitting: false,
      isLoading: false,
      error: null,

      setSession: (sessionId, role, resumeId) =>
        set({ sessionId, role, resumeId, currentQuestion: null, error: null }),

      setCurrentQuestion: (q) => set({ currentQuestion: q }),

      setSessionStatus: (s) => set({ sessionStatus: s }),

      setSubmitting: (v) => set({ isSubmitting: v }),

      setLoading: (v) => set({ isLoading: v }),

      setError: (e) => set({ error: e }),

      clearSession: () =>
        set({
          sessionId: null,
          role: null,
          resumeId: null,
          currentQuestion: null,
          sessionStatus: null,
          isSubmitting: false,
          isLoading: false,
          error: null,
        }),
    }),
    {
      name: "interview-session",
      // Only persist session IDs, not loading states
      partialize: (state) => ({
        sessionId: state.sessionId,
        role: state.role,
        resumeId: state.resumeId,
      }),
    }
  )
);
