from datetime import datetime

from ..models import Job

PAGE = 100


async def fetch(client, cfg, state):
    slug = cfg["slug"]
    jobs, offset = [], 0
    params = {"limit": PAGE}
    if cfg.get("country"):
        params["country"] = cfg["country"]
    while True:
        r = await client.get(
            f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
            params={**params, "offset": offset},
        )
        r.raise_for_status()
        data = r.json()
        for j in data["content"]:
            loc = j.get("location") or {}
            location = loc.get("fullLocation") or ", ".join(filter(None, [loc.get("city"), loc.get("country")]))
            if loc.get("remote"):
                location += ", Remote"
            jobs.append(
                Job(
                    source=cfg["key"],
                    company=cfg["name"],
                    job_id=j["id"],
                    title=j["name"],
                    url=f"https://jobs.smartrecruiters.com/{slug}/{j['id']}",
                    location=location,
                    description=" ".join(filter(None, [(j.get("department") or {}).get("label"), (j.get("function") or {}).get("label")])),
                    posted=datetime.fromisoformat(j["releasedDate"].replace("Z", "+00:00")) if j.get("releasedDate") else None,
                )
            )
        offset += PAGE
        if offset >= data["totalFound"] or not data["content"]:
            return jobs
