"""Buoc dau chung cua cac lenh textbook (crawl / process / index): kiem manifest, chon nguon theo --source.

Moi lenh khac goi `load_checked_manifest` truoc va dung voi ma 1 khi manifest loi (contracts/pipeline-cli-textbook.md).
"""
import sys
from typing import List, Optional, Sequence

from .textbook_manifest_models import Source
from .textbook_source_manifest import ManifestError
from .textbook_validate_command import ManifestCheck, check_manifest
from .topic_catalog_reader import CatalogError


def load_checked_manifest() -> Optional[ManifestCheck]:
    """Manifest da kiem; None (da in ly do ra stderr) khi khong doc duoc hoac co loi — canh bao khong chan."""
    try:
        check = check_manifest()
    except (ManifestError, CatalogError) as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return None
    if check.errors:
        for message in check.errors:
            print(f"[loi] {message}", file=sys.stderr)
        print(f"manifest co {len(check.errors)} loi: chay `python -m pipeline validate-textbook`", file=sys.stderr)
        return None
    return check


def select_sources(check: ManifestCheck, source_ids: Sequence[str]) -> Optional[List[Source]]:
    """`--source` lap lai duoc; bo trong = moi nguon status use. source_id la hoac status excluded -> None (da in loi)."""
    by_id = {source.source_id: source for source in check.sources}
    if not source_ids:
        return [source for source in check.sources if source.status == "use"]
    chosen: List[Source] = []
    for source_id in dict.fromkeys(source_ids):
        source = by_id.get(source_id)
        if source is None or source.status != "use":
            state = "khong co trong manifest" if source is None else f"co status {source.status}"
            print(f"loi: nguon {source_id!r} {state}", file=sys.stderr)
            return None
        chosen.append(source)
    return chosen
