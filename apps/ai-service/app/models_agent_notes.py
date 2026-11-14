"""Ghi chu cua agent xuyen topic (phase 07, AGENT_NOTES_ENABLED): model luu trong CandidateState.notes.

Chi Evaluator (v11) ghi va doc; text sinh tu cau tra loi khong tin cay nen qua app/agent_notes.safe_note truoc khi luu.
"""
from typing import Literal, Optional

from pydantic import BaseModel

NOTE_KINDS = ("hypothesis", "to_verify", "strength", "risk")
NOTE_STATUSES = ("open", "confirmed", "rejected")


class Note(BaseModel):
    id: str  # n{turn}: moi luot toi da 1 ghi chu moi
    turn: int
    topic_id: Optional[str] = None
    kind: Literal["hypothesis", "to_verify", "strength", "risk"]
    text: str  # <= 150 ky tu, da qua safe_note
    status: Literal["open", "confirmed", "rejected"] = "open"
