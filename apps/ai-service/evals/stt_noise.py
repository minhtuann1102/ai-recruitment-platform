"""Mau golden nhieu STT (NFR-AI-QUAL17, voice tuy chon A): cung cau hoi va noi dung voi mau sach, chi khac ban ghi
nhan dang (khong dau cau, thuat ngu Anh phien am, tu dem). Nhan nguoi lay theo mau sach vi noi dung khong doi;
chi so chinh la chenh diem giua ban nhieu va ban sach tren cung lan chay."""
import json
import re
from pathlib import Path
from statistics import mean
from typing import Dict, List

STT_GOLDEN = Path(__file__).with_name("evaluator_golden_stt.jsonl")


def stt_samples(clean: List[dict], path: Path = STT_GOLDEN) -> List[dict]:
    """Ban nhieu = mau sach thay `answer`; qid rieng de chi so thu tu khong tron ban sach voi ban nhieu."""
    by_id = {s["id"]: s for s in clean}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [{**by_id[r["stt_of"]], "id": r["id"], "qid": f"{by_id[r['stt_of']]['qid']}-stt", "answer": r["answer"],
             "stt_of": r["stt_of"], "noise": r["noise"]} for r in rows if r["stt_of"] in by_id]  # --limit bo mau sach


def spoken_plain(text: str) -> str:
    """Ban "STT tot": thuat ngu viet dung, chi mat dau cau, viet thuong, them tu dem nhu ban ghi giong noi that.
    Tach rieng anh huong cua dau cau / tu dem khoi anh huong cua thuat ngu phien am (bo nhieu chinh)."""
    sentences = [s for s in re.split(r"(?<=[.;:!?])\s+", text.replace("[]", "mảng rỗng")) if s.strip()]
    words = []
    for i, s in enumerate(sentences):
        words += (["à"] if i == 0 else ["ừm"] if i == 1 else []) + re.sub(r"[.,;:!?()\[\]\"]", " ", s).split()
    return " ".join(words).lower()


def plain_samples(clean: List[dict], path: Path = STT_GOLDEN) -> List[dict]:
    """Cung cap mau voi bo nhieu chinh, cau tra loi = spoken_plain(ban sach); id "<sach>-plain"."""
    by_id = {s["id"]: s for s in clean}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [{**by_id[r["stt_of"]], "id": f"{r['stt_of']}-plain", "qid": f"{by_id[r['stt_of']]['qid']}-plain",
             "answer": spoken_plain(by_id[r["stt_of"]]["answer"]), "stt_of": r["stt_of"],
             "noise": ["no_punctuation", "lowercase", "fillers"]} for r in rows if r["stt_of"] in by_id]


def inherit_labels(labels: Dict[str, Dict[str, dict]], noisy: List[dict]) -> Dict[str, Dict[str, dict]]:
    return {name: {**lab, **{s["id"]: lab[s["stt_of"]] for s in noisy if s["stt_of"] in lab}}
            for name, lab in labels.items()}


def stt_summary(noisy: List[dict], results: Dict[str, List[dict]]) -> dict:
    """Chenh turn_score_10 (nhieu - sach, thang 10) theo cap, trung binh cac lan chay khong degraded."""
    diffs, same_type = [], []
    for s in noisy:
        clean = [r for r in results.get(s["stt_of"], []) if not r["degraded"]]
        dirty = [r for r in results.get(s["id"], []) if not r["degraded"]]
        if not clean or not dirty:
            continue
        diffs.append(mean(r["turn_score_10"] for r in dirty) - mean(r["turn_score_10"] for r in clean))
        same_type.append(dirty[0]["answer_type"] == clean[0]["answer_type"])
    if not diffs:
        return {"pairs": 0}
    return {"pairs": len(diffs), "mean_diff": round(mean(diffs), 2), "max_abs_diff": round(max(map(abs, diffs)), 2),
            "within_1": round(sum(abs(d) <= 1.0 for d in diffs) / len(diffs), 3),
            "same_answer_type": round(sum(same_type) / len(same_type), 3)}
