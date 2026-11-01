import logging
import math
from datetime import timedelta
from pathlib import Path
from uuid import UUID
import yaml

LOG = logging.getLogger(__name__)


def _load_cfg_from_yaml(file: Path) -> dict:
    with open(file, 'r') as cfg_file:
        return yaml.safe_load(cfg_file)


def load_config(config_file: Path) -> dict:
    config = _load_cfg_from_yaml(config_file)
    validate_config(config)
    return config


def validate_config(cfg):
    if not isinstance(cfg, dict) or not isinstance(cfg.get("backup"), dict):
        raise ValueError("Configuration must contain a backup mapping")
    backup = cfg["backup"]
    uuid = backup.get("filesystem_uuid")
    if not isinstance(uuid, str) or str(UUID(uuid)) != uuid:
        raise ValueError("backup.filesystem_uuid must be a canonical filesystem UUID")
    if not isinstance(backup.get("rsync_source"), str) or not backup["rsync_source"]:
        raise ValueError("backup.rsync_source must be configured")
    mountpoint = Path(backup.get("mountpoint", "/media/BackupHDD"))
    destination = Path(backup.get("destination", "backups/current"))
    if not mountpoint.is_absolute() or mountpoint == Path("/") or ".." in mountpoint.parts:
        raise ValueError("backup.mountpoint must be an absolute, non-root path")
    if destination.is_absolute() or ".." in destination.parts or destination == Path("."):
        raise ValueError("backup.destination must be a relative path below the mountpoint")
    for section in (cfg.get("process", {}), backup.get("integrity", {}), cfg.get("logger", {}), cfg.get("debug", {})):
        if not isinstance(section, dict):
            raise ValueError("process, integrity, logger, and debug settings must be mappings")
    process = cfg.get("process", {})
    state_file = Path(process.get("state_file", "~/.local/state/bcu/state.json")).expanduser().absolute()
    if state_file == mountpoint or mountpoint in state_file.parents:
        raise ValueError("Recovery state must live on the Pi, not on the backup HDD")
    limits = (
        (backup, ("storage_timeout_seconds", "monitor_interval_seconds", "backup_timeout_seconds"), False),
        (backup.get("integrity", {}), ("interval_days", "timeout_seconds", "restore_timeout_seconds",
                                     "restore_samples", "restore_max_file_bytes"), False),
        (process, ("pcu_timeout_seconds",), False),
        (process, ("seconds_between_backup_end_and_shutdown", "maximum_reboots"), True),
    )
    for section, names, zero_allowed in limits:
        for name in names:
            if name in section:
                value = section[name]
                if (type(value) not in (int, float) or not math.isfinite(value)
                        or value < 0 or (value == 0 and not zero_allowed)):
                    raise ValueError("Invalid numeric setting: {}".format(name))
    for section, key in ((process, "maximum_reboots"), (backup.get("integrity", {}), "restore_samples")):
        if key in section and type(section[key]) is not int:
            raise ValueError("{} must be an integer".format(key))
    interval = process.get("time_between_backups", {})
    if not isinstance(interval, dict) or get_sleep_time(interval).total_seconds() <= 0:
        raise ValueError("time_between_backups must describe a positive interval")


def get_sleep_time(config) -> timedelta:
    days = config.get("days", 7)
    hours = config.get("hours", 0)
    minutes = config.get("minutes", 0)
    return timedelta(days=days, hours=hours, minutes=minutes)
