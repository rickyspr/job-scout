from datetime import datetime

from ..models import Job


async def fetch(client, cfg, state):
    r = await client.get(f"https://api.ashbyhq.com/posting-api/job-board/{cfg['slug']}")
    r.raise_for_status()
    jobs = []
    for j in r.json()["jobs"]:
        if j.get("isListed") is False:
            continue
        locations = [j.get("location") or ""]
        locations += [s.get("location", "") for s in j.get("secondaryLocations") or []]
        if j.get("isRemote") or j.get("workplaceType") == "Remote":
            locations.append("Remote")
        jobs.append(
            Job(
                source=cfg["key"],
                company=cfg["name"],
                job_id=j["id"],
                title=j["title"],
                url=j["jobUrl"],
                location=", ".join(filter(None, locations)),
                description=" ".join(filter(None, [j.get("department"), j.get("team"), (j.get("descriptionPlain") or "")[:2000]])),
                posted=datetime.fromisoformat(j["publishedAt"]) if j.get("publishedAt") else None,
            )
        )
    return jobs
