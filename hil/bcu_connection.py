from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from time import sleep
from types import TracebackType

from typing import Optional, Type


LOG = logging.getLogger(__name__)


class BCUConnection:
    def __init__(self, base_hostname: str, config_file_path: Path, config_file_content: str) -> None:
        self._base_hostname = base_hostname
        self._config_file_content = config_file_content
        self._config_file_path = config_file_path

    def __enter__(self) -> BCUConnection:
        """the way this works
        - we first create the test-config and copy it over to the base into the bcu directory,
          so it is right next to the regular config.yaml
        - we copy a hidden file that contains the password for the base-user on the base
        - we run a script over ssh which reads the password file and uses it to start the backupserver.service
          (with arguments)
        """
        trials = 0
        maximum_trials = 10
        while trials < maximum_trials:
            if self._copy_password_file() == 0:
                break
            trials += 1
            sleep(0.5)
        if trials == maximum_trials:
            LOG.warning(f"couldn't stop bcu service within {maximum_trials} trials, waiting 0.5s in between")
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        self._remove_password_file()

    def _copy_password_file(self) -> int:
        command = f"scp .base_password {self._base_hostname}:/home/base/backup-server/hil"
        return subprocess.run(command.split()).returncode

    def _remove_password_file(self) -> int:
        command = f"ssh {self._base_hostname} rm /home/base/backup-server/hil/.base_password"
        return subprocess.run(command.split()).returncode

    def copy_test_config(self) -> None:
        LOG.info(f"create testmode file on backup server named {self._base_hostname}")
        testmode_tempfile = Path("config_hiltest.yaml")
        with open(testmode_tempfile, "w") as f:
            f.write(self._config_file_content)
        subprocess.call(
            f'scp {testmode_tempfile.as_posix()} {self._base_hostname}:{self._config_file_path.as_posix()}'.split())
        testmode_tempfile.unlink()

    def remove_test_config(self) -> None:
        LOG.info(f"removing testmode file on backup server named {self._base_hostname}.")
        p = subprocess.run(f'ssh {self._base_hostname} rm {self._config_file_path.as_posix()}'.split())
        if not p.returncode == 0:
            LOG.warning("couldn't remove testmode file on BaSe")

    def stop_normal_mode(self) -> None:
        command = f"ssh {self._base_hostname} '/home/base/backup-server/hil/stop_bcu_with_normal_config.sh'"
        LOG.debug(f'attempting to stop bcu service with "{command}"')
        subprocess.run(command, shell=True, stdout=subprocess.PIPE)

    def start_test_mode(self) -> None:
        command = f"ssh {self._base_hostname} '/home/base/backup-server/hil/start_bcu_with_test_config.sh'"
        subprocess.run(command, shell=True, stdout=subprocess.PIPE)

    def stop_test_mode(self) -> None:
        command = f"ssh {self._base_hostname} '/home/base/backup-server/hil/stop_bcu_with_test_config.sh'"
        subprocess.run(command, shell=True, stdout=subprocess.PIPE)
