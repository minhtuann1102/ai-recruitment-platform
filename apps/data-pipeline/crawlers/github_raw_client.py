"""Tai noi dung file tu GitHub qua REST API (Accept: raw), khong crawl HTML.

Co GITHUB_TOKEN (vd `gh auth token`) thi duoc 5000 request/gio; khong co thi 60/gio, du cho ~60 file.
Nghi `delay` giay giua hai request (constitution V: co rate limit).
"""
import os
import time
from typing import Optional

import httpx

API_URL = "https://api.github.com/repos/{repo}/contents/{path}"
USER_AGENT = "ai-recruit-data-pipeline/0.1 (+https://github.com/minhtuann1102/ai-recruitment-platform)"


class GithubRawClient:
    def __init__(self, token: Optional[str] = None, delay: float = 0.5):
        token = token if token is not None else os.getenv("GITHUB_TOKEN", "").strip()
        headers = {"Accept": "application/vnd.github.raw", "User-Agent": USER_AGENT}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(headers=headers, timeout=60, follow_redirects=True)
        self._delay = delay
        self._last_request = 0.0

    def fetch(self, repo: str, path: str) -> str:
        wait = self._delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()
        response = self._client.get(API_URL.format(repo=repo, path=path))
        response.raise_for_status()
        return response.text

    def close(self) -> None:
        self._client.close()


def blob_url(repo: str, path: str) -> str:
    return f"https://github.com/{repo}/blob/HEAD/{path}"
