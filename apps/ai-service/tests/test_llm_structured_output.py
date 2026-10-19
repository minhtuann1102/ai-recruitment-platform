from typing import List, Optional

import pytest
from pydantic import BaseModel

from app.llm.structured_output import parse_output, repair_messages, response_format, strict_schema


class Inner(BaseModel):
    name: str
    score: int = 0


class Outer(BaseModel):
    items: List[Inner]
    note: Optional[str] = None


def objects(node):
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield node
        for v in node.values():
            yield from objects(v)
    elif isinstance(node, list):
        for v in node:
            yield from objects(v)


def test_strict_schema_forbids_extra_and_requires_all_in_every_object():
    schema = strict_schema(Outer)
    objs = list(objects(schema))
    assert len(objs) >= 2  # Outer va Inner (trong $defs)
    for o in objs:
        assert o["additionalProperties"] is False
        assert set(o["required"]) == set(o["properties"])
    assert "default" not in str(schema)
    assert "default" in str(Outer.model_json_schema())  # schema goc khong bi sua


def test_response_format_modes():
    assert response_format(Outer, True)["type"] == "json_schema"
    assert response_format(Outer, True)["json_schema"]["strict"] is True
    assert response_format(Outer, False) == {"type": "json_object"}


def test_parse_accepts_code_fence_and_plain_json():
    text = '{"items": [{"name": "a", "score": 2}]}'
    assert parse_output(Outer, text).items[0].score == 2
    assert parse_output(Outer, "```json\n" + text + "\n```").items[0].name == "a"


@pytest.mark.parametrize("bad", ["khong phai json", '{"items": "x"}', '{"items": [{"score": 1}]}'])
def test_parse_rejects_invalid(bad):
    with pytest.raises(ValueError):
        parse_output(Outer, bad)


def test_repair_message_keeps_prompt_and_reports_error():
    msgs = [{"role": "user", "content": "q"}]
    out = repair_messages(msgs, "xxx", "thieu truong name")
    assert out[:1] == msgs and out[1] == {"role": "assistant", "content": "xxx"}
    assert "Output trước không hợp lệ" in out[2]["content"] and "thieu truong name" in out[2]["content"]
    assert msgs == [{"role": "user", "content": "q"}]  # khong sua danh sach goc
