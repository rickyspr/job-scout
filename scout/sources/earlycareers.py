"""EarlyCareers (earlycareers.fabifont.dev), the database behind github.com/LorenzoLaCorte/european-tech-internships-2026.

LinkedIn jobs from a weekly scrape of European tech internships, new grad and PhD roles, unfiltered and
with the full ad text. Days behind the companies' own sites, but covers companies not in sources.yaml.
The table is emptied on the 1st of every month and refilled during the following week.
"""
import re

from ..models import Job

URL = "https://earlycareers.fabifont.dev/api/jobs/advanced"
PAGE_SIZE = 100  # API maximum
MAX_PAGES = 20
# LinkedIn sometimes drops the country, e.g. "greater stockholm metropolitan area, worldwide"
DEFAULT_LOCATIONS = ["sweden", "stockholm"]


async def fetch(client, cfg, state):
    jobs = {}
    for page in range(1, MAX_PAGES + 1):
        r = await client.get(URL, params={
            "location": cfg.get("locations", DEFAULT_LOCATIONS), "page": page, "limit": PAGE_SIZE,
        })
        r.raise_for_status()
        rows = r.json()
        for j in rows:
            m = re.search(r"(\d+)/?$", j["link"])
            job_id = m[1] if m else j["link"]
            jobs[job_id] = Job(
                source=cfg["key"],
                company=j["company"],
                job_id=job_id,
                title=j["title"],
                url=j["link"],
                location=j["location"],
                description=j.get("description") or "",
            )
        if len(rows) < PAGE_SIZE:
            return list(jobs.values())
    raise ValueError(f"EarlyCareers returned more than {MAX_PAGES} pages, narrow `locations`")
