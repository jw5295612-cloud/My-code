"""Website audit: finds concrete, pitchable problems with a business's web presence."""

import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

ISSUE_LABELS = {
    "no_website": "No website",
    "site_down": "Website doesn't load",
    "not_mobile_friendly": "Not mobile-friendly",
    "no_https": "Not secure (no HTTPS)",
    "slow": "Slow to load",
    "outdated": "Looks outdated (old copyright year)",
    "weak_seo": "Missing page title/description (hurts Google ranking)",
    "no_contact_form": "No contact or enquiry form",
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
YEAR_RE = re.compile(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", re.I)
SLOW_SECONDS = 4.0


def normalize_url(url: str) -> str:
    url = url.strip()
    if url and not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    return url


def analyze_html(html: str, final_url: str, elapsed: float) -> tuple[list[str], list[str]]:
    """Return (issues, emails) for a fetched page. Pure function, easy to test."""
    soup = BeautifulSoup(html, "html.parser")
    issues = []

    if not final_url.lower().startswith("https://"):
        issues.append("no_https")
    if not soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)}):
        issues.append("not_mobile_friendly")
    if elapsed > SLOW_SECONDS:
        issues.append("slow")

    years = [int(y) for y in YEAR_RE.findall(html)]
    if years and max(years) < date.today().year - 2:
        issues.append("outdated")

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    if not title or not soup.find("meta", attrs={"name": re.compile("^description$", re.I)}):
        issues.append("weak_seo")
    if not soup.find("form"):
        issues.append("no_contact_form")

    emails = set()
    for a in soup.find_all("a", href=True):
        if a["href"].lower().startswith("mailto:"):
            emails.add(a["href"][7:].split("?")[0])
    emails.update(EMAIL_RE.findall(soup.get_text(" ")))
    emails = sorted(e for e in emails if not e.lower().endswith((".png", ".jpg", ".webp")))
    return issues, emails


def audit(business: dict) -> dict:
    url = normalize_url(business.get("website", ""))
    result = {"checked_at": date.today().isoformat(), "url": url, "issues": [], "emails": []}
    if not url:
        result["issues"] = ["no_website"]
        return result
    try:
        start = time.monotonic()
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LocalScout/0.1)"},
        )
        elapsed = time.monotonic() - start
        if resp.status_code >= 400:
            result["issues"] = ["site_down"]
            return result
    except requests.RequestException:
        result["issues"] = ["site_down"]
        return result

    result["final_url"] = resp.url
    result["load_seconds"] = round(elapsed, 2)
    result["issues"], result["emails"] = analyze_html(resp.text, resp.url, elapsed)
    return result
