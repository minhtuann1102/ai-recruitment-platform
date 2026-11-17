"""Doc catalog ai-service theo track cho spec 012 (research R2): category chinh, topic, scenario cua tung track.

Bo sung cho topic_catalog_reader (chi doc topics[]): o day can them track (truong `track` cua file YAML) va
scenarios[]. Khong import code ai-service (005 R1); hop dong chung la chinh file YAML.
"""
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

import yaml

from .topic_catalog_reader import CatalogError


@dataclass(frozen=True)
class Track:
    track_id: str
    main_category: str  # category xuat hien nhieu nhat trong topics; hoa thi lay category xuat hien truoc
    topic_categories: Dict[str, str] = field(default_factory=dict)  # topic_id -> category
    scenario_ids: List[str] = field(default_factory=list)


def _main_category(categories: List[str]) -> str:
    """Counter.most_common giu thu tu chen khi hoa -> category xuat hien truoc thang."""
    return Counter(categories).most_common(1)[0][0]


def _parse_track(path: Path, data: Dict) -> Track:
    track_id = data.get("track")
    if not track_id:
        raise CatalogError(f"{path.name}: thieu truong 'track'")
    topic_categories: Dict[str, str] = {}
    for topic in data.get("topics") or []:
        topic_id, category = topic.get("id"), topic.get("category")
        if not topic_id or not category:
            raise CatalogError(f"{path.name}: topic thieu id hoac category: {topic!r}")
        if topic_id in topic_categories:
            raise CatalogError(f"{path.name}: topic_id trung trong track {track_id}: {topic_id}")
        topic_categories[topic_id] = category
    if not topic_categories:
        raise CatalogError(f"{path.name}: track {track_id} khong co topic nao nen khong tinh duoc category chinh")
    scenario_ids: List[str] = []
    for scenario in data.get("scenarios") or []:
        if not scenario.get("id"):
            raise CatalogError(f"{path.name}: scenario thieu id: {scenario!r}")
        scenario_ids.append(scenario["id"])
    return Track(track_id, _main_category(list(topic_categories.values())), topic_categories, scenario_ids)


def load_tracks(dirs: Iterable[Path]) -> Dict[str, Track]:
    """{track_id: Track} cua moi *.yaml trong cac thu muc theo thu tu; track hoac topic_id trung giua cac file la loi."""
    tracks: Dict[str, Track] = {}
    seen_topics: Dict[str, str] = {}
    for directory in dirs:
        files = sorted(Path(directory).glob("*.yaml"))
        if not files:
            raise CatalogError(f"khong co file *.yaml trong {directory}")
        for path in files:
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                raise CatalogError(f"{path.name}: YAML sai dinh dang: {exc}") from exc
            if not isinstance(data, dict):
                raise CatalogError(f"{path.name}: goc file phai la mapping")
            track = _parse_track(path, data)
            if track.track_id in tracks:
                raise CatalogError(f"track trung giua cac file catalog: {track.track_id} ({path.name})")
            for topic_id in track.topic_categories:
                if topic_id in seen_topics:
                    raise CatalogError(f"topic_id trung giua cac track: {topic_id} ({path.name}, {seen_topics[topic_id]})")
                seen_topics[topic_id] = path.name
            tracks[track.track_id] = track
    return tracks
