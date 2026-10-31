"""saab.com career page. Server-rendered list of all Saab group jobs (incl. Combitech).

Used instead of Saab's Workday site, which has been unreliable.
"""
import html
import re

from ..models import Job

BASE = "https://www.saab.com"
ITEM_RE = re.compile(
    r'<div class="type">(?P<type>.*?)</div>\s*<div class="location">(?P<loc>.*?)</div>.*?'
    r'<a href="(?P<path>/career/job-opportunities/[^"]+)">(?P<title>[^<]*)',
    re.S,
)


async def fetch(client, cfg, state):
    r = await client.get(f"{BASE}/career/job-opportunities")
    r.raise_for_status()
    jobs = {}
    for m in ITEM_RE.finditer(r.text):
        jobs[m["path"]] = Job(
            source=cfg["key"],
            company=cfg["name"],
            job_id=m["path"].rsplit("/", 1)[-1],
            title=html.unescape(m["title"]).strip(),
            url=BASE + m["path"],
            location=html.unescape(m["loc"]).strip(),
            description=html.unescape(m["type"]).strip(),
        )
    if not jobs:
        raise ValueError("saab.com page format changed: no jobs found")
    return list(jobs.values())
