import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
import argparse
from pathlib import Path
from typing import Callable

import config
import pcu
from config import load_config

LOG = logging.getLogger(__name__)


HDD_SPINDOWN_SECONDS = 20


def setup_logger(logger_config: dict) -> None:
    LOG.debug("Setting up logger...")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    filename = logger_config.get('filename', 'logfile.log')
    file_handler = logging.FileHandler(filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


async def init(logger_config: dict):
    setup_logger(logger_config)
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
    await asyncio.sleep(10)  # workaround for #26
    LOG.debug("Mounting HDD...")
    trials = 0
    maximum_trials = 3
    while trials < maximum_trials:
        subprocess.call("mount /dev/BACKUPHDD", shell=True)
        await asyncio.sleep(5)
        if Path('/media/BackupHDD').is_mount():
            break
        LOG.warning("mounting of backupHDD failed, try another time")
        trials += 1


async def handle_output(pipe, log_func: Callable):
    while True:
        line = await pipe.readline()
        if not line:
            break
        log_func(f"Live Output: {line.decode().rstrip()}")


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
        f"{nas_ip}::{source}/",
        "/media/BackupHDD/backups/current"
    ]
    LOG.debug(f"Backing up with command {' '.join(backup_command)}")
    process = await asyncio.create_subprocess_exec(
        *backup_command,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    output_task = asyncio.create_task(handle_output(process.stdout, LOG.debug))
    output_task_stderr = asyncio.create_task(handle_output(process.stderr, LOG.error))

    LOG.info("Starting Backup...")
    await process.wait()
    LOG.info("Backup finished.")
    await output_task
    LOG.debug("Backup stdout output task finished.")
    await output_task_stderr
    LOG.debug("Backup stderr output task finished.")


async def disengage() -> None:
    LOG.info("Disconnecting Backup HDD")
    LOG.debug("Unmounting HDD...")
    subprocess.call("umount /dev/BACKUPHDD", shell=True)
    LOG.debug("Switching HDD power off...")
    await pcu.cmd.power.hdd.off()
    await asyncio.sleep(HDD_SPINDOWN_SECONDS)
    LOG.debug("Undocking...")
    await pcu.cmd.undock()


async def wait_before_shutdown(cfg):
    try:
        sleep_duration = cfg["process"]["seconds_between_backup_end_and_shutdown"]
    except KeyError:
        sleep_duration = 60
        LOG.warning("couldn't get sleep duration from config file, default to 60")
    LOG.info(f"waiting for {sleep_duration}s before shutdown")
    await asyncio.sleep(sleep_duration)


async def set_wakeup_time(sleep_time: timedelta) -> None:
    LOG.info("Programming PCU. Setting current time and time for next wakeup")
    await pcu.set.date.now(datetime.now())
    LOG.debug(f"read current time from pcu: {await pcu.get.date.now()}")
    await pcu.set.date.wakeup(datetime.now() + sleep_time)
    LOG.debug(f"read wakeup time from pcu: {await pcu.get.date.wakeup()}")
    await pcu.set.date.backup(datetime.now() + sleep_time)
    LOG.debug(f"read backup time from pcu: {await pcu.get.date.backup()}")


async def shutdown():
    LOG.info("Shutting down...")
    await pcu.cmd.shutdown.init()
    subprocess.call(["sudo", "/sbin/shutdown", "-h", "now"])


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-shutdown", default=False, required=False, action='store_true')
    parser.add_argument("--config", default="config.yaml", type=str, required=False)
    args = parser.parse_args()
    cfg = load_config(Path(args.config))
    await init(cfg["logger"])
    LOG.info(f"loading config file {args.config}")
    await engage()
    await backup(cfg["backup"])
    await disengage()
    await wait_before_shutdown(cfg)
    await set_wakeup_time(config.get_sleep_time(cfg["process"]["time_between_backups"]))
    if not args.no_shutdown:
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())
