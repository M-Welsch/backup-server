"""Bounded, non-shell subprocesses, including process-group cleanup."""

import asyncio
import logging
import os
import signal

LOG = logging.getLogger(__name__)


async def stop_process(process, grace=5):
    # Signal the group even when its leader exited: descendants may own the pipes.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return
        except PermissionError:
            LOG.exception("Cannot signal process group %s", process.pid)
        try:
            await asyncio.wait_for(process.wait(), grace)
            if sig == signal.SIGKILL:
                return
        except asyncio.TimeoutError:
            LOG.error("Process group %s did not stop after %s", process.pid, sig.name)
    # In particular, SIGKILL cannot resolve uninterruptible kernel I/O.
    LOG.error("Process group %s may still have blocked I/O", process.pid)


async def run_checked(*command, timeout=30, log_success=True):
    """Quiet polling may suppress success logs, but never failure diagnostics."""
    if log_success:
        LOG.debug("Running %r (timeout=%ss)", command, timeout)
    try:
        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
    except Exception:
        LOG.exception("Could not start command %r (timeout=%ss)", command, timeout)
        raise
    output_task = asyncio.create_task(process.communicate())
    try:
        stdout, stderr = await asyncio.wait_for(asyncio.shield(output_task), timeout)
    except BaseException as error:
        # Stopping the storage monitor after a completed transfer is normal.
        cancelled = isinstance(error, asyncio.CancelledError)
        if not cancelled:
            LOG.error("Command %r aborted (timeout=%ss): %r", command, timeout, error)
        await stop_process(process)
        if not cancelled and output_task.done() and not output_task.cancelled() and output_task.exception() is None:
            stdout, stderr = output_task.result()
            LOG.error("Aborted command %r; stdout=%r; stderr=%r", command, stdout, stderr)
        output_task.cancel()
        await asyncio.gather(output_task, return_exceptions=True)
        raise
    stdout = stdout.decode(errors="replace")
    stderr = stderr.decode(errors="replace")
    if process.returncode:
        LOG.error("Command %r exited %s; stdout=%s; stderr=%s", command, process.returncode, stdout, stderr)
        raise RuntimeError("Command {!r} failed ({}): {}".format(command, process.returncode, stderr.strip()))
    if log_success:
        LOG.debug("Command %r exited %s; stdout=%s; stderr=%s", command, process.returncode, stdout, stderr)
    elif stderr:
        LOG.warning("Command %r succeeded with stderr=%s", command, stderr)
    return stdout
