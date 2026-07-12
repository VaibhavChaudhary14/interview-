import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


from sqlalchemy.orm import Session as DBSession


class ReportBuilderService:
    def build(self, session, questions: list, answers: list, resume_signals: dict, db: DBSession = None) -> dict:
        topics_covered = list(set(q.topic for q in questions))
        transcript = []

        qa_map = {a.question_id: a for a in answers}
        thin_topics = []
        total_words = 0
        answered_count = 0

        recording_map = {}
        if db:
            from app.models.recording import Recording
            recordings = db.query(Recording).filter(Recording.session_id == session.id).all()
            recording_map = {r.answer_id: r for r in recordings if r.answer_id}

        for q in questions:
            answer = qa_map.get(q.id)
            answer_text = answer.answer_text if answer else ""
            word_count = answer.word_count if answer else 0
            
            recording_id = None
            audio_metrics = None

            if answer:
                answered_count += 1
                total_words += word_count
                if word_count < 15:
                    thin_topics.append(q.topic)
                
                recording = recording_map.get(answer.id)
                if recording and recording.deletion_completed_at is None:
                    recording_id = str(recording.id)
                    audio_metrics = recording.metrics

            transcript.append({
                "sequence": q.sequence,
                "question": q.question_text,
                "answer": answer_text,
                "topic": q.topic,
                "source_chunks": q.source_chunk_ids or [],
                "recording_id": recording_id,
                "audio_metrics": audio_metrics,
            })

        avg_words = total_words // max(answered_count, 1)

        resume_skills = set(resume_signals.get("extracted_skills", []))
        covered_topics_lower = set(t.lower() for t in topics_covered)
        covered_skills = [s for s in resume_skills if s.lower() in covered_topics_lower]
        missing_skills = resume_skills - set(covered_skills)

        if missing_skills:
            alignment = f"Strong coverage of skills explicitly on resume ({', '.join(covered_skills[:3])}); limited depth shown on {', '.join(list(missing_skills)[:2])} despite resume mention."
        elif covered_skills:
            alignment = f"Good alignment: covered skills include {', '.join(covered_skills[:3])}."
        else:
            alignment = "Resume signals limited — evaluation is role-generic."

        return {
            "session_id": str(session.id),
            "role": session.role,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "topics_covered": topics_covered,
            "transcript": transcript,
            "insights": {
                "questions_answered": answered_count,
                "average_answer_length_words": avg_words,
                "topics_with_thin_answers": thin_topics,
                "resume_alignment_note": alignment,
            },
        }
