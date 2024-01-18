from pathlib import Path

from hil_execution import execute


PCU_SERIAL_DEVICE = '/dev/ttySTLINK'
PCU_SERIAL_BAUDRATE = 38400

BASE_HOSTNAME_IN_SSH_CONFIG = "basetest"

TESTMODE_FILE_PATH = Path('/home/base/backup-server/software/bcu/config_hiltest.yaml')
TESTMODE_FILE_CONTENT = """comment: "testmode file"

logger:
  filename: "temp_logfile_hiltest.log"

backup:
  rsync_source: "backup_testdata_source"

process:
  seconds_between_backup_end_and_shutdown: 20
"""


if __name__ == "__main__":
    execute(
        PCU_SERIAL_DEVICE, PCU_SERIAL_BAUDRATE, BASE_HOSTNAME_IN_SSH_CONFIG, TESTMODE_FILE_PATH, TESTMODE_FILE_CONTENT
    )