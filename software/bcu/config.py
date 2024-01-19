import logging
from pathlib import Path
from typing import Dict, Any, TypeVar

import yaml
import collections.abc

LOG = logging.getLogger(__name__)


def testmode(testmode_file: Path):
    return testmode_file.exists()

def _load_cfg_from_yaml(file: Path) -> dict:
    with open(file, 'r') as cfg_file:
        return yaml.safe_load(cfg_file)


KeyType = TypeVar('KeyType')


def deep_update(mapping: Dict[KeyType, Any], *updating_mappings: Dict[KeyType, Any]) -> Dict[KeyType, Any]:
    # taken from pydantic: https://github.com/pydantic/pydantic/blob/9d631a3429a66f30742c1a52c94ac18ec6ba848d/pydantic/utils.py#L198
    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if k in updated_mapping and isinstance(updated_mapping[k], dict) and isinstance(v, dict):
                updated_mapping[k] = deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping


def load_config(config_file: Path, testmode_file: Path = Path('testmode')) -> dict:
    config = _load_cfg_from_yaml(config_file)
    if testmode(testmode_file):
        LOG.warning("Testmode activated! Will use 'backup_testdata_source' regardless of what is configured!")
        test_config = _load_cfg_from_yaml(testmode_file)
        config = deep_update(config, test_config)
    return config
