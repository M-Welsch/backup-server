import subprocess
from datetime import datetime
from pathlib import Path
from shutil import copy
from time import sleep
from typing import Optional

import logging

LOG = logging.getLogger(__name__)

PCU_SERIAL_DEVICE = '/dev/ttySTLINK'
PCU_SERIAL_BAUDRATE = 38400

TESTMODE_FILE = Path.cwd().parent / "software" / "bcu" / "testmode"
BASE_HOSTNAME_IN_SSH_CONFIG = "basetest"

HIL_RESULT_DIR = Path.cwd().parent/"results"


def open_terminal(device: str, baudrate: int, logfile: Path) -> subprocess.Popen:
    return subprocess.Popen(" ".join(['minicom', '-D', device, '-b', str(baudrate), '-C', logfile.as_posix()]), shell=True)


class PcuSerialLogger:
    def __init__(self, logfile: Path):
        self._logger_process: Optional[subprocess.Popen] = None
        self._logfile = logfile

    def __enter__(self):
        open_terminal(PCU_SERIAL_DEVICE, PCU_SERIAL_BAUDRATE, self._logfile)
        LOG.info(f"opened terminal for PCU output with node {PCU_SERIAL_DEVICE}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logger_process.kill()
        self._logger_process.wait(timeout=1)

    def get_logfile(self) -> list[str]:
        with open(self._logfile, 'r') as logfile:
            return logfile.readlines()


def create_test_data_on_nas():
    # subprocess.call(Path.cwd().parent/"software"/"utils"/"generate_testdata_on_nas.sh")
    subprocess.call(["ssh", "nas", "/root/datasource/generate.sh"])
    LOG.info("created testdata on nas")


def put_bcu_into_testmode():
    LOG.info(f"create testmode file {TESTMODE_FILE.as_posix()}")
    with open(TESTMODE_FILE, "w") as f:
        f.write(
            'this file puts the bcu into test mode, which means:\n\n'
        '- backup datasource is "backup_testdata_source" instead of "backup_datasource"'
        )

def put_bcu_into_normal_mode():
    if not TESTMODE_FILE.exists():
        LOG.warning(f"testmode file {TESTMODE_FILE.as_posix()} doesn't exist")
    else:
        TESTMODE_FILE.unlink()


def wait_for_backup_server_service_to_start():
    print("Action Required: log into backup-server and type 'systemctl start backupserver'")
    while True:
        p = subprocess.run("ssh basetest systemctl status backupserver".split(), stdout=subprocess.PIPE)
        if "Active: active" in p.stdout.decode():
            LOG.info("backupserver service is active now")
            break
        sleep(1)


def _ping(ip_address):
    p = subprocess.run(f'ping -c 1 -w 1 {ip_address}'.split(), stdout=subprocess.PIPE)
    return "1 received" in p.stdout.decode()

def resolve_ip(host_name_in_ssh_config: str) -> str:
    command = "ssh -G " + host_name_in_ssh_config + " | awk '/^hostname / { print $2 }'"
    nas_ip = subprocess.check_output(command, shell=True)
    return nas_ip.decode().strip()

def wait_for_no_ping():
    while _ping(resolve_ip(BASE_HOSTNAME_IN_SSH_CONFIG)):
        sleep(1)
    LOG.info(f"{BASE_HOSTNAME_IN_SSH_CONFIG} went to sleep")


def wait_for_ping():
    while not _ping(resolve_ip(BASE_HOSTNAME_IN_SSH_CONFIG)):
        sleep(1)
    LOG.info(f"{BASE_HOSTNAME_IN_SSH_CONFIG} woke up")


def stop_bcu_service():
    print("Action Required: log into backup-server and type 'systemctl stop backupserver'")
    # we don't wait here.


def gather_bcu_logfile(result_dir: Path):
    bcu_logfile = Path.cwd().parent/"software"/"bcu"/"logfile.log"
    copy(src=bcu_logfile, dst=result_dir)
    LOG.info(f"got bcu logfile: {bcu_logfile.as_posix()}")


def create_result_directory() -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    result_dir = (Path.cwd()/"results"/timestamp)
    result_dir.mkdir(parents=True, exist_ok=True)
    LOG.info(f"created {result_dir.as_posix()} for test results")
    return result_dir


def execute():
    # user has to start bcu hardware but NOT the backupserver.service
    # user has to check out the software they want to test
    result_dir = create_result_directory()
    create_test_data_on_nas()
    put_bcu_into_testmode()
    with PcuSerialLogger(result_dir/'pcu_serial.log') as pcu_serial_logger:
        wait_for_backup_server_service_to_start()
        wait_for_no_ping()  # bcu shutdown
        wait_for_ping()  # bcu restart/wakeup
        stop_bcu_service()
    pcu_serial_logger.get_logfile()
    gather_bcu_logfile(result_dir)
    put_bcu_into_normal_mode()

    # assert stuff

