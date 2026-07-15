import { useRef, useState, useCallback, useEffect } from "react";

interface UseAnswerInputOptions {
  sessionId: string;
  questionId: string;
  audioAllowed: boolean;
  silenceTimeoutMs?: number; // default 2000 - auto-stop after this much silence
  silenceThresholdDb?: number; // default -50 - volume below this counts as silence
}

interface UseAnswerInputResult {
  mode: "audio" | "text";
  isRecording: boolean;
  autoStopping: boolean; // true during the "about to stop" grace window, for UI feedback
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob | null>;
  uploadRecording: (blob: Blob) => Promise<{ recordingId: string; transcript: string | null; status: string; message: string } | null>;
  error: string | null;
}

/**
 * Drives answer capture for a single question, with voice-activity-detection
 * (VAD) auto-stop: once the candidate finishes speaking and stays silent for
 * `silenceTimeoutMs`, recording stops automatically - no manual "stop" click
 * needed. This is a UX convenience only (matches natural pause-and-submit
 * flow); it never changes what happens to the audio afterward, and the
 * candidate can still stop manually at any time.
 *
 * VAD is volume-based (Web Audio AnalyserNode), not ML-based - simple,
 * dependency-free, good enough to detect "stopped talking" vs "still talking
 * with a mid-sentence pause." A brief pause during speech resets the silence
 * timer as soon as volume rises again, so mid-thought pauses won't cut the
 * candidate off.
 *
 * ARCHITECTURE NOTE (single resolution path):
 * Both manual `stopRecording()` and VAD auto-stop resolve through the SAME
 * `stopResolveRef`. `stopRecording` calls `stopInternal` directly, which sets
 * `stopResolveRef.current` before calling `recorder.stop()`. The `onstop`
 * handler then reads from that ref. Never split these into two separate
 * resolver mechanisms — that's the easiest way to reintroduce a race where
 * `onstop` fires with no resolver waiting.
 */
export function useAnswerInput({
  sessionId,
  questionId,
  audioAllowed,
  silenceTimeoutMs = 2000,
  silenceThresholdDb = -50,
}: UseAnswerInputOptions): UseAnswerInputResult {
  const [isRecording, setIsRecording] = useState(false);
  const [autoStopping, setAutoStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const vadRafRef = useRef<number | null>(null);
  const stopResolveRef = useRef<((blob: Blob | null) => void) | null>(null);

  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    setAutoStopping(false);
  }, []);

  // Single shared resolution path — both manual stop and VAD auto-stop go here.
  // This sets stopResolveRef.current and then calls recorder.stop(), so the
  // onstop handler always has a resolver waiting for it.
  const stopInternal = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        resolve(null);
        return;
      }
      stopResolveRef.current = resolve;
      recorder.stop();
    });
  }, []);

  // VAD loop: samples volume ~10x/second via requestAnimationFrame-throttled
  // polling. Below threshold for `silenceTimeoutMs` continuously -> auto-stop.
  const runVadLoop = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;

    const data = new Uint8Array(analyser.frequencyBinCount);

    const tick = () => {
      analyser.getByteFrequencyData(data);
      const avg = data.reduce((sum, v) => sum + v, 0) / data.length;
      // Rough conversion of average byte amplitude to a dB-like scale for
      // an intuitive threshold; not calibrated audio-engineering dB, just
      // consistent enough to compare against itself across a session.
      const level = avg === 0 ? -100 : 20 * Math.log10(avg / 255);

      if (level < silenceThresholdDb) {
        if (!silenceTimerRef.current) {
          setAutoStopping(true);
          silenceTimerRef.current = setTimeout(async () => {
            // Auto-stop path: uses the same stopInternal as the manual path.
            // stopInternal sets stopResolveRef.current before calling recorder.stop(),
            // so the onstop handler has a resolver waiting.
            await stopInternal();
            setIsRecording(false);
            clearSilenceTimer();
          }, silenceTimeoutMs);
        }
      } else {
        clearSilenceTimer();
      }

      vadRafRef.current = requestAnimationFrame(tick);
    };

    vadRafRef.current = requestAnimationFrame(tick);
  }, [silenceThresholdDb, silenceTimeoutMs, stopInternal, clearSilenceTimer]);

  const teardownVad = useCallback(() => {
    if (vadRafRef.current) cancelAnimationFrame(vadRafRef.current);
    vadRafRef.current = null;
    clearSilenceTimer();
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;
  }, [clearSilenceTimer]);

  const startRecording = useCallback(async () => {
    if (!audioAllowed) return;
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Set up VAD analyser on a parallel tap of the same stream.
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        recorder.stream.getTracks().forEach((t) => t.stop());
        teardownVad();
        if (stopResolveRef.current) {
          stopResolveRef.current(blob);
          stopResolveRef.current = null;
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      runVadLoop();
    } catch (e) {
      // Mic permission denied, no hardware, or AudioContext unsupported.
      // Degrade gracefully — VAD is a convenience layer, its absence must
      // never block the interview. Caller should fall back to text mode.
      setError("Microphone unavailable. Switching to text input.");
      setIsRecording(false);
      teardownVad();
    }
  }, [audioAllowed, runVadLoop, teardownVad]);

  // Manual stop — calls the same stopInternal the VAD auto-stop path uses,
  // so behavior (including the onstop handler resolving the blob) is identical.
  const stopRecording = useCallback((): Promise<Blob | null> => {
    setIsRecording(false);
    clearSilenceTimer();
    return stopInternal();
  }, [stopInternal, clearSilenceTimer]);

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

  // Cleanup on unmount — don't leave a mic stream or AudioContext running.
  useEffect(() => {
    return () => {
      teardownVad();
      if (mediaRecorderRef.current?.state !== "inactive") {
        mediaRecorderRef.current?.stop();
      }
    };
  }, [teardownVad]);

  return {
    mode: audioAllowed ? "audio" : "text",
    isRecording,
    autoStopping,
    startRecording,
    stopRecording,
    uploadRecording,
    error,
  };
}
