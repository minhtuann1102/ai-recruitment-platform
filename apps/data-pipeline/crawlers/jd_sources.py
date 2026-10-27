"""Cau hinh 4 nguon crawl JD (spec 009 R1, Clarifications NC-3): them nguon = them mot muc vao SOURCES.

Moi nguon: trang danh sach IT phan trang -> link chi tiet -> trang chi tiet co JSON-LD JobPosting.
detail_link_re va job_id_re khop tren PATH cua URL (bo query / #fragment); nhom 'id' = source_job_id.

TRANG THAI KIEM CHUNG (T016, may DE 2026-10-27, `crawl-jd --max-pages 2 --max-jobs 3`):
- itviec, topdev, careerviet: cau hinh dung, moi nguon 3/3 record co JobPosting. topdev: danh sach co phan trang
  that nhung lan ca tin khong phai IT (de buoc xu ly US2 loai, JD can >= 1 ky nang); selector mo ta khop o trang
  IT, trang khong khop thi lay mo ta ngan cua JSON-LD.
- careerlink: ban doan dau (/viec-lam-tai/...) tra 404; da sua theo trang that: danh sach /viec-lam/cntt-phan-mem/19,
  chi tiet /tim-viec-lam/<slug>/<id> (link danh muc /viec-lam/... khong duoc tinh la tin).
Nguon doi giao dien thi nguon bao `empty` (thoat 1), khong lang le thanh cong. Sua o day, khong sua code crawl.
"""
import re
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Pattern
from urllib.parse import urlsplit


@dataclass(frozen=True)
class JdSource:
    name: str
    base_url: str
    listing_url: Callable[[int], str]  # so trang (tu 1) -> URL trang danh sach
    detail_link_re: Pattern[str]  # path cua link chi tiet trong trang danh sach
    job_id_re: Pattern[str]  # path cua URL chi tiet -> nhom 'id'
    # CSS selector than mo ta trong HTML khi JSON-LD chi co doan rut gon (topdev); None = chi dung JSON-LD
    description_selector: Optional[str] = None

    def job_id(self, url: str) -> Optional[str]:
        match = self.job_id_re.search(urlsplit(url).path)
        return match.group("id") if match else None

    def is_own_host(self, url: str) -> bool:
        return urlsplit(url).netloc == urlsplit(self.base_url).netloc


_ITVIEC_JOB = re.compile(r"^/it-jobs/[^/?#]+-(?P<id>\d+)$")
_TOPDEV_JOB = re.compile(r"^/detail-jobs/[^/?#]+-(?P<id>\d+)$")
_CAREERVIET_JOB = re.compile(r"^/vi/tim-viec-lam/[^/?#]+\.(?P<id>[0-9A-Fa-f]{6,})\.html$")
_CAREERLINK_JOB = re.compile(r"^/tim-viec-lam/[^/?#]+/(?P<id>\d+)$")


def _careerviet_listing(page: int) -> str:
    suffix = "" if page <= 1 else f"-trang-{page}"
    return f"https://careerviet.vn/viec-lam/cntt-phan-mem-c1{suffix}-vi.html"


SOURCES: Dict[str, JdSource] = {
    source.name: source
    for source in (
        JdSource(
            name="itviec",
            base_url="https://itviec.com",
            listing_url=lambda page: f"https://itviec.com/it-jobs?page={page}",
            detail_link_re=_ITVIEC_JOB,
            job_id_re=_ITVIEC_JOB,
        ),
        JdSource(
            name="topdev",
            base_url="https://topdev.vn",
            listing_url=lambda page: f"https://topdev.vn/jobs/search?page={page}",
            detail_link_re=_TOPDEV_JOB,
            job_id_re=_TOPDEV_JOB,
            description_selector="#job-description, .job-description",
        ),
        JdSource(
            name="careerviet",
            base_url="https://careerviet.vn",
            listing_url=_careerviet_listing,
            detail_link_re=_CAREERVIET_JOB,  # id hex, vd 35C8B493
            job_id_re=_CAREERVIET_JOB,
        ),
        JdSource(
            name="careerlink",
            base_url="https://www.careerlink.vn",
            listing_url=lambda page: f"https://www.careerlink.vn/viec-lam/cntt-phan-mem/19?page={page}",
            detail_link_re=_CAREERLINK_JOB,
            job_id_re=_CAREERLINK_JOB,
        ),
    )
}
