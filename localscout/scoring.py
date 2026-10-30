"""Lead scoring: high score = clear problems + a real business you can reach."""

import math

ISSUE_WEIGHTS = {
    "no_website": 40,
    "site_down": 35,
    "not_mobile_friendly": 25,
    "outdated": 15,
    "no_https": 15,
    "no_contact_form": 10,
    "slow": 10,
    "weak_seo": 10,
}


def score(lead: dict) -> int:
    issues = lead.get("audit", {}).get("issues", [])
    pain = min(sum(ISSUE_WEIGHTS.get(i, 0) for i in issues), 70)

    # Established businesses can afford you: reward review volume and rating.
    reviews = lead.get("reviews") or 0
    established = min(math.log10(reviews + 1) * 8, 20)
    if (lead.get("rating") or 0) >= 4.0:
        established += 5

    reachable = 0
    if lead.get("email"):
        reachable += 10
    if lead.get("phone"):
        reachable += 5

    total = pain + established + reachable
    if not lead.get("email") and not lead.get("phone"):
        total *= 0.5  # no way to contact them
    return round(min(total, 100))
