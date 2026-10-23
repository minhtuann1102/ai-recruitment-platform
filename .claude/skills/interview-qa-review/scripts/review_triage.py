"""Sort review results into what the human must read, canary scoring, and quote-check lookups.

Used by build_review_report.py. Pure functions over result objects (references/review-rubric.md), no I/O except
loading the optional quote-check file written by verify_quotes.py.
"""
import json
from pathlib import Path

FORMAT_TYPES = {"interview_fit", "length", "language", "format"}
SUBSTANCE_STATUS = {"contradicted", "outdated", "unverified"}


def load_quote_check(path):
    """{qa_id: {claim_index(str): found | not_found | unreadable}} or {} when no file was given."""
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else {}


def quote_problems(result, quote_check):
    """Indexes (0-based) of claims marked supported whose quote was not found verbatim on the page."""
    checks = quote_check.get(result.get("qa_id"), {})
    return [i for i, c in enumerate(result.get("claims") or [])
            if c.get("status") == "supported" and checks.get(str(i)) == "not_found"]


def triage(result, quote_check):
    """must_read | format_only | accept.

    must_read: drop, low confidence, a contradicted/outdated/unverified claim, a critical issue, a major issue about
    substance (not wording or breadth), or a supporting quote that is not on its page.
    format_only: a fix whose major issues are all about breadth, length, language or format.
    """
    claims, issues = result.get("claims") or [], result.get("issues") or []
    serious = [i for i in issues if i.get("severity") in ("critical", "major")]
    if (result.get("verdict") == "drop" or result.get("confidence") == "low"
            or any(c.get("status") in SUBSTANCE_STATUS for c in claims)
            or any(i.get("severity") == "critical" for i in issues)
            or any(i.get("type") not in FORMAT_TYPES for i in serious)
            or quote_problems(result, quote_check)):
        return "must_read"
    return "format_only" if result.get("verdict") == "fix" else "accept"


def canary_caught(result, spec):
    """A canary counts as caught only when the review names the planted error, not for any fix/drop.

    spec is either {"error": str, "keywords": [str]} (caught when an issue or contradicted/outdated claim mentions a
    keyword) or a plain string (caught when there is a contradicted/outdated claim or a factual/outdated issue).
    """
    if not result or result.get("verdict") not in ("fix", "drop"):
        return False
    flagged_claims = [c for c in result.get("claims") or [] if c.get("status") in ("contradicted", "outdated")]
    flagged_issues = [i for i in result.get("issues") or [] if i.get("type") in ("factual", "outdated")]
    if isinstance(spec, dict) and spec.get("keywords"):
        text = " ".join([c.get("claim", "") + " " + c.get("note", "") for c in flagged_claims] +
                        [i.get("detail", "") for i in flagged_issues]).lower()
        return any(k.lower() in text for k in spec["keywords"])
    return bool(flagged_claims or flagged_issues)


def canary_error(spec):
    return spec.get("error", "") if isinstance(spec, dict) else spec
