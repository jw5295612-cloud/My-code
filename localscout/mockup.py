"""Concept homepage generator: a one-page preview you link in the pitch."""

import hashlib
import html
import re

from .config import MOCKUP_DIR

PALETTES = [
    ("#0f3d3e", "#e2b866", "#f7f5f0"),  # deep teal + gold
    ("#1d2b53", "#ff6b4a", "#f5f7fb"),  # navy + coral
    ("#2b2b2b", "#c9a227", "#faf8f3"),  # charcoal + brass
    ("#123524", "#9bc53d", "#f4f8f1"),  # forest + lime
    ("#3a1d4d", "#f2a541", "#fbf7fd"),  # plum + amber
]

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{name} | Concept homepage</title>
<style>
  :root {{ --primary: {primary}; --accent: {accent}; --bg: {bg}; }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background: var(--bg); color: #1b1b1b; line-height: 1.5; }}
  header {{ display: flex; justify-content: space-between; align-items: center; padding: 18px 6vw; background: var(--primary); color: #fff; }}
  .logo {{ font-weight: 800; letter-spacing: .5px; font-size: 1.15rem; }}
  .logo span {{ color: var(--accent); }}
  nav a {{ color: #fff; margin-left: 22px; text-decoration: none; opacity: .85; font-size: .95rem; }}
  .hero {{ padding: 90px 6vw 70px; background: linear-gradient(135deg, var(--primary), #000a); color: #fff; }}
  .hero h1 {{ font-size: clamp(2rem, 5vw, 3.4rem); max-width: 16ch; line-height: 1.1; }}
  .hero p {{ margin: 18px 0 30px; max-width: 48ch; opacity: .9; font-size: 1.1rem; }}
  .search {{ display: flex; flex-wrap: wrap; gap: 10px; background: #fff; padding: 10px; border-radius: 12px; max-width: 640px; }}
  .search input, .search select {{ flex: 1 1 150px; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 1rem; }}
  .btn {{ background: var(--accent); color: #111; border: 0; padding: 12px 22px; border-radius: 8px; font-weight: 700; font-size: 1rem; text-decoration: none; display: inline-block; }}
  section {{ padding: 64px 6vw; }}
  h2 {{ font-size: 1.8rem; margin-bottom: 26px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 22px; }}
  .card {{ background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 18px #0001; }}
  .card .img {{ height: 160px; background: linear-gradient(120deg, var(--primary), var(--accent)); opacity: .85; }}
  .card div.body {{ padding: 16px; }}
  .price {{ font-weight: 800; color: var(--primary); }}
  .why .grid div {{ background: #fff; padding: 22px; border-radius: 14px; border-top: 4px solid var(--accent); }}
  .cta {{ text-align: center; background: var(--primary); color: #fff; }}
  .cta p {{ margin: 0 auto 26px; max-width: 46ch; opacity: .9; }}
  footer {{ padding: 26px 6vw; font-size: .85rem; color: #666; text-align: center; }}
  @media (max-width: 640px) {{ nav {{ display: none; }} }}
</style>
</head>
<body>
<header>
  <div class="logo">{logo_main}<span>{logo_tail}</span></div>
  <nav><a href="#listings">Buy</a><a href="#listings">Rent</a><a href="#why">Sell</a><a href="#contact">Contact</a></nav>
</header>
<div class="hero">
  <h1>Find your next home in {city_short}</h1>
  <p>{name} helps buyers, sellers and renters move with confidence, with local knowledge and honest advice.</p>
  <form class="search" onsubmit="return false">
    <input placeholder="Area or neighbourhood">
    <select><option>Buy</option><option>Rent</option></select>
    <button class="btn">Search homes</button>
  </form>
</div>
<section id="listings">
  <h2>Featured properties</h2>
  <div class="grid">
    <div class="card"><div class="img"></div><div class="body"><p class="price">Featured listing</p><p>3 bed family home &middot; {city_short}</p></div></div>
    <div class="card"><div class="img"></div><div class="body"><p class="price">New this week</p><p>2 bed apartment &middot; City centre</p></div></div>
    <div class="card"><div class="img"></div><div class="body"><p class="price">For rent</p><p>Modern studio &middot; Close to transport</p></div></div>
  </div>
</section>
<section class="why" id="why">
  <h2>Why work with {name}</h2>
  <div class="grid">
    <div><h3>Local experts</h3><p>We know {city_short} street by street.</p></div>
    <div><h3>Free valuation</h3><p>Find out what your property is worth today.</p></div>
    <div><h3>Fast replies</h3><p>Enquire online and hear back the same day.</p></div>
  </div>
</section>
<section class="cta" id="contact">
  <h2>Thinking of buying or selling?</h2>
  <p>Book a free, no-obligation chat with our team.</p>
  <a class="btn" href="{contact_href}">{contact_label}</a>
</section>
<footer>Concept homepage prepared for {name} by {sender_business}. Not affiliated with or endorsed by {name}. Listings shown are placeholders.</footer>
</body>
</html>
"""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def mockup_slug(lead: dict) -> str:
    digest = hashlib.sha1(lead["id"].encode()).hexdigest()[:6]
    return f"{slugify(lead['name'])}-{digest}"


def build_mockup(lead: dict, cfg: dict) -> str:
    """Write the mockup HTML and return its public URL."""
    slug = mockup_slug(lead)
    primary, accent, bg = PALETTES[int(hashlib.sha1(slug.encode()).hexdigest(), 16) % len(PALETTES)]
    words = lead["name"].split()
    e = html.escape
    page = TEMPLATE.format(
        name=e(lead["name"]),
        logo_main=e(" ".join(words[:-1]) + " " if len(words) > 1 else ""),
        logo_tail=e(words[-1]),
        city_short=e(lead["city"].split(",")[0]),
        primary=primary,
        accent=accent,
        bg=bg,
        contact_href=e(f"tel:{lead['phone']}" if lead.get("phone") else "#contact"),
        contact_label="Call us today" if lead.get("phone") else "Book a free chat",
        sender_business=e(cfg["sender"]["business"]),
    )
    MOCKUP_DIR.mkdir(parents=True, exist_ok=True)
    (MOCKUP_DIR / f"{slug}.html").write_text(page, encoding="utf-8")
    return cfg["mockup_base_url"].rstrip("/") + f"/{slug}.html"
