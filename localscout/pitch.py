"""Pitch writing: Claude writes short personal messages; templates are the fallback."""

import os

import anthropic
from pydantic import BaseModel

from .audit import ISSUE_LABELS

LOCAL_SYSTEM_PROMPT = """You write short cold outreach messages for a freelance designer pitching a local business.

Rules:
- Use only the facts provided. Never invent statistics, names, awards or claims about the business.
- Mention at most two of the audit findings, phrased helpfully, never insulting.
- Mention that a free concept homepage was already made for them, and include the mockup link exactly as given.
- One clear, low-pressure call to action (a 10-minute call or a reply).
- Email body under 120 words. Plain text, no markdown. Sign with the sender's name and business.
- The call script is 3-5 short lines the sender can say on a phone or WhatsApp call."""

GIG_SYSTEM_PROMPT = """You write replies from a freelancer to a public post where someone is looking to hire.

Rules:
- Show you read the post: refer to one or two specifics from it.
- Only claim skills and experience that appear in the freelancer profile. Never invent past clients or numbers.
- Include the portfolio link exactly as given.
- Ask one useful question about the project, and suggest a next step.
- Under 110 words, plain text, friendly and direct. Sign with the sender's first name.
- subject: a short subject line for a direct message.
- call_script: leave empty."""


class Pitch(BaseModel):
    subject: str
    body: str
    call_script: str


def _ask_claude(system: str, facts: str, cfg: dict) -> Pitch | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    client = anthropic.Anthropic()
    try:
        response = client.messages.parse(
            model=cfg["pitch"]["model"],
            max_tokens=4000,
            system=system,
            output_config={"effort": cfg["pitch"]["effort"]},
            messages=[{"role": "user", "content": facts}],
            output_format=Pitch,
        )
    except anthropic.RateLimitError:
        print("  [pitch] rate limited, using template")
        return None
    except anthropic.APIStatusError as e:
        print(f"  [pitch] API error {e.status_code}, using template")
        return None
    except anthropic.APIConnectionError:
        print("  [pitch] connection error, using template")
        return None
    if response.stop_reason == "refusal":
        return None
    return response.parsed_output


def _offer(cfg: dict, keys: list[str]) -> str:
    return ", ".join(cfg["services"][k]["label"] for k in keys if k in cfg["services"])


# --- Local businesses ------------------------------------------------------------

def _local_facts(lead: dict, cfg: dict) -> str:
    issues = [ISSUE_LABELS[i] for i in lead["audit"]["issues"] if i in ISSUE_LABELS]
    return "\n".join(
        [
            f"Business: {lead['name']} ({lead.get('niche', 'local business')}) in {lead['city']}",
            f"Website: {lead.get('website') or 'none found'}",
            f"Audit findings: {', '.join(issues) or 'none'}",
            f"Google rating: {lead.get('rating') or 'unknown'} from {lead.get('reviews') or 'unknown'} reviews",
            f"Mockup link: {lead['mockup_url']}",
            f"What the sender offers: {_offer(cfg, cfg['local']['offer'])}",
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
        f"I was looking at {lead.get('niche', 'local businesses')} in {lead['city']} and noticed {problem}. "
        f"Most customers search on their phones first, so that can cost you enquiries.\n\n"
        f"I put together a free concept homepage for you: {lead['mockup_url']}\n\n"
        f"I also do logos, banners and social media graphics if you'd like a fresh look. "
        f"Happy to walk you through it on a 10-minute call. No pressure either way.\n\n"
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
    pitch = _ask_claude(LOCAL_SYSTEM_PROMPT, _local_facts(lead, cfg), cfg)
    return (pitch, "claude") if pitch else (template_pitch(lead, cfg), "template")


# --- Gigs --------------------------------------------------------------------------

def _gig_facts(gig: dict, cfg: dict) -> str:
    s = cfg["sender"]
    return "\n".join(
        [
            f"Post title: {gig['title']}",
            f"Post text: {gig['text'] or '(no body)'}",
            f"Services that match: {_offer(cfg, gig['services'])}",
            f"Freelancer profile: {s['name']}, {s['business']}. {s['bio']}",
            f"Portfolio: {s['portfolio']}",
            f"Write in: {cfg['pitch']['language']}",
        ]
    )


def template_gig_reply(gig: dict, cfg: dict) -> Pitch:
    s = cfg["sender"]
    body = (
        f"Hi! I saw your post \"{gig['title'][:80]}\". "
        f"This is exactly what I do: {_offer(cfg, gig['services']).lower()}.\n\n"
        f"Here's some of my work: {s['portfolio']}\n\n"
        f"Could you share a bit more about your timeline and what you have so far? "
        f"I can send a quick plan and quote today.\n\n"
        f"{s['name'].split()[0]}"
    )
    return Pitch(subject=f"Re: {gig['title'][:80]}", body=body, call_script="")


def write_gig_reply(gig: dict, cfg: dict) -> tuple[Pitch, str]:
    pitch = _ask_claude(GIG_SYSTEM_PROMPT, _gig_facts(gig, cfg), cfg)
    return (pitch, "claude") if pitch else (template_gig_reply(gig, cfg), "template")
