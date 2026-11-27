# Golden rating page: rater_b (FSD) label check — 2026-10-28

Page: https://claude.ai/artifact/YFmdgQvmg9HVZyTS5WeSzf (db `ratings/<uid>/{question|evaluator}`)

## Completeness
| Rater | question | evaluator | invalid/empty | notes | entered |
|---|---|---|---|---|---|
| rater_a (DE) | 60/60 | 43/43 | 0 | 11 q / 42 e | 10-25, 10-26 |
| rater_b (FSD) | 60/60 | 43/43 | 0 | 0 | 10-26→10-28 02:06 (q), 10-28 02:10–02:21 (e) |

## Page integrity (ruled out page bug)
- Live page (version 1793074934-6ac1) embedded data vs `eval_sheet.csv` / `question_sheet.csv`: same 43/60 ids, question/answer/key_points identical (key_points list in page, ` | ` string in CSV).
- No row offset: mean abs band diff lowest at shift 0 (1.22 vs 1.38–1.52 for ±1..3).
- FSD walked page order (arrow keys), so FSD saw the right content per id.

## Evaluator sheet: rater_b unusable
- Median 8 s between saves (rater_a 37 s); 43 items in 11 min.
- 8 distinct label combos; `3 3 3 2` ×20, `4 4 4 3` ×13 (bands move in lockstep).
- Agreement: 24/43 items differ ≥ 2 bands on some criterion; exact match completeness 13/43, extensibility 7/43.
- Content checks (R T C E):
  - s023c2a0a keyword-list answer, no explanation → FSD 4 4 4 3 (A 1 1 0 1)
  - sed696f55 off-topic (Docker Compose for K8s probes Q) → FSD answered 3 3 3 2 (A off_topic)
  - s219afb1a factually wrong (Node thread per request) → FSD 3 3 3 2 (A 2 0 0 0)
  - sd1433188, s3a2d3beb, sc45eaf0f full, correct answers → FSD 2 1 1 0 partial (A 4 4 4 x)

## Question sheet: weaker evidence, likely redo
- Median 7 s between saves (rater_a 21 s); 5 distinct combos; action_ok `y` on all 60 (A: 6 `n`, several defensible: `hint` action that asks a new topic).
- Exact agreement: action_ok 54/60, level_fit 40/60, natural 35/60. Sheet is subjective, so disagreement alone is not proof.

## Recommendation
- Do NOT import rater_b; do NOT run ≥2-band adjudication into `final.json` (would adjudicate noise on 24/43).
- Ask FSD to redo evaluator sheet (and review question sheet) blind: no ids, no rater_a scores in the request.
- Optional: clear FSD subtree before redo so old values don't anchor (destructive, needs user OK).

## Decision (2026-10-28)
User dropped rater_b entirely (no redo). rater_a imported for both sheets on `chore/golden-labels-rater-a`.

## Unresolved questions
- Clear `ratings/u_2xHjiPmY8ZXsn3fJxGAh2Q/{question,evaluator}` before redo, or let FSD overwrite?
- If FSD can't redo in time: who is second rater (Thắng/AIE?) or ship single-rater calibration with caveat?
