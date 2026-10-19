"""Kiem tra nhat quan tai lieu phan AIE (chay truoc moi PR co thay doi yeu cau/thiet ke).

Kiem: (1) link tuong doi, (2) ID FR/NFR khong trung, (3) moi FR/NFR duoc nhac den deu ton tai,
(4) moi BR trong BRD co dong truy vet o FR va NFR, (5) so luong trong muc luc khop,
(6) banner "BRD vX" o FR/NFR/L2 khop phien ban BRD, (7) bang tong ket trang thai FR khop so dem.

Chay: python apps/ai-service/scripts/check_docs.py   (thoat 1 neu co loi)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs" / "ai-service"
REQ = DOCS / "requirements"
BRD, FR, NFR = REQ / "01-brd.md", REQ / "02-functional-requirements.md", REQ / "03-non-functional-requirements.md"
L2 = DOCS / "11-architecture-l2-containers.md"
errors = []


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def rows(text: str, pattern: str):
    return re.findall(r"^\| \*{0,2}(" + pattern + r")\*{0,2}(?: \*\([^)]*\)\*)? \|", text, re.M)


def check_links():
    files = list(DOCS.rglob("*.md")) + list((ROOT / "plans").rglob("*.md"))
    for f in files:
        for m in re.finditer(r"\]\(([^)#\s]+)(#[^)]*)?\)", read(f)):
            t = m.group(1)
            if t.startswith(("http", "mailto:")):
                continue
            if not (f.parent / t).resolve().exists():
                errors.append(f"link hong: {f.relative_to(ROOT)} -> {t}")


def check_ids():
    fr_ids, nfr_ids = rows(read(FR), r"FR-AI-\d+"), rows(read(NFR), r"NFR-AI-[A-Z]+\d+")
    for kind, ids in (("FR", fr_ids), ("NFR", nfr_ids)):
        for i in sorted({x for x in ids if ids.count(x) > 1}):
            errors.append(f"{kind} trung ID: {i}")
    fr_set, nfr_set = set(fr_ids), set(nfr_ids)
    for f in list(DOCS.rglob("*.md")) + list((ROOT / "plans").rglob("*.md")):
        t = read(f)
        for x in set(re.findall(r"FR-AI-\d+", t)) - fr_set:
            errors.append(f"{f.relative_to(ROOT)}: nhac {x} khong ton tai")
        for x in set(re.findall(r"NFR-AI-[A-Z]+\d+", t)) - nfr_set:
            errors.append(f"{f.relative_to(ROOT)}: nhac {x} khong ton tai")
    return fr_ids, nfr_ids


def expand_br(cell: str):
    m = re.match(r"BR-(\d+)(?:\.\.(\d+))?", cell)
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    return {f"BR-{n:02d}" for n in range(a, b + 1)}


def check_traceability(fr_ids):
    brd = read(BRD)
    sec = brd[brd.index("## 6. Yêu cầu nghiệp vụ"): brd.index("## 7. Quy tắc nghiệp vụ")]
    brs = set(rows(sec, r"BR-\d+"))
    for br_row in re.findall(r"^\| \*{0,2}BR-\d+\*{0,2} \|.*\|$", sec, re.M):
        for n in re.findall(r"\b(\d{3})\b", br_row.split("|")[-2]):
            if f"FR-AI-{n}" not in fr_ids:
                errors.append(f"BRD: {br_row.split('|')[1].strip()} tro toi FR-AI-{n} khong ton tai")
    for name, path, marker in (("FR", FR, "Ma trận truy vết"), ("NFR", NFR, "Truy vết BR sang NFR")):
        t = read(path)
        sec2 = t[t.index(marker):]
        got = set()
        for c in re.findall(r"^\| (BR-[\d.]+) \|", sec2, re.M):
            got |= expand_br(c)
        for br in sorted(brs - got):
            errors.append(f"{name}: {br} thieu dong truy vet")
        for br in sorted(got - brs):
            errors.append(f"{name}: truy vet toi {br} khong co trong BRD")


def check_counts(fr_ids, nfr_ids):
    readme = read(DOCS / "README.md")
    for label, n in (("FR", len(fr_ids)), ("NFR", len(nfr_ids))):
        m = re.search(rf"{label} \((\d+) yêu cầu", readme)
        if not m:
            errors.append(f"README.md: thieu so luong {label}")
        elif int(m.group(1)) != n:
            errors.append(f"README.md: ghi {m.group(1)} {label} nhung co {n}")


def check_fr_summary():
    t = read(FR)
    counts = {"Mock": 0, "Một phần": 0, "Chưa": 0, "Ngoài": 0}
    for line in re.findall(r"^\| FR-AI-\d+ \|.*\|$", t, re.M):
        status = line.rsplit("|", 2)[-2].strip()
        for k in counts:
            if status.startswith(k):
                counts[k] += 1
    sec = t[t.index("## 14. Tổng kết trạng thái"):]
    for key, label in (("Mock", "Mock (đã có"), ("Một phần", "Một phần"), ("Chưa", "Chưa làm"), ("Ngoài", "Ngoài phạm vi")):
        m = re.search(r"^\| " + re.escape(label) + r"[^|]* \| (\d+) \|", sec, re.M)
        if not m or int(m.group(1)) != counts[key]:
            errors.append(f"FR bang tong ket: '{label}' ghi {m.group(1) if m else '?'} nhung dem duoc {counts[key]}")
    m = re.search(r"\| \*\*Tổng\*\* \| \*\*(\d+)\*\*", sec)
    if not m or int(m.group(1)) != sum(counts.values()):
        errors.append("FR bang tong ket: tong khong khop")


def check_versions():
    m = re.search(r"\| Phiên bản \| (\d+\.\d+)", read(BRD))
    ver = m.group(1)
    for f in (FR, NFR, L2):
        head = "\n".join(read(f).splitlines()[:16])
        for v in re.findall(r"BRD v(\d+\.\d+)", head):
            if v != ver:
                errors.append(f"{f.relative_to(ROOT)}: banner ghi BRD v{v} nhung BRD la v{ver}")


def main() -> int:
    check_links()
    fr_ids, nfr_ids = check_ids()
    check_traceability(fr_ids)
    check_counts(fr_ids, nfr_ids)
    check_fr_summary()
    check_versions()
    for e in errors:
        print("LOI:", e)
    print(f"{len(fr_ids)} FR, {len(nfr_ids)} NFR, {len(errors)} loi")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
