from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", text)).strip()


@dataclass
class Job:
    source: str          # source key from sources.yaml, e.g. "spotify"
    company: str
    job_id: str          # id unique within the source
    title: str
    url: str
    location: str = ""
    description: str = ""  # plain text, may be empty if the source doesn't expose it
    posted: datetime | None = None
    extra: dict = field(default_factory=dict)

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.job_id}"

    @property
    def fingerprint(self) -> str:
        """Source-independent key, so the same ad from e.g. JobStream and the company's own ATS
        only triggers one notification."""
        company = _norm(self.company).split(" ")[0]
        return f"~{company}:{_norm(self.title)}"


def _norm(s: str) -> str:
    return _WS_RE.sub(" ", re.sub(r"[^\w ]", " ", s.lower())).strip()
