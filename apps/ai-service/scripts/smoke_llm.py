"""Thu ket noi chat + embedding qua LlmGateway (S0-AIE-4, Phase 02).

Chay: python -m scripts.smoke_llm   (tu thu muc apps/ai-service). Khong in API key.
"""
import asyncio
import sys

from pydantic import BaseModel

from app.llm.errors import ConfigError
from app.llm.gateway import get_gateway
from app.llm.settings import load_llm_settings
from app.llm.usage import UsageCollector
from app.prompts.store import PromptStore

SAMPLE = "Giải thích idempotent trong REST API và cho ví dụ với PUT và DELETE."


class SmokeAnswer(BaseModel):
    answer: str


async def main() -> int:
    try:
        settings = load_llm_settings()
    except ConfigError as e:
        print(f"LOI CAU HINH: {e}")
        return 2
    print(f"base_url={settings.base_url} structured_outputs={settings.structured_outputs}")
    gw, collector, failed = get_gateway(), UsageCollector(), False
    prompt = PromptStore().get("smoke")
    try:
        res = await gw.complete("planner", [{"role": "system", "content": prompt.text},
                                            {"role": "user", "content": SAMPLE}], SmokeAnswer,
                                prompt_version=prompt.version, collector=collector)
        r = res.record
        print(f"[chat] OK model={r.model} {r.latency_ms}ms in/out={r.input_tokens}/{r.output_tokens} "
              f"attempts={r.attempts} repaired={r.repaired}")
    except Exception as e:  # in loi gon, khong lo khoa
        failed = True
        print(f"[chat] FAIL {type(e).__name__}: {str(e)[:300]}")
    try:
        vecs = await gw.embed([SAMPLE, "REST API design"], collector=collector)
        print(f"[embedding] OK model={settings.embedding_model} dims={len(vecs[0])} (mong doi {settings.embedding_dimensions})")
    except Exception as e:
        failed = True
        print(f"[embedding] FAIL {type(e).__name__}: {str(e)[:300]}")
    print("metadata:", collector.to_metadata())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
