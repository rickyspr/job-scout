"""Jobylon embed widget. The widget page embeds the job list as a JS object literal, parsed with regexes."""
import re

from ..models import Job

JOB_RE = re.compile(
    r"\{\s*id: '(?P<id>\d+)',\s*url: '(?P<url>[^']*)',\s*title: '(?P<title>(?:\\'|[^'])*)'"
    r".*?locations: \[(?P<locs>.*?)\]",
    re.S,
)


def _unescape(s):
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), s)
    return s.replace("\\'", "'")


async def fetch(client, cfg, state):
    r = await client.get(
        f"https://cdn.jobylon.com/jobs/companies/{cfg['company_id']}/embed/v2/", params={"page_size": 200}
    )
    r.raise_for_status()
    start = r.text.find("JBL.embed_v2['jobs']")
    if start < 0:
        raise ValueError("Jobylon widget format changed: jobs array not found")
    jobs = []
    for m in JOB_RE.finditer(r.text, start):
        locs = re.findall(r"'((?:\\'|[^'])+)'", m["locs"])
        jobs.append(
            Job(
                source=cfg["key"],
                company=cfg["name"],
                job_id=m["id"],
                title=_unescape(m["title"]),
                url=f"https://emp.jobylon.com{m['url']}",
                location=", ".join(_unescape(l) for l in locs),
            )
        )
    return jobs
