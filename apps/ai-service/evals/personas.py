"""Persona ung vien gia lap (design 09 muc 10.2, tang 3): 3 chat luong x 4 level x 2 track + 4 adversarial.

Kien thuc cua persona chia tu topic trong catalog cua track + level (sinh bang code, on dinh theo id), nen biet
truoc lo hong that cua ung vien de kiem bao cao. In card: python -m evals.personas
"""
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.catalog.loader import load_catalog

TRACKS = ("java_backend", "nodejs_backend")
LEVELS = ("fresher", "junior", "middle", "senior")
QUALITIES = ("strong", "average", "weak")
# ti le topic (biet tot, biet mot phan); phan con lai la khong biet
_SPLIT = {"strong": (0.75, 0.15), "average": (0.35, 0.35), "weak": (0.1, 0.2)}
SKEWED_FIXTURE = Path(__file__).parent / "fixtures" / "skewed_jd_profiles.json"
_STYLE = {"strong": "Trả lời mạch lạc, có ví dụ thực tế và trade-off.",
          "average": "Trả lời ngắn, đúng ý chính nhưng ít giải thích, đôi khi đoán ('em nghĩ là...').",
          "weak": "Trả lời mơ hồ, hay nói không chắc, đôi khi hiểu sai khái niệm."}


@dataclass
class Persona:
    id: str
    track: str
    level: str
    quality: str
    knows_well: List[str]
    knows_partially: List[str]
    does_not_know: List[str]
    style: str
    behaviors: List[str] = field(default_factory=list)  # rambling | injection_attempt | one_word_answers | end_early | english_answers
    base_id: str = ""  # persona goc cua ban adversarial (de so sanh, vd injection khong lam tang diem)
    jd_profile: Optional[Dict] = None  # co thi run_session gui o start + finalize (khoi `requirements`)
    cv_profile: Optional[Dict] = None  # co thi run_session gui o start

    def knowledge(self, catalog_ref: str) -> str:
        """well | partial | none cho topic catalog; topic khong thuoc catalog (intro, scenario) tinh theo chat luong."""
        if catalog_ref in self.knows_well:
            return "well"
        if catalog_ref in self.knows_partially:
            return "partial"
        if catalog_ref in self.does_not_know:
            return "none"
        return {"strong": "well", "average": "partial", "weak": "none"}.get(self.quality, "partial")


def build_persona(track: str, level: str, quality: str) -> Persona:
    pid = f"{level}-{track.split('_')[0]}-{quality}"
    topics = [t.id for t in load_catalog(track).topics_for(level)]
    random.Random(pid).shuffle(topics)  # on dinh theo id
    well_r, part_r = _SPLIT[quality]
    n_well, n_part = round(len(topics) * well_r), round(len(topics) * part_r)
    return Persona(pid, track, level, quality, topics[:n_well], topics[n_well:n_well + n_part],
                   topics[n_well + n_part:], _STYLE[quality])


def matrix() -> List[Persona]:
    return [build_persona(t, lv, q) for t in TRACKS for lv in LEVELS for q in QUALITIES]


def adversarial() -> List[Persona]:
    out = []
    for base, behavior in (("junior-java-average", "rambling"), ("junior-java-average", "injection_attempt"),
                           ("middle-nodejs-average", "one_word_answers"), ("junior-nodejs-strong", "end_early"),
                           ("junior-java-strong", "english_answers")):
        level, short, quality = base.split("-")
        p = build_persona(f"{short}_backend", level, quality)
        out.append(Persona(f"{base}+{behavior}", p.track, p.level, p.quality, p.knows_well, p.knows_partially,
                           p.does_not_know, p.style, [behavior], base_id=base))
    return out


def build_skewed(track: str, level: str, strong_category: str = "Backend", weak_category: str = "Database") -> Persona:
    """Manh mot category, yeu category khac (quality = skewed, ngoai ma tran strong/average/weak). Kem JD + CV gia:
    yeu cau `must` tro topic ca hai nhom, de do do phu JD va luc policy phai chon giua topic manh va yeu."""
    pid = f"{level}-{track.split('_')[0]}-skewed"
    topics = load_catalog(track).topics_for(level)
    well = [t.id for t in topics if t.category == strong_category]
    none = [t.id for t in topics if t.category == weak_category]
    rest = [t.id for t in topics if t.id not in well and t.id not in none]
    fixture = json.loads(SKEWED_FIXTURE.read_text("utf-8"))[track]
    style = f"Rất chắc phần {strong_category}, mơ hồ và hay nói không biết phần {weak_category}."
    return Persona(pid, track, level, "skewed", well, rest, none, style,
                   jd_profile=fixture["jd_profile"], cv_profile=fixture["cv_profile"])


def skewed_personas() -> Dict[str, Persona]:
    """Chay rieng bang `simulate --matrix skewed`; khong nam trong all_personas() de ma tran 29 persona khong doi."""
    return {p.id: p for p in (build_skewed(t, "junior") for t in TRACKS)}


def all_personas() -> Dict[str, Persona]:
    return {p.id: p for p in matrix() + adversarial()}


if __name__ == "__main__":
    print(json.dumps([asdict(p) for p in all_personas().values()], ensure_ascii=False, indent=1))
