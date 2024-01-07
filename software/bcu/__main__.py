import asyncio
import logging
import os
import subprocess
from datetime import datetime, timedelta

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


async def engage() -> None:
    LOG.debug("Docking...")
    await pcu.cmd.dock()
    LOG.debug("Switching HDD power on...")
    await pcu.cmd.power.hdd.on()
    await asyncio.sleep(2)
    LOG.debug("Mounting HDD...")
    subprocess.call(["mount", "/dev/BACKUPHDD"])


#def backup() -> None:
#    backup_command = [
#        "rsync",
#        "-aH",
#        "--stats",
#        "--delete",
#        "$(ssh - G nas | awk '/^hostname / { print $2 }')::backup_testdata_source/*",
#        "/media/BackupHDD/backups/current"
#    ]
#    subprocess.call(backup_command, shell=True)


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

    LOG.debug("Starting Backup...")
    await process.wait()
    LOG.debug("Backup finished.")
    await output_task
    LOG.debug("Backup output task finished.")

    stderr = await process.stderr.read()
    if stderr:
        LOG.info(f"Fehlerausgabe: {stderr.decode()}")


async def disengage() -> None:
    LOG.debug("Unmounting HDD...")
    subprocess.call(["umount", "/dev/BACKUPHDD"])
    LOG.debug("Switching HDD power off...")
    await pcu.cmd.power.hdd.off()
    LOG.debug("Undocking...")
    await pcu.cmd.undock()


async def set_wakeup_time() -> None:
    LOG.debug("Programming PCU...")
    await pcu.set.date.now(datetime.now())
    await pcu.set.date.wakeup(datetime.now() + timedelta(minutes=1))
    await pcu.set.date.backup(datetime.now() + timedelta(minutes=1))


async def shutdown():
    LOG.debug("Shutting down...")
    await pcu.cmd.shutdown.init()
    os.system("shutdown -h now")
    # subprocess.call(["shutdown", "-h", "now"])


async def main() -> None:
    setup_logger()
    await engage()
    await backup()
    await disengage()
    await asyncio.sleep(60)  # hold on for a minute to give the user time to intervene
    await set_wakeup_time()
    await shutdown()


if __name__ == "__main__":
    asyncio.run(main())
