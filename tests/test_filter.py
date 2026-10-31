from pathlib import Path

import pytest

from scout.filter import JobFilter
from scout.models import Job

FILTER = JobFilter.load(Path(__file__).resolve().parent.parent / "filters.yaml")


def job(title, location="Stockholm", description="", **extra):
    return Job(source="t", company="Acme", job_id="1", title=title, url="https://x", location=location,
               description=description, extra=extra)


@pytest.mark.parametrize("title", [
    "Summer Internship 2027 Stockholm R&D",
    "Sommarjobb Scania Sverige 2027",
    "Software Engineer Intern",
    "Ericsson Innovation Hub Internship",
    "Praktikant inom IT",
    "Sommarpraktik – backend",
    "Summer job 2027 for university/college students",
])
def test_matches_internship_titles(title):
    assert FILTER.matches(job(title))


@pytest.mark.parametrize("title", [
    "Systemingenjör till intern IT med fokus på AI",   # Swedish "intern" = internal
    "International Sales Manager",
    "Internal Communications Lead",
    "Master Thesis: Spec-to-Code AI Development",
    "Exjobb inom radar",
    "Content Marketing Intern",
    "Senior Backend Engineer",
    "Co-Op, Supply Chain Spring & Summer 2027",
    "phd ai/ml research engineer intern",
    "PhD Research Intern",
    "Ph.D. Summer Internship",
])
def test_rejects(title):
    assert not FILTER.matches(job(title))


@pytest.mark.parametrize("location,ok", [
    ("Stockholm,Stockholm,Sweden", True),
    ("Solna, Stockholms län, Sverige", True),
    ("Linköping", True),
    ("Norrköping, Östergötlands län", True),
    ("Södertälje", True),
    ("Remote", True),
    ("Gothenburg, Remote", True),
    ("", True),
    ("Sweden", True),
    ("Sweden, Multiple Locations, Multiple Locations", True),
    ("3 Locations", True),
    ("greater stockholm metropolitan area, worldwide", True),   # LinkedIn
    ("Göteborg,Västra Götaland,Sweden", False),
    ("gothenburg, västra götaland county, sweden", False),
    ("Lund", False),
    ("London, United Kingdom", False),
])
def test_location(location, ok):
    assert FILTER.location_ok(location) is ok


def test_require_tech():
    assert FILTER.matches(job("Sommarjobb", category="Data/IT Mjukvaruutvecklare"), require_tech=True)
    assert FILTER.matches(job("Summer intern", description="Backend development with Python, cloud and DevOps"), require_tech=True)
    assert not FILTER.matches(job("Sommarjobb inom hemtjänst", description="Du hjälper äldre"), require_tech=True)
    # a single passing mention in the description isn't enough
    assert not FILTER.matches(job("Sommarjobb vård", description="Vi använder IT-stöd"), require_tech=True)


def test_fingerprint_matches_across_sources():
    a = Job(source="jobstream", company="Ericsson AB", job_id="1", title="AI Learning Solutions Intern", url="")
    b = Job(source="ericsson", company="Ericsson", job_id="2", title="AI Learning Solutions Intern ", url="")
    assert a.fingerprint == b.fingerprint
