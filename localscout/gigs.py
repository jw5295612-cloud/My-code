"""Gig scout: public posts from people asking for the services you sell.

Sources: Reddit hiring subreddits, Hacker News' monthly "Seeking freelancer"
thread, and any RSS feeds you add. The agent drafts a reply; you post it
yourself (automated replies would break those sites' rules).
"""

import os
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup

from .config import user_agent

BUDGET_RE = re.compile(
    r"([$£€₦]\s?\d[\d,]*(?:\.\d+)?\s?[kK]?|\d[\d,]*\s?(?:usd|dollars|gbp|eur)\b)", re.I
)
MAX_TEXT = 1500


def _gig(source, ext_id, title, text, url, author, posted_at) -> dict:
    return {
        "id": f"gig:{source}/{ext_id}",
        "kind": "gig",
        "source": source,
        "title": title.strip()[:200],
        "text": text.strip()[:MAX_TEXT],
        "url": url,
        "author": author,
        "posted_at": int(posted_at),
    }


# --- Reddit ------------------------------------------------------------------

def _reddit_session(cfg: dict) -> tuple[requests.Session, str]:
    """Use OAuth when REDDIT_CLIENT_ID/SECRET are set (reliable from CI), else public JSON."""
    s = requests.Session()
    s.headers["User-Agent"] = user_agent(cfg)
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if cid and secret:
        resp = s.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(cid, secret),
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        resp.raise_for_status()
        s.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
        return s, "https://oauth.reddit.com"
    return s, "https://www.reddit.com"


def parse_reddit_listing(listing: dict, sub: str) -> list[dict]:
    gigs = []
    for child in listing.get("data", {}).get("children", []):
        d = child["data"]
        gigs.append(
            _gig(
                "reddit",
                d["id"],
                d.get("title", ""),
                d.get("selftext", ""),
                "https://www.reddit.com" + d.get("permalink", ""),
                f"u/{d.get('author', '')} in r/{sub}",
                d.get("created_utc", 0),
            )
        )
    return gigs


def reddit(cfg: dict) -> list[dict]:
    session, base = _reddit_session(cfg)
    gigs = []
    for sub in cfg["gigs"]["subreddits"]:
        resp = session.get(f"{base}/r/{sub}/new.json", params={"limit": 50}, timeout=30)
        if resp.status_code != 200:
            print(f"  [reddit] r/{sub}: HTTP {resp.status_code}")
            continue
        gigs += parse_reddit_listing(resp.json(), sub)
        time.sleep(1)
    return gigs


# --- Hacker News ---------------------------------------------------------------

def parse_hn_thread(item: dict) -> list[dict]:
    gigs = []
    for c in item.get("children", []):
        text = BeautifulSoup(c.get("text") or "", "html.parser").get_text(" ")
        if "SEEKING FREELANCER" not in text.upper():
            continue
        gigs.append(
            _gig(
                "hn",
                c["id"],
                text.split("\n")[0][:120],
                text,
                f"https://news.ycombinator.com/item?id={c['id']}",
                c.get("author", ""),
                c.get("created_at_i", 0),
            )
        )
    return gigs


def hacker_news(cfg: dict) -> list[dict]:
    resp = requests.get(
        "https://hn.algolia.com/api/v1/search_by_date",
        params={"tags": "story,author_whoishiring", "query": "freelancer", "hitsPerPage": 1},
        timeout=30,
    )
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    if not hits:
        return []
    item = requests.get(f"https://hn.algolia.com/api/v1/items/{hits[0]['objectID']}", timeout=60)
    item.raise_for_status()
    return parse_hn_thread(item.json())


# --- RSS -----------------------------------------------------------------------

def parse_rss(xml_text: str, feed_url: str) -> list[dict]:
    gigs = []
    for item in ET.fromstring(xml_text).iter("item"):
        link = item.findtext("link") or feed_url
        pub = item.findtext("pubDate")
        posted = parsedate_to_datetime(pub).timestamp() if pub else time.time()
        desc = BeautifulSoup(item.findtext("description") or "", "html.parser").get_text(" ")
        gigs.append(
            _gig("rss", re.sub(r"\W+", "-", link)[-80:], item.findtext("title") or "", desc, link, "", posted)
        )
    return gigs


def rss(cfg: dict) -> list[dict]:
    gigs = []
    for url in cfg["gigs"].get("rss_feeds") or []:
        resp = requests.get(url, headers={"User-Agent": user_agent(cfg)}, timeout=30)
        if resp.ok:
            gigs += parse_rss(resp.text, url)
    return gigs


# --- Matching and scoring ------------------------------------------------------

def match_services(gig: dict, cfg: dict) -> list[str]:
    text = f"{gig['title']} {gig['text']}".lower()
    if any(k.lower() in text for k in cfg["gigs"]["exclude_keywords"]):
        return []
    return [
        key
        for key, svc in cfg["services"].items()
        if any(re.search(rf"\b{re.escape(k.lower())}", text) for k in svc["keywords"])
    ]


def score_gig(gig: dict, cfg: dict, now: float | None = None) -> int:
    now = now or time.time()
    max_age = cfg["gigs"]["max_age_hours"] * 3600
    age = max(now - gig["posted_at"], 0)
    freshness = max(0.0, 1 - age / max_age) * 30  # early replies win gigs
    budget = 20 if gig.get("budget") else 0
    hiring = 10 if "hiring" in gig["title"].lower() else 0
    fit = min(len(gig["services"]), 2) * 20
    return round(min(fit + budget + hiring + freshness, 100))


def find_gigs(cfg: dict) -> list[dict]:
    found = []
    for name, fetch in (("reddit", reddit), ("hacker news", hacker_news), ("rss", rss)):
        if name == "hacker news" and not cfg["gigs"].get("hacker_news"):
            continue
        try:
            found += fetch(cfg)
        except Exception as e:  # one broken source shouldn't stop the run
            print(f"  [{name}] failed: {e}")

    cutoff = time.time() - cfg["gigs"]["max_age_hours"] * 3600
    matched = []
    for gig in found:
        if gig["posted_at"] < cutoff:
            continue
        gig["services"] = match_services(gig, cfg)
        if not gig["services"]:
            continue
        budget = BUDGET_RE.search(f"{gig['title']} {gig['text']}")
        gig["budget"] = budget.group(0).strip() if budget else None
        gig["score"] = score_gig(gig, cfg)
        matched.append(gig)
    return matched
