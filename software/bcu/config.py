import logging
from datetime import timedelta
from pathlib import Path
import yaml

LOG = logging.getLogger(__name__)


def _load_cfg_from_yaml(file: Path) -> dict:
    with open(file, 'r') as cfg_file:
        return yaml.safe_load(cfg_file)


def load_config(config_file: Path) -> dict:
    config = _load_cfg_from_yaml(config_file)
    return config


def get_sleep_time(config) -> timedelta:
    days = config.get("days", 7)
    hours = config.get("hours", 0)
    minutes = config.get("minutes", 0)
    return timedelta(days=days, hours=hours, minutes=minutes)
