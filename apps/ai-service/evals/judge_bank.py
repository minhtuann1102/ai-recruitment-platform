"""LLM cham mau cap Q&A trong kho ai_db (context/de-data-assessment.md): dung topic_id khong, do kho DE gan co hop ly
khong, dap an dung va du khong, co hop de hoi mieng khong. Chi uoc luong (judge cung ho model voi agent), khong thay
nguoi duyet; chi doc ai_db (aie_reader).
  cd apps/ai-service && python -m evals.judge_bank --n 150 --seed 7
"""
import argparse
import asyncio
import collections
import glob
import json
import random

import psycopg
import yaml
from app.llm.gateway import build_client
from app.llm.settings import load_llm_settings
from app.rag.settings import load_rag_settings

SYS = ("Bạn là chuyên gia phỏng vấn kỹ thuật. Đánh giá một cặp hỏi đáp trong kho phỏng vấn. Trả JSON: "
       "topic_fit: 'main' (câu kiểm tra đúng chủ đề), 'related' (liên quan nhưng lệch trọng tâm), 'off' (không thuộc chủ đề); "
       "difficulty: 'easy' (nhớ định nghĩa), 'medium' (giải thích cơ chế, so sánh, áp dụng), 'hard' (internals, hiệu năng, phân tán, trade-off quy mô lớn); "
       "answer_quality: 'good' (đúng, đủ ý chính), 'thin' (đúng nhưng sơ sài), 'wrong' (có lỗi kiến thức), 'broken' (lỗi dịch/cắt cụt/không đọc được); "
       "interview_style: true nếu là câu hỏi phỏng vấn tự nhiên để hỏi miệng, false nếu là câu đố/trắc nghiệm/yêu cầu viết code dài.")


async def one(sem, r, cat, client, model):
    t = cat.get(r[0], {})
    user = json.dumps({"topic": t.get("title"), "key_concepts": t.get("key_concepts"), "pair": r[3][:2500]}, ensure_ascii=False)
    async with sem:
        resp = await client.chat.completions.create(
            model=model, temperature=0, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": SYS}, {"role": "user", "content": user}])
    return r, json.loads(resp.choices[0].message.content)


async def judge(sample, cat):
    sem = asyncio.Semaphore(8)
    client, model = build_client(load_llm_settings()), load_llm_settings().default_model
    res = await asyncio.gather(*(one(sem, r, cat, client, model) for r in sample))
    C = lambda k: collections.Counter(str(j.get(k)) for _, j in res)
    print("topic_fit", C("topic_fit"), "\nanswer_quality", C("answer_quality"), "\ninterview_style", C("interview_style"))
    agree = collections.Counter((r[1], j.get("difficulty")) for r, j in res)
    print("difficulty DE->judge", sorted(agree.items()))
    print("difficulty agree", round(sum(v for (a, b), v in agree.items() if a == b) / len(res), 2))
    for r, j in res:
        if j.get("topic_fit") == "off" or j.get("answer_quality") in ("wrong", "broken"):
            print(" -", r[0], "|", r[2][:90].replace("\n", " "), "|", j.get("topic_fit"), j.get("answer_quality"))


def main() -> None:
    cat = {t["id"]: t for f in glob.glob("app/catalog/*.yaml") for t in yaml.safe_load(open(f))["topics"]}
    s = load_rag_settings()
    with psycopg.connect(s.db_url, connect_timeout=10, options="-c default_transaction_read_only=on") as c:
        rows = c.execute("""SELECT q.topic_id, q.difficulty, q.content, p.content FROM knowledge_chunks q JOIN knowledge_chunks p
          ON p.metadata->>'qa_id'=q.metadata->>'qa_id' AND p.metadata->>'chunk_type'='qa_pair'
          WHERE q.metadata->>'chunk_type'='question'""").fetchall()
    args = argparse.ArgumentParser()
    args.add_argument("--n", type=int, default=150)
    args.add_argument("--seed", type=int, default=7)
    args = args.parse_args()
    random.seed(args.seed)
    sample = random.sample(rows, min(args.n, len(rows)))
    asyncio.run(judge(sample, cat))


if __name__ == "__main__":
    main()
