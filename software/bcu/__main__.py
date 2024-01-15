import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
import argparse
from pathlib import Path

import pcu
from config import load_config

LOG = logging.getLogger(__name__)


def setup_logger() -> None:
    LOG.debug("Setting up logger...")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler('logfile.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


async def init():
    setup_logger()
    await pcu.handshake()


async def engage() -> None:
    LOG.info("Connect Backup HDD")
    LOG.debug("Docking...")
    docking_trials = 0
    while not await pcu.cmd.dock():
        LOG.warning("couldn't dock, try another time.")
        docking_trials += 1
        if docking_trials == 4:  # this is a workaround for issue #25
            raise RuntimeError("couldn't dock with two trials")
    LOG.debug("Switching HDD power on...")
    await pcu.cmd.power.hdd.on()
    await asyncio.sleep(2)  # workaround for #26
    LOG.debug("Mounting HDD...")
    subprocess.call(["mount", "/dev/BACKUPHDD"])


async def handle_output(pipe):
    while True:
        line = await pipe.readline()
        if not line:
            break
        LOG.debug(f"Live Output: {line.decode().rstrip()}")


def resolve_ip(host_name_in_ssh_config: str) -> str:
    command = "ssh -G " + host_name_in_ssh_config + " | awk '/^hostname / { print $2 }'"
    nas_ip = subprocess.check_output(command, shell=True)
    return nas_ip.decode().strip()


async def backup(config: dict):
    source = config["rsync_source"]
    nas_ip = resolve_ip(host_name_in_ssh_config="nas")
    LOG.debug(f"obtained IP Address of NAS: {nas_ip}")
    backup_command = [
        "rsync",
        "-aH",
        "--stats",
        "--delete",
        f"{nas_ip}::{source}/*",
        "/media/BackupHDD/backups/current"
    ]
    LOG.debug(f"Backing up with command {' '.join(backup_command)}")
    process = await asyncio.create_subprocess_exec(
        *backup_command,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    output_task = asyncio.create_task(handle_output(process.stdout))

    LOG.info("Starting Backup...")
    await process.wait()
    LOG.info("Backup finished.")
    await output_task
    LOG.debug("Backup output task finished.")

    stderr = await process.stderr.read()
    if stderr:
        LOG.error(f"Fehlerausgabe: {stderr.decode()}")
        exit(-1)  # to trace bug #19


async def disengage() -> None:
    LOG.info("Disconnecting Backup HDD")
    LOG.debug("Unmounting HDD...")
    subprocess.call(["umount", "/dev/BACKUPHDD"])
    LOG.debug("Switching HDD power off...")
    await pcu.cmd.power.hdd.off()
    LOG.debug("Undocking...")
    await pcu.cmd.undock()


async def set_wakeup_time() -> None:
    LOG.info("Programming PCU. Setting current time and time for next wakeup")
    await pcu.set.date.now(datetime.now())
    LOG.debug(f"read current time from pcu: {await pcu.get.date.now()}")
    await pcu.set.date.wakeup(datetime.now() + timedelta(minutes=1))
    LOG.debug(f"read wakeup time from pcu: {await pcu.get.date.wakeup()}")
    await pcu.set.date.backup(datetime.now() + timedelta(minutes=1))
    LOG.debug(f"read backup time from pcu: {await pcu.get.date.backup()}")


async def shutdown():
    LOG.info("Shutting down...")
    await pcu.cmd.shutdown.init()
    subprocess.call(["sudo", "/sbin/shutdown", "-h", "now"])


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-shutdown", default=False, required=False)
    args = parser.parse_args()
    cfg = load_config(Path('config.yaml'))
    await init()
    await engage()
    await backup(cfg["backup"])
    await disengage()
    await wait_before_shutdown(cfg)
    await set_wakeup_time()
    if not args.no_shutdown:
        await shutdown()


async def wait_before_shutdown(cfg):
    try:
        sleep_duration = cfg["process"]["seconds_between_backup_end_and_shutdown"]
    except KeyError:
        sleep_duration = 60
        LOG.warning("couldn't get sleep duration from config file, default to 60")
    LOG.info(f"waiting for {sleep_duration}s before shutdown")
    await asyncio.sleep(sleep_duration)


if __name__ == "__main__":
    asyncio.run(main())
