"""Model Pydantic cua voice-service (data-model.md). Khong co database: chi la dang request / response.

Khong co truong stt_confidence o bat ky model nao: nha cung cap khong tra va service khong bia (FR-003).
Khong co chi so ve con nguoi (tuoi, gioi tinh, cam xuc, phat am) (FR-008).
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class SpeechSegment(BaseModel):
    """Doan co tieng (VAD), giay tinh tu dau file."""
    start: float = Field(ge=0)
    end: float

    @model_validator(mode="after")
    def _end_after_start(self) -> "SpeechSegment":
        if not self.end > self.start:
            raise ValueError("end phai lon hon start")
        return self


class TurnDeliveryMetrics(BaseModel):
    """Chi so trinh bay cua mot luot (FR-006). Moi truong co the rong (null); khong bao 0 thay cho 'khong do duoc'."""
    topic_id: Optional[str] = Field(default=None, max_length=64)
    thinking_time_s: Optional[float] = Field(default=None, ge=0)
    answer_duration_s: Optional[float] = Field(default=None, ge=0)
    over_limit: Optional[bool] = None
    speech_time_s: Optional[float] = Field(default=None, ge=0)
    speech_rate_spm: Optional[float] = Field(default=None, ge=0)
    long_pause_count: Optional[int] = Field(default=None, ge=0)
    filler_ratio: Optional[float] = Field(default=None, ge=0, le=1)


class ProviderInfo(BaseModel):
    stt_model: str
    stt_ms: Optional[int] = None  # null khi khong goi STT (no_speech)
    vad_ms: int


class TranscriptionResult(BaseModel):
    no_speech: bool
    transcript: str
    segments: List[SpeechSegment]
    metrics: Optional[TurnDeliveryMetrics]
    warnings: List[str]
    provider: ProviderInfo


class SpeakRequest(BaseModel):
    # do dai toi da theo VOICE_MAX_TTS_CHARS duoc kiem o route (ma text_too_long), khong o day
    text: str = Field(min_length=1)
    voice: Optional[str] = None


class SummaryRequest(BaseModel):
    turns: List[TurnDeliveryMetrics] = Field(max_length=200)  # phien 20 phut khong co nhieu luot hon the


class MetricStats(BaseModel):
    median: float
    min: float
    max: float
    n: int


class SummaryCounts(BaseModel):
    turns_with_long_pause: int
    turns_over_limit: int
    turns_with_limit: int


class SessionDeliverySummary(BaseModel):
    voice_turns: int
    stats: Dict[str, MetricStats]
    counts: SummaryCounts
    notes: List[str]
