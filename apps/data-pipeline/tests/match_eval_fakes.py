"""Client ai-service gia cho test match-eval / match-eval-sheet (spec 017 US3). Khong mang, khong ai-service that.

FakeMatchClient.match(payload) tra dung hinh response cua contracts/match-jobs-api.md. CV nhan dien bang
cv_profile.headline (= cv_id trong du lieu test). Diem: cosine giam theo thu tu job_id, skill_match tang theo thu tu job_id,
score = nhan / 10 + cosine / 100 (xep full = xep ly tuong: nhan giam dan, hoa theo cosine).
"""
import copy
from typing import Dict, List, Optional

from pipeline.match_eval_client import MatchReply


class FakeMatchClient:
    def __init__(self, filtered: Dict[str, List[str]], labels: Dict[str, Dict[str, int]]):
        self.filtered, self.labels = filtered, labels
        self.calls: List[Dict] = []
        self.degraded_from: Optional[int] = None  # so thu tu cuoc goi (tinh tu 1) tro di tra degraded
        self.mock = False
        self.fail: Optional[Exception] = None  # nem khi goi
        self.reverse = False  # tra items nguoc thu tu: bang soat khong duoc phu thuoc thu tu response
        self.total_override: Optional[int] = None  # gia lap bi cat bot (total > len(items))

    def _item(self, cv_id: str, jd_id: str, rank: int) -> Dict:
        cosine, skill = round(0.9 - 0.1 * rank, 3), round(0.1 + 0.1 * rank, 3)
        label = self.labels.get(cv_id, {}).get(jd_id, 0)
        return {"job_id": jd_id, "title": f"LEAK-TITLE-{jd_id}", "group": "backend", "level": "Mid", "deadline": "2026-12-01",
                "score": round(label / 10 + cosine / 100, 4), "components": {"cosine": cosine, "skill_match": skill, "level_fit": 1.0},
                "matched_skills": ["LEAK-MATCHED"], "missing_skills": ["LEAK-MISSING"], "notes": []}

    def match(self, payload: Dict) -> MatchReply:
        self.calls.append(copy.deepcopy(payload))
        if self.fail:
            raise self.fail
        cv_id = payload["cv_profile"]["headline"]
        ids = sorted(self.filtered.get(cv_id, []))
        if payload.get("job_ids") is not None:
            ids = [j for j in ids if j in payload["job_ids"]]
        items = sorted((self._item(cv_id, j, n) for n, j in enumerate(ids)), key=lambda i: (-i["score"], i["job_id"]))
        shown = items[:payload.get("page_size", 10)]
        if self.reverse:
            shown.reverse()
        broken = self.degraded_from is not None and len(self.calls) >= self.degraded_from
        body = {"items": shown, "page": 1, "page_size": payload.get("page_size", 10),
                "total": self.total_override if self.total_override is not None else len(items),
                "metadata": {"as_of": payload.get("as_of"), "embedding_model": "text-embedding-3-small", "index_size": 36,
                             "weights": {"cosine": 0.6, "skill_match": 0.3, "level_fit": 0.1}, "max_level_gap": 1,
                             "degraded": broken, "degraded_reason": "embedding_timeout" if broken else None, "mock": self.mock,
                             "usage": {"embedding_tokens": 200}, "timing_ms": {"embed": 180, "score": 4 + len(self.calls) % 3, "total": 190}}}
        return MatchReply(body=body, client_ms=100.0 + len(self.calls))
