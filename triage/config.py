"""Locating and loading configuration (rules, templates, optional .env)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DEFAULT_RULES_PATH = CONFIG_DIR / "rules.json"
DEFAULT_ACK_PATH = CONFIG_DIR / "acknowledgements.json"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "requests.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


class ConfigError(Exception):
    """Raised when a configuration file is missing or malformed."""


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"{label} file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{label} file is not valid JSON ({path}): {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{label} file must contain a JSON object: {path}")
    return data


def load_rules(path: str | Path | None = None) -> dict[str, Any]:
    rules = _load_json(Path(path) if path else DEFAULT_RULES_PATH, "Rules")
    for section in ("categorisation", "validation", "review"):
        if section not in rules:
            raise ConfigError(f"Rules file is missing the '{section}' section")
    if not rules["categorisation"].get("categories"):
        raise ConfigError("Rules file defines no categories")
    return rules


def load_ack_config(path: str | Path | None = None) -> dict[str, Any]:
    config = _load_json(Path(path) if path else DEFAULT_ACK_PATH, "Acknowledgement")
    if "template" not in config:
        raise ConfigError("Acknowledgement file is missing the 'template' entry")
    return config


def load_dotenv(path: str | Path | None = None, *, override: bool = False) -> int:
    """Minimal .env loader (KEY=VALUE per line, '#' comments). Returns count set.

    Kept deliberately small so the prototype has no third-party dependency.
    Existing environment variables win unless ``override`` is True.
    """
    env_path = Path(path) if path else PROJECT_ROOT / ".env"
    if not env_path.exists():
        return 0
    count = 0
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
            count += 1
    return count
