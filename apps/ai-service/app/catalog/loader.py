"""Doc topic catalog tu cac file YAML cung thu muc."""
from functools import lru_cache
from pathlib import Path
from typing import List

import yaml

from .models import TrackCatalog

CATALOG_DIR = Path(__file__).resolve().parent


class CatalogError(RuntimeError):
    pass


def list_tracks() -> List[str]:
    return sorted(p.stem for p in CATALOG_DIR.glob("*.yaml"))


@lru_cache(maxsize=None)
def load_catalog(track: str) -> TrackCatalog:
    path = CATALOG_DIR / f"{track}.yaml"
    if not path.is_file():
        raise CatalogError(f"track khong ton tai: {track}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    catalog = TrackCatalog.model_validate(data)
    if catalog.track != track:
        raise CatalogError(f"{path.name}: truong track '{catalog.track}' khong khop ten file")
    return catalog
