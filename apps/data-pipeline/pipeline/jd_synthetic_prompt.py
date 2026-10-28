"""Tham so + prompt cho mot JD synthetic (spec 009 research R9, FR-024, FR-025).

Code chon moi thu co the kiem duoc (cong ty hu cau, ky nang, kinh nghiem, luong), deterministic theo (o, so thu tu):
cung (o, n) -> cung tham so. LLM chi viet tieu de + mo ta theo tham so, tra JSON. Prompt chi chua tham so o va ten
ky nang trong danh muc, khong chua noi dung JD crawl nao (FR-024).
"""
import hashlib
import random
from dataclasses import dataclass
from typing import AbstractSet, Dict, List, Optional, Tuple

from .skill_dictionary import SkillDictionary
from .text_cleaning import normalize_for_compare

Cell = Tuple[str, str, str]  # (group, level, city)

# Tu cap bac trong tieu de: jd_normalizer.level_from_title nhan ra dung cap (round trip FR-027)
LEVEL_TITLE_WORD = {
    "Intern": "Intern", "Junior": "Junior", "Mid": "Middle", "Senior": "Senior", "Lead": "Lead", "Manager": "Manager",
}
GROUP_ROLE_WORDS = {
    "backend": "Backend Developer",
    "frontend": "Frontend Developer",
    "mobile_fullstack": "Mobile Developer",
    "devops": "DevOps Engineer",
    "ai_data": "Data Engineer / AI Engineer",
}
# experience_raw theo cap; Lead / Manager de trong vi so nam >= 5 suy ra Senior (cap lay tu tieu de)
LEVEL_EXPERIENCE = {"Intern": "6 months", "Junior": "24 months", "Mid": "36 months", "Senior": "60 months"}
LEVEL_YEARS_TEXT = {
    "Intern": "chưa cần kinh nghiệm", "Junior": "1-2 năm", "Mid": "3-4 năm", "Senior": "5 năm trở lên",
    "Lead": "6 năm trở lên, đã dẫn dắt nhóm", "Manager": "8 năm trở lên, đã quản lý nhiều nhóm",
}
LEVEL_SALARY_MILLION = {
    "Intern": (3, 6), "Junior": (10, 18), "Mid": (18, 30), "Senior": (30, 50), "Lead": (45, 70), "Manager": (60, 90),
}
LOCATION_PREFIX = "Địa điểm: "
HEADINGS = ("Mô tả công việc", "Yêu cầu ứng viên", "Quyền lợi")
MIN_SKILLS, MAX_SKILLS = 3, 5

# Ten cong ty hu cau: ghep tu danh sach tu co dinh, tranh tu trung bi danh ky nang
_COMPANY_KINDS = ("Phần mềm", "Công nghệ", "Giải pháp số", "Hệ thống thông tin")
_COMPANY_NAMES = (
    "An Khang", "Bình Minh", "Cát Tường", "Đông Phong", "Hải Âu", "Hoàng Lam", "Kim Sơn", "Lam Ngọc",
    "Minh Triết", "Ngân Hà", "Phú Thịnh", "Sao Khuê", "Thiên Lộc", "Trúc Xanh", "Vạn Xuân", "Việt Tín",
)
_COMPANY_SUFFIXES = ("", " Labs", " Studio", " Tech")

SYSTEM_PROMPT = """Bạn viết tin tuyển dụng IT bằng tiếng Việt cho một công ty hư cấu, dùng làm dữ liệu mẫu.
Chỉ trả về một json object với hai khóa: "title" (string) và "description_text" (string).
Luật:
- title: một dòng, phải chứa đúng từ cấp bậc và từ vai trò được cho, có thể thêm 1-2 kỹ năng trong ngoặc. Ví dụ: "Senior Backend Developer (Java, Spring Boot)".
- description_text: dòng đầu tiên đúng "Địa điểm: <thành phố được cho>". Sau đó ba phần, mỗi tiêu đề nằm trên một dòng riêng, đúng chữ và đúng thứ tự: "Mô tả công việc", "Yêu cầu ứng viên", "Quyền lợi". Mỗi phần 3-6 gạch đầu dòng "- ", không phần nào được để trống.
- Kỹ năng: chỉ nhắc các kỹ năng trong danh sách được cho, viết đúng tên như danh sách. Không nhắc công nghệ, ngôn ngữ, công cụ hay framework nào khác.
- Không viết email, số điện thoại, URL, website, tên người liên hệ hay mạng xã hội.
- Không viết cụm "Khoa học máy tính"; nói về bằng cấp thì viết "tốt nghiệp đại học ngành Công nghệ thông tin hoặc liên quan". Không viết tắt bằng cấp như "TS", "ThS".
- Không dùng cụm "worker node" trừ khi vai trò là DevOps Engineer.
- Không nhắc làm việc từ xa hay hybrid; làm việc tại văn phòng.
- Không ghi mức lương cụ thể."""


@dataclass(frozen=True)
class SynthParams:
    cell: Cell
    n: int
    company: str
    skills: Tuple[str, ...]  # ten chuan trong danh muc cua nhom
    experience_raw: Optional[str]
    salary_min: int
    salary_max: int

    @property
    def source_job_id(self) -> str:
        group, level, city = self.cell
        return f"syn-{group}-{level}-{city}-{self.n}"


def _rng(cell: Cell, n: int, salt: str) -> random.Random:
    digest = hashlib.sha256("|".join((*cell, str(n), salt)).encode("utf-8")).hexdigest()
    return random.Random(int(digest, 16))


def fictional_company(cell: Cell, n: int, crawl_companies: AbstractSet[str]) -> str:
    """Ten cong ty hu cau deterministic theo (o, n), khong trung (sau chuan hoa) cong ty nao trong JD crawl."""
    taken = {normalize_for_compare(c) for c in crawl_companies}
    for attempt in range(100):
        rng = _rng(cell, n, f"company-{attempt}")
        name = (f"Công ty {rng.choice(_COMPANY_KINDS)} {rng.choice(_COMPANY_NAMES)}"
                f"{rng.choice(_COMPANY_SUFFIXES)}")
        if normalize_for_compare(name) not in taken:
            return name
    raise RuntimeError("khong tim duoc ten cong ty hu cau khong trung cong ty crawl")


def group_skill_names(dictionary: SkillDictionary, group: str) -> List[str]:
    return sorted(skill.name for skill in dictionary.skills.values() if skill.group == group)


def build_params(cell: Cell, n: int, dictionary: SkillDictionary, crawl_companies: AbstractSet[str]) -> SynthParams:
    group, level, _ = cell
    names = group_skill_names(dictionary, group)
    rng = _rng(cell, n, "skills")
    skills = tuple(sorted(rng.sample(names, min(len(names), rng.randint(MIN_SKILLS, MAX_SKILLS)))))
    low, high = LEVEL_SALARY_MILLION[level]
    return SynthParams(cell, n, fictional_company(cell, n, crawl_companies), skills,
                       LEVEL_EXPERIENCE.get(level), low * 1_000_000, high * 1_000_000)


def build_messages(params: SynthParams) -> List[Dict[str, str]]:
    group, level, city = params.cell
    user = (
        f"Công ty: {params.company}\n"
        f"Từ cấp bậc trong title: {LEVEL_TITLE_WORD[level]}\n"
        f"Từ vai trò trong title (chọn một nếu có dấu /): {GROUP_ROLE_WORDS[group]}\n"
        f"Thành phố: {city}\n"
        f"Kinh nghiệm: {LEVEL_YEARS_TEXT[level]}\n"
        f"Kỹ năng (chỉ dùng các tên này): {', '.join(params.skills)}"
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]
