"""Doan van tinh cua bao cao embedding 017 (Phase 2): ghi chu khi cong tai lap bi bo qua co dieu kien, va gioi han cua so do."""

GATE_NOTES = """Why the literal check misses (context for the decision, not a pass):

- Resolution: one top-5 swap in one CV moves full-score P@5 by 1/(5 x 24) = 0.0083, which is larger than the 0.005 tolerance, so the tolerance cannot absorb a single flip. The same flip moves nDCG@5 by +0.0047 (inside the tolerance).
- Everything else reproduces: skill-only, cosine-only, all 12 by-language rows (within 0.0005), pair set 264 = 264, JD text / content hash / metadata 0 differences.
- Re-embedded JD vectors (text verified identical by md5) differ from the stored ones by cosine >= 0.9998 and give identical metrics, so the flip comes from the CV vectors.
- Model deltas below are paired inside this harness against the oa-small baseline built from the same fresh vectors, so this miss does not enter the deltas. oa-small's own rows below (full 0.888 / 0.650) are the fresh-vector values, not the published 0.883 / 0.642.
- Ad hoc checks, 2026-11-26, throwaway scripts that are not part of the harness: re-embedding the 24 CV texts again after the gate run returned identical vectors (cosine 1.000000), so the API is stable from run to run today; CV texts are under 1200 chars (no truncation involved); untruncated / no-rstrip variants of the be-java-jr text give the same 0.00127 drift; a trailing-newline variant would give 0.0046, so the original request text was not that; cvs.json and cv_text.py have no commit after the 017 run. This points to provider-side nondeterminism between 2026-11-23 and now, but the text actually sent in the original run cannot be re-checked.
- Section 7: the "en" column here is en + mixed JDs. With en only, oa-small equals the published figures (label 0: 0.594 / 0.530, label 1: 0.614 / 0.600, label 2: 0.682 / 0.637)."""

LIMITS = """## 9. Limits

- Dev evidence only: 24 CVs x 36-JD pool, 264 LLM-labeled pairs, synthetic CVs. CIs resample CVs and are wide (oa-large +0.045 has CI [-0.010, +0.100]); only large differences are detectable. 4 comparisons, no correction. The final matching decision is made on the 019 locked test set.
- st-minilm: max_seq_length 128 cuts nearly every CV and JD text (see section 8); used as shipped, a raised limit was not tested.
- st-e5: cosines sit in a narrow high band (section 7), so the 0.6 cosine weight adds little spread and its full-score row mostly reflects the weight scale; cosine-only is the fair comparison.
- Latency: measured while other work was using a large share of this machine's CPU (CPU column), so absolute ms are inflated against a quiet e2-standard-4; use for order of magnitude, rerun with `--remeasure` on a quiet machine. OpenAI latency is a network round trip, not comparable.
- Language-split tables use within-subset ranking (4-7 JDs per CV): they cannot show cross-language bias, the section 7 columns do.
"""
