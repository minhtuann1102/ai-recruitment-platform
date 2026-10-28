"""Client LLM gia cho test synth-jd (spec 009 US5): doc tham so o tu prompt, tra JSON, khong goi mang.

Van ban tu soan (FR-007), khong nhac ky nang nao ngoai danh sach duoc cho.
"""
import json
import re
import threading
from typing import Callable, Dict, List, Optional

_FIELD_RE = {
    "level": re.compile(r"^Từ cấp bậc trong title: (.+)$", re.M),
    "role": re.compile(r"^Từ vai trò trong title.*?: (.+)$", re.M),
    "city": re.compile(r"^Thành phố: (.+)$", re.M),
    "skills": re.compile(r"^Kỹ năng \(chỉ dùng các tên này\): (.+)$", re.M),
}


def prompt_fields(messages: List[Dict[str, str]]) -> Dict[str, str]:
    user = messages[1]["content"]
    return {key: pattern.search(user).group(1) for key, pattern in _FIELD_RE.items()}


def good_description(city: str, skills: str, requirements: bool = True, extra: str = "") -> str:
    lines = [
        f"Địa điểm: {city}",
        "Mô tả công việc",
        "- Xây dựng tính năng mới cho phần mềm quản lý kho của công ty.",
        "- Phối hợp với nhóm sản phẩm để làm rõ yêu cầu và cải tiến chất lượng mã nguồn.",
    ]
    if requirements:
        lines += ["Yêu cầu ứng viên", f"- Thành thạo {skills}.",
                  "- Tốt nghiệp đại học ngành Công nghệ thông tin hoặc liên quan."]
    lines += ["Quyền lợi", "- Lương tháng 13, bảo hiểm sức khỏe, 15 ngày phép mỗi năm.",
              "- Đào tạo nội bộ hằng quý, du lịch công ty hằng năm."]
    if extra:
        lines.append(extra)
    return "\n".join(lines)


def good_answer(messages: List[Dict[str, str]], extra: str = "", requirements: bool = True,
                level: Optional[str] = None) -> str:
    f = prompt_fields(messages)
    role = f["role"].split(" / ")[0]
    title = f"{level or f['level']} {role} ({f['skills'].split(', ')[0]})"
    return json.dumps({"title": title, "description_text": good_description(f["city"], f["skills"], requirements, extra)},
                      ensure_ascii=False)


class FakeLlm:
    """complete(messages) -> (json, 600, 900); answers: ham (messages, so lan goi cua JD nay) -> chuoi tra ve."""

    def __init__(self, answer: Callable[[List[Dict[str, str]], int], str] = lambda m, i: good_answer(m)):
        self._answer = answer
        self._lock = threading.Lock()
        self.calls: List[List[Dict[str, str]]] = []

    def __call__(self, messages: List[Dict[str, str]]):
        with self._lock:
            self.calls.append(messages)
        attempt = sum(1 for m in messages if m["role"] == "assistant")  # 0 = lan dau, 1, 2 = retry
        return self._answer(messages, attempt), 600, 900
