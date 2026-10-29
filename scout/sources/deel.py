"""Deel job boards (jobs.deel.com). Job postings are embedded in the Next.js RSC payload."""
import json
from datetime import datetime

from ..models import Job


async def fetch(client, cfg, state):
    board = f"https://jobs.deel.com/job-boards/{cfg['slug']}"
    r = await client.get(board)
    r.raise_for_status()
    text = r.text.replace('\\"', '"').replace("\\\\", "\\")
    start = text.find('"jobPostings":[')
    if start < 0:
        raise ValueError("Deel page format changed: jobPostings not found")
    postings, _ = json.JSONDecoder().raw_decode(text, start + len('"jobPostings":'))
    jobs = []
    for p in postings:
        job = p.get("job") or {}
        locations = []
        for jl in job.get("jobLocations") or []:
            loc = jl.get("location") or {}
            locations.append(", ".join(filter(None, [loc.get("name"), (loc.get("country") or {}).get("name")])))
        if job.get("workArrangementEnum") == "REMOTE":
            locations.append("Remote")
        jobs.append(
            Job(
                source=cfg["key"],
                company=cfg["name"],
                job_id=p["id"],
                title=p["title"].strip(),
                url=f"{board}/{p['id']}",
                location="; ".join(locations),
                posted=datetime.fromisoformat(p["createdAt"].replace("Z", "+00:00")) if p.get("createdAt") else None,
            )
        )
    return jobs
