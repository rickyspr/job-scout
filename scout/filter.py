from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import Job


def _compile(patterns):
    return [re.compile(p, re.IGNORECASE) for p in patterns or []]


def _any(patterns, text):
    return any(p.search(text) for p in patterns)


@dataclass
class JobFilter:
    job_type: list
    exclude_title: list
    non_tech_title: list
    locations: list
    remote: list
    unspecific_locations: list
    tech: list
    tech_min_description_hits: int = 2

    @classmethod
    def load(cls, path: str | Path) -> "JobFilter":
        cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(
            job_type=_compile(cfg.get("job_type")),
            exclude_title=_compile(cfg.get("exclude_title")),
            non_tech_title=_compile(cfg.get("non_tech_title")),
            locations=_compile(re.escape(l) for l in cfg.get("locations") or []),
            remote=_compile(cfg.get("remote")),
            unspecific_locations=_compile(cfg.get("unspecific_locations")),
            tech=_compile(cfg.get("tech")),
            tech_min_description_hits=int(cfg.get("tech_min_description_hits", 2)),
        )

    def location_ok(self, location: str) -> bool:
        loc = location.strip()
        if not loc:
            return True
        if _any(self.locations, loc) or _any(self.remote, loc):
            return True
        parts = [p.strip() for p in re.split(r"[;,|/]", loc) if p.strip()]
        return all(_any(self.unspecific_locations, p) for p in parts)

    def is_tech(self, job: Job) -> bool:
        if _any(self.tech, f"{job.title} {job.extra.get('category', '')}"):
            return True
        return sum(1 for p in self.tech if p.search(job.description)) >= self.tech_min_description_hits

    def matches(self, job: Job, require_tech: bool = False) -> bool:
        title = job.title
        if not _any(self.job_type, title):
            return False
        if _any(self.exclude_title, title) or _any(self.non_tech_title, title):
            return False
        if not self.location_ok(job.location):
            return False
        return not require_tech or self.is_tech(job)
