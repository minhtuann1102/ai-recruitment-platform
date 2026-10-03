from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
CTX = {"category": "Backend", "difficulty": "medium", "candidate_skills": ["nodejs"]}


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "version": "mock-v1", "model_loaded": False}


def test_start_returns_question_and_metadata():
    r = client.post("/api/start", json={"session_id": "s1", "context": CTX})
    body = r.json()
    assert r.status_code == 200
    assert body["first_question"]
    assert body["question_metadata"]["topic"] == "Backend"
    assert body["question_metadata"]["difficulty"] == "medium"


def test_next_turn_has_no_scores_and_avoids_asked_questions():
    history = [{"turn_number": 1, "question": "Q1", "answer": "A1"}]
    r = client.post(
        "/api/next-turn",
        json={"session_id": "s1", "turn_number": 2, "question": "Q2", "answer": "A2",
              "history": history, "context": CTX},
    )
    body = r.json()
    assert r.status_code == 200
    assert "scores" not in body
    assert body["agent_decision"] in {"deepen", "switch_topic", "keep_difficulty"}
    assert body["answer_signal"] in {"weak", "ok", "strong"}
    assert body["next_question"] not in {"Q1", "Q2"}


def test_finalize_scores_every_turn_with_comment():
    turns = [{"turn_number": i, "question": f"Q{i}", "answer": f"A{i}"} for i in (1, 2, 3)]
    r = client.post("/api/finalize", json={"session_id": "s1", "context": CTX, "turns": turns})
    body = r.json()
    assert r.status_code == 200
    assert [t["turn_number"] for t in body["turns"]] == [1, 2, 3]
    assert all(t["comment"] and 0 <= t["scores"]["relevance"] <= 10 for t in body["turns"])
    expected = round(sum(t["scores"]["relevance"] for t in body["turns"]) / 3, 1)
    assert body["criteria_averages"]["relevance"] == expected
    assert 0 <= body["overall_score"] <= 10


def test_finalize_rejects_empty_turns_with_contract_error_shape():
    r = client.post("/api/finalize", json={"session_id": "s1", "context": CTX, "turns": []})
    body = r.json()
    assert r.status_code == 422
    assert body["error"] == "invalid_request"
    assert "message" in body and "details" in body


def test_missing_session_id_is_rejected():
    r = client.post("/api/start", json={"context": CTX})
    assert r.status_code == 422
    assert r.json()["error"] == "invalid_request"
