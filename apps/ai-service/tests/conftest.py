import json
import os
from typing import List, Tuple

# Test khong phu thuoc .env cua may dev (load_dotenv khong ghi de bien da co): RAG tat, moi agent mock.
# Test nao can LLM/RAG thi tu monkeypatch.
os.environ["RAG_ENABLED"] = "false"
os.environ["POLICY_WEAK_BELOW"], os.environ["POLICY_STRONG_FROM"] = "1.5", "3.0"  # nguong mac dinh du .env dev co doi
os.environ["LANGFUSE_TRACING_ENABLED"] = "false"  # .env cua dev co khoa Langfuse: test khong gui trace that
for _agent in ("CV_PARSER", "JD_PARSER", "PLANNER", "EVALUATOR", "INTERVIEWER", "REPORTER"):
    os.environ[f"AGENT_{_agent}_MODE"] = "mock"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def fresh_session_store():
    """Moi test mot InMemorySaver moi: checkpoint phien cua test truoc (cung session_id) khong lam lech guard."""
    from app.session_store.session_checkpointer import reset_memory_store
    reset_memory_store()
    yield


def parse_sse(text: str) -> List[Tuple[str, dict]]:
    """Tach body SSE thanh [(event, data)]."""
    events = []
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        name = next(l[7:] for l in lines if l.startswith("event: "))
        data = next(l[6:] for l in lines if l.startswith("data: "))
        events.append((name, json.loads(data)))
    return events


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: can Postgres + pgvector that (AI_DB_TEST_URL), bo qua trong CI")
