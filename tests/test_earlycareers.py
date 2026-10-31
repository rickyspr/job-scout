import asyncio

import httpx

from scout.sources import earlycareers


def row(n):
    return {"link": f"https://www.linkedin.com/jobs/view/{n}", "title": "software engineer intern",
            "location": "stockholm, stockholm county, sweden", "company": "acme", "description": None,
            "employment_type": "internship", "seniority_level": "internship", "job_function": None, "industries": None}


def test_fetch_reads_pages_until_a_short_one():
    params = []

    def handler(request):
        params.append(request.url.params)
        page = int(request.url.params["page"])
        return httpx.Response(200, json=[row(page * 1000 + i) for i in range(100 if page < 3 else 42)])

    async def fetch():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await earlycareers.fetch(client, {"key": "earlycareers", "name": "EarlyCareers"}, {})

    jobs = asyncio.run(fetch())
    assert len(jobs) == 242
    assert [p["page"] for p in params] == ["1", "2", "3"]
    assert params[0].get_list("location") == ["sweden", "stockholm"]
    assert jobs[0].uid == "earlycareers:1000"
    assert jobs[0].url == "https://www.linkedin.com/jobs/view/1000"
    assert jobs[0].description == ""
