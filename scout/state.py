"""Persistent state in state/*.json (committed back to the repo when running in GitHub Actions)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEEN_TTL = timedelta(days=180)


def _now():
    return datetime.now(timezone.utc)


class State:
    def __init__(self, directory: str | Path = "state"):
        self.dir = Path(directory)
        self.seen: dict[str, str] = self._read("seen.json")
        self.sources: dict[str, dict] = self._read("sources.json")
        self._seen_dirty = False

    def _read(self, name):
        path = self.dir / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def _write(self, name, data):
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.dir / f"{name}.tmp"
        tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.dir / name)

    def source(self, key: str) -> dict:
        return self.sources.setdefault(key, {"initialized": False, "fails": 0, "alerted": False, "data": {}})

    def is_seen(self, uid: str) -> bool:
        return uid in self.seen

    def mark_seen(self, job):
        now = _now().isoformat(timespec="seconds")
        self.seen[job.uid] = self.seen[job.fingerprint] = now
        self._seen_dirty = True

    def save(self) -> bool:
        """Write state to disk. Returns True if the seen-set changed since the last save."""
        cutoff = _now() - SEEN_TTL
        for uid, ts in list(self.seen.items()):
            if datetime.fromisoformat(ts) < cutoff:
                del self.seen[uid]
        self._write("seen.json", self.seen)
        self._write("sources.json", self.sources)
        changed, self._seen_dirty = self._seen_dirty, False
        return changed
