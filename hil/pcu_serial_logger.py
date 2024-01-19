from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from types import TracebackType

from typing import Optional, Type


LOG = logging.getLogger(__name__)


class PcuSerialLogger:
    def __init__(self, device: str, baud_rate: int, logfile: Path) -> None:
        self._logger_process: Optional[subprocess.Popen] = None
        self._device = device
        self._baud_rate = baud_rate
        self._logfile = logfile

    def __enter__(self) -> PcuSerialLogger:
        self._logger_process = self._open_terminal()
        LOG.info(f"opened terminal for PCU output with node {self._device}")
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        self._logger_process.kill()
        self._logger_process.wait(timeout=1)

    def _open_terminal(self) -> subprocess.Popen:
        subprocess.call(["stty", "-F", self._device, str(self._baud_rate)])
        return subprocess.Popen(f"cat {self._device} > {self._logfile.as_posix()}", shell=True)

    def get_logfile(self) -> list[str]:
        with open(self._logfile, 'r') as logfile:
            return logfile.readlines()
