"""scrub_jd_pii / count_jd_pii (FR-009, research R4): email, SDT, dong lien he, URL ho so ca nhan.

PII cai vao test dung mien trong that (congty-gia.vn): pii_patterns coi .test / .example / example.com
khong phai PII, dung chung se qua test ma khong kiem gi.
"""
import unicodedata

import pytest

from pipeline.jd_pii import count_jd_pii, scrub_jd_pii


def test_email_and_phone_replaced_with_labels():
    text = "Gui CV ve tuyendung@congty-gia.vn hoac goi 0912 345 678 de hoi them"
    assert scrub_jd_pii(text) == "Gui CV ve [email] hoac goi [phone] de hoi them"


@pytest.mark.parametrize(
    "line",
    [
        "Liên hệ: Chị Lan 0912 345 678",
        "- Liên hệ: Anh Minh - 0912 345 678 - hr@congty-gia.vn",
        "Người liên hệ: Anh Nam",  # ten nguoi ngay sau tu khoa, khong can SDT
        "Contact: Ms. Hoa hoa.tuyendung@congty-gia.vn",
        "Hotline 0283-822-1234",
        "Mr. Quang - quang.hr@congty-gia.vn",
        "A. Hùng 0988 111 222",
        "C. Thảo thao@congty-gia.vn",
        "1. Liên hệ: Chị Lan 0912 345 678",  # dong danh so thu tu
        "2) Hotline: 0283-822-1234",
    ],
)
def test_contact_line_dropped_entirely(line):
    out = scrub_jd_pii(f"Yêu cầu: biết Node.js\n{line}\nQuyền lợi: bảo hiểm")
    assert out == "Yêu cầu: biết Node.js\nQuyền lợi: bảo hiểm"


def test_contact_line_matched_after_unicode_decomposition():
    line = unicodedata.normalize("NFD", "Liên hệ: Chị Lan 0912 345 678")
    assert scrub_jd_pii(f"Mô tả\n{line}\nHết") == "Mô tả\nHết"


@pytest.mark.parametrize(
    "line",
    [
        "Contact us to learn more",  # co tu khoa nhung khong kem SDT / email / ten nguoi
        "Hotline: 1900 1234",  # tong dai cong ty, khong phai SDT ca nhan
        "Anh em trong team rất thân thiện",  # "Anh" + chu thuong, khong kem SDT / email
        "A. Bachelor degree in Computer Science",  # danh so muc, khong kem SDT / email
        "Công ty TNHH Phần mềm Mây Xanh Giả - congty-gia.vn/careers",
    ],
)
def test_non_contact_lines_kept(line):
    assert scrub_jd_pii(line) == line
    assert count_jd_pii(line) == 0


def test_honorific_line_with_lowercase_word_only_scrubbed_not_dropped():
    out = scrub_jd_pii("Anh em thân thiện, gửi CV tới hr@congty-gia.vn")
    assert out == "Anh em thân thiện, gửi CV tới [email]"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.linkedin.com/in/nguyen-van-a",
        "linkedin.com/in/tran-thi-b-123",
        "https://facebook.com/chi.lan.123",
        "www.facebook.com/profile.php?id=100001",
        "fb.com/anh.minh",
        "https://zalo.me/0912345678",
        "https://t.me/anh_minh",
    ],
)
def test_personal_profile_urls_removed(url):
    out = scrub_jd_pii(f"Theo dõi tại {url}. Cảm ơn!")
    assert out == "Theo dõi tại [link]. Cảm ơn!"
    assert count_jd_pii(out) == 0


def test_company_page_on_linkedin_is_not_personal():
    text = "Xem thêm https://www.linkedin.com/company/may-xanh-gia"
    assert scrub_jd_pii(text) == text


def test_count_covers_all_three_kinds_and_is_zero_after_scrub():
    assert count_jd_pii("Gửi tuyendung@congty-gia.vn") == 1
    assert count_jd_pii("Xem https://linkedin.com/in/lan-nguyen") == 1
    assert count_jd_pii("Người liên hệ: Anh Nam") == 1
    text = (
        "Liên hệ: Chị Lan 0912 345 678\n"
        "Xem https://linkedin.com/in/lan-nguyen\n"
        "Email tuyendung@congty-gia.vn\n"
        "Mô tả công việc: viết API"
    )
    assert count_jd_pii(text) >= 3
    cleaned = scrub_jd_pii(text)
    assert count_jd_pii(cleaned) == 0
    assert cleaned == "Xem [link]\nEmail [email]\nMô tả công việc: viết API"


def test_scrub_is_idempotent_and_keeps_vietnamese():
    text = "Yêu cầu: thành thạo Node.js\nLiên hệ: Anh Minh 0912 345 678"
    once = scrub_jd_pii(text)
    assert once == "Yêu cầu: thành thạo Node.js"
    assert scrub_jd_pii(once) == once
