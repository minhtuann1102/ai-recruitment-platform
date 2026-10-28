"""Danh muc ky nang JD (spec 009 T019, research R5): luat YAML, bi danh, khop trong van ban."""
import pytest

from pipeline.settings import SKILL_DICTIONARY_PATH
from pipeline.skill_dictionary import (
    GROUPS,
    Skill,
    SkillDictionary,
    SkillDictionaryError,
    load_skill_dictionary,
)


@pytest.fixture(scope="module")
def dictionary():
    return load_skill_dictionary()


def _skill(slug, aliases=(), group="backend", name=None):
    return Skill(slug, name or slug.title(), "Backend", group, tuple(aliases))


def test_real_yaml_passes_rules(dictionary):
    assert SKILL_DICTIONARY_PATH.name == "skill_dictionary.yaml"
    assert len(dictionary.skills) >= 100
    assert all(skill.slug == skill.slug.lower() for skill in dictionary.skills.values())
    assert {skill.group for skill in dictionary.skills.values()} == set(GROUPS)


def test_duplicate_slug_is_error():
    with pytest.raises(SkillDictionaryError, match="slug trung"):
        SkillDictionary([_skill("java"), _skill("java", name="Java 2")])


def test_alias_shared_by_two_skills_is_error_case_insensitive():
    with pytest.raises(SkillDictionaryError, match="trung giua"):
        SkillDictionary([_skill("react", ["ReactJS"]), _skill("react-native", ["reactjs"])])


def test_uppercase_slug_is_error(tmp_path):
    path = tmp_path / "skills.yaml"
    path.write_text("- {slug: Java, name: Java, category: Backend, group: backend, aliases: []}\n", encoding="utf-8")
    with pytest.raises(SkillDictionaryError, match="chu thuong"):
        load_skill_dictionary(path)


def test_unknown_group_is_error(tmp_path):
    path = tmp_path / "skills.yaml"
    path.write_text("- {slug: java, name: Java, category: Backend, group: sales, aliases: []}\n", encoding="utf-8")
    with pytest.raises(SkillDictionaryError, match="group"):
        load_skill_dictionary(path)


def test_missing_file_is_error(tmp_path):
    with pytest.raises(SkillDictionaryError, match="khong doc duoc"):
        load_skill_dictionary(tmp_path / "missing.yaml")


@pytest.mark.parametrize("name", ["ReactJS", "React.js", "react", "  REACT  "])
def test_react_spellings_map_to_one_slug(dictionary, name):
    assert dictionary.canonical(name) == "react"


def test_resolve_reports_unknown_skills_without_losing_them(dictionary):
    known, unknown = dictionary.resolve(["NodeJS", "Postgres", "Haskell Pro", "haskell pro", "Odoo"])
    assert known == ["nodejs", "postgresql"]
    assert unknown == ["Haskell Pro", "Odoo"]


def test_cpp_does_not_match_c(dictionary):
    assert dictionary.find_in_text("Thành thạo C++ và STL") == ["cpp"]
    assert dictionary.find_in_text("Kinh nghiệm C# / .NET Core") == ["csharp", "dotnet"]


def test_alias_followed_by_plus_or_hash_does_not_match():
    # "c" la TAG_ONLY nen test tren khong cham toi lookahead; kiem lookahead bang bi danh thuong
    small = SkillDictionary([Skill("foo", "Foo", "Backend", "backend", ())])
    assert small.find_in_text("Thành thạo Foo") == ["foo"]
    assert small.find_in_text("Thành thạo Foo++ và Foo#") == []


def test_computer_science_degree_is_not_machine_learning(dictionary):
    assert dictionary.find_in_text("Tốt nghiệp Khoa học máy tính, Công nghệ thông tin") == []
    assert dictionary.find_in_text("Có kiến thức về học máy và học sâu") == ["deep-learning", "machine-learning"]


def test_ts_abbreviation_is_tag_only(dictionary):
    assert dictionary.find_in_text("Ưu tiên ứng viên có học vị TS. hoặc ThS.") == []
    assert dictionary.canonical("TS") == "typescript"


def test_distinct_tools_keep_their_own_slug(dictionary):
    text = "Vite, Webpack, Grafana, Prometheus, GitLab CI, Jest, Tableau, Power BI, RAG, NumPy, MariaDB"
    assert dictionary.find_in_text(text) == [
        "gitlab-ci", "grafana", "jest", "mariadb", "numpy", "power-bi", "prometheus", "rag", "tableau", "vite", "webpack",
    ]


def test_find_in_text_respects_word_boundaries(dictionary):
    text = "Biết JavaScript, Node.js, React Native; ưu tiên ASP.NET và PostgreSQL."
    assert dictionary.find_in_text(text) == ["dotnet", "javascript", "nodejs", "postgresql", "react-native"]
    assert "java" not in dictionary.find_in_text("JavaScript developer")


def test_ambiguous_words_only_count_as_tags(dictionary):
    # "go", "rest", "spring" la tu thuong trong mo ta; chi nhan khi la the skills_raw
    assert dictionary.find_in_text("Ready to go live; the rest of the team; spring release") == []
    assert dictionary.canonical("Go") == "golang"
    assert dictionary.find_in_text("Kinh nghiệm Golang và Spring Boot") == ["golang", "spring-boot"]


def test_group_of_most_common_with_tie_order(dictionary):
    assert dictionary.group_of(["react", "vuejs", "nodejs"]) == "frontend"
    assert dictionary.group_of(["react", "nodejs"]) == "backend"  # hoa -> backend dung truoc
    assert dictionary.group_of(["postgresql", "system-design"]) == "backend"  # Database / System Design -> backend
    assert dictionary.group_of([]) is None
