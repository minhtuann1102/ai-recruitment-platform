"""Web gia lap cho test crawl-jd: httpx.MockTransport phuc vu fixture tu soan, khong ra mang (FR-007).

Moi host (theo base_url cua nguon) co mot che do:
- normal: robots, danh sach trang 1 co link (<nguon>_listing.html), trang >= 2 va trang khac khong co link,
  trang chi tiet = <nguon>_detail.html
- blocked: moi trang tra 403 (robots van doc duoc, tru khi robots_status doi)
- server_error: moi trang tra 500
- no_links: trang danh sach khong co link nao (cau truc HTML doi)
- bad_details: trang chi tiet khong co JobPosting
- endless: moi trang danh sach co 2 link moi (chi itviec), de kiem tra gioi han --max-pages
"""
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlsplit

import httpx

from crawlers.jd_sources import SOURCES

OPEN_ROBOTS = "User-agent: *\nAllow: /\n"


class FakeJdWeb:
    def __init__(self, fixtures_dir: Path):
        self._dir = fixtures_dir / "jd"
        self._sites: Dict[str, Dict] = {}
        self.requests: List[str] = []  # URL day du, theo thu tu gui
        self.transport = httpx.MockTransport(self._handle)

    def serve(self, name: str, mode: str = "normal", robots_status: int = 200, robots_text: str = OPEN_ROBOTS) -> None:
        host = urlsplit(SOURCES[name].base_url).netloc
        self._sites[host] = {"source": SOURCES[name], "mode": mode, "robots": (robots_status, robots_text)}

    def host_requests(self, name: str) -> List[str]:
        host = urlsplit(SOURCES[name].base_url).netloc
        return [url for url in self.requests if urlsplit(url).netloc == host]

    def page_requests(self, name: str) -> List[str]:
        return [url for url in self.host_requests(name) if urlsplit(url).path != "/robots.txt"]

    def detail_requests(self, name: str) -> List[str]:
        return [url for url in self.page_requests(name) if SOURCES[name].detail_link_re.search(urlsplit(url).path)]

    def _fixture(self, name: str) -> str:
        return (self._dir / name).read_text(encoding="utf-8")

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(str(request.url))
        site = self._sites.get(request.url.host)
        if site is None:
            return httpx.Response(404, text="host la")
        source, mode, path = site["source"], site["mode"], request.url.path
        if path == "/robots.txt":
            status, text = site["robots"]
            return httpx.Response(status, text=text)
        if mode == "blocked":
            return httpx.Response(403, html="<html><body>blocked</body></html>")
        if mode == "server_error":
            return httpx.Response(500, html="<html><body>oops</body></html>")
        if source.detail_link_re.search(path):
            page = "no_jobposting.html" if mode == "bad_details" else f"{source.name}_detail.html"
            return httpx.Response(200, html=self._fixture(page))
        if mode == "endless":
            page = int(request.url.params.get("page", "1"))
            links = "".join(f'<a href="/it-jobs/dev-{page}0{i}">tin</a>' for i in (1, 2))
            return httpx.Response(200, html=f"<html><body>{links}</body></html>")
        if str(request.url) == source.listing_url(1) and mode != "no_links":
            return httpx.Response(200, html=self._fixture(f"{source.name}_listing.html"))
        return httpx.Response(200, html=self._fixture("no_jobposting.html"))  # trang danh sach het link
