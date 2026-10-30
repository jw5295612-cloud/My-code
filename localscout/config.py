from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MOCKUP_DIR = ROOT / "docs" / "mockups"
REPORT_DIR = ROOT / "reports"
OUTBOX_DIR = ROOT / "outbox"


def load_config(path: Path | None = None) -> dict:
    with open(path or ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def user_agent(cfg: dict) -> str:
    # OSM's usage policies require an identifying User-Agent with a contact.
    return f"LocalScout/0.1 (+{cfg['sender']['email']})"
