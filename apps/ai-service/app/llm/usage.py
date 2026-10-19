"""Ghi nhan token, do tre, phien ban prompt va fallback cua cac lan goi LLM trong mot request."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CallRecord:
    agent: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    prompt_version: str = ""
    attempts: int = 1
    repaired: bool = False
    fallback: Optional[str] = None


@dataclass
class UsageCollector:
    records: List[CallRecord] = field(default_factory=list)

    def add(self, record: CallRecord) -> None:
        self.records.append(record)

    def total_tokens(self) -> int:
        return sum(r.input_tokens + r.output_tokens for r in self.records)

    def to_metadata(self) -> Dict:
        """Dung hinh dang `metadata` cua response (docs/ai-service/06 muc 7.4). Khong chua noi dung."""
        usage: Dict[str, Dict[str, int]] = {}
        latency: Dict[str, int] = {}
        for r in self.records:
            u = usage.setdefault(r.agent, {"input_tokens": 0, "output_tokens": 0})
            u["input_tokens"] += r.input_tokens
            u["output_tokens"] += r.output_tokens
            latency[r.agent] = latency.get(r.agent, 0) + r.latency_ms
        latency["total"] = sum(r.latency_ms for r in self.records)
        return {
            "usage": usage,
            "latency_ms": latency,
            "prompt_versions": {r.agent: r.prompt_version for r in self.records if r.prompt_version},
            "fallbacks": [r.fallback for r in self.records if r.fallback],
        }
