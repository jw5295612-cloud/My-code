# LocalScout

An autonomous client-finding agent for a freelance **designer and writer**: websites, logos, banners and graphics, book covers, book editing, formatting and ghostwriting, and business proposals.

It finds paying clients in two ways, every day:

**Scout 1: local businesses with weak websites.** Realtors, dental clinics, salons, restaurants, gyms, law firms and auto shops, in cities anywhere in the world. These are *your customers*: the agent finds the ones with no website or a bad one. For each, it builds a free concept homepage and drafts a pitch for a website, logo and banners.

**Scout 2: people already asking for help.** It reads public "hiring" posts on Reddit (r/forhire, r/HireAWriter, r/selfpublish, r/HungryArtists and more), the monthly Hacker News "Seeking freelancer" thread, and any RSS job feeds you add. It matches each post to your services, scores it, and drafts a reply.

Each run:

1. **Scouts** both sources. Local search uses OpenStreetMap (free) and optionally Google Places. It rotates through niches and cities each day.
2. **Audits** each local business's website: missing site, broken site, not mobile-friendly, no HTTPS, slow, outdated, weak SEO, no enquiry form.
3. **Scores** everything. Clear problems, signs of an established business and reachability rank local leads. Fit, budget and freshness rank gigs, since early replies win.
4. **Builds a concept homepage** for each top local lead (published on GitHub Pages).
5. **Drafts messages** with Claude: cold pitches with a call/WhatsApp script, and gig replies.
6. **Asks you to review.** It opens one GitHub issue with a checklist of the day's best leads and gigs.
7. **Sells.** When you tick items and save the issue:
   - Local leads with an email address are emailed.
   - Everything else goes to `outbox/` with the message ready. That includes every gig: you post the reply yourself, because automated replies break those sites' rules.

Nothing is sent without your tick, and you can comment insights on any review issue.

```
GitHub Actions (daily)
  local scout → audit → score → mockup → pitch ─┐
  gig scout   → match → score → reply draft ────┴→ review issue
                                                     │ you tick ✔
                              email / outbox  ←  approvals workflow
```

**Guardrail:** posts asking someone to do a student's homework, exam or thesis are skipped (`exclude_keywords`). Selling work that gets submitted as the student's own is academic fraud and risks bans. Editing, formatting and business/NGO proposals are fine.

## Setup (about 15 minutes)

1. **Edit `config.yaml`.** Fill in your name, studio name, email, website, portfolio link, a short bio and your postal address (cold-email law requires the address). Put your city first under `local.cities`. Add or remove niches, services and subreddits as you like.
2. **Add repository secrets** under *Settings → Secrets and variables → Actions*:
   | Secret | Required? | What for |
   |---|---|---|
   | `ANTHROPIC_API_KEY` | Recommended | Claude-written pitches. Without it, a decent template is used. |
   | `GOOGLE_PLACES_API_KEY` | Optional | Ratings, review counts and more businesses |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | Recommended | Reliable Reddit access from GitHub's servers. Create a free "script" app at reddit.com/prefs/apps. |
   | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `FROM_EMAIL` | Optional | Automatic emailing. Without them, everything goes to `outbox/`. |
3. **Turn on GitHub Pages** under *Settings → Pages → Deploy from branch → `main` / `/docs`*. Then set `mockup_base_url` in `config.yaml` to match.
4. **Run it now** from *Actions → Daily scout → Run workflow*. You can type a city and/or niche (e.g. `dental clinics`) there.

### Run locally

```bash
pip install -r requirements.txt
python -m localscout run --city "Austin, USA" --niche "dental clinics"
python -m localscout run --skip-local           # gigs only
python -m localscout stats                      # pipeline summary
python -m localscout mark "osm:node/123" won    # record outcomes
pytest
```

## Daily routine (2–3 hours)

- **10 minutes:** open the review issue, check the mockups and gigs, tick the best ones.
- **30 minutes:** post the gig replies from `outbox/`. Gigs go fast, so do this first.
- **30 minutes:** call or WhatsApp the local leads in `outbox/`, then reply to any responses.
- **The rest:** deliver client work. Use `python -m localscout mark <id> replied|won` so the agent learns what works.

## Pricing guide (starting point)

| Offer | Price idea |
|---|---|
| Concept → full 5-page realtor website | $300–800 (adjust to the local market) |
| Logo + brand kit | $100–250 |
| Banner / flyer / social media pack | $30–150 |
| Book cover (ebook + print) | $80–300 |
| Book formatting (print + ebook) | $50–250 |
| Editing / proofreading | $0.01–0.03 per word |
| Business plan or grant proposal | $150–600 |
| Monthly care plan (hosting, updates, review replies) | $30–100 per month |

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
- [ ] Portfolio page generated from your finished work, linked in every pitch
- [ ] Phase 3: a real-estate *deal* scout sold as a subscription
