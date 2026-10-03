"""S0-AIE-4: thu ket noi chat + embedding qua nha cung cap cau hinh trong .env.

Chay: python -m scripts.smoke_llm   (tu thu muc apps/ai-service)
Khong in API key.
"""
import json
import sys
import time

from app.config import ConfigError
from app.llm_client import get_client_and_settings

SAMPLE = "Giải thích idempotent trong REST API và cho ví dụ với PUT và DELETE."


def check_chat(client, settings) -> None:
    start = time.perf_counter()
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": 'Tra loi bang JSON: {"answer": "<1 cau>"}'},
            {"role": "user", "content": SAMPLE},
        ],
        response_format={"type": "json_object"},
        max_tokens=200,
    )
    elapsed = int((time.perf_counter() - start) * 1000)
    content = resp.choices[0].message.content or ""
    json.loads(content)  # chung minh JSON hop le
    usage = resp.usage
    print(f"[chat] OK model={resp.model} {elapsed}ms tokens in/out="
          f"{usage.prompt_tokens}/{usage.completion_tokens}")


def check_embedding(client, settings) -> None:
    start = time.perf_counter()
    resp = client.embeddings.create(model=settings.embedding_model, input=[SAMPLE, "REST API design"])
    elapsed = int((time.perf_counter() - start) * 1000)
    dims = len(resp.data[0].embedding)
    ok = dims == settings.embedding_dimensions
    print(f"[embedding] {'OK' if ok else 'SAI SO CHIEU'} model={settings.embedding_model} "
          f"{elapsed}ms dims={dims} (mong doi {settings.embedding_dimensions})")
    if not ok:
        raise SystemExit(1)


def main() -> int:
    try:
        client, settings = get_client_and_settings()
    except ConfigError as e:
        print(f"LOI CAU HINH: {e}")
        return 2
    print(f"base_url={settings.base_url}")
    failed = False
    for name, fn in (("chat", check_chat), ("embedding", check_embedding)):
        try:
            fn(client, settings)
        except Exception as e:  # in loi gon, khong lo key
            failed = True
            print(f"[{name}] FAIL {type(e).__name__}: {str(e)[:300]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
