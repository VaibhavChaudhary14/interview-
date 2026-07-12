"use client";

import { useEffect, useState } from "react";

interface ConsentModalProps {
  sessionId: string;
  onResolved: (audioAllowed: boolean) => void;
}

/**
 * Consent gate shown once, before the first question of a session.
 *
 * IMPORTANT: This modal must never block the interview itself.
 * Declining audio routes the candidate into text-only mode with the
 * same question/report pipeline - it does not end the session.
 */
export default function ConsentModal({
  sessionId,
  onResolved,
}: ConsentModalProps) {
  const [policyVersion, setPolicyVersion] = useState<string | null>(null);
  const [consentText, setConsentText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fatalError, setFatalError] = useState<boolean>(false);

  useEffect(() => {
    async function fetchActiveVersion() {
      try {
        const res = await fetch(`/api/v1/sessions/${sessionId}/consent/active-version`);
        if (!res.ok) throw new Error(`Failed to load policy (${res.status})`);
        const data = await res.json();
        setPolicyVersion(data.version);
        setConsentText(data.consent_text);
      } catch (e) {
        setError("Could not retrieve the consent policy. Please refresh the page or contact support.");
        setFatalError(true);
      } finally {
        setLoading(false);
      }
    }
    fetchActiveVersion();
  }, [sessionId]);

  async function submitConsent(audioAllowed: boolean) {
    if (!policyVersion) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}/consent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audio_recording_allowed: audioAllowed,
          consent_text_version: policyVersion,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const errCode = errData?.detail?.error_code;
        if (res.status === 400 && errCode === "INVALID_CONSENT_VERSION") {
          setError("Consent configuration error: The policy version is invalid. Please contact support.");
          setFatalError(true);
          return;
        }
        throw new Error(`Consent submission failed (${res.status})`);
      }

      onResolved(audioAllowed);
    } catch (e) {
      setError(
        "Couldn't save your choice. You can retry, or continue in text-only mode."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
        <div className="max-w-lg w-full rounded-xl bg-white p-6 shadow-xl text-black text-center">
          <p className="text-sm font-medium">Loading consent policy...</p>
        </div>
      </div>
    );
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    >
      <div className="max-w-lg w-full rounded-xl bg-white p-6 shadow-xl text-black">
        <h2 id="consent-title" className="text-lg font-semibold mb-3">
          Before we start
        </h2>

        {consentText ? (
          <p className="text-sm text-gray-700 mb-3">
            {consentText}{" "}
            {policyVersion && (
              <span className="text-xs text-gray-400 block mt-1">
                Policy version: {policyVersion}
              </span>
            )}
          </p>
        ) : (
          <p className="text-sm text-gray-700 mb-3">
            This interview can be conducted by voice. If you allow it, we'll
            record your spoken answers to transcribe them and generate delivery
            feedback (pace, pauses, clarity). Recordings are stored securely and
            retained according to our{" "}
            <a href="/legal/retention-policy" className="underline" target="_blank">
              retention policy
            </a>.
          </p>
        )}

        <p className="text-sm text-gray-700 mb-5">
          You can decline voice recording and complete the same interview by
          typing your answers instead - nothing about the questions or your
          results will be different.
        </p>

        {error && (
          <p className="text-sm text-red-600 mb-3" role="alert">
            {error}
          </p>
        )}

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            disabled={submitting || fatalError || !policyVersion}
            onClick={() => submitConsent(true)}
            className="flex-1 rounded-lg bg-black text-white py-2.5 px-4 text-sm font-medium disabled:opacity-50"
          >
            Allow voice recording
          </button>
          <button
            disabled={submitting || fatalError || !policyVersion}
            onClick={() => submitConsent(false)}
            className="flex-1 rounded-lg border border-gray-300 py-2.5 px-4 text-sm font-medium disabled:opacity-50"
          >
            Continue text-only
          </button>
        </div>

        <p className="text-xs text-gray-400 mt-4">
          You can request deletion of any recording at any time from your
          session summary page.
        </p>
      </div>
    </div>
  );
}
