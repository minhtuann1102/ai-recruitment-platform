"""Chuan hoa truong JD (spec 009 T021, research R6): cap bac, loai hinh, thanh pho, luong, ngon ngu."""
import pytest

from pipeline.jd_normalizer import (
    EN_RATIO_MAX,
    VI_RATIO_MIN,
    detect_language,
    normalize_city,
    normalize_level,
    normalize_work_type,
)
from pipeline.jd_salary import normalize_salary, parse_salary_text


@pytest.mark.parametrize(
    "title, experience, expected",
    [
        ("Senior Java Developer", "12 months", "Senior"),  # tieu de thang so nam
        ("Fresher PHP Developer", None, "Junior"),
        ("Thực tập sinh Kiểm thử phần mềm", None, "Intern"),
        ("Junior/Middle React Developer", None, "Junior"),  # tu khoa som nhat
        ("Trưởng nhóm Backend", None, "Lead"),
        ("Engineering Manager", None, "Manager"),
        ("Backend Developer", "6 months", "Intern"),
        ("Backend Developer", "2 năm", "Junior"),
        ("Backend Developer", "36 months", "Mid"),
        ("Backend Developer", "5+ years", "Senior"),
        ("Backend Developer", "Không yêu cầu kinh nghiệm", None),  # khong suy ra duoc
        ("Backend Developer", None, None),
    ],
)
def test_level(title, experience, expected):
    assert normalize_level(title, experience) == expected


def test_lead_keyword_does_not_match_leading():
    assert normalize_level("Developer at a leading fintech", None) is None


@pytest.mark.parametrize(
    "types, texts, expected",
    [
        (["FULL_TIME", "TELECOMMUTE"], (), "remote"),
        (["FULL_TIME"], ("Backend Developer (Remote)",), "remote"),
        (["FULL_TIME"], ("Lập trình viên làm việc từ xa",), "remote"),
        (["FULL_TIME"], ("Frontend Developer - Hybrid",), "hybrid"),
        (["FULL_TIME"], ("Backend Developer", "Hà Nội"), "onsite"),
        ([], (), "onsite"),
    ],
)
def test_work_type(types, texts, expected):
    assert normalize_work_type(types, *texts) == expected


@pytest.mark.parametrize(
    "locations, expected",
    [
        (["Ho Chi Minh"], "Hồ Chí Minh"),
        (["HCM"], "Hồ Chí Minh"),
        (["Quận 1, TP.HCM"], "Hồ Chí Minh"),
        (["Hanoi"], "Hà Nội"),
        (["Tầng 5, Cầu Giấy, Hà Nội", "Đà Nẵng"], "Hà Nội"),  # nhieu dia diem -> dia diem dau
        (["Remote", "Da Nang"], "Đà Nẵng"),  # bo qua dia diem khong nhan ra
        (["Singapore"], None),
        ([], None),
    ],
)
def test_city(locations, expected):
    assert normalize_city(locations) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("9.000.000 VND - 20.000.000 VND", (9_000_000, 20_000_000, "VND")),
        ("15 - 25 triệu", (15_000_000, 25_000_000, "VND")),
        ("$1,000 - 2,000", (1000, 2000, "USD")),
        ("Up to 2000$", (None, 2000, "USD")),
        ("Up to 60M", (None, 60_000_000, "VND")),
        ("Từ 15 triệu", (15_000_000, None, "VND")),
    ],
)
def test_numeric_salary_text(text, expected):
    assert parse_salary_text(text) == expected


@pytest.mark.parametrize(
    "text", ["You'll love it", "Cạnh tranh", "Negotiable", "Thỏa thuận", "Sign in to view salary", "Java 8", ""]
)
def test_text_salary_is_empty(text):
    assert normalize_salary({"text": text, "min": None, "max": None}) == (None, None, None)


def test_base_salary_numbers_and_min_only():
    assert normalize_salary({"currency": "VND", "min": 20_000_000, "max": 30_000_000, "text": None}) == (
        20_000_000, 30_000_000, "VND",
    )
    assert normalize_salary({"currency": "VND", "min": 20_000_000, "max": None, "text": None}) == (
        20_000_000, None, "VND",
    )
    assert normalize_salary({"currency": None, "min": 1500, "max": 2500, "text": None}) == (1500, 2500, "USD")


def test_salary_from_title_when_raw_is_text():
    raw = {"text": "You'll love it", "min": None, "max": None}
    assert normalize_salary(raw, "Senior Backend Engineer (Java, 5 years) - Up to 60M") == (None, 60_000_000, "VND")
    assert normalize_salary(None, "Senior Backend Engineer") == (None, None, None)


def test_language_thresholds_are_pinned():
    assert (VI_RATIO_MIN, EN_RATIO_MAX) == (0.12, 0.03)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Mô tả công việc: phát triển và bảo trì hệ thống backend cho khách hàng trong nước.", "vi"),
        ("We are looking for a backend engineer to join our product team at Công ty Gió Mới. You will design APIs, "
         "review code and mentor junior engineers.", "en"),
        ("Mô tả công việc: phát triển hệ thống. We are looking for a backend engineer with strong Java skills.", "mixed"),
        ("", "en"),
    ],
)
def test_language(text, expected):
    assert detect_language(text) == expected
