import logging
from pathlib import Path
import yaml

LOG = logging.getLogger(__name__)


def _load_cfg_from_yaml(file: Path) -> dict:
    with open(file, 'r') as cfg_file:
        return yaml.safe_load(cfg_file)


def load_config(config_file: Path) -> dict:
    config = _load_cfg_from_yaml(config_file)
    return config
