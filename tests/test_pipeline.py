import time
from datetime import date

from localscout import review
from localscout.audit import analyze_html
from localscout.cli import next_cities, next_niche
from localscout.gigs import match_services, parse_hn_thread, parse_reddit_listing, score_gig
from localscout.config import load_config
from localscout.pitch import template_gig_reply, template_pitch
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
        "niche": "realtors",
        "kind": "local",
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


def make_gig(title, text="", hours_old=1):
    return {
        "id": f"gig:reddit/{abs(hash(title))}",
        "kind": "gig",
        "title": title,
        "text": text,
        "url": "https://www.reddit.com/r/forhire/x",
        "author": "u/someone in r/forhire",
        "posted_at": time.time() - hours_old * 3600,
    }


def test_gig_matching_and_exclusions():
    assert match_services(make_gig("[Hiring] Need a logo and website for my bakery"), CFG) == ["website", "logo"]
    assert match_services(make_gig("Looking for an editor for my fantasy manuscript"), CFG) == ["book_editing"]
    assert "book_formatting" in match_services(make_gig("Need KDP formatting for my novel"), CFG)
    assert match_services(make_gig("[For Hire] Logo designer available"), CFG) == []
    assert match_services(make_gig("Someone to do my homework essay"), CFG) == []


def test_gig_scoring_prefers_fresh_paid_posts():
    fresh = make_gig("[Hiring] logo", hours_old=1)
    old = make_gig("[Hiring] logo", hours_old=40)
    for g in (fresh, old):
        g["services"], g["budget"] = ["logo"], "$200"
    assert score_gig(fresh, CFG) > score_gig(old, CFG)


def test_source_parsers():
    listing = {"data": {"children": [{"data": {"id": "abc", "title": "[Hiring] Book cover",
               "selftext": "fantasy", "permalink": "/r/HungryArtists/abc/", "created_utc": 1700000000,
               "author": "writer1"}}]}}
    gig = parse_reddit_listing(listing, "HungryArtists")[0]
    assert gig["id"] == "gig:reddit/abc" and gig["url"].endswith("/r/HungryArtists/abc/")
    thread = {"children": [
        {"id": 1, "text": "SEEKING FREELANCER | Remote<p>Need a Webflow website", "created_at_i": 1, "author": "a"},
        {"id": 2, "text": "SEEKING WORK | me", "created_at_i": 1, "author": "b"},
    ]}
    assert [g["id"] for g in parse_hn_thread(thread)] == ["gig:hn/1"]


def test_report_roundtrip_approves_only_ticked_items():
    leads = []
    for i in range(2):
        lead = make_lead(id=f"osm:node/{i}", name=f"Agency {i}", score=70)
        lead["pitch"] = template_pitch(lead, CFG).model_dump()
        lead["pitch_generator"] = "template"
        leads.append(lead)
    gig = make_gig("[Hiring] Logo | for my *bakery*")
    gig.update(services=["logo"], budget=None, score=60)
    gig["pitch"], gig["pitch_generator"] = template_gig_reply(gig, CFG).model_dump(), "template"
    stats = {"found": 5, "new": 2, "gigs": 1, "cities": ["Austin, USA"], "niche": "realtors"}
    body = review.build_report(leads, [gig], stats, CFG)
    assert "- [ ] **Hiring  Logo   for my  bakery**" in body  # markdown-breaking chars stripped
    ticked = body.replace("- [ ] **Agency 1**", "- [x] **Agency 1**").replace("- [ ] **Hiring", "- [x] **Hiring")
    assert review.checked_lead_ids(body) == []
    assert review.checked_lead_ids(ticked) == ["osm:node/1", gig["id"]]


def test_rotation_wraps():
    local = {"cities": ["A", "B", "C"], "cities_per_run": 2, "niches": [{"name": "x"}, {"name": "y"}]}
    state = {}
    assert next_cities(local, state) == ["A", "B"]
    assert next_cities(local, state) == ["C", "A"]
    assert [next_niche(local, state)["name"] for _ in range(3)] == ["x", "y", "x"]
