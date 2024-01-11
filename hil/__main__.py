import subprocess
from pathlib import Path
from typing import Optional

PCU_SERIAL_DEVICE = '/dev/ttySTLINK'
PCU_SERIAL_BAUDRATE = 38400


class PcuSerialLogger:
    def __init__(self, logfile_name):
        self._logger_process: Optional[subprocess.Popen] = None
        self._logfile = logfile_name

    def __enter__(self):
        self._logger_process = subprocess.Popen(['minicom', '-D', PCU_SERIAL_DEVICE, '-b', PCU_SERIAL_BAUDRATE, '-C', self._logfile])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logger_process.kill()
        self._logger_process.wait(timeout=1)

    def get_logfile(self) -> list[str]:
        with open(self._logfile, 'r') as logfile:
            return logfile.readlines()


def create_test_data_on_nas():
    subprocess.call(Path.cwd().parent/"software"/"utils"/"generate_testdata_on_nas.sh")


def start_bcu_service():
    subprocess.call(
        ['ssh', 'basetest', 'cd /home/base/backup-server/software/bcu', '&&', '/usr/bin/python3', '.', '--test-args',
         'zeugs43'])  # replace with meaningful command


def main():
    # user has to start bcu hardware but NOT the backupserver.service
    # user has to check out the software they want to test
    create_test_data_on_nas()
    with PcuSerialLogger('pcu_serial.log') as pcu_serial_logger:
        start_bcu_service()  # bcu firmware docks, performs backup, undocks, shuts down, starts up again
        wait_for_no_ping()  # bcu shutdown
        wait_for_ping()  # bcu restart/wakeup
        stop_bcu_service()
    pcu_serial_logger.get_logfile()
    gather_bcu_logfile()

    # assert stuff
