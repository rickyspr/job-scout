from datetime import datetime

from ..models import Job


async def fetch(client, cfg, state):
    r = await client.get(f"https://boards-api.greenhouse.io/v1/boards/{cfg['slug']}/jobs")
    r.raise_for_status()
    return [
        Job(
            source=cfg["key"],
            company=cfg["name"],
            job_id=str(j["id"]),
            title=j["title"],
            url=j["absolute_url"],
            location=(j.get("location") or {}).get("name", ""),
            posted=_parse(j.get("first_published") or j.get("updated_at")),
        )
        for j in r.json()["jobs"]
    ]


def _parse(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except ValueError:
        return None
