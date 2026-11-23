"""Client httpx goi POST /api/match/jobs cua ai-service (spec 017 US3, contracts/match-jobs-api.md).

Header X-Internal-Token chi gui khi co token (ai-service dev khong dat token thi bo qua kiem tra). Moi loi ket noi / timeout,
HTTP khac 200, JSON hong hoac response sai hinh deu thanh AiServiceError (ma thoat 2 cua lenh). Do thoi gian phia client
quanh dung mot lan POST tren ket noi giu nguyen (khong tinh phi mo ket noi moi moi cuoc goi).
"""
import time
from typing import Dict, List, NamedTuple, Optional

import httpx

from .settings import MatchEvalSettings

MATCH_PATH = "/api/match/jobs"
REQUEST_TIMEOUT_S = 30.0  # lon hon MATCH_EMBED_TIMEOUT_S (5 s) cua ai-service de thay degraded thay vi timeout phia client


class AiServiceError(RuntimeError):
    pass


class MatchReply(NamedTuple):
    body: Dict
    client_ms: float  # thoi gian mot POST phia client (gom mang + embed CV + tinh diem)


def build_request(cv: Dict, as_of: str, job_ids: Optional[List[str]], page_size: int) -> Dict:
    """Request theo contract; job_ids None = khong gioi han (xet ca chi muc)."""
    request = {"cv_profile": cv["cv_profile"], "track": cv["track"], "level": cv["level"], "as_of": as_of,
               "page": 1, "page_size": page_size}
    if job_ids is not None:
        request["job_ids"] = list(job_ids)
    return request


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_body(body, url: str) -> None:
    """Hinh response toi thieu ma lenh can; sai hinh la loi dich vu (khong doan, khong bo qua)."""
    if not isinstance(body, dict) or not isinstance(body.get("items"), list):
        raise AiServiceError(f"{url}: response thieu danh sach items")
    if not isinstance(body.get("metadata"), dict):
        raise AiServiceError(f"{url}: response thieu metadata")
    if type(body.get("total")) is not int:
        raise AiServiceError(f"{url}: response thieu total (so nguyen)")
    degraded = bool(body["metadata"].get("degraded") or body["metadata"].get("mock"))
    for item in body["items"]:
        job_id = item.get("job_id") if isinstance(item, dict) else None
        if not isinstance(job_id, str):
            raise AiServiceError(f"{url}: item thieu job_id")
        if degraded:  # lenh se dung o ma 4; response degraded co the thieu cosine nen khong doi du diem / components
            continue
        components = item.get("components")
        if not isinstance(components, dict):
            raise AiServiceError(f"{url}: item {job_id} thieu components")
        if not all(_number(v) for v in (item.get("score"), components.get("cosine"), components.get("skill_match"))):
            raise AiServiceError(f"{url}: item {job_id}: score / components.cosine / components.skill_match phai la so")


def require_complete_page(cv_id: str, body: Dict) -> None:
    """total > so item = bi cat bot (vuot tran MATCH_MAX_RESULTS hoac page_size): se lam nhan trong nhu 'thua nhan'."""
    if body["total"] > len(body["items"]):
        raise AiServiceError(f"{cv_id}: endpoint chi tra {len(body['items'])} / {body['total']} JD cua pool (bi cat bot)")


class MatchClient:
    def __init__(self, settings: MatchEvalSettings, timeout_s: float = REQUEST_TIMEOUT_S,
                 transport: Optional[httpx.BaseTransport] = None):
        headers = {"X-Internal-Token": settings.token} if settings.token else {}
        self._url = settings.base_url.rstrip("/") + MATCH_PATH
        self._http = httpx.Client(timeout=timeout_s, headers=headers, transport=transport)

    def match(self, payload: Dict) -> MatchReply:
        started = time.perf_counter()
        try:
            response = self._http.post(self._url, json=payload)
        except httpx.HTTPError as exc:  # gom TransportError (ket noi, timeout) va loi giao thuc
            raise AiServiceError(f"khong goi duoc {self._url}: {type(exc).__name__} {exc}") from exc
        elapsed_ms = (time.perf_counter() - started) * 1000
        if response.status_code != 200:
            raise AiServiceError(f"{self._url} tra {response.status_code}{_error_detail(response)}")
        try:
            body = response.json()
        except ValueError as exc:
            raise AiServiceError(f"{self._url}: response khong phai JSON") from exc
        _check_body(body, self._url)
        return MatchReply(body=body, client_ms=elapsed_ms)


def _error_detail(response: httpx.Response) -> str:
    """' (error: message)' theo {error, message, details} cua ai-service; body khac dang thi bo qua."""
    try:
        data = response.json()
        return f" ({data['error']}: {data.get('message')})" if isinstance(data, dict) and "error" in data else ""
    except ValueError:
        return ""
