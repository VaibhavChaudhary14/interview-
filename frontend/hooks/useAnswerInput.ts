import { useRef, useState, useCallback } from "react";

interface UseAnswerInputOptions {
  sessionId: string;
  questionId: string;
  audioAllowed: boolean;
}

interface UseAnswerInputResult {
  mode: "audio" | "text";
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob | null>;
  uploadRecording: (blob: Blob) => Promise<{ recordingId: string; transcript: string | null; status: string; message: string } | null>;
  error: string | null;
}

/**
 * Drives answer capture for a single question.
 *
 * If audioAllowed is false (candidate declined consent, or browser mic
 * access fails), the caller should render a plain <textarea> and post to
 * the existing text-answer endpoint - this hook is only responsible for
 * the audio branch, and callers should never assume audio is available.
 */
export function useAnswerInput({
  sessionId,
  questionId,
  audioAllowed,
}: UseAnswerInputOptions): UseAnswerInputResult {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    if (!audioAllowed) return;
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (e) {
      // Mic permission denied or unavailable - degrade gracefully, do not
      // block the interview. Caller should fall back to text mode.
      setError("Microphone unavailable. Switching to text input.");
      setIsRecording(false);
    }
  }, [audioAllowed]);

  const stopRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder) return resolve(null);
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        recorder.stream.getTracks().forEach((t) => t.stop());
        setIsRecording(false);
        resolve(blob);
      };
      recorder.stop();
    });
  }, []);

  const uploadRecording = useCallback(
    async (blob: Blob) => {
      try {
        const formData = new FormData();
        formData.append("file", blob, "answer.webm");
        const res = await fetch(
          `/api/v1/sessions/${sessionId}/questions/${questionId}/audio`,
          { method: "POST", body: formData }
        );
        if (!res.ok) throw new Error(`Upload failed (${res.status})`);
        const data = await res.json();
        return {
          recordingId: data.recording_id as string,
          transcript: data.transcript as string | null,
          status: data.status as string,
          message: data.message as string,
        };
      } catch (e) {
        setError(
          "Couldn't upload your recording. Your answer was still saved as text if you typed it, or you can retry."
        );
        return null;
      }
    },
    [sessionId, questionId]
  );

  return {
    mode: audioAllowed ? "audio" : "text",
    isRecording,
    startRecording,
    stopRecording,
    uploadRecording,
    error,
  };
}
