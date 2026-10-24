"""Choi thu mot buoi phong van that trong terminal: BAN la ung vien, ai-service chay LLM/RAG that.

Goi API giong interview-service (start -> next-turn ... -> finalize), dung lai evals/simulate_session.
Khong hien diem giua buoi (BR-07); bao cao chi hien sau khi ket thuc. Go /end de ket thuc som.
  cd apps/ai-service
  AGENT_EVALUATOR_MODE=llm AGENT_INTERVIEWER_MODE=llm AGENT_PLANNER_MODE=llm AGENT_REPORTER_MODE=llm \\
    .venv/bin/python -m evals.play --track java_backend --level junior                 # in-process
  .venv/bin/python -m evals.play --base-url http://localhost:8000 --track nodejs_backend   # server dang chay
Thoi gian trong phien la gia lap (30 s + 0.4 s x so tu moi cau), khong tinh theo dong ho that.
"""
import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.catalog.loader import list_tracks
from app.models_interview import PlanTopic
from evals.personas import Persona
from evals.simulate import make_client
from evals.simulate_session import run_session

REPORTS = Path(__file__).resolve().parents[3] / "plans" / "reports"
TAGS = {"hint": " (gợi ý)", "clarify": " (hỏi lại)", "wrap_up": " (kết thúc)"}


class HumanCandidate:
    """Doc cau tra loi tu ban phim; dong trong ket thuc cau tra loi nhieu dong; /end ket thuc phien."""

    async def answer(self, persona: Persona, topic: Optional[PlanTopic], question: str,
                     action: str) -> Optional[str]:
        title = f" · {topic.title}" if topic else ""
        print(f"\n\033[1mAI{TAGS.get(action, '')}{title}:\033[0m {question}")
        print("Bạn (Enter 2 lần để gửi, /end để kết thúc):")
        lines = []
        while True:
            line = await asyncio.to_thread(input, "> " if not lines else "  ")
            if line.strip() == "/end" and not lines:
                return None
            if not line.strip():
                if lines:
                    break
                continue
            lines.append(line.rstrip())
        return "\n".join(lines)


def print_report(report: dict) -> None:
    o = report["overall"]
    print(f"\n\033[1m=== Báo cáo ({report['status']}) ===\033[0m")
    print(f"Điểm tổng: {o['score']}/10 · {o['verdict']} · độ tin cậy {report['session']['confidence']}")
    print(o["summary"])
    print("Theo phần: " + ", ".join(f"{s['phase']} {s['score']}" for s in report["sections"]))
    print("Theo tiêu chí: " + ", ".join(f"{k} {v}" for k, v in report["criteria"].items()))
    for title, key in (("Điểm mạnh", "strengths"), ("Cần cải thiện", "improvements")):
        for item in report.get(key, []):
            print(f"- {title}: {item['point']} (lượt {item['evidence_turns']})")
    for item in report.get("study_plan", []):
        print(f"- Lộ trình [{item['priority']}] {item['topic']}: " + "; ".join(item["actions"]))
    for t in report.get("turns", []):
        print(f"  lượt {t['turn_number']}: {t['scores']} · {t['comment']}")
    print(report["meta"]["disclaimer"])


async def main_async(args) -> None:
    persona = Persona("play", args.track, args.level, "human", [], [], [], "")
    async with make_client(args.base_url) as client:
        session = await run_session(client, persona, HumanCandidate(), args.duration)
    if session["report"] is None:
        print("Đã kết thúc trước khi trả lời câu nào, không có báo cáo.")
        return
    print_report(session["report"])
    out = REPORTS / f"play-{datetime.now():%y%m%d-%H%M}.json"  # plans/reports/*.json: git bo qua (.gitignore)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(session, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nĐã lưu phiên (transcript + metadata) vào {out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", default="java_backend", choices=list_tracks())
    parser.add_argument("--level", default="junior", choices=["fresher", "junior", "middle", "senior"])
    parser.add_argument("--duration", type=int, default=20)
    parser.add_argument("--base-url")
    args = parser.parse_args()
    try:
        asyncio.run(main_async(args))
    except (KeyboardInterrupt, EOFError):
        print("\nĐã dừng.")


if __name__ == "__main__":
    main()
