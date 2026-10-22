# Review rubric

How the platform uses a pair decides what "good" means:
- **Interviewer / Planner** (ai-service, PR #14 and #19) picks hard pairs for middle/senior sessions by `topic_id`
  and difficulty, and puts at most 3 chunks / 600 tokens of reference snippets into a topic plan. A session lasts
  15–20 minutes with a handful of questions, so one question gets roughly 3–5 minutes of spoken answer.
- **Evaluator** fetches the pair by `qa_id` as the reference answer and grades the candidate against it. A wrong
  key point in the answer makes the Evaluator punish correct candidates or reward wrong ones.
- **Golden set** (`apps/ai-service/evals/rag_golden.json`) labels some pairs as the expected retrieval result;
  dropping or rewording those pairs changes recall numbers.

## Criteria

1. **Correctness.** Every load-bearing claim checked against a fetched source.
   - `supported`: a quoted sentence says the same thing.
   - `contradicted`: a quoted sentence says otherwise.
   - `outdated`: true for an older version, superseded now (quote the newer source; name both versions in `note`).
   - `unverified`: no source found or fetch failed. Never counts as support.
2. **Currency.** A version-specific claim must name its version or be phrased so it stays true. Check every item
   listed for the track in `domain-pitfalls.md` that the answer touches.
3. **Topic fit.** The pair belongs to its `topic_id`: it exercises the topic's key concepts, not a neighbouring
   topic. `checks.topic_levels_ok` false means the topic has no middle/senior level, so a hard pair there is
   misplaced.
4. **Difficulty.** Hard means reasoning, not recall: trade-offs, internals, failure modes, debugging a concrete
   scenario. A solid middle answers part of it; a senior answers it fully. A definition question in hard
   clothing is not hard.
5. **Interview fit.**
   - Answerable aloud in about 3–5 minutes. More than 2 sub-questions (count the asks, e.g. "schema, errors,
     idempotency, timeout and authz" is 5) is too broad: propose a split or a narrower question.
   - The answer contains 3–6 points a grader can check. A wall of facts with no priority is hard to grade.
   - No vendor trivia, exact flag names or version numbers as the thing being tested, unless the topic is that
     tool. No long code to type.
6. **Chunk length.** `checks.over_plan_budget` true means the Planner snippet gets cut. Major if the must-have
   points sit in the part that is cut, minor otherwise; propose what to trim.
7. **Language.** Natural Vietnamese, English technical terms kept, code blocks intact, no machine-translation
   phrasing.

## Severity

- **critical**: a wrong or dangerous key point (contradicted fact the grading depends on, insecure advice
  presented as good practice).
- **major**: outdated or unverified load-bearing claim, too broad, not really hard, wrong topic, key points lost to
  truncation, ambiguous question with several valid readings.
- **minor**: wording, small missing nuance, length that does not hide key points, weak source.

## Verdict rules

- `ok`: no critical or major issue, and every load-bearing claim is `supported` with a quote.
  - `confidence: high` when the supporting quotes come from official docs or specs.
  - `confidence: medium` when some rely on secondary sources (blogs, books, vendor posts).
- `fix`: any major issue, or any contradicted / outdated / unverified load-bearing claim that can be corrected.
  `proposed_fix` is required and concrete (the corrected sentence, the narrower question, what to cut).
- `drop`: critical problem that cannot be fixed cheaply, off-topic, duplicate of another pair, or unusable in an
  interview. If `checks.drop_breaks_sc001` is true, say that dropping leaves the topic under 2 hard pairs.
- `confidence: low` whenever a judgement rests on unverified claims or on reasoning without sources. Low
  confidence pairs go to the human reviewer first.

## Field-by-field schema

| Field | Type | Meaning |
|---|---|---|
| `qa_id` | string | id from the batch |
| `verdict` | `ok` \| `fix` \| `drop` | per rules above |
| `confidence` | `high` \| `medium` \| `low` | per rules above |
| `summary_vi` | string | 1–2 sentences: the verdict and the main reason |
| `claims[]` | array | 3–8 load-bearing claims |
| `claims[].claim` | string | the claim, short, in Vietnamese |
| `claims[].status` | enum | `supported` \| `contradicted` \| `outdated` \| `unverified` |
| `claims[].source_url` | string | page the quote comes from; empty only when `unverified` |
| `claims[].quote` | string | exact sentence, source language, ≤ 300 chars; empty only when `unverified` |
| `claims[].note` | string | optional: versions involved, why unverified |
| `issues[]` | array | empty for a clean `ok` |
| `issues[].severity` | enum | `critical` \| `major` \| `minor` |
| `issues[].type` | enum | `factual` \| `outdated` \| `topic` \| `difficulty` \| `interview_fit` \| `length` \| `language` \| `format` |
| `issues[].detail` | string | what is wrong, Vietnamese |
| `issues[].fix` | string | how to fix it, Vietnamese |
| `difficulty.is_hard` | bool | criterion 4 |
| `difficulty.levels` | array | levels the question suits: `junior` / `middle` / `senior` |
| `difficulty.note` | string | why |
| `interview_fit.minutes` | number | estimated spoken answer time |
| `interview_fit.sub_questions` | number | asks counted in the question |
| `interview_fit.gradeable` | bool | answer has 3–6 checkable points |
| `interview_fit.note` | string | why |
| `junior_guide.tests` | string | the skill or understanding the question probes |
| `junior_guide.must_have` | array | 3–6 points a good answer hits, in priority order |
| `junior_guide.red_flags` | array | 2–4 answers that show a misunderstanding |
| `junior_guide.follow_up` | string | one follow-up question an interviewer could ask next |
| `proposed_fix` | object \| null | required for `fix`: `question` (new wording or empty), `answer_change` (what to change) |

## Junior guide

Write it for someone who knows the basics but not this domain: plain Vietnamese, one line per point, no jargon
without a short gloss. The must-have points must agree with the claims marked `supported`.
