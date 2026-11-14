"""Ghi chu cua agent xuyen topic (phase 07, AGENT_NOTES_ENABLED): model luu trong CandidateState.notes.

Chi Evaluator (v11) ghi va doc; text sinh tu cau tra loi khong tin cay nen qua app/agent_notes.safe_note truoc khi luu.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

NOTE_KINDS = ("hypothesis", "to_verify", "strength", "risk")
NOTE_STATUSES = ("open", "confirmed", "rejected")
MAX_NOTES = 8  # state.notes toi da (code ghi khong qua so nay)
MAX_INPUT_TEXT = 300  # chan state gia tu client (422); code luon ghi <= 150 (agent_notes.MAX_TEXT)


class Note(BaseModel):
    id: str  # n{turn}: moi luot toi da 1 ghi chu moi
    turn: int
    topic_id: Optional[str] = None
    kind: Literal["hypothesis", "to_verify", "strength", "risk"]
    text: str = Field(max_length=MAX_INPUT_TEXT)  # code ghi <= 150 ky tu, da qua safe_note
    status: Literal["open", "confirmed", "rejected"] = "open"
