"""Pitch writing: Claude writes a short personal pitch; a template is the fallback."""

import os

import anthropic
from pydantic import BaseModel

from .audit import ISSUE_LABELS

SYSTEM_PROMPT = """You write short cold outreach messages for a freelance web designer.

Rules:
- Use only the facts provided. Never invent statistics, names, awards or claims about the business.
- Mention at most two of the audit findings, phrased helpfully, never insulting.
- Mention that a free concept homepage was already made for them, and include the mockup link exactly as given.
- One clear, low-pressure call to action (a 10-minute call or a reply).
- Email body under 120 words. Plain text, no markdown. Sign with the sender's name and business.
- The call script is 3-5 short lines the sender can say on a phone or WhatsApp call."""


class Pitch(BaseModel):
    subject: str
    body: str
    call_script: str


def _facts(lead: dict, cfg: dict) -> str:
    issues = [ISSUE_LABELS[i] for i in lead["audit"]["issues"] if i in ISSUE_LABELS]
    return "\n".join(
        [
            f"Business: {lead['name']} ({cfg['niche']['name']}) in {lead['city']}",
            f"Website: {lead.get('website') or 'none found'}",
            f"Audit findings: {', '.join(issues) or 'none'}",
            f"Google rating: {lead.get('rating') or 'unknown'} from {lead.get('reviews') or 'unknown'} reviews",
            f"Mockup link: {lead['mockup_url']}",
            f"What the sender offers: {cfg['niche']['services_offered']}",
            f"Sender: {cfg['sender']['name']}, {cfg['sender']['business']} ({cfg['sender']['website']})",
            f"Write in: {cfg['pitch']['language']}",
        ]
    )


def template_pitch(lead: dict, cfg: dict) -> Pitch:
    issues = [ISSUE_LABELS[i].lower() for i in lead["audit"]["issues"][:2] if i in ISSUE_LABELS]
    problem = " and ".join(issues) if issues else "a few quick wins on your website"
    s = cfg["sender"]
    body = (
        f"Hi {lead['name']} team,\n\n"
        f"I was looking at real estate agencies in {lead['city']} and noticed {problem}. "
        f"Most home buyers search on their phones, so that can cost you enquiries.\n\n"
        f"I put together a free concept homepage for you: {lead['mockup_url']}\n\n"
        f"If you like the direction, I'd be happy to walk you through it on a 10-minute call. "
        f"No pressure either way.\n\n"
        f"{s['name']}\n{s['business']} | {s['website']}"
    )
    script = (
        f"Hi, this is {s['name']} from {s['business']}.\n"
        f"I noticed {problem} on your site and made you a free concept homepage.\n"
        f"Can I send you the link on WhatsApp or email?"
    )
    return Pitch(subject=f"A free homepage concept for {lead['name']}", body=body, call_script=script)


def write_pitch(lead: dict, cfg: dict) -> tuple[Pitch, str]:
    """Return (pitch, generator) where generator is 'claude' or 'template'."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return template_pitch(lead, cfg), "template"
    client = anthropic.Anthropic()
    try:
        response = client.messages.parse(
            model=cfg["pitch"]["model"],
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            output_config={"effort": cfg["pitch"]["effort"]},
            messages=[{"role": "user", "content": _facts(lead, cfg)}],
            output_format=Pitch,
        )
    except anthropic.RateLimitError:
        print("  [pitch] rate limited, using template")
        return template_pitch(lead, cfg), "template"
    except anthropic.APIStatusError as e:
        print(f"  [pitch] API error {e.status_code}, using template")
        return template_pitch(lead, cfg), "template"
    except anthropic.APIConnectionError:
        print("  [pitch] connection error, using template")
        return template_pitch(lead, cfg), "template"

    if response.stop_reason == "refusal" or response.parsed_output is None:
        return template_pitch(lead, cfg), "template"
    return response.parsed_output, "claude"
