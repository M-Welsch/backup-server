import yaml
from py import path
from pathlib import Path

from config import load_config


normal_cfg = """backup:
  nas_name_in_ssh_config: nas
  rsync_source: backup_data_source

process:
  seconds_between_backup_end_and_shutdown: 60
"""


testmode_cfg = """backup:
  rsync_source: backup_testdata_source
  
process:
  seconds_between_backup_end_and_shutdown: 60
"""


def test_normal_config(tmp_path: path.local) -> None:
    tmp_path = Path(tmp_path)
    normal_config_file = tmp_path/"test_normal_cfg.yaml"
    testmode_config_file = tmp_path/"testmode_config_file"
    with open(normal_config_file, "w") as f:
        f.write(normal_cfg)
    print(f"working in temp path " + tmp_path.as_posix())
    cfg = load_config(normal_config_file, testmode_file=testmode_config_file)
    cfg_ref = yaml.load(normal_cfg)
    assert cfg == cfg_ref


def test_testmode_config(tmp_path: path.local) -> None:
    tmp_path = Path(tmp_path)
    normal_config_file = tmp_path/"test_normal_cfg.yaml"
    testmode_config_file = tmp_path/"testmode_config_file"
    with open(normal_config_file, "w") as f:
        f.write(normal_cfg)
    with open(testmode_config_file, "w") as f:
        f.write(testmode_cfg)
    print(f"working in temp path " + tmp_path.as_posix())
    cfg = load_config(normal_config_file, testmode_file=testmode_config_file)
    cfg_normal_ref = yaml.load(normal_cfg)
    cfg_testmode_ref = yaml.load(testmode_cfg)
    assert cfg_normal_ref["backup"]["nas_name_in_ssh_config"] == cfg["backup"]["nas_name_in_ssh_config"]
    assert cfg_testmode_ref["backup"]["rsync_source"] == cfg["backup"]["rsync_source"]

