from __future__ import annotations

import logging
import subprocess
from time import sleep


LOG = logging.getLogger(__name__)


def wait_until_rebooted(hostname: str) -> None:
    def _ping(ip_address: str) -> bool:
        p = subprocess.run(f'ping -c 1 -w 1 {ip_address}'.split(), stdout=subprocess.PIPE)
        return "1 received" in p.stdout.decode()

    def _resolve_ip() -> str:
        command = "ssh -GT " + hostname + " | awk '/^hostname / { print $2 }'"
        nas_ip = subprocess.check_output(command, shell=True)
        return nas_ip.decode().strip()

    def wait_for_no_ping() -> None:
        ip_address = _resolve_ip()
        LOG.info(f"pinging host '{hostname}' on {ip_address} until it disappears")
        while _ping(ip_address):
            sleep(1)
        LOG.info(f"{hostname} went to sleep")

    def wait_for_ping() -> None:
        ip_address = _resolve_ip()
        LOG.info(f"pinging host '{hostname}' on {ip_address} until it appears")
        while not _ping(ip_address):
            sleep(1)
        LOG.info(f"{hostname} woke up")

    wait_for_no_ping()  # bcu shutdown
    wait_for_ping()  # bcu restart/wakeup