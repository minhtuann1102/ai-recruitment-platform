# Matching embedding comparison: 017 scorer, embedding swapped (Phase 2)

Dev evidence on **264 labeled pairs (24 CVs x 36-JD pool, as_of 2026-11-01)** from 017; labels are LLM labels. Only the embedding model changes; hard filters, skill_match, level_fit and the 0.6/0.3/0.1 weights are the 017 code. The final matching decision is made on the 019 locked test set, not on this table.

## 1. Models and pinned revisions

| id | model | dims | revision |
|---|---|---|---|
| oa-small | text-embedding-3-small | 1536 | api |
| oa-large | text-embedding-3-large | 1536 | api |
| st-minilm | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | 384 | e8f8c211226b894fcb81acc59f3b34ba3efd5f42 |
| st-e5 | intfloat/multilingual-e5-base | 768 | d128750597153bb5987e10b1c3493a34e5a4502a |
| st-bge | BAAI/bge-m3 | 1024 | 5617a9f61b028005a4858fdac845db406aefb181 |

Prefixes: st-e5 uses `query: ` for CV text and `passage: ` for JD text. oa-large uses `dimensions=1536`. All vectors L2-normalized, cosine. Every model embeds the same strings: CV = `build_cv_text`, JD = the stored `content` that 3-small indexed.

## 2. Gate: reproduced except one API-nondeterminism tie flip (accepted by main session)

Literal tolerance check (+-0.005) FAILED on full-score P@5 only; the miss was investigated (below) and the caller accepted it as reproduced. The numbers in the table are unchanged and unwaived.

Result: **FAIL** (overall, tolerance +-0.005); by-language rows all within tolerance.

JD side: vectors, metadata and content read **read-only from ai_db** (same WHERE / ORDER as `job_index.JD_SQL`, loaded through the real `rows_to_snapshot`); role `aie_reader`, 356 rows -> 356 jobs, newest `created_at` 2026-11-23T04:28:05.306821+00:00, embedding_model `text-embedding-3-small`. CV side: `cv_text.build_cv_text` embedded fresh with text-embedding-3-small. Filter + score: the real `group_for_track`, `cv_skills`, `candidate_level_rank`, `rank_jobs` (job_ids = 36-JD pool, as_of 2026-11-01, weights {'cosine': 0.6, 'skill_match': 0.3, 'level_fit': 0.1}, max_level_gap 1).

Pair set: filtered 264 vs labeled 264 -> equal.

Overall (eval-results.md section 2):
| method | pub P@5 | got P@5 | delta | pub nDCG@5 | got nDCG@5 | delta | n_cv got/pub |  |
|---|---|---|---|---|---|---|---|---|
| full | 0.642 | 0.650 | +0.0080 | 0.883 | 0.888 | +0.0047 | 24/24 | MISS |
| skill_match | 0.625 | 0.625 | +0.0000 | 0.847 | 0.847 | -0.0001 | 24/24 | ok |
| cosine | 0.617 | 0.617 | -0.0003 | 0.842 | 0.842 | +0.0001 | 24/24 | ok |

By JD language (eval-results.md section 3; same = vi JD, cross = en/mixed JD):
| method | pub P@5 | got P@5 | delta | pub nDCG@5 | got nDCG@5 | delta | n_cv got/pub |  |
|---|---|---|---|---|---|---|---|---|
| full/same | 0.455 | 0.455 | -0.0005 | 0.857 | 0.857 | +0.0003 | 22/22 | ok |
| skill_match/same | 0.482 | 0.482 | -0.0002 | 0.795 | 0.795 | -0.0004 | 22/22 | ok |
| cosine/same | 0.473 | 0.473 | -0.0003 | 0.875 | 0.875 | -0.0002 | 22/22 | ok |
| full/cross | 0.396 | 0.396 | -0.0002 | 0.962 | 0.965 | +0.0034 | 24/24 | ok |
| skill_match/cross | 0.396 | 0.396 | -0.0002 | 0.971 | 0.971 | -0.0003 | 24/24 | ok |
| cosine/cross | 0.396 | 0.396 | -0.0002 | 0.903 | 0.903 | +0.0000 | 24/24 | ok |

Pool text vs stored content: 0/36 differ; stored hash vs md5(content): 0 differ; metadata (title/group/level/deadline/skills) vs jd_normalized: 0 differ; stored-vector/snapshot row mismatches: 0.

Re-embedded JD vectors vs stored: cosine min 0.999798, mean 0.999989; gate with re-embedded JD vectors: overall FAIL.

Bootstrap sanity on oa-small (eval-analysis.md section 1 reports full vs skill +0.036 [-0.010, +0.084], 12/6/6 and full vs cosine +0.041, 12/10/2):
- full - skill_match: +0.041 [-0.001, +0.087], W/L/T 12/6/6
- full - cosine: +0.046 [-0.015, +0.109], W/L/T 12/10/2

Comparison with the original 017 run (`run-20261123T044343309633Z.json`, per-pair scores, not committed): max |cosine diff| over all 264 pairs 0.00130; CVs with diff > 1e-4: {'be-java-jr': 0.0013, 'do-sre-mid': 0.0004, 'do-sysadmin-mid': 0.0004}.
CVs whose full-score order differs from the original run: 1
- be-java-jr: first difference at rank 5; now {'job_id': 'itviec:2159', 'score': 0.4923, 'label': 1}, original {'job_id': 'careerviet:35C7AC66', 'score': 0.4923, 'label': 0}
CVs with rank-5/rank-6 full-score gap < 0.003 (flip-prone): [{'cv_id': 'be-java-jr', 'gap_rank5_rank6': 0.0002, 'labels_rank5_rank6': [1, 0]}, {'cv_id': 'do-cloud-mid', 'gap_rank5_rank6': 0.0012, 'labels_rank5_rank6': [1, 0]}, {'cv_id': 'do-sysadmin-jr', 'gap_rank5_rank6': 0.0012, 'labels_rank5_rank6': [0, 0]}, {'cv_id': 'do-sysadmin-mid', 'gap_rank5_rank6': 0.0025, 'labels_rank5_rank6': [0, 1]}, {'cv_id': 'ai-de-mid', 'gap_rank5_rank6': 0.001, 'labels_rank5_rank6': [0, 0]}]
Published numbers if only the differing CVs use the original ranking: full P@5 0.642 nDCG@5 0.883; skill_match P@5 0.625 nDCG@5 0.847; cosine P@5 0.617 nDCG@5 0.842

Why the literal check misses (context for the decision, not a pass):

- Resolution: one top-5 swap in one CV moves full-score P@5 by 1/(5 x 24) = 0.0083, which is larger than the 0.005 tolerance, so the tolerance cannot absorb a single flip. The same flip moves nDCG@5 by +0.0047 (inside the tolerance).
- Everything else reproduces: skill-only, cosine-only, all 12 by-language rows (within 0.0005), pair set 264 = 264, JD text / content hash / metadata 0 differences.
- Re-embedded JD vectors (text verified identical by md5) differ from the stored ones by cosine >= 0.9998 and give identical metrics, so the flip comes from the CV vectors.
- Model deltas below are paired inside this harness against the oa-small baseline built from the same fresh vectors, so this miss does not enter the deltas. oa-small's own rows below (full 0.888 / 0.650) are the fresh-vector values, not the published 0.883 / 0.642.
- Ad hoc checks, 2026-11-26, throwaway scripts that are not part of the harness: re-embedding the 24 CV texts again after the gate run returned identical vectors (cosine 1.000000), so the API is stable from run to run today; CV texts are under 1200 chars (no truncation involved); untruncated / no-rstrip variants of the be-java-jr text give the same 0.00127 drift; a trailing-newline variant would give 0.0046, so the original request text was not that; cvs.json and cv_text.py have no commit after the 017 run. This points to provider-side nondeterminism between 2026-11-23 and now, but the text actually sent in the original run cannot be re-checked.
- Section 7: the "en" column here is en + mixed JDs. With en only, oa-small equals the published figures (label 0: 0.594 / 0.530, label 1: 0.614 / 0.600, label 2: 0.682 / 0.637).

## 3. PRIMARY: cosine-only ranking per CV (scale-invariant)

Raw cosine (no clipping/rounding) over the 264 hard-filter survivors; nDCG@5 / P@5 mean over 24 CVs. Delta = model - oa-small on per-CV nDCG@5, paired bootstrap by CV (10,000 resamples, seed 20261126), 95% percentile CI.

| model | nDCG@5 | P@5 | delta nDCG@5 vs oa-small [95% CI] | W/L/T (CVs) | verdict |
|---|---|---|---|---|---|
| oa-small | 0.842 | 0.617 | (baseline) | - | - |
| oa-large | 0.888 | 0.633 | +0.045 [-0.010, +0.100] | 14/7/3 | EQUAL |
| st-minilm | 0.851 | 0.633 | +0.009 [-0.081, +0.094] | 15/9/0 | EQUAL |
| st-e5 | 0.772 | 0.575 | -0.070 [-0.131, -0.013] | 8/14/2 | WORSE |
| st-bge | 0.827 | 0.600 | -0.015 [-0.064, +0.034] | 10/11/3 | EQUAL |

Skill-only baseline (model independent): nDCG@5 0.847, P@5 0.625. Endpoint-style cosine-only (clipped at 0, rounded to 4 digits, as in eval-results): oa-small 0.842/0.617; oa-large 0.888/0.633; st-minilm 0.851/0.633; st-e5 0.772/0.575; st-bge 0.827/0.600 (nDCG/P@5).

## 4. Decision rule (predeclared, applied literally)

A model wins on quality only if the 95% bootstrap CI of the nDCG@5 difference (by CV) excludes 0; otherwise it is treated as equal and the choice is operational. No multiple-comparison correction (as in the plan); 4 comparisons were made.

- Quality winners over oa-small: **none**
- Significantly worse than oa-small: st-e5
- Everything else: statistically indistinguishable from oa-small on these 24 CVs (equal); decide on cost/ops.

## 5. SECONDARY: full score (0.6 cosine + 0.3 skill + 0.1 level, unchanged weights)

**Weights were tuned on the 3-small cosine scale**; other models have a different cosine scale/spread (see section 7), so the 0.6 weight means something different per model. Not used for the decision rule.

| model | nDCG@5 | P@5 | delta nDCG@5 vs oa-small [95% CI] | verdict |
|---|---|---|---|---|
| oa-small | 0.888 | 0.650 | (baseline) | - |
| oa-large | 0.879 | 0.625 | -0.009 [-0.045, +0.019] | EQUAL |
| st-minilm | 0.907 | 0.667 | +0.019 [-0.025, +0.061] | EQUAL |
| st-e5 | 0.824 | 0.592 | -0.064 [-0.098, -0.034] | WORSE |
| st-bge | 0.862 | 0.608 | -0.026 [-0.072, +0.009] | EQUAL |

## 6. By JD language (CVs are all Vietnamese)

Within-subset ranking only (eval-analysis.md section 2: cannot show cross-language bias; ignore P@5 there, subsets have 4-7 JDs per CV).

| model | method | vi JD nDCG@5 | P@5 | n_cv | en/mixed JD nDCG@5 | P@5 | n_cv |
|---|---|---|---|---|---|---|---|
| oa-small | cosine-only | 0.875 | 0.473 | 22 | 0.903 | 0.396 | 24 |
| oa-small | full | 0.857 | 0.455 | 22 | 0.965 | 0.396 | 24 |
| oa-large | cosine-only | 0.877 | 0.464 | 22 | 0.866 | 0.388 | 24 |
| oa-large | full | 0.853 | 0.464 | 22 | 0.966 | 0.396 | 24 |
| st-minilm | cosine-only | 0.834 | 0.455 | 22 | 0.885 | 0.396 | 24 |
| st-minilm | full | 0.865 | 0.482 | 22 | 0.948 | 0.396 | 24 |
| st-e5 | cosine-only | 0.828 | 0.455 | 22 | 0.797 | 0.371 | 24 |
| st-e5 | full | 0.808 | 0.482 | 22 | 0.934 | 0.396 | 24 |
| st-bge | cosine-only | 0.838 | 0.436 | 22 | 0.812 | 0.371 | 24 |
| st-bge | full | 0.822 | 0.464 | 22 | 0.926 | 0.396 | 24 |

## 7. Cross-language bias and cosine scale

vi share of top-5: share of Vietnamese JDs among each CV's top 5 (published for 3-small: cosine-only 69%, full 56%; about 55% of relevant pairs are vi JD). Mean cosine by label for vi / en+mixed JD (published 3-small: label 0 0.594 / 0.530, label 2 0.682 / 0.637).

| model | vi share top5 (cos-only) | vi share top5 (full) | vi share of relevant pairs | label 0 vi / en | label 1 vi / en | label 2 vi / en |
|---|---|---|---|---|---|---|
| oa-small | 69% | 56% | 55% | 0.594 / 0.532 | 0.614 / 0.600 | 0.682 / 0.650 |
| oa-large | 58% | 53% | 55% | 0.602 / 0.573 | 0.642 / 0.652 | 0.707 / 0.727 |
| st-minilm | 62% | 53% | 55% | 0.535 / 0.488 | 0.598 / 0.595 | 0.691 / 0.683 |
| st-e5 | 62% | 52% | 55% | 0.849 / 0.840 | 0.856 / 0.852 | 0.875 / 0.864 |
| st-bge | 60% | 51% | 55% | 0.604 / 0.576 | 0.620 / 0.628 | 0.691 / 0.673 |

| model | cosine mean | std | min .. max | negative pairs (clipped to 0 in scorer) | tied pairs after 4-digit rounding |
|---|---|---|---|---|---|
| oa-small | 0.588 | 0.066 | 0.421 .. 0.789 | 0 | 1 |
| oa-large | 0.620 | 0.069 | 0.457 .. 0.796 | 0 | 0 |
| st-minilm | 0.557 | 0.115 | 0.222 .. 0.836 | 0 | 0 |
| st-e5 | 0.851 | 0.019 | 0.804 .. 0.910 | 0 | 0 |
| st-bge | 0.612 | 0.055 | 0.499 .. 0.761 | 0 | 0 |

## 8. Operations (CPU, torch 4 threads = e2-standard-4 shape; this machine is 12 logical cores)

Single-text encodes, 3 rounds after 3 warm-up calls, nearest-rank percentiles; each ST model in its own process (peak RSS = process peak working set). OpenAI latency is a network round trip: not comparable with local CPU. `other` = system CPU% minus this process's share during the timed window (contention from other work on this machine, e.g. the Phase 1 worker); high values inflate latency.

| model | dims | max_seq | truncated (tokens incl. special + prefix) | load s | peak RSS MB | CV embed p50 / p95 ms | JD embed p50 / p95 ms | CPU in window |
|---|---|---|---|---|---|---|---|---|
| oa-small | 1536 | 8191 tokens (API) | 0 (texts <= 1200 chars) | n/a | n/a | 470 / 723 (network, n=24) | n/a (API) | n/a |
| oa-large | 1536 | 8191 tokens (API) | 0 (texts <= 1200 chars) | n/a | n/a | 220 / 410 (network, n=24) | n/a (API) | n/a |
| st-minilm | 384 | 128 | CV 100% (mean 172 tok, max 207); JD 97% (mean 260, max 362) | 3.3 | 1158 | 61 / 97  (n=72) | 61 / 101  (n=108) | 59% other, 31% own |
| st-e5 | 768 | 512 | CV 0% (mean 175 tok, max 210); JD 0% (mean 262, max 364) | 6.2 | 1862 | 210 / 283  (n=72) | 305 / 386  (n=108) | 56% other, 32% own |
| st-bge | 1024 | 8192 | CV 0% (mean 172 tok, max 207); JD 0% (mean 260, max 362) | 3.8 | 1950 | 712 / 878  (n=72) | 1005 / 1473  (n=108) | 62% other, 30% own |

## 9. Limits

- Dev evidence only: 24 CVs x 36-JD pool, 264 LLM-labeled pairs, synthetic CVs. CIs resample CVs and are wide (oa-large +0.045 has CI [-0.010, +0.100]); only large differences are detectable. 4 comparisons, no correction. The final matching decision is made on the 019 locked test set.
- st-minilm: max_seq_length 128 cuts nearly every CV and JD text (see section 8); used as shipped, a raised limit was not tested.
- st-e5: cosines sit in a narrow high band (section 7), so the 0.6 cosine weight adds little spread and its full-score row mostly reflects the weight scale; cosine-only is the fair comparison.
- Latency: measured while other work was using a large share of this machine's CPU (CPU column), so absolute ms are inflated against a quiet e2-standard-4; use for order of magnitude, rerun with `--remeasure` on a quiet machine. OpenAI latency is a network round trip, not comparable.
- Language-split tables use within-subset ranking (4-7 JDs per CV): they cannot show cross-language bias, the section 7 columns do.

## 10. Failures

- none

## 11. Reproduce

```bash
cd apps/data-pipeline
.venv/Scripts/python.exe -m pip install --use-feature=truststore --index-url https://download.pytorch.org/whl/cpu torch
.venv/Scripts/python.exe -m pip install --use-feature=truststore -r requirements-embedding-experiment.txt
.venv/Scripts/python.exe -m pipeline.match_embedding_experiment            # gate, then all models (cached under data/processed/match_eval/embedding_cache); stops (exit 3) if the gate misses
.venv/Scripts/python.exe -m pipeline.match_embedding_experiment --accept-gate-miss "reproduced except one API-nondeterminism tie flip (accepted by main session)"   # command that produced this report
.venv/Scripts/python.exe -m pipeline.match_embedding_experiment --gate-only
.venv/Scripts/python.exe -m pipeline.match_embedding_experiment --models oa-small,st-bge --remeasure
```
Needs sandbox off for network (OpenAI, Hugging Face, ai_db). Keys: data-pipeline/.env (EMBEDDING_API_KEY), ai-service/.env (AI_DB_URL, read-only role).
