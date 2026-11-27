"""Chay ai-service tren may dev (dung cho /dev/play, /dev/interview): python scripts/run_local.py [--port 8000] [--reload]

Windows: uvicorn mac dinh dung ProactorEventLoop, psycopg async (RAG / session store tren ai_db) khong chay duoc tren
loop do -> moi truy van RAG PoolTimeout va phong van roi vao fallback. Script dat WindowsSelectorEventLoopPolicy truoc
khi uvicorn tao loop. May co kiem tra TLS chan giua (CERTIFICATE_VERIFY_FAILED) thi cai `truststore` (khong bat buoc):
script tu bat neu co.
"""
import argparse
import asyncio
import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[1]  # apps/ai-service: chua package app/


def main() -> None:
    parser = argparse.ArgumentParser(description="Chay ai-service local")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="tu nap lai khi sua code")
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        import truststore  # chi may dev can: khong them vao requirements
        truststore.inject_into_ssl()
    except ImportError:
        pass
    import uvicorn
    # --reload chay subprocess: uvicorn tu dat SelectorEventLoop tren Windows trong subprocess
    uvicorn.run("app.main:app", port=args.port, reload=args.reload, app_dir=str(SERVICE_DIR))


if __name__ == "__main__":
    main()
