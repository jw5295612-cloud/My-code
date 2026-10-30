# LocalScout

An autonomous lead-generation agent for a freelance design studio. Every day it:

1. **Scouts** businesses in a niche (starting with **realtors**) in cities anywhere in the world. It uses OpenStreetMap (free) and, optionally, Google Places.
2. **Audits** each business's website: missing site, broken site, not mobile-friendly, no HTTPS, slow, outdated, weak SEO, no enquiry form.
3. **Scores** each lead. Clear problems, signs of an established business and a way to make contact all raise the score.
4. **Builds a free concept homepage** for each top lead and publishes it on GitHub Pages.
5. **Writes a personal pitch** with Claude, plus a phone or WhatsApp script.
6. **Asks you to review.** It opens a GitHub issue with a checklist of the day's leads.
7. **Sells.** When you tick leads and save the issue, approved leads with an email address are emailed. The rest go to `outbox/` with a ready script and a WhatsApp link.

You stay in the loop: nothing is sent without your tick, and you can comment insights on any review issue.

```
GitHub Actions (daily) → scout → audit → score → mockup → pitch → review issue
                                                                     │ you tick ✔
                                       email / outbox  ←  approvals workflow
```

## Setup (about 15 minutes)

1. **Edit `config.yaml`.** Fill in your name, studio name, email, website and postal address (cold-email law requires the address). Put your city first in `cities`.
2. **Add repository secrets** under *Settings → Secrets and variables → Actions*:
   | Secret | Required? | What for |
   |---|---|---|
   | `ANTHROPIC_API_KEY` | Recommended | Claude-written pitches. Without it, a decent template is used. |
   | `GOOGLE_PLACES_API_KEY` | Optional | Ratings, review counts and more businesses |
   | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `FROM_EMAIL` | Optional | Automatic emailing. Without them, everything goes to `outbox/`. |
3. **Turn on GitHub Pages** under *Settings → Pages → Deploy from branch → `main` / `/docs`*. Then set `mockup_base_url` in `config.yaml` to match.
4. **Run it now** from *Actions → Daily scout → Run workflow*. You can type a city there to scout it right away.

### Run locally

```bash
pip install -r requirements.txt
python -m localscout run --city "Austin, USA"   # scout one city
python -m localscout stats                      # pipeline summary
python -m localscout mark "osm:node/123" won    # record outcomes
pytest
```

## Daily routine (2–3 hours)

- **10 minutes:** open the review issue, check the mockups, tick the best leads.
- **60 minutes:** call or WhatsApp the leads in `outbox/`, then reply to any responses.
- **The rest:** deliver client work. Use `python -m localscout mark <id> replied|won` so the agent learns what works.

## Pricing guide (starting point)

| Offer | Price idea |
|---|---|
| Concept → full 5-page realtor website | $300–800 (adjust to the local market) |
| Logo + brand kit | $100–250 |
| Monthly care plan (hosting, updates, listing uploads, review replies) | $30–100 per month |

The care plan is the important one: recurring income that compounds.

## Staying safe and legal

- Email is capped (`max_emails_per_day`) to protect your domain's reputation. Send from a separate domain, not your main one.
- Every email includes your address and an opt-out line. Add anyone who opts out to `data/suppressed.json`.
- Mockups say they are concepts and not affiliated with the business. They use only the business's public name and city.
- Lead data and mockups are committed to this repo. If the repo is public, so is the data. A private repo keeps it private, but GitHub Pages on private repos needs a paid plan. You can also host mockups on Netlify or Vercel.

## Roadmap

- [ ] Follow-up emails 4 and 9 days after the first send
- [ ] Weekly insight report: which cities, issues and pitch styles get replies, then auto-tune the scoring
- [ ] Inbox reader that marks replies and opt-outs automatically
- [ ] More niches: clinics, dentists, property managers (change `niche` in the config)
- [ ] Phase 3: a real-estate *deal* scout sold as a subscription
