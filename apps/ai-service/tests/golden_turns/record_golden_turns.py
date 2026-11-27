"""Ghi lai fixture golden: `cd apps/ai-service && .venv/bin/python -m tests.golden_turns.record_golden_turns`.

Chi chay khi CO Y doi hanh vi (doc ky diff fixture truoc khi giu). Boc LangGraph (plan 261127-1517) KHONG duoc doi
fixture: test_golden_turns_match_fixture phai xanh ma khong ghi lai.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # nhu pytest: test import `fakes`, `conftest` truc tiep
import tests.conftest  # noqa: F401,E402  dat env mock / RAG tat truoc khi import app (nhu khi chay pytest)
from tests.golden_turns.golden_fixture_paths import FIXTURE_DIR, fixture_path
from tests.golden_turns.golden_scenarios import SCENARIOS, run_scenario


def main(names) -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for name in names or SCENARIOS:
        trace = run_scenario(name)
        fixture_path(name).write_text(json.dumps(trace, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        print(f"{name}: {len(trace['turns'])} luot")


if __name__ == "__main__":
    main(sys.argv[1:])
