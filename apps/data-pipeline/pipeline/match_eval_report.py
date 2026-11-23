"""Dung bang markdown ket qua danh gia goi y CV-JD (spec 017 US3, FR-021) tu dict cua match_eval_summary.build_summary.

Bang dung truc tiep cho bao cao do an nen viet tieng Viet co dau; moi quy uoc do (mau so P@5, nDCG khi khong co JD lien quan,
percentile, cach tach ngon ngu, phuong phap gan nhan) duoc in ngay duoi bang de nguoi doc khong phai doan.
"""
from typing import Dict, List, Optional

from .match_eval_metrics import METHODS

METHOD_NAMES = {"full": "Đầy đủ (`score`)", "skill_match": "Chỉ `skill_match`", "cosine": "Chỉ `cosine`"}
GROUP_NAMES = {"same": "cùng ngôn ngữ (JD vi)", "cross": "khác ngôn ngữ (JD en/mixed)"}
SC002_LIMIT_MS = 500.0


def _num(value: Optional[float], digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _ms(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.1f} ms"


def _usd(value: Optional[float]) -> str:
    return "n/a" if value is None else f"${value:.6f}"


def _table(header: List[str], rows: List[List[str]]) -> List[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(row) + " |" for row in rows]


def _dataset(summary: Dict) -> List[str]:
    d, label = summary["dataset"], summary["dataset"]["labeling"]
    agree = label.get("agreement") or {}
    langs = ", ".join(f"{k} {v}" for k, v in d["jd_languages"].items())
    counts = ", ".join(f"{k} = {v}" for k, v in d["label_counts"].items())
    weights = " / ".join(f"{k} {v}" for k, v in (d["weights"] or {}).items()) or "n/a"
    lines = [
        "## 1. Bộ dữ liệu", "",
        f"- {d['n_cv']} CV tổng hợp (viết tiếng Việt), {d['n_jd']} JD của 009 ({d['n_synthetic_jd']} tổng hợp; ngôn ngữ JD: {langs}), "
        f"{d['n_pairs']} cặp có nhãn (mọi cặp qua lọc cứng), as-of {d['as_of']}.",
        "- Tập cặp qua lọc cứng của endpoint trùng đúng tập đã gán nhãn (lệnh dừng với mã 1 nếu lệch, nên bảng này chỉ có khi hai tập "
        "bằng nhau): bằng chứng cho vế bộ lọc cứng của SC-004.",
        f"- Model embedding `{d['embedding_model']}`, chỉ mục {d['index_size']} JD, trọng số {weights}, lệch bậc tối đa {d['max_level_gap']}.",
        f"- Phân bố nhãn: {counts}.",
        f"- Cách gán nhãn: `{label.get('labeled_by')}` ({label.get('labeled_at')}), phương pháp `{label.get('method')}`; "
        f"rubric: {label.get('rubric')}; tập cặp: {label.get('pair_set')}.",
    ]
    if agree:
        lines.append(
            f"- Đồng thuận: kappa có trọng số (quadratic) giữa DE gán mù và LLM = {_num(agree.get('weighted_kappa_quadratic'))} "
            f"trên {agree.get('n_blind')} cặp gán mù (trước khi sửa rubric: {_num(agree.get('weighted_kappa_before_rubric_fix'))}; "
            f"khớp tuyệt đối {_num(agree.get('exact'))}, lệch tối đa một mức {_num(agree.get('within_one'))}).")
    else:
        lines.append("- Đồng thuận: `labels.json` không ghi kappa.")
    if label.get("final_source"):
        lines.append(f"- Nguồn nhãn cuối: {', '.join(f'{k} {v}' for k, v in label['final_source'].items())}.")
    lines.append("- Giới hạn của nhãn: nhãn cuối là nhãn LLM, không phải nhãn của người; DE chỉ gán mù một phần nhỏ để đo đồng "
                 "thuận, nên số liệu bên dưới đo độ khớp với cách LLM chấm theo rubric.")
    return lines + [""]


def _quality(summary: Dict) -> List[str]:
    q = summary["quality"]
    rows = [[METHOD_NAMES[m], _num(q[m]["p_at_5"]), _num(q[m]["ndcg_at_5"]), str(q[m]["n_cv"])] for m in METHODS]
    full, base = q["full"]["ndcg_at_5"], q["skill_match"]["ndcg_at_5"]
    ok = full is not None and base is not None and full > base
    verdict = (f"**SC-001** (nDCG@5 đầy đủ > chỉ `skill_match`): {'đạt' if ok else 'không đạt'} "
               f"({_num(full)} so với {_num(base)}, chênh {_num(None if full is None or base is None else full - base)}).")
    return ["## 2. Chất lượng gợi ý", "",
            "Trung bình trên các CV. Cả ba cách xếp lại kết quả của cùng một lần gọi endpoint (cùng bộ lọc cứng); hòa điểm thì `job_id` tăng dần.", "",
            *_table(["Cách tính", "P@5", "nDCG@5", "Số CV"], rows), "",
            "P@5: liên quan = nhãn ≥ 1. nDCG@5: gain = nhãn 0/1/2 (tuyến tính), ideal tính từ mọi nhãn của CV. "
            "CV không có JD liên quan trong tập đang xét bị bỏ khỏi cả hai trung bình (cột số CV).", "", verdict, ""]


def _language(summary: Dict) -> List[str]:
    rows = [[METHOD_NAMES[m], GROUP_NAMES[g], _num(s["p_at_5"]), _num(s["ndcg_at_5"]), str(s["n_cv"]), str(s["n_pairs"])]
            for g, by_method in summary["language_split"].items() for m, s in by_method.items()]
    return ["## 3. Theo ngôn ngữ", "",
            "Cách tính: CV đều viết tiếng Việt; ngôn ngữ JD lấy từ trường `language` của `jd_normalized.jsonl` (vi / en / mixed). "
            "Với mỗi CV, giữ các JD qua lọc cứng thuộc nhóm ngôn ngữ, xếp theo từng cách tính, tính P@5 và nDCG@5 trên tập con đó, "
            "rồi lấy trung bình theo từng CV. Tập con dưới 5 JD thì P@5 chia cho số JD của tập; CV không có JD liên quan trong "
            "tập con bị bỏ (cột số CV).", "",
            *_table(["Cách tính", "Nhóm JD", "P@5", "nDCG@5", "Số CV", "Số cặp"], rows), ""]


def _latency(summary: Dict) -> List[str]:
    lat, rounds, n_cv = summary["latency"], summary["rounds"], summary["dataset"]["n_cv"]
    names = {"with_job_ids": "có `job_ids` (pool)", "without_job_ids": "không `job_ids` (toàn chỉ mục)"}
    rows = [[f"{label} {names[v]}", str(lat[v][key]["n"]), _ms(lat[v][key]["p50"]), _ms(lat[v][key]["p95"])]
            for key, label in (("server_score_ms", "Tính điểm, server (`timing_ms.score`),"), ("client_ms", "Toàn bộ yêu cầu, client (gồm embed CV),"))
            for v in names]
    p95 = lat["without_job_ids"]["server_score_ms"]["p95"]
    verdict = ("chưa đo được" if p95 is None else f"{'đạt' if p95 <= SC002_LIMIT_MS else 'không đạt'} (p95 = {_ms(p95)})")
    return ["## 4. Độ trễ", "",
            f"{rounds} vòng × {n_cv} CV; mỗi vòng gọi cả hai kiểu (page_size 50 khi có `job_ids`, 10 khi không có). "
            "Lần gọi chất lượng ở mục 2 không tính (khởi động chỉ mục). Percentile theo nearest-rank.", "",
            *_table(["Phép đo", "Số mẫu", "p50", "p95"], rows), "",
            f"**SC-002** (p95 phần tính điểm ≤ {SC002_LIMIT_MS:.0f} ms trên toàn chỉ mục): {verdict}.", ""]


def _cost(summary: Dict) -> List[str]:
    cost = summary["cost"]
    index, request = cost["index"], cost["request"]
    if index["embedding_tokens"] is None:
        index_line = "- Index toàn bộ JD: chưa có run report index-jd-match nên chưa tính được (chạy `index-jd-match` trước)."
    else:
        if index["embedding_tokens"] == 0:
            note = "; lần chạy này không embed bản ghi nào nên đây không phải chi phí index đầy đủ"
        elif not index["complete"]:
            note = (f"; lần chạy chưa đầy đủ (cleanup `{index['cleanup']}`), không phải chi phí index đầy đủ: "
                    "chạy `index-jd-match --rebuild` để có số đo đủ")
        else:
            note = ""
        index_line = (f"- Index toàn bộ JD: {index['embedding_tokens']} token ≈ {_usd(index['usd'])}, "
                      f"từ `{index['source']}` (embed {index['embedded']} / {index['records']} bản ghi){note}.")
    return ["## 5. Chi phí embedding", "",
            f"Đơn giá `EMBEDDING_PRICE_PER_1M` = ${cost['price_per_1m_usd']} / 1 triệu token.", "", index_line,
            f"- Mỗi yêu cầu: trung bình {_num(request['mean_embedding_tokens'], 1)} token ≈ {_usd(request['usd'])} "
            f"(từ `metadata.usage` của {request['n_requests']} yêu cầu).", ""]


def _limits(summary: Dict) -> List[str]:
    d = summary["dataset"]
    return ["## 6. Hạn chế", "",
            f"- Bộ dữ liệu nhỏ ({d['n_cv']} CV, {d['n_jd']} JD, {d['n_pairs']} cặp): chênh lệch nhỏ giữa các cách tính có thể là nhiễu; không có khoảng tin cậy.",
            "- CV tổng hợp viết thẳng dưới dạng `CvProfile`, bỏ qua sai số của CV Parser: chưa đo cả chuỗi từ file CV.",
            "- Độ trễ đo trên một máy, từng yêu cầu một, chưa đo tải đồng thời; phụ thuộc đường truyền tới provider embedding.",
            "- Lệnh này không kiểm phần `matched_skills` / `missing_skills` khớp `skill_match` của SC-004.",
            "- Mỗi cách tính hòa điểm thì xếp theo `job_id`; `skill_match` là tỉ lệ nên dễ hòa, khi đó thứ hạng baseline phụ thuộc thứ tự `job_id`.",
            "- Kết quả chỉ đúng với bộ lọc cứng, trọng số và chỉ mục ghi ở mục 1 tại thời điểm chạy.", ""]


def render_markdown(summary: Dict, raw_name: str) -> str:
    head = ["# Kết quả đánh giá gợi ý việc làm CV–JD (spec 017, US3)", "",
            f"Sinh bởi `python -m pipeline match-eval --rounds {summary['rounds']}` lúc {summary['generated_at']}. "
            f"Số liệu thô: `data/processed/match_eval/{raw_name}` (không commit).", ""]
    return "\n".join(head + _dataset(summary) + _quality(summary) + _language(summary) + _latency(summary) + _cost(summary) + _limits(summary))
