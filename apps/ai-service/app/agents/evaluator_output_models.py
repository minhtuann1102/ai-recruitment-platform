"""Schema output cua Evaluator (gui cho LLM) va phien ban prompt co trich nguon; tach khoi evaluator.py de file gon."""
from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator

from ..models_common import AnswerType


# Schema gui cho LLM: khong rang buoc min/max (che do strict khong ho tro het); code tu kep va cat.
class CoveredPoint(BaseModel):
    point: str
    quote: str


class RawBands(BaseModel):
    technical_accuracy: int
    completeness: int
    extensibility: int
    relevance: int


class EvaluatorOutput(BaseModel):
    answer_type: AnswerType
    covered: List[CoveredPoint]
    missing_points: List[str]
    misconceptions: List[str]
    scores: RawBands
    follow_up_focus: Optional[str]


class SourcedCoveredPoint(CoveredPoint):
    # mac dinh chi cho che do json_object (khong strict) chiu duoc model bo truong; strict_schema bat buoc moi truong
    source_ids: List[str] = []
    support: Literal["supported", "contradicted", "no_source"] = "no_source"


class EvaluatorOutputV4(EvaluatorOutput):
    """v4 (Phase 03a): moi y covered ghi tai lieu doi chieu (S1.., R) va muc ung ho."""
    covered: List[SourcedCoveredPoint]


def uses_sources(prompt_version: str) -> bool:
    return int(prompt_version.lstrip("v") or 0) >= 4


class EvaluatorOutputV9(EvaluatorOutputV4):
    """v9 (phase 04, POLICY_MODE=hybrid): them de xuat hanh dong tiep theo. Kieu long (str / int) co chu dich: gia tri
    la khong hop le thi code bo de xuat va dung luat (policy_hybrid), khong lam hong ca luot cham."""
    next_action: str = ""  # follow_up | hint | clarify | next_topic
    next_focus: Optional[str] = None
    difficulty_delta: int = 0  # -1 | 0 | 1, code kep theo phan loai
    action_reason: str = ""  # <= 20 tu

    @field_validator("difficulty_delta", mode="before")
    @classmethod
    def _delta_in_range(cls, v):
        """0.5, "+1", 7, None, chuoi la: ep ve int trong [-1, 1], khong duoc thi 0 (khong lam hong luot cham)."""
        try:
            return max(-1, min(1, int(float(v))))
        except (TypeError, ValueError, OverflowError):
            return 0

    @field_validator("next_action", "action_reason", mode="before")
    @classmethod
    def _text_or_empty(cls, v):
        return v if isinstance(v, str) else ""

    @field_validator("next_focus", mode="before")
    @classmethod
    def _focus_or_none(cls, v):
        return v if isinstance(v, str) else None


def uses_policy(prompt_version: str) -> bool:
    return int(prompt_version.lstrip("v") or 0) >= 9


class SwapProposal(BaseModel):
    """Phase 05: de xuat doi topic technical pending (drop) lay topic du phong (add). Kieu long co chu dich (nhu V9):
    id la / thieu thi code bac (replan.validate_swap), khong lam hong ca luot cham."""
    drop: str = ""
    add: str = ""
    reason: str = ""  # <= 20 tu; qua safe_reason truoc khi vao state

    @field_validator("drop", "add", "reason", mode="before")
    @classmethod
    def _text_or_empty(cls, v):
        return v.strip() if isinstance(v, str) else ""


class EvaluatorOutputV10(EvaluatorOutputV9):
    """v10 (phase 05, POLICY_MODE=hybrid + REPLAN_ENABLED): V9 them `swap` (null khi khong ap dung)."""
    swap: Optional[SwapProposal] = None

    @field_validator("swap", mode="before")
    @classmethod
    def _swap_or_none(cls, v):
        return v if isinstance(v, (dict, SwapProposal)) else None


def uses_replan(prompt_version: str) -> bool:
    return int(prompt_version.lstrip("v") or 0) >= 10


class RawNote(BaseModel):
    """Phase 07: ghi chu moi LLM de xuat. Kieu long (str) co chu dich: kind / text la -> code bo (agent_notes), khong lam
    hong ca luot cham."""
    kind: str = ""  # hypothesis | to_verify | strength | risk
    text: str = ""

    @field_validator("kind", "text", mode="before")
    @classmethod
    def _text_or_empty(cls, v):
        return v.strip() if isinstance(v, str) else ""


class RawNoteUpdate(BaseModel):
    id: str = ""
    status: str = ""  # confirmed | rejected

    @field_validator("id", "status", mode="before")
    @classmethod
    def _text_or_empty(cls, v):
        return v.strip() if isinstance(v, str) else ""


class EvaluatorOutputV11(EvaluatorOutputV10):
    """v11 (phase 07, POLICY_MODE=hybrid + AGENT_NOTES_ENABLED): V10 them `new_note` (null khi khong co) va `note_updates`."""
    new_note: Optional[RawNote] = None
    note_updates: List[RawNoteUpdate] = []

    @field_validator("new_note", mode="before")
    @classmethod
    def _note_or_none(cls, v):
        return v if isinstance(v, (dict, RawNote)) else None

    @field_validator("note_updates", mode="before")
    @classmethod
    def _updates_or_empty(cls, v):
        return [u for u in v if isinstance(u, (dict, RawNoteUpdate))] if isinstance(v, list) else []


def uses_notes(prompt_version: str) -> bool:
    return int(prompt_version.lstrip("v") or 0) >= 11


NO_NOTE_KIND = "none"  # v12: new_note.kind khi khong ghi chu


def _field(v, name: str):
    return v.get(name) if isinstance(v, dict) else getattr(v, name, None)


class EvaluatorOutputV12(EvaluatorOutputV11):
    """v12 (2026-11-20): cung truong voi V11, nhung schema strict bat `swap` / `new_note` luon la object. Do probe:
    gpt-4o-mini voi truong `anyOf [object, null]` tra null o moi luot (ca cau sai ro rang); bat buoc object thi ghi chu
    dung cho. "Khong de xuat" = swap.drop rong / new_note.kind "none": doi ve None sau parse, code phia sau nhu V11."""

    # Cung ten voi validator cua V10 / V11 de THAY THE (pydantic chi chay ban cua lop con), khong chay hai lan.
    @field_validator("swap", mode="before")
    @classmethod
    def _swap_or_none(cls, v):
        if not isinstance(v, (dict, SwapProposal)) or not str(_field(v, "drop") or "").strip():
            return None
        return v

    @field_validator("new_note", mode="before")
    @classmethod
    def _note_or_none(cls, v):
        if not isinstance(v, (dict, RawNote)) or str(_field(v, "kind") or "").strip().lower() in ("", NO_NOTE_KIND):
            return None
        return v

    @classmethod
    def model_json_schema(cls, *args, **kwargs):
        schema = super().model_json_schema(*args, **kwargs)
        props = schema["properties"]
        props["swap"] = {"$ref": "#/$defs/SwapProposal"}
        props["new_note"] = {"$ref": "#/$defs/RawNote"}
        schema["$defs"]["RawNote"]["properties"]["kind"]["enum"] = [NO_NOTE_KIND, "hypothesis", "to_verify", "strength",
                                                                    "risk"]
        return schema


def uses_required_proposals(prompt_version: str) -> bool:
    return int(prompt_version.lstrip("v") or 0) >= 12


def output_schema(prompt_version: str, sourced: bool, policy: bool, replan: bool, notes: bool):
    """Model dau ra theo ban prompt (v12 > v11 > v10 > v9 > v4 > co ban)."""
    if uses_required_proposals(prompt_version):
        return EvaluatorOutputV12
    return EvaluatorOutputV11 if notes else EvaluatorOutputV10 if replan else EvaluatorOutputV9 if policy else \
        EvaluatorOutputV4 if sourced else EvaluatorOutput
