# Prompt cho các phiên Claude Code cloud (credit hết hạn 04/11/2026)

Mỗi phiên: mở claude.ai/code → chọn repo → chọn môi trường **có quyền truy cập Internet đầy đủ** → chọn model
(gói 1 và gói 4: **Sonnet**; gói 2 và gói 3: **Opus**) → dán prompt. Prompt giống nhau cho mọi model; model chỉ chọn
được ở ô chọn model của phiên. Mốc giá: java-3 trên Opus 5.5 tốn 3$ / 16 cặp; java-4 là lô đo giá Sonnet.

**Thứ tự bắt buộc:** chỉ chạy phiên java-3 trước, so số dư credit trước và sau. Chưa mở phiên nào khác (kể cả gói 2
và gói 4) cho tới khi có số đo đó.

## Chuẩn bị (1 lần)

1. Cấp quyền cho Claude GitHub app vào repo private `minhtuann1102/ai-recruit-crawl-review`
   (GitHub → Settings → Applications → Claude → Repository access → thêm repo này).
2. Ghi lại số dư credit trước phiên đầu tiên.

## Gói 1: duyệt lô crawl (repo `minhtuann1102/ai-recruit-crawl-review`, 1 lô mỗi phiên)

**Chạy 1 phiên trước (java-3) để đo giá**: so số dư trước và sau rồi mới mở các phiên còn lại. Mỗi phiên dán đúng 1 dòng.

| Lô | Prompt |
|---|---|
| java-3 | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: java-3, pair count: 16. Track: Java (official sources: docs.oracle.com Java SE 21 API / JLS / JVMS, openjdk.org JEPs, docs.spring.io, hibernate docs, postgresql.org docs).` |
| java-4 | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: java-4, pair count: 16. Track: Java (official sources: docs.oracle.com Java SE 21 API / JLS / JVMS, openjdk.org JEPs, docs.spring.io, hibernate docs, postgresql.org docs).` |
| node-3 | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: node-3, pair count: 16. Track: Node.js (official sources: nodejs.org docs/API, developer.mozilla.org, typescriptlang.org, expressjs.com, docs.nestjs.com, redis.io, docs.bullmq.io, jestjs.io).` |
| node-4 | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: node-4, pair count: 15. Track: Node.js (official sources: nodejs.org docs/API, developer.mozilla.org, typescriptlang.org, expressjs.com, docs.nestjs.com, redis.io, docs.bullmq.io, jestjs.io).` |
| fe-4 | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: fe-4, pair count: 17. Track: Frontend (official sources: react.dev, developer.mozilla.org, nextjs.org/docs, web.dev, typescriptlang.org, w3.org).` |
| fe-5 | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: fe-5, pair count: 16. Track: Frontend (official sources: react.dev, developer.mozilla.org, nextjs.org/docs, web.dev, typescriptlang.org, w3.org).` |
| devops-4 | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: devops-4, pair count: 15. Track: DevOps (official sources: docs.docker.com, kubernetes.io, git-scm.com, developer.hashicorp.com, AWS docs, man pages, OWASP for security terms).` |
| devops-5 | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: devops-5, pair count: 15. Track: DevOps (official sources: docs.docker.com, kubernetes.io, git-scm.com, developer.hashicorp.com, AWS docs, man pages, OWASP for security terms).` |
| py-3 | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: py-3, pair count: 16. Track: Python (official sources: docs.python.org, peps.python.org, docs.djangoproject.com, docs.pytest.org, docs.pydantic.dev, packaging.python.org).` |
| ai-4 | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: ai-4, pair count: 15. Track: AI (official sources: scikit-learn, PyTorch, Hugging Face docs, original papers on arxiv, Google ML crash course, OpenAI / Anthropic docs for LLM topics; non-official sources give at most confidence medium).` |
| py-2 (chạy lại) | `Read CLOUD-SESSION.md in the repo root and follow it exactly. Batch name: py-2, pair count: 16. Track: Python (official sources: docs.python.org, peps.python.org, docs.djangoproject.com, docs.pytest.org, docs.pydantic.dev, packaging.python.org).` |

Phiên nào dừng giữa chừng (hết context, lỗi mạng): dán lại đúng dòng đó vào phiên mới, phiên sau tự làm tiếp.

## Gói 2: code 009 PR `jd-crawl` (repo `minhtuann1102/ai-recruitment-platform`, 1 phiên)

```text
Implement tasks T001–T015 of specs/009-jd-crawling-seeding/tasks.md with /speckit-implement, only those tasks.

- T001 override: PR #42 is not merged yet, so create branch feat/data-pipeline/jd-crawl from
  docs/jd-crawling-seeding-plan (not main). Keep the .gitignore check of T001.
- Read first: README.md, CLAUDE.md, .claude/rules/development-rules.md, .specify/memory/constitution.md; in
  specs/009-jd-crawling-seeding/: spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md.
- Offline only. Do NOT do T016, do NOT run crawl-jd, and send no request to itviec, topdev, careerviet or careerlink
  (the spec requires real crawling from the DE machine). Tests use httpx.MockTransport and self-written fixtures with
  invented companies, people and content (FR-007); never copy real job pages into fixtures.
- Setup per specs/005-rag-knowledge-base-qa/quickstart.md §0 (venv, requirements-dev.txt). No new dependency.
- Keep each code file under 200 lines. Run the full pytest suite of apps/data-pipeline; all new tests must pass.
  If a test that existed before this work fails only because the container lacks a DB or network, report it and do
  not modify it.
- Tick T001–T015 in tasks.md. Conventional commit messages, no AI references and no Co-Authored-By trailer.
- Push branch feat/data-pipeline/jd-crawl. Do not open a PR, do not touch other branches.

Final reply (short): tasks done, pytest summary, files changed, anything unclear in the spec.
```

## Gói 4: kiểm trước nhãn golden set (repo `minhtuann1102/ai-recruitment-platform`, 1 phiên)

```text
Pre-check the retrieval labels of the RAG golden sets so the DE can review them (spec 005 T041). Report only.

- Create branch chore/golden-label-precheck from main.
- Inputs on main: apps/ai-service/evals/rag_golden.json (24 queries) and rag_golden_holdout.json (32 queries); the
  corpus is the 144 pairs in apps/data-pipeline/data/seeds/interview_qa/hard-*.json (every `relevant` id is there).
  Read the `status`, `groups` and `k` fields of both files and the golden-set sections of
  docs/architecture/rag-design.md.
- For every query: (1) does each `relevant` pair actually answer it (quote the pair's question and the answer
  sentence that matches)? (2) search all 144 pairs for pairs that answer it as well or better and are not labelled
  (list qa_id + one-line reason); (3) does the query follow its group rule (vi: pure Vietnamese, no English terms;
  no_diacritics; mixed; en) and does `filters` match the labelled pairs? (4) proposal: keep / add id / remove id /
  reword query, with a confidence.
- Do NOT edit rag_golden*.json, do not set approved_by, do not run evals against a database: AIE owns these files and
  the DE decides every change.
- Write the report in Vietnamese (keep English terms) to plans/reports/golden-label-precheck-261027.md: a summary
  table (query id, group, proposal, confidence) first, then one short section per query that needs a change.
- Commit only that file (conventional message, no AI references, no Co-Authored-By trailer) and push the branch.
  Do not open a PR.

Final reply (short): counts per proposal, the 5 most important changes, anything unclear.
```

## Gói 3: code 009 PR `jd-process` (repo `minhtuann1102/ai-recruitment-platform`, Opus, 1 phiên)

Chỉ chạy sau khi DE đã force-push nhánh `feat/data-pipeline/jd-crawl` (bản đã review, đứng tên DE).

```text
Implement tasks T017–T028 of specs/009-jd-crawling-seeding/tasks.md with /speckit-implement, only those tasks.

- Create branch feat/data-pipeline/jd-process from feat/data-pipeline/jd-crawl (PR jd-crawl, not merged yet).
- Read first: README.md, CLAUDE.md, .claude/rules/development-rules.md, .specify/memory/constitution.md; in
  specs/009-jd-crawling-seeding/: spec.md (US2, FR-008..FR-013, FR-028), plan.md, research.md R5–R8, data-model.md,
  contracts/, quickstart.md §3. Reuse the existing modules of the jd-crawl branch (jd_pii, jd_sources, settings).
- Offline only: the real raw JDs are on the DE machine and are not in git. Do NOT run T029, send no request to any job
  site, and write fixtures with invented companies, people and text (FR-007).
- What the real crawl (515 raw JDs, 2026-10-27) showed, so rules and tests cover it:
  - salary_raw text values seen: "You'll love it" (itviec hides salary), "Cạnh tranh", "Negotiable", "Thỏa thuận";
    numeric salary may have only min (max null); titles may carry salary ("Up to 60M").
  - careerlink never has skills_raw; ~28% of careerviet JDs have none: skills must come from description_text too.
  - topdev lists non-IT postings (retail, F&B, accounting, HR) and some descriptions are only ~180 characters:
    `not_it` and too-short rejection must handle both.
  - Descriptions use Vietnamese and English section headings; numbers use dots as thousands separators.
- Output must be deterministic (stable sort, sorted keys) and written with newline="\n". No new dependency.
- Keep each code file under 200 lines. Run the full pytest suite of apps/data-pipeline; all new tests must pass.
  If a test that existed before this work fails only because the container lacks a DB or network, report it and do
  not modify it.
- Tick T017–T028 in tasks.md. Conventional commit messages, no AI references and no Co-Authored-By trailer.
- Push branch feat/data-pipeline/jd-process. Do not open a PR, do not touch other branches.

Final reply (short): tasks done, pytest summary, files changed, anything unclear in the spec.
```

## Sau khi phiên xong (phiên local, không tốn credit)

- Gói 1: kéo `results/<lô>` về `crawl-review/`, chạy lại `verify_quotes.py` ở máy (quote-check trên cloud chỉ để
  tham khảo), rồi `check_crawl_batches.py` + `update_progress.py`. Lô để lọt canary thì bỏ kết quả lô đó. Riêng py-2:
  chuyển `results-py-2.json` và `quote-check-py-2.json` cũ vào `crawl-review-admin/archive-261026/` trước khi chép bản
  cloud vào; bản mới không qua kiểm thì khôi phục bản cũ.
- Gói 2: đổi tác giả commit sang tên DE ở máy rồi mới mở PR. Nhánh `jd-crawl` xếp chồng lên #42: chỉ mở PR vào main
  sau khi #42 merge. Sau đó mới soạn gói 3 (`jd-process`, T017–T028).
- Gói 4: DE đọc báo cáo, quyết từng nhãn, rồi báo AIE.

## Gói 5: code 009 PR `jd-synthetic` (repo `minhtuann1102/ai-recruitment-platform`, Opus, 1 phiên)

Chạy sau khi DE force-push nhánh `jd-process` đã sửa (2026-10-28). Nếu phiên đã chạy từ bản cũ (f0f3b0d): rebase `--onto` sau.

```text
Implement tasks T030–T036 of specs/009-jd-crawling-seeding/tasks.md with /speckit-implement, only those tasks.

- Create branch feat/data-pipeline/jd-synthetic from origin/feat/data-pipeline/jd-process (already rebased onto main
  with the review fixes: jd_it_filter.py, jd_city.py, title-first group, 138 skills).
- Read first: README.md, CLAUDE.md, .claude/rules/development-rules.md, .specify/memory/constitution.md; in
  specs/009-jd-crawling-seeding/: spec.md (US5, FR-022, FR-024..FR-027), plan.md, research.md R9, data-model.md,
  contracts/, quickstart.md §4. Reuse existing modules: jd_pii (count_jd_pii), skill_dictionary, jd_process_report
  (the `cells` key), jd_normalizer, jd_sections, jd_record_builder, and the LLM client + LlmSettings /
  require_llm_settings of feature 005 in apps/data-pipeline.
- Keep conflicts small: only create the new US5 files (jd_gap_planner.py, jd_synthetic_generator.py,
  jd_synth_command.py and their tests), register `synth-jd` in pipeline/__main__.py, and tick the US5 rows in tasks.md.
  Do NOT edit jd_normalizer, jd_city, jd_it_filter, jd_sections, jd_record_builder, skill_dictionary(.yaml),
  jd_salary or other US2 files (reviewed and merged separately in PR jd-process).
- Round trip through process-jd (FR-027 re-infers group/level/city from the generated text):
  - The title decides the group (spec Clarifications 2026-10-28): code puts one specific dictionary skill of the
    cell's group into the title (e.g. "Senior Java Developer"), never only a generic one (database, network, cloud,
    QA/QC, IT support, information security). Titles must avoid out-of-scope words: sales, tư vấn, presale, trainer,
    business analyst, product owner/manager, project manager, scrum master, BA/PO/PM.
  - Ask the LLM for a title that carries an explicit level word (Intern, Junior, Mid/Middle, Senior, Lead, Manager)
    and a group-typical role word, a location line "Địa điểm: <Hà Nội|Hồ Chí Minh|Đà Nẵng>", and section headings
    "Mô tả công việc", "Yêu cầu ứng viên", "Quyền lợi" so the requirements section is never empty.
  - Code (not the LLM) fills the Raw JD fields the normalizer reads first: location_raw = the cell's city name,
    skills_raw = the chosen canonical skills, experience_raw consistent with the level (or empty).
  - After generation, run the code path process-jd uses (record builder / normalizer) on the candidate in memory. If
    the re-inferred (group, level, city) differs from the cell, or requirements come out empty, retry (max 2 retries,
    same as other post-check failures), then drop it and count it as failed for that cell. Never loop on one cell.
  - Skills in the generated text must be canonical names from the dictionary of the cell's group.
- Real data after fixes (2026-10-28): 341 valid JDs of 515, only 186 meet the T041 seed conditions (title,
  description, requirements, city, type, level, >= 1 skill), so every synthetic JD must meet them too.
- Lessons from the real data: the phrase "Khoa học máy tính" (Computer Science
  degree) must not appear in generated text (it matched the machine-learning alias); do not write "TS" as a degree
  abbreviation; avoid "worker node" style phrases outside DevOps cells.
- Tests: use a fake LLM client and clear-cut fixtures. Do NOT assert exact outputs of the current normalizer or
  section splitter beyond simple unambiguous cases (they will change); assert the US5 behaviour instead (retry then
  drop, no loop, ids, flags, prompt contains no raw crawl text, PII post-check via count_jd_pii, dry-run makes 0 calls).
- Offline only: no real LLM call, no request to any job site, do NOT run T037. Fixtures use invented companies,
  people and text (FR-007).
- Output must be deterministic (stable sort, sorted keys) and written with newline="\n". No new dependency.
- Keep each code file under 200 lines. Run the full pytest suite of apps/data-pipeline; all new tests must pass.
  If a test that existed before this work fails only because the container lacks a DB or network, report it and do
  not modify it.
- Conventional commit messages, no AI references and no Co-Authored-By trailer.
- Push branch feat/data-pipeline/jd-synthetic. Do not open a PR, do not touch other branches.

Final reply (short): tasks done, pytest summary, files changed, anything unclear in the spec.
```
