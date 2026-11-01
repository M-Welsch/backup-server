import argparse
import asyncio
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import config
import pcu
from config import load_config
from process_ops import run_checked, stop_process
from recovery import RecoveryState
from storage import Storage

LOG = logging.getLogger(__name__)


HDD_SPINDOWN_SECONDS = 20


def setup_logger(logger_config: dict) -> None:
    LOG.debug("Setting up logger...")
    logger = logging.getLogger()
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


async def pcu_operation(action, timeout=30, attempts=3):
    for attempt in range(attempts):
        try:
            result = await asyncio.wait_for(action(), timeout)
            if result is False:
                raise RuntimeError("PCU operation returned failure")
            return result
        except Exception:
            LOG.exception("PCU operation failed (attempt %s/%s)", attempt + 1, attempts)
            if attempt + 1 == attempts:
                raise
            await asyncio.sleep(1)


async def engage(storage, pcu_timeout=30):
    LOG.info("Connect Backup HDD")
    LOG.info("Initial docking state: %s", await pcu_operation(pcu.get.dockingstate, pcu_timeout))
    await pcu_operation(pcu.cmd.dock, pcu_timeout, attempts=4)
    await pcu_operation(pcu.cmd.power.hdd.on, pcu_timeout)
    await asyncio.sleep(10)  # Allow the HDD to initialize (#26).
    for attempt in range(3):
        try:
            if not await storage.mounted():
                await run_checked("mount", str(storage.mountpoint), timeout=storage.timeout)
            await storage.verify(access=True)
            return
        except Exception:
            LOG.exception("Mount/verification failed (attempt %s/3)", attempt + 1)
            if attempt == 2:
                raise
            await asyncio.sleep(5)


async def handle_output(pipe, log_func: Callable):
    while True:
        line = await pipe.readline()
        if not line:
            break
        log_func(f"Live Output: {line.decode(errors='replace').rstrip()}")


async def resolve_ip(host_name_in_ssh_config: str) -> str:
    output = await run_checked("ssh", "-G", host_name_in_ssh_config, timeout=10)
    for line in output.splitlines():
        key, _, value = line.partition(" ")
        if key.lower() == "hostname" and value.strip():
            return value.strip()
    raise RuntimeError("No hostname in SSH configuration")


async def monitored_transfer(command, storage, timeout, interval=2, reject_output=False):
    await storage.verify(access=True)
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    changed = False

    def stdout_log(line):
        nonlocal changed
        changed = True
        LOG.debug(line)

    stream_tasks = [
        asyncio.create_task(process.wait()),
        asyncio.create_task(handle_output(process.stdout, stdout_log)),
        asyncio.create_task(handle_output(process.stderr, LOG.error)),
    ]

    async def completion():
        await asyncio.gather(*stream_tasks)
        if process.returncode != 0:
            raise RuntimeError("rsync failed: {}".format(process.returncode))
        if reject_output and changed:
            raise RuntimeError("Checksum verification found differences from the NAS source")

    async def monitor():
        while True:
            await asyncio.sleep(interval)
            await storage.verify(access=True)

    completed = asyncio.create_task(completion())
    monitoring = asyncio.create_task(monitor())
    try:
        done, _ = await asyncio.wait({completed, monitoring}, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
        if not done:
            raise TimeoutError("Backup/verification exceeded {} seconds".format(timeout))
        for task in done:
            await task
        # Final storage validation is required even after rsync exit 0.
        await storage.verify(access=True)
    except BaseException:
        await stop_process(process)
        raise
    finally:
        completed.cancel()
        monitoring.cancel()
        for task in stream_tasks:
            task.cancel()
        await asyncio.gather(completed, monitoring, *stream_tasks, return_exceptions=True)


async def backup(cfg, storage, state):
    nas_ip = await resolve_ip(cfg.get("nas_name_in_ssh_config", "nas"))
    source = "{}::{}/".format(nas_ip, cfg["rsync_source"].rstrip("/"))
    logfile = str(Path(datetime.now().strftime("%Y-%m-%d_rsync.log")).absolute())
    command = ["sudo", "-n", "rsync", "-aH", "--timeout=120", "--no-motd", "--delete"]
    interval = cfg.get("monitor_interval_seconds", 2)
    LOG.info("Starting backup")
    await storage.verify(access=True)
    await monitored_transfer(
        storage.worker_command("transfer", *command, "--stats", "--log-file=" + logfile, source, "."),
        storage, cfg.get("backup_timeout_seconds", 86400), interval,
    )
    LOG.info("Backup transfer finished successfully; finalization still pending")
    integrity = cfg.get("integrity", {})
    due = state.data["last_integrity_check"] + integrity.get("interval_days", 7) * 86400 <= time.time()
    if due:
        LOG.info("Starting periodic NAS-to-backup checksum verification")
        await monitored_transfer(
            storage.worker_command("transfer", *command, "--checksum", "--dry-run", "--itemize-changes", source, "."),
            storage, integrity.get("timeout_seconds", 86400), interval, reject_output=True,
        )
        state.path.parent.mkdir(parents=True, exist_ok=True)
        restored = await run_checked(
            *storage.worker_command("restore", str(state.path.parent), str(integrity.get("restore_samples", 5)),
                                    str(integrity.get("restore_max_file_bytes", 67108864))),
            timeout=integrity.get("restore_timeout_seconds", 300),
        )
        await storage.verify(access=True)
        LOG.info("Sample restore verification passed: %s", restored.strip())
        state.data["last_integrity_check"] = time.time()


async def disengage(storage, pcu_timeout=30):
    LOG.info("Disconnecting Backup HDD")
    clean = True
    try:
        if await storage.mounted():
            await run_checked("umount", str(storage.mountpoint), timeout=storage.timeout)
        if await storage.mounted():
            raise RuntimeError("Backup filesystem remains mounted after unmount")
    except Exception:
        clean = False
        LOG.exception("EMERGENCY: unmount failed; cutting HDD power to prioritize physical isolation. "
                      "Backup/filesystem may be inconsistent; this is NOT a clean shutdown")
    # Explicit emergency policy: continue even when the device is still present.
    # Power-off acknowledgment AND observable state are checked by pcu.power().
    await pcu_operation(pcu.cmd.power.hdd.off, pcu_timeout)
    await asyncio.sleep(HDD_SPINDOWN_SECONDS)
    await pcu_operation(pcu.cmd.undock, pcu_timeout)
    LOG.info("HDD power-off and undocking confirmed (clean_unmount=%s)", clean)
    return clean


async def wait_before_shutdown(cfg):
    try:
        sleep_duration = cfg["process"]["seconds_between_backup_end_and_shutdown"]
    except KeyError:
        sleep_duration = 60
        LOG.warning("couldn't get sleep duration from config file, default to 60")
    LOG.info(f"waiting for {sleep_duration}s before shutdown")
    await asyncio.sleep(sleep_duration)


async def set_wakeup_time(sleep_time: timedelta) -> None:
    now = datetime.now().replace(second=0, microsecond=0)
    wakeup = now + sleep_time
    for setter, getter, expected in (
        (pcu.set.date.now, pcu.get.date.now, now),
        (pcu.set.date.wakeup, pcu.get.date.wakeup, wakeup),
        (pcu.set.date.backup, pcu.get.date.backup, wakeup),
    ):
        await setter(expected)
        observed = await getter()
        if abs((observed - expected).total_seconds()) >= 60:
            raise RuntimeError("PCU date verification failed: expected {}, got {}".format(expected, observed))


async def shutdown(pcu_timeout=30, pcu_notified=False):
    LOG.info("Shutting down")
    if not pcu_notified:
        try:
            await pcu_operation(pcu.cmd.shutdown.init, pcu_timeout)
        except Exception:
            LOG.exception("PCU shutdown unavailable; physical state may be unknown. Halting the Pi regardless")
    flush_logs()
    await run_checked("sudo", "-n", "/sbin/shutdown", "-h", "now", timeout=15)


async def diagnostics(storage, pcu_timeout):
    for command in (
        ("findmnt", "--json", "--list", "--output", "TARGET,SOURCE,FSTYPE,OPTIONS"),
        ("lsblk", "--exclude", "1,7", "--output", "NAME,MAJ:MIN,MODEL,SERIAL,FSTYPE,UUID,MOUNTPOINT"),
        ("journalctl", "-k", "-n", "100", "--no-pager"),
        ("vcgencmd", "get_throttled"),
    ):
        try:
            LOG.error("Failure diagnostics %r:\n%s", command, await run_checked(*command, timeout=10))
        except Exception:
            LOG.exception("Diagnostic command failed: %r", command)
    try:
        LOG.error("PCU failure state: %s", await pcu_operation(pcu.get.dockingstate, pcu_timeout, attempts=1))
    except Exception:
        LOG.exception("Cannot obtain PCU state")


def flush_logs():
    for handler in logging.getLogger().handlers:
        try:
            handler.flush()
        except Exception:
            # Broken log storage must not prevent physical isolation/shutdown.
            LOG.exception("Could not flush a log handler")


async def copy_logs(cfg):
    remote = cfg.get("debug", {})
    if not remote.get("remote_ssh_connect_string") or not remote.get("remote_logging_logfile_path"):
        return
    flush_logs()
    try:
        await run_checked(
            "scp", "-oBatchMode=yes", "-oConnectTimeout=5", cfg.get("logger", {}).get("filename", "logfile.log"),
            "{}:{}".format(remote["remote_ssh_connect_string"], remote["remote_logging_logfile_path"]), timeout=15,
        )
    except Exception:
        LOG.exception("Remote log copy failed; retaining local diagnostics")


async def run_cycle(cfg, no_shutdown=False, startup_error=None):
    settings = cfg.get("process", {})
    pcu_timeout = settings.get("pcu_timeout_seconds", 30)
    storage = Storage(cfg.get("backup", {}))
    state = None
    previous_reboots = 0
    failure = None
    stage = "initialization"
    try:
        if startup_error:
            raise startup_error
        state = RecoveryState(settings.get("state_file", "~/.local/state/bcu/state.json"))
        previous_reboots = state.data["reboots"]
        LOG.info("Recovery state: %r", state.data)
        await pcu_operation(pcu.handshake, pcu_timeout)
        # A previous shutdown timer must not cut power during a reboot retry.
        await pcu_operation(pcu.cmd.shutdown.abort, pcu_timeout)
        stage = "engage"
        await engage(storage, pcu_timeout)
        stage = "backup/verification"
        await backup(cfg["backup"], storage, state)
    except Exception as error:
        failure = "{}: {!r}".format(stage, error)
        LOG.exception("Backup FAILED at %s", stage)
        await diagnostics(storage, pcu_timeout)
    finally:
        try:
            clean = await disengage(storage, pcu_timeout)
            if not clean:
                failure = (failure or "Backup transferred") + "; emergency unclean power-off"
                await diagnostics(storage, pcu_timeout)
        except Exception as error:
            LOG.exception("Physical cleanup FAILED; docking/power state may be unknown")
            failure = (failure or "Backup transferred") + "; cleanup: {!r}".format(error)
            await diagnostics(storage, pcu_timeout)

    if failure is None and not no_shutdown:
        try:
            stage = "wakeup programming"
            await pcu_operation(
                lambda: set_wakeup_time(config.get_sleep_time(settings.get("time_between_backups", {}))),
                pcu_timeout,
            )
            await wait_before_shutdown(cfg)
            # Check this before resetting the durable retry budget.
            await pcu_operation(pcu.cmd.shutdown.init, pcu_timeout)
        except Exception as error:
            failure = "{}: {!r}".format(stage, error)
            LOG.exception("Finalization FAILED")

    try:
        if state is not None:
            state.data["last_failure"] = failure
            if failure is None:
                state.data["reboots"] = 0
            else:
                # An emergency/failed cycle must be verified on the next attempt.
                state.data["last_integrity_check"] = 0
            state.save()
    except Exception as error:
        failure = (failure or "State persistence") + "; {!r}".format(error)
        LOG.exception("Cannot persist recovery state; reboot retries are disabled")
        state = None

    if failure is None:
        LOG.info("Backup cycle finished SUCCESSFULLY: transfer, verification (if due), and clean isolation")
    else:
        LOG.error("Backup cycle FAILED: %s", failure)

    if no_shutdown:
        await copy_logs(cfg)
        return failure is None

    if failure is None:
        try:
            await copy_logs(cfg)
            await shutdown(pcu_timeout, pcu_notified=True)
            return True
        except Exception as error:
            failure = "System shutdown failed: {!r}".format(error)
            LOG.exception(failure)
            if state is not None:
                try:
                    state.data.update(reboots=previous_reboots, last_failure=failure, last_integrity_check=0)
                    state.save()
                except Exception:
                    LOG.exception("Cannot persist shutdown failure; disabling retries")
                    state = None

    maximum_reboots = settings.get("maximum_reboots", 2)
    if failure and state is not None and state.data["reboots"] < maximum_reboots:
        try:
            # Persist BEFORE reboot. Failure to save must never cause an endless loop.
            state.data["reboots"] += 1
            state.save()
            LOG.warning("Reboot-and-retry %s/%s; last failure: %s", state.data["reboots"], maximum_reboots, failure)
            # Abort an acknowledged shutdown timer if finalization failed later.
            try:
                await pcu_operation(pcu.cmd.shutdown.abort, pcu_timeout, attempts=1)
            except Exception:
                LOG.exception("Could not cancel PCU shutdown timer before reboot")
            await copy_logs(cfg)
            flush_logs()
            await run_checked("sudo", "-n", "/sbin/shutdown", "-r", "now", timeout=15)
            return False
        except Exception:
            LOG.exception("Reboot retry unavailable; proceeding to final shutdown")

    if failure:
        LOG.error("Reboot retries exhausted or unavailable; final shutdown (physical isolation may be incomplete)")
        try:
            await pcu_operation(
                lambda: set_wakeup_time(config.get_sleep_time(settings.get("time_between_backups", {}))), pcu_timeout,
            )
        except Exception:
            LOG.exception("Could not program next wakeup")
    await copy_logs(cfg)
    try:
        await shutdown(pcu_timeout)
    except Exception:
        LOG.critical("OS shutdown failed as well; no software recovery remains", exc_info=True)
    return False


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-shutdown", default=False, required=False, action='store_true')
    parser.add_argument("--config", default="config.yaml", type=str, required=False)
    args = parser.parse_args()
    startup_error = None
    cfg = {}
    try:
        cfg = load_config(Path(args.config))
        setup_logger(cfg.get("logger", {}))
    except Exception as error:
        startup_error = error
        logging.basicConfig(level=logging.DEBUG)
        LOG.exception("Configuration/log initialization failed; attempting emergency cleanup and shutdown")
    LOG.info("Loading config file %s", args.config)
    success = await run_cycle(cfg, args.no_shutdown, startup_error)
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
