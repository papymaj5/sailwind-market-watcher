"""Defaults and persisted player inputs for Market Watcher."""

import json
import math
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

APP_DIR = Path(__file__).resolve().parent


def read_app_version(path):
    try:
        metadata = path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    version = re.search(r'^version\s*=\s*"([^"]+)"', metadata, re.MULTILINE)
    return version[1] if version else "unknown"


APP_VERSION = read_app_version(APP_DIR / "pyproject.toml")
with (APP_DIR / "config.json").open(encoding="utf-8") as file:
    CONFIG = json.load(file)

PLAYER_SETTINGS = CONFIG["player_settings"]
DEFAULT_CURRENCY = PLAYER_SETTINGS["currency"]
GOLD_CURRENCY = "Gold Lions"
PLAYER_SETTINGS_PATH = (
    Path(os.environ.get("LOCALAPPDATA") or Path.home())
    / "SailwindMarketWatcher"
    / "player-settings.json"
)


def load_player_settings(path):
    settings = PLAYER_SETTINGS.copy()
    rates = settings["conversion_rates"] = PLAYER_SETTINGS["conversion_rates"].copy()
    try:
        with path.open(encoding="utf-8") as file:
            saved_settings = json.load(file)
    except (OSError, ValueError):
        return settings

    if not isinstance(saved_settings, dict):
        return settings
    for key in ("auto_rates", "auto_balance"):
        if isinstance(saved_settings.get(key), bool):
            settings[key] = saved_settings[key]

    for key in ("principal", "mass_limit", "volume_limit", "min_profit"):
        value = saved_settings.get(key)
        if type(value) in (int, float) and abs(value) < math.inf:
            settings[key] = value

    currency = saved_settings.get("currency")
    if isinstance(currency, str) and currency in rates:
        settings["currency"] = currency
    saved_rates = saved_settings.get("conversion_rates")
    if not isinstance(saved_rates, dict):
        saved_rates = {DEFAULT_CURRENCY: saved_settings.get("conversion_rate")}
    for currency in rates:
        rate = saved_rates.get(currency)
        if (
            currency != GOLD_CURRENCY
            and type(rate) in (int, float)
            and 0 < rate < math.inf
        ):
            rates[currency] = rate
    return settings


def save_player_settings(path, settings):
    path.parent.mkdir(parents=True, exist_ok=True)
    file = NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False)
    temporary_path = Path(file.name)
    try:
        with file:
            json.dump(settings, file, indent=2, allow_nan=False)
            file.write("\n")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


class Player:
    def __init__(self):
        self.update(**load_player_settings(PLAYER_SETTINGS_PATH))

    def update(
        self,
        principal,
        mass_limit,
        volume_limit,
        min_profit,
        currency,
        conversion_rates,
        auto_rates,
        auto_balance,
    ):
        self.principal = principal
        self.mass_limit = mass_limit
        self.volume_limit = volume_limit
        self.min_profit = min_profit
        self.currency = currency
        self.conversion_rates = conversion_rates
        self.auto_rates = auto_rates
        self.auto_balance = auto_balance

    @property
    def conversion_rate(self):
        return self.conversion_rates[self.currency]

    def __repr__(self):
        # Print float values without decimals
        return (
            f"Player:\n Principal: {self.principal:.0f} {self.currency}\n Rate: {self.conversion_rate}\n "
            f"Mass: {self.mass_limit:.0f}\n Volume: {self.volume_limit:.0f}"
        )
