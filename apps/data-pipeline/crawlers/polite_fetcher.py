"""Tai trang web lich su (FR-022, constitution V): ton trong robots.txt, nghi giua request, gioi han so trang.

- robots.txt doc MOT lan cho moi host khi khoi tao; URL bi cam -> bo qua + log (US5-2)
- khoang nghi = max(--delay, Crawl-delay cua robots) giay giua hai request trang
- dung khi da gui du max_pages request trang (request robots.txt khong tinh)
- mac dinh httpx (trang tinh); render=True dung Playwright Chromium cho trang can JS (US5-4),
  import luoi de CI / test khong can trinh duyet
"""
import time
from typing import Callable, Optional
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "ai-recruit-data-pipeline/0.1 (+https://github.com/minhtuann1102/ai-recruitment-platform)"
ROBOTS_AGENT = "ai-recruit-data-pipeline"

Log = Callable[[str], None]


def _default_log(message: str) -> None:
    print(message, flush=True)


class PoliteFetcher:
    def __init__(
        self,
        base_url: str,
        delay: float = 1.0,
        max_pages: int = 60,
        render: bool = False,
        transport: Optional[httpx.BaseTransport] = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        log: Log = _default_log,
    ):
        parts = urlsplit(base_url)
        self._origin = f"{parts.scheme}://{parts.netloc}"
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True, transport=transport
        )
        self._clock, self._sleep, self._log = clock, sleep, log
        self._max_pages = max_pages
        self._render = render
        self._browser = None  # (playwright, browser) khi render
        self._last_request: Optional[float] = None
        self.pages_requested = 0
        self.skipped_by_robots = 0
        self._robots = self._load_robots()
        crawl_delay = self._robots.crawl_delay(ROBOTS_AGENT)
        self.delay = max(delay, float(crawl_delay or 0))

    def _load_robots(self) -> RobotFileParser:
        """Theo quy uoc robots: 404 -> cho phep het; 401/403/5xx/loi mang -> cam het cho an toan."""
        robots_url = f"{self._origin}/robots.txt"
        parser = RobotFileParser(robots_url)
        try:
            response = self._client.get(robots_url)
            status = response.status_code
        except httpx.HTTPError as exc:
            response, status = None, f"loi mang ({exc})"
        if response is not None and response.status_code == 200:
            parser.parse(response.text.splitlines())
            verdict = "doc luat"
        elif response is not None and response.status_code == 404:
            parser.parse([])
            verdict = "khong co file -> cho phep het"
        else:
            parser.parse(["User-agent: *", "Disallow: /"])
            verdict = "khong doc duoc -> cam het"
        self._log(f"robots checked: {robots_url} [{status}] {verdict}")
        return parser

    @property
    def exhausted(self) -> bool:
        return self.pages_requested >= self._max_pages

    def allowed(self, url: str) -> bool:
        if self._robots.can_fetch(ROBOTS_AGENT, url):
            return True
        self.skipped_by_robots += 1
        self._log(f"robots disallow, bo qua: {url}")
        return False

    def _wait_turn(self) -> None:
        if self._last_request is not None:
            wait = self.delay - (self._clock() - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._clock()

    def fetch(self, url: str) -> Optional[str]:
        """HTML cua trang; None neu bi robots cam, het luot, loi HTTP hoac khong phai HTML."""
        if self.exhausted or not self.allowed(url):
            return None
        self._wait_turn()
        self.pages_requested += 1
        try:
            return self._render_page(url) if self._render else self._get_html(url)
        except Exception as exc:  # loi mot trang khong dung ca lan crawl
            self._log(f"[loi] {url}: {exc}")
            return None

    def _get_html(self, url: str) -> Optional[str]:
        response = self._client.get(url)
        response.raise_for_status()
        if "html" not in response.headers.get("content-type", ""):
            self._log(f"bo qua (khong phai HTML): {url}")
            return None
        return response.text

    def _render_page(self, url: str) -> str:
        if self._browser is None:
            from playwright.sync_api import sync_playwright  # import luoi: chi khi --render

            playwright = sync_playwright().start()
            try:
                self._browser = (playwright, playwright.chromium.launch())
            except Exception:
                playwright.stop()  # khong de playwright treo lam hong cac trang sau
                raise
        page = self._browser[1].new_page(user_agent=USER_AGENT)
        try:
            page.goto(url, wait_until="networkidle", timeout=30_000)
            return page.content()
        finally:
            page.close()

    def close(self) -> None:
        self._client.close()
        if self._browser is not None:
            playwright, browser = self._browser
            browser.close()
            playwright.stop()
            self._browser = None
