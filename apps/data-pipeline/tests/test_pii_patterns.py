import pytest

from pipeline.pii_patterns import find_pii, scrub_pii


@pytest.mark.parametrize(
    "text",
    [
        "Liên hệ nguyen.van.a@gmail.com để biết thêm",
        "Gọi 0912 345 678 nhé",
        "SĐT: +84 912.345.678",
        "Hotline 0283-822-1234",
        "Call +1 (415) 555-0100",
    ],
)
def test_detects_personal_contacts(text):
    assert find_pii(text)


@pytest.mark.parametrize(
    "text",
    [
        "Gửi tới user@example.com hoặc admin@mail.example.org",
        "git clone git@github.com:org/repo.git",
        "Cài lodash@4.17.21 và @nestjs/core",
        "Server lắng nghe 0.0.0.0:8080, phiên bản 1.2.3, năm 2026",
        "Timestamp 1697040000 và port 5432",
    ],
)
def test_ignores_examples_versions_and_numbers(text):
    assert find_pii(text) == []


def test_scrub_replaces_with_labels():
    assert scrub_pii("Mail a.b@corp.vn, gọi 0912345678") == "Mail [email], gọi [phone]"
