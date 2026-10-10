"""
core/jobs.py
Aggregate job listings from free, public job-listing APIs (Remotive, Adzuna,
Arbeitnow, Jooble). This module only READS documented public APIs; it does not
scrape any site. (Auto-apply lives separately in core/applier.py -- see the
warning there about job-board Terms of Service.)
"""

import html
import os
import re

import requests

_STOPWORDS = {"a", "an", "the", "and", "or", "for", "in", "on", "at", "to",
              "of", "with", "remote", "job", "jobs"}
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(value) -> str:
    """Strip HTML tags/entities (Jooble etc. return '<b>Data</b> Analyst')."""
    if not value:
        return ""
    return " ".join(html.unescape(_TAG_RE.sub("", str(value))).split())


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
    except (requests.RequestException, ValueError):
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
    """Free tier available at https://developer.adzuna.com -- set ADZUNA_APP_ID
    and ADZUNA_APP_KEY in .env to enable. Covers on-site + remote roles.
    `country` is a 2-letter code (us, gb, in, ca, au, ...)."""
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
        resp = requests.get(ADZUNA_URL.format(country=country.lower()), params=params, timeout=15)
        resp.raise_for_status()
        jobs = resp.json().get("results", [])
    except (requests.RequestException, ValueError):
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
    """No API key required. Aggregates mostly tech/remote roles. The API has no
    search parameter, so filter by query BEFORE applying the limit (otherwise
    the first N unrelated listings are taken and then filtered away)."""
    try:
        resp = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
        resp.raise_for_status()
        jobs = resp.json().get("data", [])
    except (requests.RequestException, ValueError):
        return []
    jobs = [j for j in jobs if _title_matches(j.get("title", ""), query)][:limit]
    return [
        {
            "title": j.get("title"),
            "company": j.get("company_name"),
            "location": j.get("location") or ("Remote" if j.get("remote") else ""),
            "url": j.get("url"),
            "source": "Arbeitnow",
        }
        for j in jobs
    ]


def search_jooble(query: str, api_key: str, location: str = "", limit: int = 20) -> list[dict]:
    """Free key at https://jooble.org/api/about. Jooble is itself a
    meta-aggregator across thousands of job sites/boards."""
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
    except (requests.RequestException, ValueError):
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
                jooble_api_key: str = "", location: str = "", country: str = "") -> list[dict]:
    country = country or os.getenv("ADZUNA_COUNTRY", "us")
    results = search_remotive(query)
    results += search_adzuna(query, adzuna_app_id, adzuna_app_key, country=country, location=location)
    results += search_arbeitnow(query)
    results += search_jooble(query, jooble_api_key, location=location)

    cleaned, seen = [], set()
    for r in results:
        url = (r.get("url") or "").strip()
        title = _clean(r.get("title"))
        # The UI needs a title and a real http(s) link; also blocks javascript: URLs.
        if not title or not url.lower().startswith(("http://", "https://")):
            continue
        if url in seen or not _title_matches(title, query):
            continue
        seen.add(url)
        cleaned.append({
            "title": title,
            "company": _clean(r.get("company")),
            "location": _clean(r.get("location")),
            "url": url,
            "source": r.get("source", ""),
        })
    return cleaned
