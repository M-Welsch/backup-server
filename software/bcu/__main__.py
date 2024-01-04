import asyncio
import logging
import subprocess
from datetime import datetime, timedelta

import pcu


LOG = logging.getLogger(__name__)


def setup_logger() -> None:
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
    await pcu.cmd.dock()
    await pcu.cmd.power.hdd.on()
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
    backup_command = [
        "rsync",
        "-aH",
        "--stats",
        "--delete",
        "$(ssh - G nas | awk '/^hostname / { print $2 }')::backup_testdata_source/*",
        "/media/BackupHDD/backups/current"
    ]
    process = await asyncio.create_subprocess_exec(
        *backup_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    output_task = asyncio.create_task(handle_output(process.stdout))

    await process.wait()
    await output_task

    stderr = await process.stderr.read()
    if stderr:
        LOG.info(f"Fehlerausgabe: {stderr.decode()}")


async def disengage() -> None:
    subprocess.call(["umount", "/dev/BACKUPHDD"])
    await pcu.cmd.power.hdd.off()
    await pcu.cmd.undock()


async def set_wakeup_time() -> None:
    await pcu.set.date.now(datetime.now())
    await pcu.set.date.wakeup(datetime.now() + timedelta(days=7))
    await pcu.set.date.backup(datetime.now() + timedelta(days=7))


def shutdown():
    pcu.cmd.shutdown()
    subprocess.call(["shutdown", "-h", "now"])


async def main() -> None:
    setup_logger()
    await engage()
    await backup()
    await disengage()
    await set_wakeup_time()
    shutdown()


if __name__ == "__main__":
    asyncio.run(main())
