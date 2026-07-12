"use client";

import { useState } from "react";

interface RecordingPlaybackProps {
  sessionId: string;
  recordingId: string;
  questionSequence: number;
}

/**
 * Playback control for agency reviewers.
 *
 * Deliberately does NOT prefetch the presigned URL on mount - the URL is
 * only requested when the reviewer explicitly clicks play, since each
 * request is audit-logged server-side (routes_audio.py: GET .../play).
 * Prefetching on page load would generate audit noise unrelated to
 * actual review activity and could leak a live URL to anyone who loads
 * the dashboard page without watching.
 */
export default function RecordingPlayback({
  sessionId,
  recordingId,
  questionSequence,
}: RecordingPlaybackProps) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<Date | null>(null);

  async function requestPlayback() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/v1/sessions/${sessionId}/recordings/${recordingId}/play`
      );
      if (res.status === 404) {
        throw new Error(
          "Recording no longer available (may have been deleted per retention policy)."
        );
      }
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const data = await res.json();
      setAudioUrl(data.url);
      // Presigned URLs are short-lived (24h per report schema); surface
      // that to the reviewer so a stale tab doesn't silently fail later.
      if (data.expires_at) setExpiresAt(new Date(data.expires_at));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't load recording.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 p-3 text-black">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">Question {questionSequence}</span>
        {!audioUrl && (
          <button
            onClick={requestPlayback}
            disabled={loading}
            className="text-sm rounded-md bg-gray-900 text-white px-3 py-1.5 disabled:opacity-50"
          >
            {loading ? "Loading…" : "Play recording"}
          </button>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {audioUrl && (
        <>
          <audio controls src={audioUrl} className="w-full" />
          {expiresAt && (
            <p className="text-xs text-gray-400 mt-1">
              Link expires {expiresAt.toLocaleTimeString()} - reload to refresh.
            </p>
          )}
        </>
      )}

      <p className="text-xs text-gray-400 mt-2">
        Access to this recording is logged for audit purposes.
      </p>
    </div>
  );
}
