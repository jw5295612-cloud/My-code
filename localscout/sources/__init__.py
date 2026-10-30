import os

from . import google_places, osm


def find_businesses(city: str, niche: dict, cfg: dict) -> list[dict]:
    """Collect businesses of one niche in one city from every source, merged by name."""
    found = osm.search(city, niche, cfg)
    if os.environ.get("GOOGLE_PLACES_API_KEY"):
        found += google_places.search(city, niche)

    merged: dict[str, dict] = {}
    for biz in found:
        biz["niche"] = niche["name"]
        key = biz["name"].strip().lower()
        if key in merged:
            # Fill gaps (e.g. Google has review counts, OSM has an email).
            for field, value in biz.items():
                if value and not merged[key].get(field):
                    merged[key][field] = value
        else:
            merged[key] = biz
    return list(merged.values())
