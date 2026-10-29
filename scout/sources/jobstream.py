"""Arbetsförmedlingen / JobTech. Platsbanken plus ads aggregated from other Swedish job sites.

Normal polls read the JobStream change feed since the last successful poll.
The first poll (no cursor yet) instead searches currently open ads, so the startup digest
covers what is already out there.
"""
from datetime import datetime, timedelta, timezone

from ..models import Job

STREAM_URL = "https://jobstream.api.jobtechdev.se/v2/stream"
SEARCH_URL = "https://jobsearch.api.jobtechdev.se/search"
OVERLAP = timedelta(minutes=5)
BACKFILL_QUERIES = ["sommarjobb", "sommar", "summer", "internship", "intern", "praktik", "praktikant", "sommarpraktik"]
HEADERS = {"accept": "application/json"}


async def fetch(client, cfg, state):
    now = datetime.now(timezone.utc)
    if "cursor" not in state:
        jobs = await _backfill(client, cfg)
    else:
        since = datetime.fromisoformat(state["cursor"]) - OVERLAP
        r = await client.get(
            STREAM_URL,
            params={"updated-after": since.strftime("%Y-%m-%dT%H:%M:%S")},
            headers=HEADERS,
            timeout=60,
        )
        r.raise_for_status()
        jobs = [_to_job(cfg, ad) for ad in r.json() if not ad.get("removed")]
    state["cursor"] = now.isoformat()
    return jobs


async def _backfill(client, cfg):
    seen = {}
    for q in BACKFILL_QUERIES:
        r = await client.get(SEARCH_URL, params={"q": q, "limit": 100}, headers=HEADERS, timeout=60)
        r.raise_for_status()
        for ad in r.json()["hits"]:
            seen[ad["id"]] = _to_job(cfg, ad)
    return list(seen.values())


def _to_job(cfg, ad):
    addr = ad.get("workplace_address") or {}
    employer = ad.get("employer") or {}
    apply = (ad.get("application_details") or {}).get("url")
    location = ", ".join(filter(None, [addr.get("city"), addr.get("municipality"), addr.get("region"), addr.get("country")]))
    occupation = " ".join(
        filter(None, [(ad.get(k) or {}).get("label") for k in ("occupation", "occupation_group", "occupation_field")])
    )
    return Job(
        source=cfg["key"],
        company=employer.get("workplace") or employer.get("name") or "Okänd arbetsgivare",
        job_id=str(ad["id"]),
        title=ad.get("headline") or "",
        url=ad.get("webpage_url") or apply or "",
        location=location,
        description=((ad.get("description") or {}).get("text") or "")[:3000],
        posted=datetime.fromisoformat(ad["publication_date"]) if ad.get("publication_date") else None,
        extra={"category": occupation, **({"apply_url": apply} if apply else {})},
    )
