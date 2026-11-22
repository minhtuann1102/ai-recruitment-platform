"""017 US2 T021: van ban embed cua CV (research R4) va tap ky nang CV (FR-009)."""
from app.matching.cv_text import MAX_EMBED_CHARS, build_cv_text, cv_skill_names, cv_skills
from app.models_cv import CvEducation, CvExperience, CvProfile, CvProject, CvSkill


def skill(name):
    return CvSkill(name=name, category="framework", evidence="listed")


def profile(**kw):
    base = dict(
        headline="Backend Developer 3 nam Java",
        skills=[skill("Spring Boot"), skill("PostgreSQL")],
        experiences=[
            CvExperience(role="Backend Developer", summary="Xay dung REST API cho he thong thanh toan",
                         tech=["Java", "Kafka"]),
            CvExperience(role="Intern", summary="", tech=["Java"]),
        ],
        projects=[
            CvProject(id="p1", name="Shop API", role="Lead", summary="Dat hang va thanh toan", tech=["Redis"],
                      highlights=["Giam latency 40%"]),
            CvProject(id="p2", name="Blog", role="", summary="", tech=[]),
        ],
        education=[CvEducation(degree="Cu nhan CNTT", year=2020)],
    )
    base.update(kw)
    return CvProfile(**base)


def test_text_has_headline_roles_and_projects_in_order():
    text = build_cv_text(profile())
    assert text.splitlines() == [
        "Backend Developer 3 nam Java",
        "Backend Developer — Xay dung REST API cho he thong thanh toan",
        "Intern",  # summary rong: khong co dau gach thua
        "Shop API — Lead — Dat hang va thanh toan",
        "Blog",
    ]


def test_text_has_no_skill_list_tech_highlights_or_education():
    text = build_cv_text(profile())
    for banned in ("Spring Boot", "PostgreSQL", "Kafka", "Redis", "Giam latency", "Cu nhan", "Kỹ năng", "skills"):
        assert banned not in text


def test_text_is_capped_and_deterministic():
    long = profile(experiences=[CvExperience(role="Dev", summary="x" * 5000)])
    text = build_cv_text(long)
    assert len(text) <= MAX_EMBED_CHARS == 1200
    assert text == build_cv_text(long)


def test_text_of_empty_ish_profile():
    assert build_cv_text(profile(headline="Dev", skills=[], experiences=[], projects=[], education=[])) == "Dev"


def test_skill_names_union_in_order_without_duplicates():
    assert cv_skill_names(profile()) == ["Spring Boot", "PostgreSQL", "Java", "Kafka", "Redis"]


def test_cv_skills_normalizes_to_slugs_and_counts_unknown():
    cv = profile(skills=[skill("springboot"), skill("Spring-Boot"), skill("Quantum Basket")],
                 experiences=[CvExperience(role="Dev", tech=["JAVA", "k8s"])], projects=[])
    assert cv_skills(cv) == (["java", "kubernetes", "spring-boot"], 1)


def test_cv_without_skills_gives_empty_set():
    assert cv_skills(profile(skills=[], experiences=[], projects=[])) == ([], 0)
