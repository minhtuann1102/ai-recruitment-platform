import json
from typing import List, Tuple

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def parse_sse(text: str) -> List[Tuple[str, dict]]:
    """Tach body SSE thanh [(event, data)]."""
    events = []
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        name = next(l[7:] for l in lines if l.startswith("event: "))
        data = next(l[6:] for l in lines if l.startswith("data: "))
        events.append((name, json.loads(data)))
    return events
