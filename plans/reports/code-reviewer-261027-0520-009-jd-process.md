# Code review: 009 US2 `jd-process` (T017–T028)

Branch `review/jd-process` (= origin/feat/data-pipeline/jd-process), diff vs `origin/feat/data-pipeline/jd-crawl`, 6 commits, 17 files, +1564/-12.
Read-only review. Real-data run used the worktree code, the main repo's raw files, and scratchpad outputs. Nothing was written to either repo's `data/processed`.

## Scope
- Files: `data/seeds/skill_dictionary.yaml`, `pipeline/{skill_dictionary,jd_normalizer,jd_salary,jd_sections,jd_record_builder,jd_record_dedup,jd_process_command,jd_process_report}.py`, `__main__.py`, 5 test files + conftest, tasks.md
- Every code file is under 200 lines (largest: jd_sections.py at 126). No new deps (pyyaml is already in base requirements).
- Tests: the US2 subset passes (91). No network use. FR-007 holds: 0 raw company names, titles or description lines (>40 chars) appear in tests.

## Overall
- Clean, modular code that follows the spec closely. The process is deterministic: a rerun gives byte-identical jsonl files, exit 0, `pii_remaining` 0.
- Exit codes, report keys and determinism all match the contract.
- The problems are data quality on real records: skill false positives, IT-filter precision and recall, level from itviec months, cities from careerviet districts, and section headings for careerlink/careerviet.

## Critical (data correctness)
1. **The `học máy` alias matches "Khoa học máy tính" (the Computer Science degree).**
   - Where: `skill_dictionary.yaml:109`; the regex is in `skill_dictionary.py:79-81`.
   - Real data: 57 of the 103 output JDs tagged `machine-learning` get the tag only from this phrase.
   - 8 JDs flip their group to `ai_data`, and 3 JDs pass the IT filter only because of it.
   - Impact: these tags would be seeded into `job_skills` (US4).
   - Fix: drop the bare `học máy` alias (keep `machine learning`/`ml`), or add a negative lookbehind for `khoa\s+`.

## Major
2. **itviec `experience_raw = "10 months"` turns into Intern.**
   - Where: `jd_normalizer.py:183-200`.
   - 67 raw records have this value. For 42 output JDs with no level keyword in the title, the level comes out Intern, although the titles are engineer and senior-specialist roles.
   - These 42 are 42 of the 45 Intern JDs in the distribution.
   - This follows the spec literally (< 1 year → Intern), but 10 months looks like an itviec sentinel value.
   - Options: treat < 12 months as null unless the text has an intern/thực tập cue, or map the value per source.
3. **IT filter precision and recall** (`jd_record_builder.py:30-35, 56-58`).
   - False rejects:
     - Bare "IT" is not a keyword: "Nhân viên IT", "IT Staff", "IT Business Analyst".
     - The Vietnamese word for engineer is not a keyword: "Kỹ sư hệ thống", "Kỹ sư IT network".
     - Security / an toàn thông tin titles are rejected.
     - Canonical `skills_raw` is ignored: an itviec posting tagged Java was rejected.
     - 19 itviec records are rejected as not_it, on a site that only lists IT jobs.
   - False keeps from the extra keywords (`phần mềm`, `cntt`, `ai`, `engineer`):
     - software sales/consultant roles (≥ 8)
     - a lecturer
     - transmission / field-service engineers
     - a data-labeling admin role
   - 80 JDs are kept on the title regex alone; 41 of the kept JDs have 0 skills and `group` null.
   - This pulls `with_skill_ratio` to 0.8801, below the SC-001 target of 0.9.
4. **Section headings miss real templates** (`jd_sections.py:115-120`).
   - careerlink "* Kinh nghiệm / Kỹ năng chi tiết:" (31 of 37 raw) is not recognized.
   - careerviet "(II.) Tiêu chuẩn tuyển dụng" (~23 raw), "Yêu cầu bắt buộc" and "Knowledge requirements" are not recognized.
   - Result: 19/22 careerlink and 96/136 careerviet outputs have only summary + description, so `job_postings.requirements` would be empty.
   - Part of this is on the crawl side: 109 careerviet raw records contain no requirements block at all.
5. **City is null for 45% of careerviet** (`jd_normalizer.py:154-170, 216-222`).
   - careerviet `location_raw` holds only a district ("Quận Cầu Giấy", "Quận 3", "Thành phố Thủ Đức"), giving 61/136 careerviet and 66/342 total with no city.
   - These JDs are dropped from `cells`, so US5 would over-generate.
   - The description does contain an "Địa điểm: <city>" line, which a district→city or description fallback could use. The alternative is a crawler fix.
6. **Aliases merge distinct products into one slug** (`skill_dictionary.yaml:72, 89, 96, 104, 106, 113, 123` and others).
   - Examples:
     - vite → webpack
     - playwright → cypress
     - tableau/looker → power-bi
     - grafana → prometheus
     - jest/junit/pytest → unit-testing
     - github/gitlab/bitbucket → git
     - gitlab ci → github-actions
     - rag/genai → llm
     - keras → tensorflow
     - numpy → pandas
     - bigquery/snowflake/redshift → data-warehouse
     - mariadb → mysql
     - jpa → hibernate
     - sre → devops
   - Real hits include grafana 25, gitlab ci 23, rag 31, genai 21 and tableau 15.
   - Impact: wrong `job_skills` in US4, and these tools never show up in `unknown_skills`, which the T029 loop relies on.

## Minor
7. **Salary in "k" units** (`jd_salary.py:19-23, 60-62`).
   - "1.5k - 2.5k" → (1500, 2500, VND). "1.5k - 2k USD" → VND, because the currency after the second unit is not captured and `units != ["k"]` is a list compare.
   - There is no sanity guard for VND values under 1M.
   - 0 real hits. The real data is fine: no unparsed text containing digits, no VND under 1M, no USD over 20k.
8. **`TAG_ONLY_TERMS`** (`skill_dictionary.py:22`) is a deviation from T018 that is not documented in tasks.md.
   - C, R, Go, Swift, Spring, Express and REST are never matched in free text. That costs recall on careerlink, which has no `skills_raw`.
   - It also makes the T019 test "c++ không khớp c" (`test_skill_dictionary.py:70`) unable to fail on the lookahead, since `c` is excluded before the lookahead matters.
9. **Other text false positives / misses.**
   - False positives: "TS" (Vietnamese abbreviation for PhD) → typescript; "worker node" → nodejs (2 real hits).
   - Misses: "Java8", "c++11", "Angular2+", "VB.NET".
10. **Experience parsing** (`jd_normalizer.py:186-190`).
    - Months are checked first, so "1 year 6 months" → 0.5 → Intern.
    - "Dưới 1 năm" → Junior.
    - 0 real hits; real values are all "N months".
11. **Level precedence: the earliest keyword wins.** "Senior Manager" → Senior; "Lead Generation Specialist" → Lead. The spec does not say which should win.
12. **work_type is effectively constant: 340 of 342 JDs are onsite.**
    - Only employment type, title and location are scanned (`jd_record_builder.py:103`).
    - Scanning descriptions would be noisy: real text includes "hybrid cloud", "secure remote access" and "No hybrid, no remote".
    - The itviec work model is not in the raw data, so this is a crawl gap.
13. **Long-line splitting:** `split_text` inserts "\n" between pieces of a line longer than the limit (`jd_sections.py:167-196`). No characters are lost and the docstring is accurate.
14. **tasks.md T024 annotation adds a new rule** (description < 200 chars → `missing_field`). It needs owner sign-off. Current effect is 0: all 15 short topdev records are rejected as not_it first.
15. **Cross-JD chunk dedup** (`jd_process_command.py:53-60`) drops 67 of 1089 chunks; some JDs lose their boilerplate benefits chunk. This matches the data-model key (`content_hash`), but should be flagged for US3.
16. **Unconfirmed vocabulary and grouping.**
    - Category values (AI/ML, Cloud, Testing, Mobile, Fullstack, Data) are not confirmed with FSD; `knowledge_chunks` uses "AI".
    - Testing → devops and Scala → ai_data are grouping decisions that are not documented.

## Task completeness
- T017–T028 are all implemented as written: fields and names per data-model, chunk contract fields, exit codes, report keys plus `cells`, determinism.
- T029 is still open, as expected: `with_skill_ratio` is 0.8801.

## process-jd on real raw (aggregates)

| Metric | Value |
|---|---|
| records_in | 515 crawl (careerlink 37, careerviet 173, itviec 152, topdev 153), 0 synthetic |
| rejected | not_it 172 (topdev 101, careerviet 37, itviec 19, careerlink 15), missing_field 0, duplicate 1 |
| jd_out | 342 |
| dedup_ratio | 0.0029 |
| chunks_out | 1022 |
| with_skill_ratio | 0.8801 (careerlink 0.77, careerviet 0.91, itviec 0.96, topdev 0.63) |
| pii_remaining | 0 |
| cells | 54 |
| near-duplicate groups | 5 |
| group | backend 148, devops 85, ai_data 55, unknown 41, frontend 9, mobile_fullstack 4 |
| level | Mid 83, Senior 77, Junior 70, Intern 45, Manager 29, unknown 29, Lead 9 |
| city | Hà Nội 160, Hồ Chí Minh 94, unknown 66, Đà Nẵng 11, other 11 |
| work_type | onsite 340, hybrid 1, remote 1 |

## Recommended actions (priority)
1. Remove or guard the `học máy` alias.
2. Decide how to handle itviec "10 months".
3. Widen the IT keywords: `it`, `kỹ sư`, `security`, `an toàn thông tin`, `network`. Consider counting canonical `skills_raw`, and drop or narrow `phần mềm`/`cntt` for sales roles.
4. Add the careerlink and careerviet requirement headings.
5. Add a district→city or "Địa điểm:" fallback, or fix the crawler.
6. Split merged aliases into their own slugs.
7. Fix the "k" currency handling and add a VND under 1M guard.

## Unresolved questions
- What does itviec "10 months" mean? Should level fall back to null for it?
- Should the IT filter count canonical `skills_raw`? The spec only names title and description.
- Are BA, PO, PM and Security roles IT for this platform's 5 groups?
- Should careerviet city and requirements be fixed in the crawler (jd-crawl) or in the normalizer?
- Synthetic JDs have group/level/city re-inferred (FR-027) rather than taken from `cell`. A mismatch means synth-jd keeps regenerating for that cell. Who checks this, the US5 post-check?
- Does FSD confirm the category vocabulary? Is the `MIN_DESCRIPTION_CHARS` rule signed off?
