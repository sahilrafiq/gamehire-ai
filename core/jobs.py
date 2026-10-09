"""
core/jobs.py
Aggregate job listings from free, ToS-friendly public APIs.

We deliberately do NOT scrape or auto-submit applications on LinkedIn, Indeed,
Workday, etc. Automating those sites violates their Terms of Service and can
get your account banned (and carries real legal risk). This module only reads
public, documented job-listing APIs. Add more sources (Greenhouse/Lever job
boards, USAJobs, etc.) the same way.
"""

import re

import requests

_STOPWORDS = {"a", "an", "the", "and", "or", "for", "in", "on", "at", "to",
              "of", "with", "remote", "job", "jobs"}


def _title_matches(title: str, query: str) -> bool:
    """Remotive/Adzuna search loosely matches descriptions, not just titles,
    so 'data analysis' can return unrelated postings. Client-side filter:
    require at least one meaningful query word in the job title."""
    title_l = (title or "").lower()
    tokens = [t for t in re.findall(r"[a-zA-Z]+", query.lower()) if t not in _STOPWORDS]
    return any(t in title_l for t in tokens) if tokens else True

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


def search_remotive(query: str, limit: int = 20) -> list[dict]:
    """No API key required. Remote jobs only."""
    try:
        resp = requests.get(REMOTIVE_URL, params={"search": query}, timeout=15)
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])[:limit]
    except requests.RequestException:
        return []
    return [
        {
            "title": j.get("title"),
            "company": j.get("company_name"),
            "location": j.get("candidate_required_location"),
            "url": j.get("url"),
            "source": "Remotive",
        }
        for j in jobs
    ]


def search_adzuna(query: str, app_id: str, app_key: str, country: str = "us",
                   location: str = "", limit: int = 20) -> list[dict]:
    """Free tier available at https://developer.adzuna.com — set ADZUNA_APP_ID
    and ADZUNA_APP_KEY in .env to enable. Covers on-site + remote roles."""
    if not app_id or not app_key:
        return []
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": query,
        "results_per_page": limit,
    }
    if location:
        params["where"] = location
    try:
        resp = requests.get(ADZUNA_URL.format(country=country), params=params, timeout=15)
        resp.raise_for_status()
        jobs = resp.json().get("results", [])
    except requests.RequestException:
        return []
    return [
        {
            "title": j.get("title"),
            "company": (j.get("company") or {}).get("display_name"),
            "location": (j.get("location") or {}).get("display_name"),
            "url": j.get("redirect_url"),
            "source": "Adzuna",
        }
        for j in jobs
    ]


def search_arbeitnow(query: str, limit: int = 20) -> list[dict]:
    """No API key required. Aggregates mostly tech/remote roles."""
    try:
        resp = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
        resp.raise_for_status()
        jobs = resp.json().get("data", [])
    except requests.RequestException:
        return []
    return [
        {
            "title": j.get("title"),
            "company": j.get("company_name"),
            "location": j.get("location") or ("Remote" if j.get("remote") else ""),
            "url": j.get("url"),
            "source": "Arbeitnow",
        }
        for j in jobs
    ][:limit]


def search_jooble(query: str, api_key: str, location: str = "", limit: int = 20) -> list[dict]:
    """Free key at https://jooble.org/api/about. Jooble is itself a
    meta-aggregator across thousands of job sites/boards -- the closest
    thing to 'search the whole web' via one clean, ToS-compliant API."""
    if not api_key:
        return []
    try:
        resp = requests.post(
            f"https://jooble.org/api/{api_key}",
            json={"keywords": query, "location": location},
            timeout=15,
        )
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])[:limit]
    except requests.RequestException:
        return []
    return [
        {
            "title": j.get("title"),
            "company": j.get("company"),
            "location": j.get("location"),
            "url": j.get("link"),
            "source": "Jooble",
        }
        for j in jobs
    ]


def search_all(query: str, adzuna_app_id: str = "", adzuna_app_key: str = "",
                jooble_api_key: str = "", location: str = "") -> list[dict]:
    results = search_remotive(query)
    results += search_adzuna(query, adzuna_app_id, adzuna_app_key, location=location)
    results += search_arbeitnow(query)
    results += search_jooble(query, jooble_api_key, location=location)
    return [r for r in results if _title_matches(r.get("title", ""), query)]
