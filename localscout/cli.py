"""Command-line entry point.

  python -m localscout run                     both scouts -> drafts -> review report
  python -m localscout approve-from-issue F    mark leads ticked in an issue body file as approved
  python -m localscout send                    email approved local leads, outbox the rest
  python -m localscout mark ID STATUS          record an outcome (sent, replied, won, skipped...)
  python -m localscout stats                   pipeline summary
"""

import argparse
import sys
from collections import Counter

from . import outreach, review
from .audit import audit
from .config import load_config
from .gigs import find_gigs
from .mockup import build_mockup
from .pitch import write_gig_reply, write_pitch
from .scoring import score
from .sources import find_businesses
from .store import (
    load_leads,
    load_state,
    load_suppressed,
    now_iso,
    save_leads,
    save_state,
    set_status,
)


def next_cities(local_cfg: dict, state: dict) -> list[str]:
    cities = local_cfg["cities"]
    n = min(local_cfg["cities_per_run"], len(cities))
    start = state.get("city_cursor", 0) % len(cities)
    state["city_cursor"] = (start + n) % len(cities)
    return [cities[(start + i) % len(cities)] for i in range(n)]


def next_niche(local_cfg: dict, state: dict) -> dict:
    niches = local_cfg["niches"]
    i = state.get("niche_cursor", 0) % len(niches)
    state["niche_cursor"] = (i + 1) % len(niches)
    return niches[i]


def find_niche(local_cfg: dict, name: str) -> dict:
    for niche in local_cfg["niches"]:
        if niche["name"].lower() == name.lower():
            return niche
    sys.exit(f"No niche named {name!r} in config.yaml")


def scout_local(cfg, leads, state, stats, cities=None, niche_name=None) -> list[dict]:
    local = cfg["local"]
    niche = find_niche(local, niche_name) if niche_name else next_niche(local, state)
    cities = cities or next_cities(local, state)
    stats.update(niche=niche["name"], cities=cities)
    fresh = []

    for city in cities:
        print(f"Scouting {niche['name']} in {city}...")
        try:
            businesses = find_businesses(city, niche, cfg)
        except Exception as e:  # one bad city shouldn't stop the run
            print(f"  failed: {e}")
            continue
        stats["found"] += len(businesses)
        new = [b for b in businesses if b["id"] not in leads]
        print(f"  {len(businesses)} found, {len(new)} new")
        for biz in new[: cfg["limits"]["max_new_leads_per_city"]]:
            biz["kind"], biz["niche"] = "local", niche["name"]
            biz["audit"] = audit(biz)
            if not biz.get("email") and biz["audit"]["emails"]:
                biz["email"] = biz["audit"]["emails"][0]
            biz["score"] = score(biz)
            biz["found_at"] = now_iso()
            set_status(biz, "new")
            leads[biz["id"]] = biz
            fresh.append(biz)
    stats["new"] = len(fresh)

    shortlist = sorted(
        (l for l in fresh if l["score"] >= cfg["limits"]["min_score_for_review"]),
        key=lambda l: l["score"],
        reverse=True,
    )[: cfg["limits"]["leads_in_daily_review"]]
    for lead in shortlist:
        print(f"  drafting pitch for {lead['name']} (score {lead['score']})")
        lead["mockup_url"] = build_mockup(lead, cfg, niche)
        pitch, generator = write_pitch(lead, cfg)
        lead["pitch"], lead["pitch_generator"] = pitch.model_dump(), generator
        set_status(lead, "queued")
    return shortlist


def scout_gigs(cfg, leads, stats) -> list[dict]:
    print("Scouting gigs...")
    new = [g for g in find_gigs(cfg) if g["id"] not in leads]
    stats["gigs"] = len(new)
    print(f"  {len(new)} new matching posts")
    for gig in new:
        gig["found_at"] = now_iso()
        set_status(gig, "new")
        leads[gig["id"]] = gig

    shortlist = sorted(
        (g for g in new if g["score"] >= cfg["limits"]["min_score_for_review"]),
        key=lambda g: g["score"],
        reverse=True,
    )[: cfg["limits"]["gigs_in_daily_review"]]
    for gig in shortlist:
        print(f"  drafting reply for {gig['title'][:60]} (score {gig['score']})")
        pitch, generator = write_gig_reply(gig, cfg)
        gig["pitch"], gig["pitch_generator"] = pitch.model_dump(), generator
        set_status(gig, "queued")
    return shortlist


def cmd_run(cfg, cities=None, niche=None, local=True, gigs=True) -> None:
    leads, state = load_leads(), load_state()
    stats = {"cities": [], "found": 0, "new": 0, "gigs": 0}
    local_list = (
        scout_local(cfg, leads, state, stats, cities, niche)
        if local and cfg["local"]["enabled"]
        else []
    )
    gig_list = scout_gigs(cfg, leads, stats) if gigs and cfg["gigs"]["enabled"] else []

    save_leads(leads)
    save_state(state)
    if local_list or gig_list:
        path = review.write_report(review.build_report(local_list, gig_list, stats, cfg))
        print(f"Review report: {path}")
    else:
        print("Nothing made the shortlist today.")


def cmd_approve_from_issue(path: str) -> None:
    leads = load_leads()
    with open(path, encoding="utf-8") as f:
        ids = review.checked_lead_ids(f.read())
    approved = 0
    for lead_id in ids:
        lead = leads.get(lead_id)
        if lead and lead["status"] == "queued":
            set_status(lead, "approved")
            approved += 1
    save_leads(leads)
    print(f"Approved {approved} lead(s).")


def cmd_send(cfg: dict) -> None:
    leads, state = load_leads(), load_state()
    summary = outreach.send_approved(leads, state, load_suppressed(), cfg)
    save_leads(leads)
    save_state(state)
    print(
        f"Emailed: {len(summary['emailed'])} | outbox: {len(summary['outbox'])} | "
        f"suppressed: {len(summary['suppressed'])}"
    )
    if summary["outbox"]:
        print("Open the outbox/ folder for the messages to send yourself.")


def cmd_mark(lead_id: str, status: str) -> None:
    leads = load_leads()
    if lead_id not in leads:
        sys.exit(f"No lead {lead_id!r}")
    set_status(leads[lead_id], status)
    save_leads(leads)
    print(f"{leads[lead_id].get('name') or leads[lead_id].get('title')} -> {status}")


def cmd_stats() -> None:
    leads = load_leads()
    print(f"{len(leads)} leads total")
    for status, n in Counter(l["status"] for l in leads.values()).most_common():
        print(f"  {status:<11} {n}")
    local = [l for l in leads.values() if l.get("kind", "local") == "local"]
    print("Local by niche:", ", ".join(f"{k} ({n})" for k, n in Counter(l.get("niche") for l in local).most_common()))
    print("Local by city:", ", ".join(f"{k} ({n})" for k, n in Counter(l["city"] for l in local).most_common()))
    gigs = [l for l in leads.values() if l.get("kind") == "gig"]
    by_service = Counter(s for g in gigs for s in g["services"])
    print("Gigs by service:", ", ".join(f"{k} ({n})" for k, n in by_service.most_common()))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="localscout")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--city", action="append", help="scout these cities instead of the rotation")
    run.add_argument("--niche", help="scout this niche (name from config.yaml) instead of the rotation")
    run.add_argument("--skip-local", action="store_true")
    run.add_argument("--skip-gigs", action="store_true")
    sub.add_parser("approve-from-issue").add_argument("issue_body_file")
    sub.add_parser("send")
    mark = sub.add_parser("mark")
    mark.add_argument("lead_id")
    mark.add_argument("status")
    sub.add_parser("stats")
    args = parser.parse_args(argv)

    cfg = load_config()
    if args.command == "run":
        cmd_run(cfg, args.city, args.niche, not args.skip_local, not args.skip_gigs)
    elif args.command == "approve-from-issue":
        cmd_approve_from_issue(args.issue_body_file)
    elif args.command == "send":
        cmd_send(cfg)
    elif args.command == "mark":
        cmd_mark(args.lead_id, args.status)
    elif args.command == "stats":
        cmd_stats()
