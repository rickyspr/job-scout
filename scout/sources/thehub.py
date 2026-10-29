"""The Hub (thehub.io), Nordic startup jobs. Parses the server-rendered job list (newest first)."""
import html
import re

from ..models import Job

CARD_RE = re.compile(
    r'card-job-find-list__position">(?P<title>.*?)</span>\s*'
    r'<div class="bullet-inline-list[^>]*>(?P<meta>.*?)</div>.*?'
    r'<a href="/jobs/(?P<id>[0-9a-f]{24})"',
    re.S,
)


async def fetch(client, cfg, state):
    jobs = {}
    for page in range(1, cfg.get("pages", 3) + 1):
        r = await client.get(
            "https://thehub.io/jobs",
            params={"countryCode": cfg.get("country", "SE"), "sorting": "newJobs", "page": page},
        )
        r.raise_for_status()
        cards = list(CARD_RE.finditer(r.text))
        if page == 1 and not cards:
            raise ValueError("The Hub page format changed: no job cards found")
        for m in cards:
            meta = [html.unescape(s) for s in re.findall(r"<span>(.*?)</span>", m["meta"])]
            jobs[m["id"]] = Job(
                source=cfg["key"],
                company=meta[0] if meta else "Startup",
                job_id=m["id"],
                title=html.unescape(m["title"]).strip(),
                url=f"https://thehub.io/jobs/{m['id']}",
                location=meta[1] if len(meta) > 1 else "",
                description=" ".join(meta[2:]),
            )
    return list(jobs.values())
