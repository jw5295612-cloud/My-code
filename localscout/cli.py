"""Command-line entry point.

  python -m localscout run                     scout -> audit -> score -> mockup -> pitch -> report
  python -m localscout approve-from-issue F    mark leads ticked in an issue body file as approved
  python -m localscout send                    email approved leads, outbox the rest
  python -m localscout mark ID STATUS          record an outcome (sent, replied, won, skipped...)
  python -m localscout stats                   pipeline summary
"""

import argparse
import sys
from collections import Counter

from . import outreach, review
from .audit import audit
from .config import load_config
from .mockup import build_mockup
from .pitch import write_pitch
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


def next_cities(cfg: dict, state: dict) -> list[str]:
    cities = cfg["cities"]
    n = min(cfg["cities_per_run"], len(cities))
    start = state["city_cursor"] % len(cities)
    state["city_cursor"] = (start + n) % len(cities)
    return [cities[(start + i) % len(cities)] for i in range(n)]


def cmd_run(cfg: dict, cities: list[str] | None = None) -> None:
    leads, state = load_leads(), load_state()
    cities = cities or next_cities(cfg, state)
    stats = {"cities": cities, "found": 0, "new": 0}
    fresh = []

    for city in cities:
        print(f"Scouting {cfg['niche']['name']} in {city}...")
        try:
            businesses = find_businesses(city, cfg)
        except Exception as e:  # one bad city shouldn't stop the run
            print(f"  failed: {e}")
            continue
        stats["found"] += len(businesses)
        new = [b for b in businesses if b["id"] not in leads]
        print(f"  {len(businesses)} found, {len(new)} new")
        for biz in new[: cfg["limits"]["max_new_leads_per_city"]]:
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
        print(f"  preparing pitch for {lead['name']} (score {lead['score']})")
        lead["mockup_url"] = build_mockup(lead, cfg)
        pitch, generator = write_pitch(lead, cfg)
        lead["pitch"], lead["pitch_generator"] = pitch.model_dump(), generator
        set_status(lead, "queued")

    save_leads(leads)
    save_state(state)
    if shortlist:
        path = review.write_report(review.build_report(shortlist, stats))
        print(f"Review report: {path}")
    else:
        print("No leads made the shortlist today.")


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
    if summary["outbox"] and not outreach.smtp_configured():
        print("SMTP is not configured, so every approved lead went to the outbox/ folder.")


def cmd_mark(lead_id: str, status: str) -> None:
    leads = load_leads()
    if lead_id not in leads:
        sys.exit(f"No lead {lead_id!r}")
    set_status(leads[lead_id], status)
    save_leads(leads)
    print(f"{leads[lead_id]['name']} -> {status}")


def cmd_stats() -> None:
    leads = load_leads()
    print(f"{len(leads)} leads total")
    for status, n in Counter(l["status"] for l in leads.values()).most_common():
        print(f"  {status:<11} {n}")
    cities = Counter(l["city"] for l in leads.values())
    print("By city:", ", ".join(f"{c} ({n})" for c, n in cities.most_common()))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="localscout")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--city", action="append", help="scout these cities instead of the rotation")
    sub.add_parser("approve-from-issue").add_argument("issue_body_file")
    sub.add_parser("send")
    mark = sub.add_parser("mark")
    mark.add_argument("lead_id")
    mark.add_argument("status")
    sub.add_parser("stats")
    args = parser.parse_args(argv)

    cfg = load_config()
    if args.command == "run":
        cmd_run(cfg, args.city)
    elif args.command == "approve-from-issue":
        cmd_approve_from_issue(args.issue_body_file)
    elif args.command == "send":
        cmd_send(cfg)
    elif args.command == "mark":
        cmd_mark(args.lead_id, args.status)
    elif args.command == "stats":
        cmd_stats()
