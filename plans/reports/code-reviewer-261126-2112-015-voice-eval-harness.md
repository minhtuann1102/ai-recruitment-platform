# Code review: 015 US4 voice eval harness (d316ca9, T026–T027)

## Scope
- Files: `apps/voice-service/evals/{build_manifest,eval_inputs,voice_eval_client,eval_stats,eval_report,run_voice_eval}.py`, `manifest.jsonl`, `pricing.json`, `phrases/*.json`, `README.md`, `tests/test_voice_eval_{run,manifest_and_stats}.py`, spec edits (tasks, quickstart, specs/README)
- LOC: ~610 Python (largest 143), tests 207
- Checked against: research R10/R12, spec SC-001..007, contract transcribe/speak/health, data-model "Mẫu đo", tasks T026/T027, AIE consumer `apps/ai-service/evals/stt_noise.py`
- Tests: `python -m pytest -q` → 227 passed (13 new), offline

## Overall
Solid, small, readable. Client matches contract (bytes → Content-Length, `consent_confirmed=true`, keywords as one JSON-array field which `parse_keywords` accepts, token header only). No retries in harness; errors recorded, not repeated. Privacy of committed report OK. Nearest-rank percentile correct (checked n=1..499 for p50/p95, no float off-by-one). `stt_samples.jsonl` shape matches `stt_noise.stt_samples` (`id`, `stt_of`, `noise`, `answer`; `stt_of` resolves to golden id). Exit 2 with no report and no network calls verified by test. All files < 200 lines.

No Critical issues. One High that must be fixed **before T028 recordings start**; nothing blocks merging the code.

## High

### H1. Recording ↔ reference binding not pinned; drift test invites remapping recorded clips
- `eval_inputs.py:287-305` resolves `reference` from live AIE `evaluator_golden.jsonl` at run time; manifest stores only `golden_id`.
- `test_voice_eval_manifest_and_stats.py:162-164` compares manifest to `build(golden)`, and `build()` (`build_manifest.py:216-231`) only looks at id/track/tier/adversarial:
  - AIE edits an `answer` text → test still green, SER/terms silently scored against text the speaker never read.
  - AIE adds/relabels rows (ids sorting earlier, tier change) → test red; obvious "fix" is `python -m evals.build_manifest` (README table advertises "Sinh lại"), which reassigns `r01…r24` to different golden ids while `evals/audio/r01.webm` still holds the old reading → wrong reference for every shifted clip, no error.
  - CI (`.github/workflows/ci.yml`) has no path filter, voice-service in matrix → an AIE-only golden PR turns voice-service CI red (cross-team coupling). Golden last edited 2026-10-31 (b4d2fd0), so plausible again.
- Fix:
  - Add `ref_sha256` (sha256 of `answer`, or of `" ".join(tokens(answer))`) to each `read` row; `load_clips` raises `ValueError` on mismatch.
  - Replace exact-equality drift test with: (a) determinism test of `build()` on a fixed in-test fixture; (b) integrity test: every committed `golden_id` exists, hash matches, rules (24/6, tiers, no adversarial) hold for the committed file.
  - README + `build_manifest` docstring: "do not regenerate after recordings exist"; optionally make `main()` refuse to overwrite when `evals/audio/` has files unless `--force`.

## Medium

### M1. SC-001 latency: failures dropped from p95, nokw runs pooled
- `run_voice_eval.py:52-57`: error/timeout/no_speech → `continue` before `out["latency"].append`. A 504 `provider_timeout` or client `ReadTimeout` (the slowest cases) is excluded, so p95 looks better and the row can print "đạt".
- Same block pools `nokw` runs into SC-001. Production caller always sends keywords (R10 spike "keywords bắt buộc thực tế"); pooling also counts each read clip twice (pseudo-replication; nearest-rank p95 on correlated pairs).
- Fix: collect latency only for `mode == "kw"` (read kw + free). Count failed kw runs per bucket (bucket from nokw duration if available, else "unknown") and add a "lỗi" column; `passed = None` (or "không đạt") when the bucket has failures.

### M2. Results lost after credit spent → re-run double-charges
- Everything after `evaluate_clips` can raise with results only in memory: `load_pricing()` (`run_voice_eval.py:109`), `args.out.write_text` with missing parent dir (`:118`), non-JSON 200 `response.json()` / missing `s["end"]` (`voice_eval_client.py:219-223`), `_score` `ValueError` on empty reference (`wer.py:299-300`), KeyboardInterrupt.
- Fix: preflight before `health()`: `load_pricing()`, `args.out.parent.is_dir()`, `out_dir.mkdir`, and check every read clip's reference tokenizes non-empty. Wrap 200 parsing in `try/except (ValueError, KeyError, TypeError)` → `TranscribeResult(ok=False, error="bad_response")`. Optionally append each call's result to `out/raw.jsonl` as it lands (also delivers the "bản ghi thô" README promises, see L2).

### M3. Fatal errors don't stop the run
- 401 `unauthorized` (token missing/mismatch), 503 `provider_unconfigured|misconfigured`, 402 `quota_exceeded` → loop continues for all 30 clips + 21 TTS, then writes a report of pure errors over `eval-results.md`. Not a credit leak (rejected calls), but wastes time and clobbers the result file.
- Fix: on first result with `error in {"unauthorized", "quota_exceeded", "provider_unconfigured", "misconfigured"}` abort with exit 1 and no report.

### M4. SC-002 "with vs without keywords" comparison is unpaired
- `run_voice_eval.py:64-66` + `recognition_summary`: kw and nokw summaries can cover different clip sets when one mode errors/no_speech, so the improvement shown in the report compares different clips.
- Fix: compute both summaries over clips where both modes succeeded (keep kw-only pooled number for the ≥85% gate), or add a "paired" row.

## Low
- L1 SER headline is macro mean/median of per-clip SER (`eval_stats.py:55-58`) while terms are pooled (micro). Weak clips (~15–22 syllables) dominate the mean. Consider adding pooled SER = Σedits / Σref tokens (have `_score` return edits and ref length). R10 doesn't mandate either, so optional.
- L2 README table (`evals/README.md`, `out/` row) says `out/` holds "bản ghi thô"; nothing writes it. Fix doc or write `raw.jsonl` (M2).
- L3 Free prompt: `reading_sheet` (`build_manifest.py:241-252`) gives one question per track → f01 and f05 (both s1, java) get the same prompt, and it is q01, whose strong/medium/weak answers s1 just read aloud → free answers primed by the read text. Rotate questions per free clip (e.g. pick the i-th question of the track by clip index, skipping ones the speaker read).
- L4 With `--limit`, header shows "Clip có file: X/Y" but not how many were measured; add `clips_measured` and the limit to the header.
- L5 `stt_samples.jsonl` written without `newline="\n"` (`run_voice_eval.py:121`) → CRLF on Windows; harmless for AIE reader, inconsistent with other writers.
- L6 Tests assert TOKEN/FREE_SECRET not in report only; add `capsys` check that stdout/stderr never contain them either (cheap guard against future debug prints).
- L7 Uncaught `httpx.ConnectError` / `HTTPStatusError` from `health()` gives a traceback instead of a one-line hint (service not running); harmless, before any spend.
- L8 Credit estimate excludes calls that failed after reaching Blaze (504, client timeout) and VAD; label already says "ước lượng", could add "lượt lỗi chưa tính".

## Caveat (not a defect, by R10 definition)
Term vocabulary = tokens of track phrases, so it includes generic/split tokens: `i`, `o` (from I/O, 10 of ~200 term tokens in the 24 references), `test`, `key`, `code`, `set`, `model`, `fine`, `top`. Easy tokens make SC-002 rate optimistic; "Promise.all" → `promiseall` means STT "promise all" counts as a miss (pessimistic). Mention in `eval-results.md` limitations; no code change asked.

## Verified OK
- Privacy: free transcripts never stored (only metrics + warning codes); errors carry only contract code / exception class name; report has clip ids + s1/s2 only; `audio/` and `out/` gitignored (checked with `git check-ignore`).
- Token: only in `X-Internal-Token` header, never printed; env var then `.env` fallback.
- Cost: no retries in harness; client timeout 120 s (spike 60 s clip = 14.6 s); TTS warm-up excluded (as decided); credit math matches R12 (17.6 + 29.6 = 47.2).
- Contract: Content-Length present (test asserts), consent field, keywords JSON array parsed by `transcribe_form.parse_keywords`, `language` field valid.
- Manifest: deterministic (sorted ids, zero-padded), 24 read / 6 free, 2 per tier per track, no adversarial, 3 clips per speaker per track; sheet prints UTF-8 on Windows console.
- Percentile: nearest-rank, `ceil(p/100*n)` exact for n ≤ 499.
- SC-001 buckets: `≤ 30` then `≤ 90` inclusive, `> 90` shown without target; duration = last segment end (as decided).
- AIE consumer compatibility: ids `rNN-stt` unique, `stt_of` = golden id, `noise` list; `stt_noise.stt_samples` joins on `stt_of`.

## Recommended actions
1. H1 before T028 (pin reference hash, rework drift test, README warning).
2. M1, M2, M3 before the real 30-clip run.
3. M4 + L-items when convenient.

## Unresolved questions
- Will AIE keep editing `evaluator_golden.jsonl` answers (v6 evaluator)? If yes, H1 hash pin is mandatory; also decide whether voice-service CI should depend on AIE's file at all.
- Should SC-001 count failed/timeout runs as "không đạt" or report them separately? Spec silent.
