from datetime import date

from localscout import review
from localscout.audit import analyze_html
from localscout.cli import next_cities
from localscout.config import load_config
from localscout.pitch import template_pitch
from localscout.scoring import score
from localscout.sources.osm import build_query, element_to_business

CFG = load_config()

GOOD_PAGE = f"""<html><head><title>Acme Homes</title>
<meta name="viewport" content="width=device-width"><meta name="description" content="x"></head>
<body><form></form><a href="mailto:hello@acme.com">Email</a> &copy; {date.today().year}</body></html>"""

BAD_PAGE = "<html><body>Call us! Copyright 2014 sales@oldsite.com</body></html>"


def make_lead(**overrides):
    lead = {
        "id": "osm:node/1",
        "name": "Acme Homes",
        "city": "Austin, USA",
        "phone": "+1 512 555 0100",
        "email": "",
        "website": "",
        "rating": None,
        "reviews": None,
        "audit": {"issues": ["no_website"], "emails": []},
        "mockup_url": "https://example.com/m.html",
    }
    lead.update(overrides)
    return lead


def test_good_page_has_no_issues():
    issues, emails = analyze_html(GOOD_PAGE, "https://acme.com", 1.0)
    assert issues == []
    assert emails == ["hello@acme.com"]


def test_bad_page_flags_problems():
    issues, emails = analyze_html(BAD_PAGE, "http://oldsite.com", 6.0)
    assert set(issues) == {
        "no_https",
        "not_mobile_friendly",
        "slow",
        "outdated",
        "weak_seo",
        "no_contact_form",
    }
    assert emails == ["sales@oldsite.com"]


def test_scoring_prefers_reachable_businesses_with_problems():
    reachable = score(make_lead(email="a@b.com", reviews=150, rating=4.6))
    unreachable = score(make_lead(phone="", email=""))
    healthy = score(make_lead(email="a@b.com", audit={"issues": [], "emails": []}))
    assert reachable > healthy
    assert reachable > unreachable


def test_osm_element_parsing_and_query():
    el = {"type": "node", "id": 42, "tags": {"name": "Prime Realty", "contact:phone": "123"}}
    biz = element_to_business(el, "Lagos, Nigeria")
    assert biz["id"] == "osm:node/42" and biz["phone"] == "123"
    assert element_to_business({"type": "node", "id": 1, "tags": {}}, "x") is None
    q = build_query((1, 2, 3, 4), [["office", "estate_agent"]])
    assert 'nwr["office"="estate_agent"](1,2,3,4);' in q


def test_report_roundtrip_approves_only_ticked_leads():
    leads = []
    for i in range(2):
        lead = make_lead(id=f"osm:node/{i}", name=f"Agency {i}", score=70)
        lead["pitch"] = template_pitch(lead, CFG).model_dump()
        lead["pitch_generator"] = "template"
        leads.append(lead)
    body = review.build_report(leads, {"found": 5, "new": 2, "cities": ["Austin, USA"]})
    ticked = body.replace("- [ ] **Agency 1**", "- [x] **Agency 1**")
    assert review.checked_lead_ids(body) == []
    assert review.checked_lead_ids(ticked) == ["osm:node/1"]


def test_city_rotation_wraps():
    cfg = {"cities": ["A", "B", "C"], "cities_per_run": 2}
    state = {"city_cursor": 0}
    assert next_cities(cfg, state) == ["A", "B"]
    assert next_cities(cfg, state) == ["C", "A"]
