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


def _md(text: str) -> str:
    """Keep untrusted titles from breaking the checklist line."""
    return re.sub(r"[\r\n<>\[\]|`*]", " ", text).strip()


def lead_line(lead: dict) -> str:
    issues = ", ".join(ISSUE_LABELS.get(i, i) for i in lead["audit"]["issues"])
    contact = "email" if lead.get("email") else ("phone only" if lead.get("phone") else "no contact")
    return (
        f"- [ ] **{_md(lead['name'])}** ({lead.get('niche', '')}, {lead['city']}) | score {lead['score']} | "
        f"{contact} | {issues} | [mockup]({lead['mockup_url']}) <!-- lead:{lead['id']} -->"
    )


def gig_line(gig: dict, cfg: dict) -> str:
    services = ", ".join(cfg["services"][s]["label"] for s in gig["services"])
    budget = f" | budget {gig['budget']}" if gig.get("budget") else ""
    return (
        f"- [ ] **{_md(gig['title'])}** | score {gig['score']} | {services}{budget} | "
        f"[post]({gig['url']}) <!-- lead:{gig['id']} -->"
    )


def details(lead: dict) -> str:
    p = lead["pitch"]
    title = _md(lead.get("name") or lead.get("title", ""))
    if lead.get("kind") == "gig":
        info = f"**Post:** {lead['url']} · **By:** {_md(lead.get('author', ''))}"
    else:
        info = (
            f"**Website:** {lead.get('website') or 'none'} · **Phone:** {lead.get('phone') or 'n/a'} · "
            f"**Email:** {lead.get('email') or 'n/a'}"
        )
    parts = [
        f"<details><summary>{title}: draft ({lead['pitch_generator']})</summary>",
        "",
        info,
        "",
        f"**Subject:** {p['subject']}",
        "",
        "```",
        p["body"],
        "```",
    ]
    if p.get("call_script"):
        parts += ["", "**Call / WhatsApp script:**", "```", p["call_script"], "```"]
    return "\n".join(parts + ["</details>"])


def build_report(local: list[dict], gigs: list[dict], stats: dict, cfg: dict) -> str:
    today = date.today().isoformat()
    lines = [
        f"# LocalScout: {today}",
        "",
        f"Local scout: **{stats['found']}** {stats.get('niche', 'businesses')} found in "
        f"{', '.join(stats['cities']) or 'no cities'}, **{stats['new']}** new. "
        f"Gig scout: **{stats['gigs']}** matching posts.",
        "",
        "**How to review:** tick what you want to pursue, then save the issue. "
        "Ticked local businesses with an email are emailed automatically (up to the daily cap); "
        "everything else, including all gigs, goes to the outbox with a ready message for you to send. "
        "Leave a comment with any insight and I'll adjust the config.",
        "",
    ]
    if local:
        lines += ["## Local businesses to pitch", ""] + [lead_line(l) for l in local] + [""]
    if gigs:
        lines += ["## Gigs to apply for", ""] + [gig_line(g, cfg) for g in gigs] + [""]
    lines += ["## Drafts", ""]
    body = "\n".join(lines)
    for lead in local + gigs:
        detail = details(lead) + "\n\n"
        if len(body) + len(detail) > MAX_ISSUE_CHARS:
            body += "_More drafts are in `data/leads.json`._\n"
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
