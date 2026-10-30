"""Lead storage: a single JSON file committed to the repo, so every run has history."""

import json
from datetime import datetime, timezone

from .config import DATA_DIR

LEADS_FILE = DATA_DIR / "leads.json"
STATE_FILE = DATA_DIR / "state.json"
SUPPRESSED_FILE = DATA_DIR / "suppressed.json"

# Lead lifecycle: new -> queued (in a review issue) -> approved -> sent
#                 any  -> skipped | suppressed | replied | won
STATUSES = {"new", "queued", "approved", "sent", "skipped", "suppressed", "replied", "won"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def load_leads() -> dict[str, dict]:
    return _read(LEADS_FILE, {})


def save_leads(leads: dict[str, dict]) -> None:
    _write(LEADS_FILE, leads)


def load_state() -> dict:
    return _read(STATE_FILE, {"city_cursor": 0, "emails_sent": {}})


def save_state(state: dict) -> None:
    _write(STATE_FILE, state)


def load_suppressed() -> set[str]:
    return {s.lower() for s in _read(SUPPRESSED_FILE, [])}


def set_status(lead: dict, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    lead["status"] = status
    lead["updated_at"] = now_iso()
