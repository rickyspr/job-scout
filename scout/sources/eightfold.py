from datetime import datetime, timezone

from ..models import Job

PAGE = 10
MAX_PAGES = 20      # first fetch: everything (for the startup digest)
NEWEST_PAGES = 2    # later fetches: results are sorted newest first, so new jobs are on top


async def fetch(client, cfg, state):
    host, jobs = cfg["host"], []
    for page in range(NEWEST_PAGES if state.get("full_fetch_done") else MAX_PAGES):
        r = await client.get(
            f"https://{host}/api/pcsx/search",
            params={
                "domain": cfg["domain"],
                "query": cfg.get("query", ""),
                "location": cfg.get("location", "Sweden"),
                "start": page * PAGE,
                "sort_by": "timestamp",
            },
        )
        r.raise_for_status()
        data = r.json()["data"]
        for p in data["positions"]:
            jobs.append(
                Job(
                    source=cfg["key"],
                    company=cfg["name"],
                    job_id=str(p["id"]),
                    title=p["name"],
                    url=f"https://{host}{p['positionUrl']}",
                    location="; ".join(p.get("locations") or []) + (", Remote" if p.get("workLocationOption") == "remote" else ""),
                    description=p.get("department") or "",
                    posted=datetime.fromtimestamp(p["postedTs"], tz=timezone.utc) if p.get("postedTs") else None,
                )
            )
        if len(data["positions"]) < PAGE or (page + 1) * PAGE >= (data.get("count") or 0):
            break
    state["full_fetch_done"] = True
    return jobs
