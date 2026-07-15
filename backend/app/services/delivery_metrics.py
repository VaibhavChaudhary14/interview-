"""
DeliveryMetricsService — computes speaking pace, pause, and filler-word
metrics from a recorded audio file and its transcript.

Design principles:
- Never raises. Any exception is caught and returned as {"computation_error": str(e)}.
  The metrics job runs after an answer is already saved, so a crash here must
  not roll back or corrupt the answer record.
- Filler words are split into two tiers: unambiguous fillers (um, uh, etc.)
  and contextual connectors (so, actually, basically). Contextual connectors
  are common in legitimate speech patterns — the UI labels them differently
  and weights them less in coaching feedback.
- WPM feedback is descriptive coaching ("a bit slow", "good pace"), not
  pass/fail scoring. The ideal range (110–170 WPM) is a broad general-purpose
  default; roles and individuals vary.
"""
import re
import logging
import tempfile
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Filler words that are almost always non-content speech.
UNAMBIGUOUS_FILLERS = ["um", "uh", "you know", "i mean"]

# Words that can be legitimate sentence connectors but are also common fillers.
# Counted separately so the UI can display them with softer framing.
CONTEXTUAL_CONNECTORS = ["like", "so", "actually", "basically"]

WPM_FEEDBACK_SLOW = 110   # Below this: "a bit slow"
WPM_FEEDBACK_FAST = 170   # Above this: "spoke quickly"


class DeliveryMetricsService:
    def compute(
        self,
        answer_id: str,
        audio_bytes: bytes,
        transcript: str,
    ) -> dict:
        """
        Compute delivery metrics from raw audio bytes and a transcript string.

        Returns a dict suitable for **kwargs into AnswerMetrics(**result).
        On any failure, all metric fields are None and computation_error is set.
        """
        try:
            import librosa
            import numpy as np
            import soundfile as sf

            # Write audio to a temp file so librosa can load it.
            # Using NamedTemporaryFile with delete=False so we can close it
            # before passing the path to librosa (required on Windows).
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                y, sr = librosa.load(tmp_path, sr=None, mono=True)
            finally:
                os.unlink(tmp_path)

            duration_seconds = float(librosa.get_duration(y=y, sr=sr))

            words = transcript.split() if transcript else []
            word_count = len(words)
            wpm = round((word_count / duration_seconds) * 60, 1) if duration_seconds > 0 else None

            pauses = self._detect_pauses(y, sr)
            filler_breakdown = self._count_filler_words(transcript or "")
            total_fillers = sum(filler_breakdown.get("unambiguous", {}).values()) + sum(
                filler_breakdown.get("contextual", {}).values()
            )

            return {
                "wpm": wpm,
                "word_count": word_count,
                "audio_duration_seconds": round(duration_seconds, 1),
                "pause_count": len(pauses),
                "avg_pause_duration": round(float(__import__("numpy").mean(pauses)), 2) if pauses else 0.0,
                "longest_pause_seconds": round(max(pauses), 2) if pauses else 0.0,
                "filler_word_count": total_fillers,
                "filler_word_breakdown": filler_breakdown,
                "computed_at": datetime.now(timezone.utc),
                "computation_error": None,
            }
        except Exception as exc:
            logger.warning("DeliveryMetricsService.compute failed for answer %s: %s", answer_id, exc)
            return {
                "wpm": None,
                "word_count": None,
                "audio_duration_seconds": None,
                "pause_count": None,
                "avg_pause_duration": None,
                "longest_pause_seconds": None,
                "filler_word_count": None,
                "filler_word_breakdown": {},
                "computed_at": datetime.now(timezone.utc),
                "computation_error": str(exc),
            }

    def _detect_pauses(
        self,
        y,
        sr: int,
        silence_threshold_db: float = -40.0,
        min_pause_seconds: float = 0.5,
    ) -> list:
        """
        Detect silence gaps longer than min_pause_seconds using librosa's
        non-silent intervals.

        silence_threshold_db=-40 is intentionally conservative (i.e., generous
        about what counts as speech). Background noise at -40 dBFS is usually
        still audible; if anything it under-counts pauses rather than
        over-counting them, which is the safer direction for coaching feedback.
        """
        try:
            import librosa
            intervals = librosa.effects.split(y, top_db=abs(silence_threshold_db))
            pauses = []
            for i in range(1, len(intervals)):
                gap_samples = intervals[i][0] - intervals[i - 1][1]
                gap_seconds = gap_samples / sr
                if gap_seconds >= min_pause_seconds:
                    pauses.append(round(float(gap_seconds), 2))
            return pauses
        except Exception as exc:
            logger.warning("Pause detection failed: %s", exc)
            return []

    def _count_filler_words(self, transcript: str) -> dict:
        """
        Count filler word occurrences using word-boundary regex, returning two
        sub-dicts so the UI can display unambiguous fillers and contextual
        connectors with different framing.

        "like" matching "likely" or "unlike" is avoided by \\b anchors.
        """
        text = transcript.lower()
        unambiguous = {}
        for word in UNAMBIGUOUS_FILLERS:
            pattern = r"\b" + re.escape(word) + r"\b"
            count = len(re.findall(pattern, text))
            if count:
                unambiguous[word] = count

        contextual = {}
        for word in CONTEXTUAL_CONNECTORS:
            pattern = r"\b" + re.escape(word) + r"\b"
            count = len(re.findall(pattern, text))
            if count:
                contextual[word] = count

        return {
            "unambiguous": unambiguous,
            "contextual": contextual,
        }

    @staticmethod
    def wpm_feedback(wpm: Optional[float]) -> str:
        """Plain-language coaching feedback for a WPM value."""
        if wpm is None:
            return "Speaking pace unavailable."
        if wpm < WPM_FEEDBACK_SLOW:
            return f"{wpm:.0f} WPM — a bit slow. A slightly faster, more energetic pace can help engagement."
        if wpm > WPM_FEEDBACK_FAST:
            return f"{wpm:.0f} WPM — spoke quickly. Slowing down slightly improves clarity for the listener."
        return f"{wpm:.0f} WPM — good pace."
