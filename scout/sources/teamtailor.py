import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from ..models import Job, strip_html

TT_NS = "{https://teamtailor.com/locations}"


async def fetch(client, cfg, state):
    base = cfg.get("url") or f"https://{cfg['slug']}.teamtailor.com"
    r = await client.get(f"{base.rstrip('/')}/jobs.rss")
    r.raise_for_status()
    root = ET.fromstring(r.content)
    jobs = []
    for item in root.iter("item"):
        link = item.findtext("link", "")
        locations = [
            ", ".join(filter(None, [loc.findtext(f"{TT_NS}city"), loc.findtext(f"{TT_NS}country")]))
            for loc in item.iter(f"{TT_NS}location")
        ]
        remote = item.findtext("remoteStatus") or item.findtext(f"{TT_NS}remoteStatus") or ""
        if remote and remote.lower() not in ("none", "no"):
            locations.append(f"Remote ({remote})")
        pub = item.findtext("pubDate")
        jobs.append(
            Job(
                source=cfg["key"],
                company=cfg["name"],
                job_id=item.findtext("guid") or link,
                title=(item.findtext("title") or "").strip(),
                url=link,
                location=", ".join(filter(None, locations)),
                description=" ".join(filter(None, [item.findtext(f"{TT_NS}department"), strip_html(item.findtext("description"))[:2000]])),
                posted=parsedate_to_datetime(pub) if pub else None,
            )
        )
    return jobs
