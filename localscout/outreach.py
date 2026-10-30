"""Sending approved pitches: email via SMTP, everything else to a manual outbox."""

import os
import smtplib
from datetime import date
from email.message import EmailMessage

from .config import OUTBOX_DIR
from .store import set_status

FOOTER = (
    "\n\n--\n{business} | {address}\n"
    "Not interested? Just reply \"no thanks\" and I won't contact you again."
)


def smtp_configured() -> bool:
    return all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def _send_email(to: str, subject: str, body: str, cfg: dict) -> None:
    msg = EmailMessage()
    msg["From"] = f"{cfg['sender']['name']} <{os.environ.get('FROM_EMAIL', cfg['sender']['email'])}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = cfg["sender"]["email"]
    msg.set_content(body)
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(os.environ["SMTP_HOST"], port, timeout=30) as server:
        server.starttls()
        server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        server.send_message(msg)


def send_approved(leads: dict, state: dict, suppressed: set[str], cfg: dict) -> dict:
    today = date.today().isoformat()
    sent_today = state["emails_sent"].get(today, 0)
    cap = cfg["limits"]["max_emails_per_day"]
    footer = FOOTER.format(
        business=cfg["sender"]["business"], address=cfg["sender"]["postal_address"]
    )
    summary = {"emailed": [], "outbox": [], "suppressed": []}
    outbox_entries = []

    for lead in leads.values():
        if lead.get("status") != "approved":
            continue
        if lead.get("kind") == "gig":
            # Gigs are answered on the site they were posted on, by you.
            if not lead.get("in_outbox"):
                lead["in_outbox"] = today
                outbox_entries.append(lead)
                summary["outbox"].append(lead["title"])
            continue
        email = (lead.get("email") or "").lower()
        if email and email in suppressed:
            set_status(lead, "suppressed")
            summary["suppressed"].append(lead["name"])
            continue
        if email and smtp_configured() and sent_today < cap:
            _send_email(email, lead["pitch"]["subject"], lead["pitch"]["body"] + footer, cfg)
            sent_today += 1
            lead["sent_via"] = "email"
            set_status(lead, "sent")
            summary["emailed"].append(lead["name"])
        elif not lead.get("in_outbox"):
            lead["in_outbox"] = today
            outbox_entries.append(lead)
            summary["outbox"].append(lead["name"])

    state["emails_sent"][today] = sent_today
    if outbox_entries:
        _append_outbox(outbox_entries, today)
    return summary


def _append_outbox(leads: list[dict], today: str) -> None:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTBOX_DIR / f"{today}.md"
    parts = [] if path.exists() else [f"# Outbox {today}: contact these yourself\n"]
    for lead in leads:
        if lead.get("kind") == "gig":
            parts.append(
                f"## Gig: {lead['title']}\n"
                f"Reply here: {lead['url']}\n\n"
                f"**Message:**\n```\n{lead['pitch']['body']}\n```\n"
                f"After replying, run: `python -m localscout mark {lead['id']} sent`\n"
            )
            continue
        phone = lead.get("phone") or "n/a"
        digits = "".join(c for c in phone if c.isdigit())
        whatsapp = f" · [WhatsApp](https://wa.me/{digits})" if phone.strip().startswith("+") else ""
        parts.append(
            f"## {lead['name']} ({lead['city']})\n"
            f"Phone: {phone}{whatsapp} · Email: {lead.get('email') or 'n/a'} · "
            f"Mockup: {lead['mockup_url']}\n\n"
            f"**Script:**\n```\n{lead['pitch']['call_script']}\n```\n"
            f"**Message:**\n```\n{lead['pitch']['body']}\n```\n"
            f"After contacting, run: `python -m localscout mark {lead['id']} sent`\n"
        )
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
