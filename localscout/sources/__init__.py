import os

from . import google_places, osm


def find_businesses(city: str, cfg: dict) -> list[dict]:
    """Collect businesses from every configured source, merged by name."""
    found = osm.search(city, cfg)
    if os.environ.get("GOOGLE_PLACES_API_KEY"):
        found += google_places.search(city, cfg)

    merged: dict[str, dict] = {}
    for biz in found:
        key = biz["name"].strip().lower()
        if key in merged:
            # Fill gaps (e.g. Google has review counts, OSM has an email).
            for field, value in biz.items():
                if value and not merged[key].get(field):
                    merged[key][field] = value
        else:
            merged[key] = biz
    return list(merged.values())
