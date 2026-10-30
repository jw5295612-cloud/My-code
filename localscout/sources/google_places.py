"""Google Places (New) text search. Optional: richer data (ratings, review counts).

Only runs when GOOGLE_PLACES_API_KEY is set. Google gives a monthly free usage
allowance; check current pricing before raising the limits.
"""

import os

import requests

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join(
    f"places.{f}"
    for f in (
        "id",
        "displayName",
        "formattedAddress",
        "websiteUri",
        "nationalPhoneNumber",
        "rating",
        "userRatingCount",
    )
)


def search(city: str, cfg: dict) -> list[dict]:
    resp = requests.post(
        SEARCH_URL,
        json={"textQuery": f"{cfg['niche']['google_query']} in {city}"},
        headers={
            "X-Goog-Api-Key": os.environ["GOOGLE_PLACES_API_KEY"],
            "X-Goog-FieldMask": FIELDS,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  [google] {resp.status_code}: {resp.text[:200]}")
        return []
    return [
        {
            "id": f"google:{p['id']}",
            "name": p.get("displayName", {}).get("text", ""),
            "city": city,
            "address": p.get("formattedAddress", ""),
            "phone": p.get("nationalPhoneNumber", ""),
            "email": "",
            "website": p.get("websiteUri", ""),
            "rating": p.get("rating"),
            "reviews": p.get("userRatingCount"),
            "source": "google_places",
        }
        for p in resp.json().get("places", [])
        if p.get("displayName", {}).get("text")
    ]
