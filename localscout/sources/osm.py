"""OpenStreetMap source: free, worldwide, no API key."""

import time

import requests

from ..config import user_agent

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def geocode_bbox(city: str, cfg: dict) -> tuple[float, float, float, float] | None:
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": city, "format": "json", "limit": 1},
        headers={"User-Agent": user_agent(cfg)},
        timeout=30,
    )
    resp.raise_for_status()
    time.sleep(1)  # Nominatim policy: max 1 request per second
    results = resp.json()
    if not results:
        return None
    south, north, west, east = map(float, results[0]["boundingbox"])
    return south, west, north, east


def build_query(bbox, tags) -> str:
    s, w, n, e = bbox
    selectors = "".join(f'nwr["{k}"="{v}"]({s},{w},{n},{e});' for k, v in tags)
    return f"[out:json][timeout:90];({selectors});out center tags;"


def element_to_business(el: dict, city: str) -> dict | None:
    tags = el.get("tags", {})
    name = tags.get("name")
    if not name:
        return None
    address = " ".join(
        tags[k] for k in ("addr:housenumber", "addr:street", "addr:city") if tags.get(k)
    )
    return {
        "id": f"osm:{el['type']}/{el['id']}",
        "name": name,
        "city": city,
        "address": address,
        "phone": tags.get("phone") or tags.get("contact:phone") or "",
        "email": tags.get("email") or tags.get("contact:email") or "",
        "website": tags.get("website") or tags.get("contact:website") or tags.get("url") or "",
        "rating": None,
        "reviews": None,
        "source": "openstreetmap",
    }


def search(city: str, cfg: dict) -> list[dict]:
    bbox = geocode_bbox(city, cfg)
    if not bbox:
        print(f"  [osm] could not geocode {city!r}")
        return []
    resp = requests.post(
        OVERPASS_URL,
        data={"data": build_query(bbox, cfg["niche"]["osm_tags"])},
        headers={"User-Agent": user_agent(cfg)},
        timeout=120,
    )
    resp.raise_for_status()
    businesses = [element_to_business(el, city) for el in resp.json().get("elements", [])]
    return [b for b in businesses if b]
