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

TESTMODE_FILE_CONTENT = """comment: "testmode file"

backup:
  rsync_source: "backup_testdata_source"
  
process:
  seconds_between_backup_end_and_shutdown: 20
"""
BASE_HOSTNAME_IN_SSH_CONFIG = "basetest"

HIL_RESULT_DIR = Path.cwd().parent/"results"

def setup_logger() -> None:
    LOG.debug("Setting up logger...")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler('logfile.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def check_prequisites():
    if not Path(PCU_SERIAL_DEVICE).exists():
        raise RuntimeError(f"PCU_SERIAL_DEVICE {PCU_SERIAL_DEVICE} is not available")


def open_terminal(device: str, baudrate: int, logfile: Path) -> subprocess.Popen:
    subprocess.call(["stty", "-F", device, str(baudrate)])
    return subprocess.Popen(f"cat {PCU_SERIAL_DEVICE} > {logfile.as_posix()}", shell=True)

class PcuSerialLogger:

    def __init__(self, logfile: Path):
        self._logger_process: Optional[subprocess.Popen] = None
        self._logfile = logfile

    def __enter__(self):
        self._logger_process = open_terminal(PCU_SERIAL_DEVICE, PCU_SERIAL_BAUDRATE, self._logfile)
        LOG.info(f"opened terminal for PCU output with node {PCU_SERIAL_DEVICE}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logger_process.kill()
        self._logger_process.wait(timeout=1)
    def get_logfile(self) -> list[str]:
        with open(self._logfile, 'r') as logfile:
            return logfile.readlines()

def copy_password_file():
    command = "scp .base_password basetest:/home/base/backup-server/hil"
    subprocess.run(command.split())

def remove_password_file():
    command = "ssh basetest rm /home/base/backup-server/hil/.base_password"
    subprocess.run(command.split())

def stop_bcu_service_normalmode(base_name_in_ssh_config: str = BASE_HOSTNAME_IN_SSH_CONFIG, pw_file: str = '.base_password'):
    copy_password_file()
    command = f"ssh {base_name_in_ssh_config} '/home/base/backup-server/hil/stop_bcu_with_normal_config.sh'"
    trials = 0
    maximum_trials = 4
    while trials < maximum_trials:
        p = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        if p.returncode == 0:
            break
        trials += 1
        sleep(0.2)
    remove_password_file()


class BcuTestmode:
    def __init__(self):
        self._testmode_configfile_on_bcu = Path('/home/base/backup-server/software/bcu/config_hiltest.yaml')
        arguments = subprocess.check_output(['systemd-escape', f'" --config {self._testmode_configfile_on_bcu.as_posix()}"']).decode().strip()
        self._bcu_servicename = "backupserver@" + arguments + ".service"

    def start_bcu_service(self, base_name_in_ssh_config: str = BASE_HOSTNAME_IN_SSH_CONFIG, pw_file: str = '.base_password'):
        # command = f"cat {pw_file} | ssh -tt {base_name_in_ssh_config} 'sudo systemctl start {self._bcu_servicename}'"
        command = f"ssh {base_name_in_ssh_config} '/home/base/backup-server/hil/start_bcu_with_test_config.sh'"
        p = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        # Todo: verify service runs and retry if not



    def stop_bcu_service(self, base_name_in_ssh_config: str = BASE_HOSTNAME_IN_SSH_CONFIG, pw_file: str = '.base_password'):
        # command = f"cat {pw_file} | ssh -tt {base_name_in_ssh_config} 'sudo systemctl stop {self._bcu_servicename}'"
        command = f"ssh {base_name_in_ssh_config} '/home/base/backup-server/hil/stop_bcu_with_test_config.sh'"
        p = subprocess.run(command, shell=True, stdout=subprocess.PIPE)

    def copy_test_config(self):
        LOG.info(f"create testmode file on backup server named {BASE_HOSTNAME_IN_SSH_CONFIG}")
        testmode_tempfile = Path("config_hiltest.yaml")
        with open(testmode_tempfile, "w") as f:
            f.write(TESTMODE_FILE_CONTENT)
        subprocess.call(
            f'scp {testmode_tempfile.as_posix()} {BASE_HOSTNAME_IN_SSH_CONFIG}:{self._testmode_configfile_on_bcu.as_posix()}'.split())
        testmode_tempfile.unlink()

    def remove_test_config(self):
        LOG.info(f"removing testmode file on backup server named {BASE_HOSTNAME_IN_SSH_CONFIG}.")
        p = subprocess.run(f'ssh {BASE_HOSTNAME_IN_SSH_CONFIG} rm {self._testmode_configfile_on_bcu.as_posix()}'.split())
        if not p.returncode == 0:
            LOG.warning("couldn't remove testmode file on BaSe")

    def __enter__(self):
        """the way this works
        - we first create the test-config and copy it over to the base into the bcu directory, so it is right next to the regular config.yaml
        - we copy a hidden file that contains the password for the base-user on the base
        - we run a script over ssh which reads the password file and uses it to start the backupserver.service (with arguments)
        """
        self.copy_test_config()
        copy_password_file()
        self.start_bcu_service()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.remove_test_config()
        self.stop_bcu_service()
        remove_password_file()


def create_test_data_on_nas():
    # subprocess.call(Path.cwd().parent/"software"/"utils"/"generate_testdata_on_nas.sh")
    subprocess.call(["ssh", "nas", "/root/datasource/generate.sh"])
    LOG.info("created testdata on nas")


def _ping(ip_address):
    p = subprocess.run(f'ping -c 1 -w 1 {ip_address}'.split(), stdout=subprocess.PIPE)
    return "1 received" in p.stdout.decode()


def resolve_ip(host_name_in_ssh_config: str) -> str:
    command = "ssh -GT " + host_name_in_ssh_config + " | awk '/^hostname / { print $2 }'"
    nas_ip = subprocess.check_output(command, shell=True)
    return nas_ip.decode().strip()


def wait_for_no_ping():
    LOG.info(f"pinging host '{BASE_HOSTNAME_IN_SSH_CONFIG}' on {resolve_ip(BASE_HOSTNAME_IN_SSH_CONFIG)} until it disappears")
    while _ping(resolve_ip(BASE_HOSTNAME_IN_SSH_CONFIG)):
        sleep(1)
    LOG.info(f"{BASE_HOSTNAME_IN_SSH_CONFIG} went to sleep")


def wait_for_ping():
    LOG.info(f"pinging host '{BASE_HOSTNAME_IN_SSH_CONFIG}' on {resolve_ip(BASE_HOSTNAME_IN_SSH_CONFIG)} until it appears")
    while not _ping(resolve_ip(BASE_HOSTNAME_IN_SSH_CONFIG)):
        sleep(1)
    LOG.info(f"{BASE_HOSTNAME_IN_SSH_CONFIG} woke up")


def gather_bcu_logfile(result_dir: Path):
    subprocess.run(f'scp basetest:/home/base/backup-server/software/bcu/logfile.log {result_dir/"bcu.log"}'.split())
    LOG.info(f"got bcu logfile")


def create_result_directory() -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    result_dir = (Path.cwd()/"results"/timestamp)
    result_dir.mkdir(parents=True, exist_ok=True)
    LOG.info(f"created {result_dir.as_posix()} for test results")
    return result_dir


def execute():
    # user has to start bcu hardware but NOT the backupserver.service
    # user has to check out the software they want to test
    check_prequisites()
    stop_bcu_service_normalmode()
    setup_logger()
    result_dir = create_result_directory()
    create_test_data_on_nas()
    with PcuSerialLogger(result_dir/'pcu_serial.log') as pcu_serial_logger:
        with BcuTestmode() as bcu_testmode:
            wait_for_no_ping()  # bcu shutdown
            wait_for_ping()  # bcu restart/wakeup
        stop_bcu_service_normalmode()
    pcu_serial_logger.get_logfile()
    gather_bcu_logfile(result_dir)

    # assert stuff
