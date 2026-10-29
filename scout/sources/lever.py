from datetime import datetime, timezone

from ..models import Job


async def fetch(client, cfg, state):
    host = "api.eu.lever.co" if cfg.get("region") == "eu" else "api.lever.co"
    r = await client.get(f"https://{host}/v0/postings/{cfg['slug']}", params={"mode": "json"})
    r.raise_for_status()
    jobs = []
    for j in r.json():
        cats = j.get("categories") or {}
        locations = cats.get("allLocations") or [cats.get("location") or ""]
        if j.get("workplaceType") == "remote":
            locations.append("Remote")
        jobs.append(
            Job(
                source=cfg["key"],
                company=cfg["name"],
                job_id=j["id"],
                title=j["text"],
                url=j["hostedUrl"],
                location=", ".join(filter(None, locations)),
                description=" ".join(filter(None, [cats.get("team"), cats.get("department"), j.get("descriptionPlain", "")[:2000]])),
                posted=datetime.fromtimestamp(j["createdAt"] / 1000, tz=timezone.utc) if j.get("createdAt") else None,
            )
        )
    return jobs
