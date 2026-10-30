"""Human-in-the-loop review: a daily Markdown report you approve by ticking checkboxes.

The report becomes a GitHub issue. Ticking a box and saving the issue triggers
the approvals workflow, which marks those leads approved and sends them.
"""

import re
from datetime import date

from .audit import ISSUE_LABELS
from .config import REPORT_DIR

MAX_ISSUE_CHARS = 60000  # GitHub's issue body limit is 65536
CHECKED_RE = re.compile(r"^\s*-\s*\[[xX]\].*<!--\s*lead:(\S+)\s*-->", re.M)


def lead_line(lead: dict) -> str:
    issues = ", ".join(ISSUE_LABELS.get(i, i) for i in lead["audit"]["issues"])
    contact = "email" if lead.get("email") else ("phone only" if lead.get("phone") else "no contact")
    return (
        f"- [ ] **{lead['name']}** ({lead['city']}) | score {lead['score']} | {contact} | "
        f"{issues} | [mockup]({lead['mockup_url']}) <!-- lead:{lead['id']} -->"
    )


def lead_details(lead: dict) -> str:
    p = lead["pitch"]
    return "\n".join(
        [
            f"<details><summary>{lead['name']}: pitch ({lead['pitch_generator']})</summary>",
            "",
            f"**Website:** {lead.get('website') or 'none'} · **Phone:** {lead.get('phone') or 'n/a'} · "
            f"**Email:** {lead.get('email') or 'n/a'}",
            "",
            f"**Subject:** {p['subject']}",
            "",
            "```",
            p["body"],
            "```",
            "",
            "**Call / WhatsApp script:**",
            "```",
            p["call_script"],
            "```",
            "</details>",
        ]
    )


def build_report(leads: list[dict], stats: dict) -> str:
    today = date.today().isoformat()
    header = [
        f"# LocalScout leads: {today}",
        "",
        f"Scouted **{stats['found']}** businesses in {', '.join(stats['cities'])}; "
        f"**{stats['new']}** were new, **{len(leads)}** made today's shortlist.",
        "",
        "**How to review:** tick the leads you want contacted, then save the issue. "
        "Ticked leads with an email are sent automatically (up to the daily cap); "
        "the rest go to the outbox for you to call or WhatsApp. "
        "Leave a comment with any insight and I'll adjust the config.",
        "",
        "## Shortlist",
        "",
    ]
    lines = header + [lead_line(lead) for lead in leads] + ["", "## Pitches", ""]
    body = "\n".join(lines)
    for lead in leads:
        detail = lead_details(lead) + "\n\n"
        if len(body) + len(detail) > MAX_ISSUE_CHARS:
            body += "_More pitches are in `data/leads.json`._\n"
            break
        body += detail
    return body


def write_report(text: str) -> str:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{date.today().isoformat()}.md"
    path.write_text(text, encoding="utf-8")
    return str(path)


def checked_lead_ids(issue_body: str) -> list[str]:
    return CHECKED_RE.findall(issue_body)
