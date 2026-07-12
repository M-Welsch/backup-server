import subprocess
from pathlib import Path

import logging

LOG = logging.getLogger(__file__)


def push_logfile_to_nas_over_ssh(logfile_local: Path, logfile_remote: Path, remote_ssh_login: str):
    command = f"scp {logfile_local.as_posix()} {remote_ssh_login}:{logfile_remote.as_posix()}"
    LOG.debug(f"pushing logfile to NAS using: {command}")
    subprocess.run(command, shell=True, timeout=10)


async def copy_logfile_to_nas(config: dict) -> None:
    try:
        logfile_local: Path = Path(config["logger"]["logfile.log"])
        logfile_remote: Path = Path(config["debug"]["remote_logging_logfile_path"])
        remote_ssh_login = config["debug"]["remote_ssh_connect_string"]
        push_logfile_to_nas_over_ssh(logfile_local, logfile_remote, remote_ssh_login)
    except Exception as e:
        LOG.warning("pushing logfile to NAS failed.")
        LOG.exception(e)
