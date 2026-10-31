"""Job sources. Each module exposes `async def fetch(client, cfg, state) -> list[Job]`.

`cfg` is the source entry from sources.yaml (always has `key`, `name`, `type`).
`state` is a per-source dict persisted between polls (e.g. cursors).
"""
from . import (
    ashby,
    deel,
    earlycareers,
    eightfold,
    greenhouse,
    jobstream,
    jobylon,
    lever,
    saab,
    smartrecruiters,
    successfactors,
    teamtailor,
    thehub,
    workday,
)

FETCHERS = {
    "ashby": ashby.fetch,
    "deel": deel.fetch,
    "earlycareers": earlycareers.fetch,
    "eightfold": eightfold.fetch,
    "greenhouse": greenhouse.fetch,
    "jobstream": jobstream.fetch,
    "jobylon": jobylon.fetch,
    "lever": lever.fetch,
    "saab": saab.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "successfactors": successfactors.fetch,
    "teamtailor": teamtailor.fetch,
    "thehub": thehub.fetch,
    "workday": workday.fetch,
}
