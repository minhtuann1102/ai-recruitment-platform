"""Fixture dung chung: app voi Settings tuong minh + httpx.MockTransport (khong mang, khong key).

Moi test di qua Settings(...) chu khong qua os.environ, de .env cua may dev khong anh huong. Cac bien ben duoi chi dam bao
`app.main` import duoc (cuoi file tao `app = create_app()` tu env) ma khong dung key that; dat truoc khi import app.
"""
import os

os.environ["BLAZE_API_KEY"] = ""
os.environ["APP_ENV"] = "dev"
os.environ["VOICE_SERVICE_INTERNAL_TOKEN"] = ""

from typing import List

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import FakeBlaze, make_settings


@pytest.fixture()
def build_client():
    """build_client(fake_blaze, **settings) -> TestClient dang mo (mot event loop cho ca test), dong sau test."""
    opened: List[TestClient] = []

    def build(fake: FakeBlaze, **overrides) -> TestClient:
        client = TestClient(create_app(make_settings(**overrides), transport=fake.transport))
        client.__enter__()
        opened.append(client)
        return client

    yield build
    for client in opened:
        client.__exit__(None, None, None)
