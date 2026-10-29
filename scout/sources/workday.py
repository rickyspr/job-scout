"""Workday career sites (myworkdayjobs.com) via the JSON API the site itself uses.

Workday sorts by relevance, not date, so instead of paging through every job we run a few
targeted searches (summer/intern/...) and take the top results of each.
"""
from ..models import Job

DEFAULT_QUERIES = ["summer", "sommar", "intern", "praktik", "student"]


async def fetch(client, cfg, state):
    tenant, wd, site = cfg["tenant"], cfg["wd"], cfg["site"]
    base = f"https://{tenant}.{wd}.myworkdayjobs.com"
    jobs = {}
    for q in cfg.get("queries", DEFAULT_QUERIES):
        r = await client.post(
            f"{base}/wday/cxs/{tenant}/{site}/jobs",
            json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q},
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        for p in r.json().get("jobPostings", []):
            path = p.get("externalPath")
            if not path or path in jobs:
                continue
            jobs[path] = Job(
                source=cfg["key"],
                company=cfg["name"],
                job_id=path,
                title=p.get("title", ""),
                url=f"{base}/{site}{path}",
                location=p.get("locationsText", ""),
                extra={"posted_text": p.get("postedOn", "")},
            )
    return list(jobs.values())
