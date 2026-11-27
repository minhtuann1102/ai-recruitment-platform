"""Golden trace (plan 261127-1517): moi kich ban qua HTTP phai cho ra dung trace da ghi tu code truoc khi boc LangGraph.

Hong test nay sau khi refactor = hanh vi da doi. Khong ghi lai fixture de cho xanh; chi ghi lai khi co y doi hanh
vi (tests/golden_turns/record_golden_turns.py) va ghi ro ly do trong PR.
"""
import json

import pytest

from tests.golden_turns.golden_fixture_paths import fixture_path
from tests.golden_turns.golden_scenarios import SCENARIOS, run_scenario

pytestmark = pytest.mark.usefixtures("session_graph_mode")  # chay ca hai gia tri SESSION_GRAPH


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario_matches_golden_fixture(name):
    expected = json.loads(fixture_path(name).read_text())
    actual = json.loads(json.dumps(run_scenario(name), ensure_ascii=False))  # cung chuan hoa JSON nhu luc ghi
    assert actual["start"] == expected["start"]
    assert len(actual["turns"]) == len(expected["turns"])
    for i, (got, want) in enumerate(zip(actual["turns"], expected["turns"])):
        assert got == want, f"{name}: luot thu {i} (turn_number {want['request']['turn_number']}) khac golden"
    assert actual.get("finalize") == expected.get("finalize")
