"""Job sources. Each module exposes `async def fetch(client, cfg, state) -> list[Job]`.

`cfg` is the source entry from sources.yaml (always has `key`, `name`, `type`).
`state` is a per-source dict persisted between polls (e.g. cursors).
"""
from . import (
    ashby,
    deel,
    eightfold,
    greenhouse,
    jobstream,
    jobylon,
    lever,
    smartrecruiters,
    successfactors,
    teamtailor,
    thehub,
    workday,
)

FETCHERS = {
    "ashby": ashby.fetch,
    "deel": deel.fetch,
    "eightfold": eightfold.fetch,
    "greenhouse": greenhouse.fetch,
    "jobstream": jobstream.fetch,
    "jobylon": jobylon.fetch,
    "lever": lever.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "successfactors": successfactors.fetch,
    "teamtailor": teamtailor.fetch,
    "thehub": thehub.fetch,
    "workday": workday.fetch,
}
