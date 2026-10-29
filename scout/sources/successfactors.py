"""SAP SuccessFactors career sites (e.g. jobs.scania.com) via their built-in RSS search feed."""
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from ..models import Job, strip_html

DEFAULT_QUERIES = ["sommarjobb", "summer", "sommar", "intern", "praktik"]


async def fetch(client, cfg, state):
    base = cfg["url"].rstrip("/")
    jobs = {}
    for q in cfg.get("queries", DEFAULT_QUERIES):
        r = await client.get(f"{base}/services/rss/job/", params={"locale": cfg.get("locale", "sv_SE"), "keywords": q})
        r.raise_for_status()
        for item in ET.fromstring(r.content).iter("item"):
            link = item.findtext("link", "")
            if link.rstrip("/") == base:  # "no jobs available" placeholder item
                continue
            title = item.findtext("title") or ""
            pub = item.findtext("pubDate")
            jobs[link] = Job(
                source=cfg["key"],
                company=cfg["name"],
                job_id=link,
                title=title.split(" (")[0].strip(),
                url=link,
                location=title.split(" (")[1].rstrip(")") if " (" in title else "",
                description=strip_html(item.findtext("description"))[:2000],
                posted=parsedate_to_datetime(pub) if pub else None,
            )
    return list(jobs.values())
