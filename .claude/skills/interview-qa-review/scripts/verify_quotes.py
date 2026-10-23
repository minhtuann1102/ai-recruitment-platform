"""Check that every quoted sentence in review results appears verbatim on its source page.

WebFetch answers through a summarising model, so a "quote" can be a paraphrase. This script downloads each
source_url itself, strips the HTML and looks for the quote after normalising whitespace, quote marks and markdown.
Quotes containing an ellipsis are split and every fragment must be found.

Statuses per claim: found | not_found | unreadable (fetch failed, page has almost no text or is a PDF: often a block
on the checking machine's network or a JavaScript-only page, so it means "not checked", not "wrong").

Usage:
  python verify_quotes.py --results results-java.json [--results ...] --cache .quote-cache --out quote-check.json
"""
import argparse
import hashlib
import html
import json
import re
import time
import urllib.request
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (compatible; ai-recruit-qa-review/0.1)"
MIN_PAGE_CHARS = 1500
QUOTE_MAP = {"‘": "'", "’": "'", "“": '"', "”": '"', " ": " ", "–": "-", "—": "-"}


def normalise(text):
    for src, dst in QUOTE_MAP.items():
        text = text.replace(src, dst)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # markdown link [text](url) -> text
    text = re.sub(r"\{\{[<%].*?[>%]\}\}", " ", text)          # Hugo shortcodes in raw docs sources
    text = re.sub(r"[`*_\[\]]", "", text)
    return re.sub(r"\s+", "", text).lower()


def page_text(url, cache_dir, timeout):
    cache = Path(cache_dir) / (hashlib.sha1(url.encode()).hexdigest() + ".txt")
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(8_000_000).decode("utf-8", errors="replace")
            is_html = "html" in (response.headers.get("Content-Type") or "")
    except Exception:  # network problems are reported as "unreadable", not as a failed quote
        return ""
    text = body
    if is_html:  # plain text sources (.d.ts, raw markdown) keep their angle brackets, e.g. Promise<any>
        text = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", text)
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    cache.write_text(text, encoding="utf-8")
    time.sleep(0.3)
    return text


def check_quote(quote, text):
    # PDF bytes decoded as text (arxiv.org/pdf/...) are not searchable: "not checked", not "wrong"
    if len(text.strip()) < MIN_PAGE_CHARS or text.lstrip().startswith("%PDF"):
        return "unreadable"
    haystack = normalise(text)
    fragments = [f for f in re.split(r"\.\.\.|…", quote) if normalise(f)]
    return "found" if fragments and all(normalise(f) in haystack for f in fragments) else "not_found"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", action="append", required=True)
    parser.add_argument("--cache", default=".quote-cache")
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()
    Path(args.cache).mkdir(parents=True, exist_ok=True)

    report, counts = {}, {"found": 0, "not_found": 0, "unreadable": 0}
    for results_file in args.results:
        for result in json.loads(Path(results_file).read_text(encoding="utf-8")):
            checks = {}
            for index, claim in enumerate(result.get("claims") or []):
                quote, url = claim.get("quote", "").strip(), claim.get("source_url", "").strip()
                if not quote or not url:
                    continue
                status = check_quote(quote, page_text(url, args.cache, args.timeout))
                checks[str(index)] = status
                counts[status] += 1
                if status != "found":
                    print(f"  {result['qa_id']} claim {index + 1}: {status}  {url[:70]}")
            report[result["qa_id"]] = checks
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"quotes: {counts} -> {args.out}")


if __name__ == "__main__":
    main()
