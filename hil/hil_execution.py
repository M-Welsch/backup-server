from __future__ import annotations
from pathlib import Path

import logging

from bcu_connection import BCUConnection
from file_system_utils import gather_bcu_logfile, create_result_directory, create_test_data_on_nas
from network_utils import wait_until_rebooted
from pcu_serial_logger import PcuSerialLogger

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


def check_prerequisites(device: str) -> None:
    if not Path(device).exists():
        raise RuntimeError(f"PCU_SERIAL_DEVICE {device} is not available")


def execute(
        pcu_serial_device: str,
        pcu_serial_baud_rate: int,
        base_hostname: str,
        testmode_file_path: Path,
        testmode_file_content: str
) -> None:
    """
    Perform HIL test.

    user has to start bcu hardware but NOT the backupserver.service
    user has to check out the software they want to test

    :param pcu_serial_device:
    :param pcu_serial_baud_rate:
    :param base_hostname:
    :param testmode_file_path:
    :param testmode_file_content:
    :return:
    """
    check_prerequisites(device=pcu_serial_device)
    result_dir = create_result_directory(parent=Path.cwd())
    setup_logger(log_dir=result_dir)
    create_test_data_on_nas()

    with PcuSerialLogger(
            device=pcu_serial_device, baud_rate=pcu_serial_baud_rate, logfile=result_dir / "pcu.log"
    ) as pcu_serial_logger:
        with BCUConnection(
                base_hostname=base_hostname,
                config_file_path=testmode_file_path,
                config_file_content=testmode_file_content
        ) as connection:
            connection.stop_normal_mode()
            try:
                connection.copy_test_config()
                connection.start_test_mode()
                wait_until_rebooted(hostname=base_hostname)
            finally:
                connection.remove_test_config()
            connection.stop_normal_mode()


    pcu_serial_logger.get_logfile()
    gather_bcu_logfile(base_hostname=base_hostname, log_file=result_dir / "bcu.log")

    # TODO: assert stuff
