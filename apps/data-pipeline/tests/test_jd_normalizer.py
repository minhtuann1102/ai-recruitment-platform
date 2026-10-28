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
        ("Backend Developer", "6 months", "Junior"),  # duoi 12 thang = fresher -> Junior (Clarifications 2026-10-28)
        ("Backend Developer", "1 year 6 months", "Junior"),  # 1.5 nam, khong phai 0.5
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
    "experience, description, source, expected",
    [
        # itviec: experience_raw la nhom tu gan ("10 months") -> bo qua, lay so nam trong mo ta
        ("10 months", "Yêu cầu:\n- Có 3 năm kinh nghiệm Java", "itviec", "Mid"),
        ("10 months", "Requirements:\n- At least 5+ years of hands-on experience", "itviec", "Senior"),
        ("10 months", "Requirements:\n- Good English", "itviec", None),
        ("10 months", "", "topdev", "Junior"),  # nguon khac van tin experience_raw
        (None, "Kinh nghiệm: tối thiểu 2 năm", "careerlink", "Junior"),
        (None, "Với hơn 20 năm kinh nghiệm trong ngành ngân hàng", "careerviet", None),  # so nam cua cong ty
    ],
)
def test_level_from_description_years(experience, description, source, expected):
    assert normalize_level("Backend Developer", experience, description, source) == expected


def test_title_level_beats_description_years():
    assert normalize_level("Senior Backend Developer", "10 months", "1 năm kinh nghiệm", "itviec") == "Senior"


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
    "locations, description, expected",
    [
        (["Quận Cầu Giấy"], "", "Hà Nội"),  # careerviet chi ghi quan
        (["Quận 3"], "", "Hồ Chí Minh"),
        (["Quận 10"], "", "Hồ Chí Minh"),  # "quan 1" khong khop nham "quan 10"
        (["Thành Phố Thủ Đức"], "", "Hồ Chí Minh"),
        (["Quận Hải Châu"], "", "Đà Nẵng"),
        (["Trụ sở chính"], "Mô tả công việc\nĐịa điểm: Hồ Chí Minh", "Hồ Chí Minh"),
        (["Quận Cầu Giấy"], "Địa điểm: Hồ Chí Minh", "Hồ Chí Minh"),  # ten thanh pho thang ten quan
        ([], "Địa điểm làm việc: 25 Trần Hưng Đạo, quận Hoàn Kiếm", "Hà Nội"),
        ([], "Công ty có văn phòng tại Hà Nội", None),  # chi doc dong dia diem, khong doc ca mo ta
    ],
)
def test_city_fallbacks(locations, description, expected):
    assert normalize_city(locations, description) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("9.000.000 VND - 20.000.000 VND", (9_000_000, 20_000_000, "VND")),
        ("15 - 25 triệu", (15_000_000, 25_000_000, "VND")),
        ("$1,000 - 2,000", (1000, 2000, "USD")),
        ("Up to 2000$", (None, 2000, "USD")),
        ("Up to 60M", (None, 60_000_000, "VND")),
        ("Từ 15 triệu", (15_000_000, None, "VND")),
        ("1.5k - 2k USD", (1500, 2000, "USD")),  # tien te sau don vi k
        ("1.5k - 2.5k", (1500, 2500, "USD")),  # chi co k -> doan theo do lon, khong mac dinh VND
        ("500k VND", (None, None, None)),  # VND duoi 1 trieu: doc sai, bo
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
