"""Doc topic catalog (YAML cua ai-service) nhu du lieu: {topic_id: category}.

Chi lay topics[], bo scenarios[]: topic_id cua Q&A phai tro toi topic (FR-002). Khong import code
ai-service (research R1, R5); hop dong chung la chinh file YAML.
"""
from pathlib import Path
from typing import Dict, Iterable

import yaml


class CatalogError(RuntimeError):
    pass


def load_topic_categories(dirs: Iterable[Path]) -> Dict[str, str]:
    """Gop topic cua moi *.yaml trong cac thu muc theo thu tu; id trung giua cac file la loi."""
    topics: Dict[str, str] = {}
    for directory in dirs:
        directory = Path(directory)
        files = sorted(directory.glob("*.yaml"))
        if not files:
            raise CatalogError(f"khong co file *.yaml trong {directory}")
        for path in files:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for topic in data.get("topics") or []:
                topic_id, category = topic.get("id"), topic.get("category")
                if not topic_id or not category:
                    raise CatalogError(f"{path.name}: topic thieu id hoac category: {topic!r}")
                if topic_id in topics:
                    raise CatalogError(f"topic_id trung giua cac file catalog: {topic_id} ({path.name})")
                topics[topic_id] = category
    return topics
