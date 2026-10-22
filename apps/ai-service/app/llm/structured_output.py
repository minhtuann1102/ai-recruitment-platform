"""Structured output: JSON schema strict (hoac json_object du phong) va parse + repair (design 03 muc 4.6)."""
import copy
import json
import re
from typing import List, Type, TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


def strict_schema(model: Type[BaseModel]) -> dict:
    """JSON schema theo che do strict: moi object additionalProperties=false va moi truong deu required."""
    schema = copy.deepcopy(model.model_json_schema())

    def walk(node) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            node.pop("default", None)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
    return schema


def response_format(model: Type[BaseModel], structured: bool) -> dict:
    if structured:
        return {"type": "json_schema",
                "json_schema": {"name": model.__name__, "schema": strict_schema(model), "strict": True}}
    return {"type": "json_object"}


def parse_output(model: Type[M], content: str) -> M:
    """Parse JSON (chap nhan khoi ```json ... ```); nem ValidationError/ValueError neu sai."""
    text = content.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fenced:
        text = fenced.group(1)
    json.loads(text)  # loi cu phap -> ValueError (JSONDecodeError)
    return model.model_validate_json(text)


def repair_messages(messages: List[dict], bad_output: str, error: str) -> List[dict]:
    """Gui lai cung prompt kem dau ra loi va thong bao ngan (repair retry 1 lan)."""
    note = f"Output trước không hợp lệ: {error[:300]}. Trả lại JSON đúng schema, không thêm chữ nào khác."
    return list(messages) + [{"role": "assistant", "content": bad_output}, {"role": "user", "content": note}]
