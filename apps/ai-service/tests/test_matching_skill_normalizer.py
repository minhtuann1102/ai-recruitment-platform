"""017 US2 T012: chuan hoa ky nang CV theo danh muc 009 (ban sao skill_dictionary.yaml)."""
import unicodedata

from app.matching.skill_normalizer import display_name, normalize


def test_spring_boot_variants_collapse_to_one_slug():
    slugs, unknown = normalize(["Spring Boot", "springboot", "spring-boot", "SPRING   BOOT"])
    assert slugs == ["spring-boot"] and unknown == 0


def test_aliases_from_yaml_resolve():
    slugs, _ = normalize(["Postgres", "k8s", "ReactJS", "Node.js"])
    assert slugs == ["kubernetes", "nodejs", "postgresql", "react"]  # sap theo slug


def test_unknown_names_are_counted_distinct_not_returned():
    slugs, unknown = normalize(["Java", "Cobol-ish thing", "cobol-ish   THING", "Quantum Basket Weaving", "  "])
    assert slugs == ["java"] and unknown == 2  # rong khong tinh; trung sau chuan hoa tinh mot


def test_key_is_nfc_lowercase_whitespace_collapsed():
    decomposed = unicodedata.normalize("NFD", "Cơ sở dữ liệu")  # alias tieng Viet cua database
    composed = unicodedata.normalize("NFC", "Cơ sở dữ liệu")
    assert decomposed != composed
    assert normalize([decomposed]) == (["database"], 0)
    assert normalize(["  Cơ   Sở  DỮ LIỆU "]) == (["database"], 0)


def test_empty_input():
    assert normalize([]) == ([], 0)


def test_display_name_and_unknown_slug_falls_back_to_slug():
    assert display_name("spring-boot") == "Spring Boot" and display_name("postgresql") == "PostgreSQL"
    assert display_name("not-a-skill") == "not-a-skill"
