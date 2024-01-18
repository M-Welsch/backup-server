import subprocess
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Optional

import logging

LOG = logging.getLogger(__name__)


def setup_logger(log_dir: Path) -> None:
    LOG.debug("Setting up logger...")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_dir / 'hil.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def check_prerequisites(device):
    if not Path(device).exists():
        raise RuntimeError(f"PCU_SERIAL_DEVICE {device} is not available")


class PcuSerialLogger:
    def __init__(self, device: str, baud_rate: int, logfile: Path):
        self._logger_process: Optional[subprocess.Popen] = None
        self._device = device
        self._baud_rate = baud_rate
        self._logfile = logfile

    def __enter__(self):
        self._logger_process = self._open_terminal()
        LOG.info(f"opened terminal for PCU output with node {self._device}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logger_process.kill()
        self._logger_process.wait(timeout=1)

    def _open_terminal(self) -> subprocess.Popen:
        subprocess.call(["stty", "-F", self._device, str(self._baud_rate)])
        return subprocess.Popen(f"cat {self._device} > {self._logfile.as_posix()}", shell=True)

    def get_logfile(self) -> list[str]:
        with open(self._logfile, 'r') as logfile:
            return logfile.readlines()


def copy_password_file(hostname: str):
    command = f"scp .base_password {hostname}:/home/base/backup-server/hil"
    subprocess.run(command.split())


def remove_password_file(hostname: str):
    command = f"ssh {hostname} rm /home/base/backup-server/hil/.base_password"
    subprocess.run(command.split())


def stop_bcu_service_normal_mode(base_hostname: str):
    copy_password_file(base_hostname)
    command = f"ssh {base_hostname} '/home/base/backup-server/hil/stop_bcu_with_normal_config.sh'"
    trials = 0
    maximum_trials = 10
    while trials < maximum_trials:
        LOG.debug(f'attempting to stop bcu service with "{command}"')
        p = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        if p.returncode == 0:
            break
        trials += 1
        sleep(0.5)
    if trials == maximum_trials:
        LOG.warning(f"couldn't stop bcu service within {maximum_trials} trials, waiting 0.5s in between")
    remove_password_file(base_hostname)


class BcuTestMode:
    def __init__(self, base_hostname: str, config_file_path: Path, config_file_content: str):
        self._base_hostname = base_hostname
        self._config_file_content = config_file_content
        self._config_file_path = config_file_path
        arguments = subprocess.check_output(
            ['systemd-escape', f'" --config {self._config_file_path.as_posix()}"']
        ).decode().strip()
        self._bcu_service_name = f"backupserver@{arguments}.service"

    def _start_bcu_service(self):
        # command = f"cat {pw_file} | ssh -tt {self._base_hostname} 'sudo systemctl start {self._bcu_service_name}'"
        command = f"ssh {self._base_hostname} '/home/base/backup-server/hil/start_bcu_with_test_config.sh'"
        subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        # Todo: verify service runs and retry if not

    def _stop_bcu_service(self):
        # command = f"cat {pw_file} | ssh -tt {self._base_hostname} 'sudo systemctl stop {self._bcu_service_name}'"
        command = f"ssh {self._base_hostname} '/home/base/backup-server/hil/stop_bcu_with_test_config.sh'"
        subprocess.run(command, shell=True, stdout=subprocess.PIPE)

    def _copy_test_config(self):
        LOG.info(f"create testmode file on backup server named {self._base_hostname}")
        testmode_tempfile = Path("config_hiltest.yaml")
        with open(testmode_tempfile, "w") as f:
            f.write(self._config_file_content)
        subprocess.call(
            f'scp {testmode_tempfile.as_posix()} {self._base_hostname}:{self._config_file_path.as_posix()}'.split())
        testmode_tempfile.unlink()

    def _remove_test_config(self):
        LOG.info(f"removing testmode file on backup server named {self._base_hostname}.")
        p = subprocess.run(f'ssh {self._base_hostname} rm {self._config_file_path.as_posix()}'.split())
        if not p.returncode == 0:
            LOG.warning("couldn't remove testmode file on BaSe")

    def __enter__(self):
        """the way this works
        - we first create the test-config and copy it over to the base into the bcu directory, so it is right next to the regular config.yaml
        - we copy a hidden file that contains the password for the base-user on the base
        - we run a script over ssh which reads the password file and uses it to start the backupserver.service (with arguments)
        """
        self._copy_test_config()
        copy_password_file(self._base_hostname)
        self._start_bcu_service()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remove_test_config()
        self._stop_bcu_service()
        remove_password_file(self._base_hostname)


def create_test_data_on_nas():
    # subprocess.call(Path.cwd().parent/"software"/"utils"/"generate_testdata_on_nas.sh")
    subprocess.call(["ssh", "nas", "/root/datasource/generate.sh"])
    LOG.info("created testdata on nas")


def wait_until_rebooted(hostname: str):
    def _ping(ip_address):
        p = subprocess.run(f'ping -c 1 -w 1 {ip_address}'.split(), stdout=subprocess.PIPE)
        return "1 received" in p.stdout.decode()

    def _resolve_ip() -> str:
        command = "ssh -GT " + hostname + " | awk '/^hostname / { print $2 }'"
        nas_ip = subprocess.check_output(command, shell=True)
        return nas_ip.decode().strip()

    def wait_for_no_ping():
        ip_address = _resolve_ip()
        LOG.info(f"pinging host '{hostname}' on {ip_address} until it disappears")
        while _ping(ip_address):
            sleep(1)
        LOG.info(f"{hostname} went to sleep")

    def wait_for_ping():
        ip_address = _resolve_ip()
        LOG.info(f"pinging host '{hostname}' on {ip_address} until it appears")
        while not _ping(ip_address):
            sleep(1)
        LOG.info(f"{hostname} woke up")

    wait_for_no_ping()  # bcu shutdown
    wait_for_ping()  # bcu restart/wakeup


def gather_bcu_logfile(base_hostname: str, log_file: Path):
    subprocess.run(f'scp {base_hostname}:/home/base/backup-server/software/bcu/temp_logfile_hiltest.log {log_file}'.split())
    LOG.info(f"got bcu logfile")


def create_result_directory(parent: Path) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    result_dir = parent / "results" / timestamp
    result_dir.mkdir(parents=True, exist_ok=True)
    LOG.info(f"created {result_dir.as_posix()} for test results")
    return result_dir


def execute(
        pcu_serial_device: str,
        pcu_serial_baud_rate: int,
        base_hostname: str,
        testmode_file_path: Path,
        testmode_file_content: str
):
    # user has to start bcu hardware but NOT the backupserver.service
    # user has to check out the software they want to test
    check_prerequisites(device=pcu_serial_device)
    stop_bcu_service_normal_mode(base_hostname=base_hostname)
    result_dir = create_result_directory(parent=Path.cwd())
    setup_logger(log_dir=result_dir)
    create_test_data_on_nas()
    with PcuSerialLogger(
            device=pcu_serial_device, baud_rate=pcu_serial_baud_rate, logfile=result_dir / "pcu.log"
    ) as pcu_serial_logger:
        with BcuTestMode(
                base_hostname=base_hostname,
                config_file_path=testmode_file_path,
                config_file_content=testmode_file_content
        ):
            wait_until_rebooted(hostname=base_hostname)
        stop_bcu_service_normal_mode(base_hostname=base_hostname)
    pcu_serial_logger.get_logfile()
    gather_bcu_logfile(base_hostname=base_hostname, log_file=result_dir / "bcu.log")

    # assert stuff
