"""In so do Mermaid cua graph mot luot next-turn (docs/ai-service/03 muc so do graph, bao cao do an).

Chay: `cd apps/ai-service && .venv/bin/python scripts/export_turn_graph_mermaid.py`. Khong goi LLM, khong can .env.
"""
import os
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("RAG_ENABLED", "false")
warnings.filterwarnings("ignore")  # LangChainPendingDeprecationWarning luc import serde: khong lien quan so do

from app.turn_graph.turn_graph_builder import turn_graph_mermaid  # noqa: E402

if __name__ == "__main__":
    sys.stdout.write(turn_graph_mermaid())
