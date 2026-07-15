import uuid
from datetime import datetime, timedelta, timezone
from app.models.session import Session
from app.models.feedback import Feedback


def test_submit_feedback_success_and_validation(client, db_session):
    # 1. Create a dummy session
    session = Session(
        role="Product Designer",
        status="REPORT_READY",
        questions_asked=5
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # 2. POST feedback with invalid rating
    payload = {
        "rating_realistic": 6,
        "rating_feedback": 3,
        "comments": "Great realism, poor coaching."
    }
    resp = client.post(f"/api/v1/sessions/{session.id}/feedback", json=payload)
    assert resp.status_code == 422

    # 3. POST feedback with valid rating
    payload["rating_realistic"] = 5
    resp = client.post(f"/api/v1/sessions/{session.id}/feedback", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == str(session.id)
    assert data["rating_realistic"] == 5
    assert data["rating_feedback"] == 3
    assert data["comments"] == "Great realism, poor coaching."

    # 4. Assert row saved in DB
    fb = db_session.query(Feedback).filter(Feedback.session_id == session.id).first()
    assert fb is not None
    assert fb.rating_realistic == 5

    # 5. POST duplicate feedback -> 409 Conflict
    resp = client.post(f"/api/v1/sessions/{session.id}/feedback", json=payload)
    assert resp.status_code == 409


def test_analytics_overview_funnel_and_dropoffs(client, db_session):
    # 1. Create sessions in various states
    s1 = Session(role="QA Engineer", status="CREATED")
    s2 = Session(role="Backend Dev", status="IN_PROGRESS", questions_asked=3)
    s3 = Session(role="Frontend Dev", status="IN_PROGRESS", questions_asked=5)
    s4 = Session(role="Product Manager", status="REPORT_READY", questions_asked=8)
    s5 = Session(role="Ayurvedic practitioner", status="REPORT_READY", classification_method="unclassified")
    
    # 2. Out of window session (10 days ago)
    s6 = Session(role="SRE", status="CREATED")
    s6.created_at = datetime.now(timezone.utc) - timedelta(days=10)

    db_session.add_all([s1, s2, s3, s4, s5, s6])
    db_session.commit()

    # 3. Query analytics overview (default 7 days)
    resp = client.get("/api/v1/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["time_window_days"] == 7
    
    funnel = data["funnel"]
    assert funnel["CREATED"] == 1
    assert funnel["IN_PROGRESS"] == 2
    assert funnel["REPORT_READY"] == 2

    # Verify out of window is excluded in 7 days
    assert s6.status == "CREATED"
    
    # 4. Query analytics overview for 14 days (should include s6)
    resp_14 = client.get("/api/v1/analytics/overview?days=14")
    assert resp_14.status_code == 200
    data_14 = resp_14.json()
    assert data_14["time_window_days"] == 14
    assert data_14["funnel"]["CREATED"] == 2
    
    dropoffs = data["mid_interview_dropoffs"]
    assert dropoffs["3"] == 1
    assert dropoffs["5"] == 1
    assert dropoffs["1"] == 0

    unclassified = data["unclassified_roles"]
    assert len(unclassified) == 1
    assert unclassified[0]["role"] == "ayurvedic practitioner"
    assert unclassified[0]["count"] == 1


def test_report_endpoint_contains_has_feedback(client, db_session):
    # 1. Create session and report
    session = Session(role="Staff Engineer", status="COMPLETED")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Trigger report generation endpoint
    resp = client.post(f"/api/v1/sessions/{session.id}/report")
    assert resp.status_code == 200

    # 2. Query report -> has_feedback should be False
    resp = client.get(f"/api/v1/sessions/{session.id}/report")
    assert resp.status_code == 200
    assert resp.json()["has_feedback"] is False

    # 3. Add feedback
    fb = Feedback(session_id=session.id, rating_realistic=4, rating_feedback=4)
    db_session.add(fb)
    db_session.commit()

    # 4. Query report again -> has_feedback should be True
    resp = client.get(f"/api/v1/sessions/{session.id}/report")
    assert resp.status_code == 200
    assert resp.json()["has_feedback"] is True
