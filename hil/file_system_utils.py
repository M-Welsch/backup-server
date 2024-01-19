from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path

LOG = logging.getLogger(__name__)


def gather_bcu_logfile(base_hostname: str, log_file: Path) -> None:
    subprocess.run(f'scp {base_hostname}:/home/base/backup-server/software/bcu/temp_logfile_hiltest.log {log_file}'.split())
    LOG.info(f"got bcu logfile")


def create_result_directory(parent: Path) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    result_dir = parent / "results" / timestamp
    result_dir.mkdir(parents=True, exist_ok=True)
    LOG.info(f"created {result_dir.as_posix()} for test results")
    return result_dir


def create_test_data_on_nas() -> None:
    subprocess.call(["ssh", "nas", "/root/datasource/generate.sh"])
    LOG.info("created testdata on nas")