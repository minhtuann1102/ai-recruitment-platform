"""Cau hinh 4 nguon crawl JD (spec 009 R1, Clarifications NC-3): them nguon = them mot muc vao SOURCES.

Moi nguon: trang danh sach IT phan trang -> link chi tiet -> trang chi tiet co JSON-LD JobPosting.
detail_link_re va job_id_re khop tren PATH cua URL (bo query / #fragment); nhom 'id' = source_job_id.

TRANG THAI KIEM CHUNG (T008 viet offline, khong gui request toi nguon):
- itviec: danh sach /it-jobs?page=N va chi tiet /it-jobs/<slug>-<id> theo spec ("Kiem tra nguon crawl");
  kieu id (so o cuoi slug) chua do tren trang that.
- topdev, careerviet, careerlink: URL danh sach, tham so trang, regex link / id va selector la DU DOAN,
  CHUA kiem bang request that. careerviet: dang id hex (vd 35C1A2B3) theo vi du trong contracts/jd-record-formats.md.
  Cach kiem: `crawl-jd --source <ten> --max-pages 2 --max-jobs 3` tren may DE (quickstart §1). Sai cau hinh thi
  nguon bao `empty` (thoat 1), khong lang le thanh cong. Sua o day, khong sua code crawl.
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
_CAREERLINK_JOB = re.compile(r"^/viec-lam/[^/?#]+/(?P<id>\d+)$")


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
            listing_url=lambda page: f"https://topdev.vn/jobs/search?page={page}",  # DU DOAN
            detail_link_re=_TOPDEV_JOB,  # DU DOAN
            job_id_re=_TOPDEV_JOB,
            description_selector="#job-description, .job-description",  # DU DOAN
        ),
        JdSource(
            name="careerviet",
            base_url="https://careerviet.vn",
            listing_url=_careerviet_listing,  # DU DOAN
            detail_link_re=_CAREERVIET_JOB,  # DU DOAN (id hex theo contract)
            job_id_re=_CAREERVIET_JOB,
        ),
        JdSource(
            name="careerlink",
            base_url="https://www.careerlink.vn",
            listing_url=lambda page: f"https://www.careerlink.vn/viec-lam-tai/cntt-phan-mem/19?page={page}",  # DU DOAN
            detail_link_re=_CAREERLINK_JOB,  # DU DOAN
            job_id_re=_CAREERLINK_JOB,
        ),
    )
}
