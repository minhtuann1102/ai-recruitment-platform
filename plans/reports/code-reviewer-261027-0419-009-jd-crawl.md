# Code Review: 009 jd-crawl (T001–T015)

## Scope
- Worktree `C:/Users/NITRO/arp-jd-crawl`, branch `review/jd-crawl` (= `origin/feat/data-pipeline/jd-crawl`), diff vs `origin/docs/jd-crawling-seeding-plan`, 8 commits, +1573/-38
- Code: `crawlers/{jd_sources,jd_page_parser,jd_listing_crawler,polite_fetcher}.py`, `pipeline/{jd_crawl_command,jd_pii,settings,__main__}.py`
- Tests: `test_jd_{pii,page_parser,crawl_listing,crawl_command}.py`, `test_polite_fetcher*.py`, `jd_fake_site.py`, 13 fixtures
- Docs: `docs/architecture/data-pipeline.md`, `specs/009-jd-crawling-seeding/tasks.md`
- Re-ran `pytest -k "jd_ or polite_fetcher"`: 84 passed. Probed edge cases with scratch scripts (PII, JSON-LD shapes, pagination, CRLF).
- Paths below relative to `apps/data-pipeline/`.

## Overall
Solid, readable, well-tested crawl slice. Stop rules, robots, idempotency, exit codes and per-source isolation match
T005/T011/T012. No critical issue. Three major items: T008 not actually done, salary string parsing, recruiter names
survive scrub without being counted.

## Critical
None.

## Major
1. **T008 marked [X] but core deliverable not done.** `crawlers/jd_sources.py:9-12,62-79`: topdev / careerviet / careerlink
   listing URL, page param, link/id regex, selector are guesses (`DU DOAN`), no sample URLs. Fixtures for those 3 sources
   were written to match the guessed regexes, so their tests prove the parser, not the config. Annotation in tasks.md is
   honest, but the box should stay unchecked or the work be explicitly moved into T016.
2. **Salary string parsing wrong / lossy.** `crawlers/jd_page_parser.py:19,109-113`: `_PLAIN_NUMBER_RE` treats one dot as
   decimal → `"1.500"` → `1.5` (VN thousands separator). `"15.000.000"` fails the regex → numbers dropped, and the text
   fallback (`:130`) only reads `value`, so `salary_raw` becomes `null` (salary silently lost, not even kept as text).
   Fix: treat strings with `.`/`,` grouping as text (or strip separators when the pattern is `\d{1,3}([.,]\d{3})+`),
   and fall back to `minValue`/`maxValue` text when not numeric. Feeds US2 normalizer and US4 seed.
3. **Recruiter names survive scrub and `count_jd_pii` reports 0 (FR-009 gap).** `pipeline/jd_pii.py:19,36`:
   `_LEADING_MARK_RE` does not strip list numbering → `"1. Liên hệ: Chị Lan 0912 345 678"` → `"1. Liên hệ: Chị Lan [phone]"`.
   Cheap fix: add `\d+[.)]` to the leading-mark pattern. Outside T003's literal rule (spec gap, but `pii_remaining`
   cannot catch them): mid-line `"xin liên hệ Chị Lan [phone]"`, `"Contact person: Ms. Hoa"`, `"Contact:Ms.Hoa"`,
   `"Recruiter: Nguyễn Thị Lan - [email]"`, `"Zalo: [phone] (Chị Lan)"`.

## Minor
- Over-scrub: lines starting `"Anh Văn: ..."`, `"Ms. Office ..."`, `"C. Cách ứng tuyển ..."` with an email are dropped whole (`jd_pii.py:18`). Privacy-safe direction, loses content.
- `_BLOCK_TAGS` lacks `td`/`th` (`jd_page_parser.py:18`): `<td>Mức lương</td><td>Thỏa thuận</td>` → `"Mức lươngThỏa thuận"`.
- JSON-LD shapes not handled (`jd_page_parser.py:23-41`): `@type` `"schema:JobPosting"` / full IRI, `JobPosting` under `mainEntity`, CDATA / HTML-comment-wrapped block, `baseSalary` as list → `None` / salary null. First `JobPosting` wins even if incomplete while a later one is complete. No `min > max` check. `monthsOfExperience: 24.0` → `"24.0 months"`.
- `itviec` exposes `jobBenefits` (spec "Kiểm tra nguồn") but parser ignores it → benefits may be lost (FR-001 "quyền lợi nếu có"); T009 mapping does not list it.
- Listing end via 404 (`jd_listing_crawler.py:84-90`): 3 wasted requests + `errors: 3` on a normal finish. Transient 5xx on page 1 skips page 1 and continues at page 2.
- `_UNSCRUBBED_KEYS` keeps `url`/`source_job_id` raw (`jd_listing_crawler.py:21`), but `count_jd_pii("https://itviec.com/it-jobs/x-0912345678") == 1`. T014(a) passes only because fixture ids are 4 digits. US2 `pii_remaining` must decide whether ids/URLs are counted.
- Raw JSONL written with CRLF on Windows (`jd_crawl_command.py:45`, `Path.write_text` without `newline="\n"`; verified 2 `\r\n` in 2 lines). Same as 005 `crawl_command.py:40`, but `offline_commands.py:91` uses `newline="\n"`. Not atomic; records are written only at end of a source, so Ctrl-C after N detail pages loses all and re-requests next run. Same-second rerun would overwrite the file (`:44`).
- `follow_redirects=True` (`polite_fetcher.py:50`, pre-existing): redirect target is not robots-checked and can be another host.
- Behaviour change for 005 `crawl`: first page now waits `delay` after robots (`polite_fetcher.py:62`). Harmless, outside T005 text.
- Tests: no CLI wiring test (`main(["crawl-jd", ...])`, `--source` choices, `HANDLERS`, default `--delay 2.0`); no command-level test for >50% missing-required → exit 1 (only `too_many_unusable` unit); `"subscriptions"` assertion in `tests/test_jd_crawl_command.py:72` is vacuous (link never matches detail regex, robots not exercised); `count_jd_pii(text) >= 3` (`tests/test_jd_pii.py:94`) could be exact; only "Attention Required" challenge tested, not "Just a moment"; topdev JSON-LD description is ~115 chars, not ~180.

## Task status
- Done as written: T001 (base branch deviation noted), T002, T003, T004, T005, T006, T007, T009, T010, T011, T012, T013, T014, T015.
- Partly done: **T008** (3 of 4 source configs unverified).
- Deviations (acceptable, documented in code): challenge detection limited to `<title>` (`polite_fetcher.py:26`); streak reset on any non-block response, not only 2xx (`:139`, locked by `tests/test_polite_fetcher.py:154`); `status=empty` broader than T011 text (`jd_listing_crawler.py:130`); "no JobPosting" counted as unusable in the >50% rule.

## Positive
- Block handling clean: no retry, robots 403/429 → blocked before any page request, other sources keep running, records already fetched still written when blocked.
- Idempotency: known ids skipped before request; broken raw lines tolerated.
- PII scrub runs on all nested string fields; NFC normalisation; profile URLs replaced before `scrub_pii` (correct ordering for `zalo.me/<phone>`).
- Fixtures invented (`... Giả` companies, `nguon-gia.example`, `congty-gia.vn`); every test goes through `MockTransport`, no real network; all files < 200 lines; no new dependencies; UTF-8 stdout reconfigured in `__main__`.

## Metrics
- Tests: 84 JD/fetcher tests pass (184 full suite per caller). Type hints present on public functions. Lint not run.

## Unresolved questions
1. T005: should 404/5xx between two 403s reset the block streak (code: yes; spec text: only 2xx)?
2. T012 bold "exit 1 only when 0 links / 0 parsed" vs code also exiting 1 on source exception, 3 listing 5xx, robots-disallowed listing: intended?
3. "Link mới" = new in this run (code) or not in raw yet? Current reading makes a rerun walk every listing page up to `--max-pages`.
4. Spec profile-URL list turns company Facebook pages (`facebook.com/congtygia`) into `[link]`: accepted?
5. Should FR-009 contact-line rule be widened (numbered prefixes, mid-line "liên hệ + honorific + Name", "Contact person", "Recruiter")?
6. Does US2 `pii_remaining` count `source_url` / `source_job_id`?
