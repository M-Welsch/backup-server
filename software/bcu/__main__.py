import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
import argparse

import pcu


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
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


async def init():
    setup_logger()
    await pcu.handshake()


async def engage() -> None:
    LOG.info("Docking...")
    docking_trials = 0
    while not await pcu.cmd.dock():
        LOG.warning("couldn't dock, try another time.")
        docking_trials += 1
        if docking_trials == 4:
            raise RuntimeError("couldn't dock with two trials")
    LOG.info("Switching HDD power on...")
    await pcu.cmd.power.hdd.on()
    await asyncio.sleep(2)
    LOG.info("Mounting HDD...")
    subprocess.call(["mount", "/dev/BACKUPHDD"])


async def handle_output(pipe):
    while True:
        line = await pipe.readline()
        if not line:
            break
        LOG.info(f"Live Output: {line.decode().rstrip()}")


async def backup():
    nas_ip = subprocess.check_output("ssh -G nas | awk '/^hostname / { print $2 }'", shell=True)
    nas_ip = nas_ip.decode().strip()
    LOG.info(f"obtained IP Address of NAS: {nas_ip}")
    backup_command = [
        "rsync",
        "-aH",
        "--stats",
        "--delete",
        f"{nas_ip}::backup_testdata_source/*",
        "/media/BackupHDD/backups/current"
    ]
    LOG.info(f"Backing up with command {' '.join(backup_command)}")
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
    LOG.info("Unmounting HDD...")
    subprocess.call(["umount", "/dev/BACKUPHDD"])
    LOG.info("Switching HDD power off...")
    await pcu.cmd.power.hdd.off()
    LOG.info("Undocking...")
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
    parser.add_argument("--wait-before-shutdown", type=int, default=60, required=False)
    args = parser.parse_args()
    await init()
    await engage()
    await backup()
    await disengage()
    await asyncio.sleep(args.wait_before_shutdown)
    await set_wakeup_time()
    if not args.no_shutdown:
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())
