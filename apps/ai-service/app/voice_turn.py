"""Luot tra loi bang giong noi (NFR-AI-QUAL17, voice tuy chon A): ban ghi STT di vao /api/next-turn nhu van ban.

- answer_source = voice: doi thuat ngu phien am (stt_terms) cho moi noi doc cau tra loi - Evaluator, truy van RAG theo
  luot, topic_turns, last_answer cua Interviewer. Cau go tay (text, mac dinh) giu nguyen.
- Ban ghi rong / chi co tu dem ("ừm", "à"): micro khong thu duoc tieng. Tra loi 422 voice_no_speech ngay, khong
  cham, khong doi state; interview-service bao ung vien kiem tra micro / chuyen sang chat roi gui lai cung luot.
  Cau wrap-up (khong cham) va luc het gio / het luot (dieu kien uu tien) thi khong chan: luot di tiep, khong cham.
- stt_confidence < STT_MIN_CONFIDENCE: ban ghi khong dang tin, luot khong cham (khong goi Evaluator), khong tinh diem.
  Lan dau trong topic thi hoi lai nguyen cau; lan sau tra 422 voice_unclear goi y go chat (state giu nguyen, ung
  vien khong mat topic vi micro / moi truong on). Het gio (dieu kien uu tien) thi khong chan, luot di tiep khong cham.
"""
import os
import re
from typing import List

from .agents.interviewer import QuestionSpec
from .api_error import ApiError
from .evaluation_checks import zero_evaluation
from .mock_evaluator import fold
from .models_interview import Evaluation, NextTurnRequest, PlanTopic, TopicTurn
from .stt_terms import normalize_stt_terms

# Gia dinh, chua do tren dich vu STT that (thang confidence moi dich vu mot kieu): chot khi chon dich vu (QUAL16)
STT_MIN_CONFIDENCE = float(os.getenv("STT_MIN_CONFIDENCE", "0.6"))
if not 0 <= STT_MIN_CONFIDENCE <= 1:  # dat nham phan tram (60) thi moi luot voice deu bi bo cham: dung ngay khi chay
    raise ValueError(f"STT_MIN_CONFIDENCE phai trong [0, 1], dang la {STT_MIN_CONFIDENCE}")
MAX_REASKS = 1  # moi topic hoi lai toi da mot lan, tranh vong lap khi micro / moi truong on lien tuc
REASK = "Xin lỗi, mình chưa nghe rõ câu trả lời vừa rồi. Bạn nói lại giúp mình nhé: {q}"
NO_SPEECH = "Micro chưa thu được tiếng. Bạn kiểm tra micro rồi nói lại, hoặc chuyển sang gõ chat nhé."
UNCLEAR = "Mình vẫn chưa nghe rõ câu trả lời. Bạn thử gõ câu trả lời vào khung chat nhé."
_RETRY = {"retryable": True, "suggest_chat": True}  # interview-service: khong luu luot, gui lai cung turn_number
# am dem khi nguoi noi im / micro chi bat tieng on (da bo dau): "ừm" -> um, "ờ" -> o, "à" -> a
_NOISE_WORDS = {"a", "ah", "am", "e", "ha", "hm", "hmm", "hu", "hum", "o", "oh", "om", "u", "uh", "uhm", "um"}


def is_voice(req: NextTurnRequest) -> bool:
    return req.answer_source == "voice"


def heard_answer(req: NextTurnRequest) -> str:
    return normalize_stt_terms(req.answer) if is_voice(req) else req.answer


def heard_topic_turns(req: NextTurnRequest) -> List[TopicTurn]:
    """Luot truoc doi theo nguon cua chinh no; khong ghi nguon thi coi nhu cung nguon voi luot hien tai."""
    return [t.model_copy(update={"a": normalize_stt_terms(t.a)}) if (t.source or req.answer_source) == "voice" else t
            for t in req.topic_turns]


def no_speech(req: NextTurnRequest) -> bool:
    """Luot voice khong co tu nao ngoai am dem (micro khong thu tieng)."""
    return is_voice(req) and set(re.findall(r"\w+", fold(req.answer))) <= _NOISE_WORDS


def reject_no_speech() -> None:
    """Bao ngay cho ung vien, khong ton luot, khong goi LLM."""
    raise ApiError(422, "voice_no_speech", NO_SPEECH, dict(_RETRY))


def reject_unclear() -> None:
    """Da hoi lai trong topic ma ban ghi van kem: khong cham, khong doi state, goi y chuyen sang chat."""
    raise ApiError(422, "voice_unclear", UNCLEAR, dict(_RETRY))


def low_confidence(req: NextTurnRequest) -> bool:
    return is_voice(req) and req.stt_confidence is not None and req.stt_confidence < STT_MIN_CONFIDENCE


def unclear_evaluation(turn_number: int) -> Evaluation:
    """Khong cham noi dung: band 0 nhung is_scored = False nen khong vao diem topic / bao cao."""
    return zero_evaluation(turn_number, "answered").model_copy(update={"transcript_low_confidence": True})


def reask_spec(req: NextTurnRequest, phase: str, topic: PlanTopic, difficulty: int) -> QuestionSpec:
    """Cau hoi lai co dinh bang code (khong goi Interviewer): ung vien can nghe lai dung cau vua hoi."""
    return QuestionSpec("clarify", phase, topic, difficulty, last_question=req.question,
                        fixed_question=REASK.format(q=req.question))
