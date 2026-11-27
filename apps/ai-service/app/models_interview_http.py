"""Body HTTP cua /api/next-turn va /api/finalize (docs/ai-service/06 muc 7.4).

Ben goi chi gui phan MOI cua luot; plan / state / cau hoi / lich su da nam trong checkpoint cua phien. Truong cu
(plan, state, question...) bi tu choi (422) de ben goi sua som, khong am tham bo qua. Request noi bo (NextTurnRequest,
FinalizeRequest) khong doi: app/session_store/session_request_builder.py dung lai chung tu checkpoint.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NextTurnBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1)
    turn_number: int = Field(ge=1)
    answer: str = Field(max_length=4000)  # voice duoc rong (micro khong thu tieng): turn_engine tra voice_no_speech
    answer_source: Literal["text", "voice"] = "text"
    stt_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    elapsed_seconds: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _typed_answer_not_empty(self):
        if self.answer_source == "text" and not self.answer:
            raise ValueError("answer khong duoc rong")
        return self


class FinalizeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1)
    end_reason: str = Field(min_length=1, max_length=64)
    duration_s: int = Field(ge=0)
