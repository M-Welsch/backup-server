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


async def run_checked(*command, timeout=30):
    LOG.debug("Running %r (timeout=%ss)", command, timeout)
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    output_task = asyncio.create_task(process.communicate())
    try:
        stdout, stderr = await asyncio.wait_for(asyncio.shield(output_task), timeout)
    except BaseException:
        await stop_process(process)
        if output_task.done() and not output_task.cancelled() and output_task.exception() is None:
            stdout, stderr = output_task.result()
            LOG.error("Aborted command %r; stdout=%r; stderr=%r", command, stdout, stderr)
        output_task.cancel()
        await asyncio.gather(output_task, return_exceptions=True)
        raise
    stdout = stdout.decode(errors="replace")
    stderr = stderr.decode(errors="replace")
    LOG.debug("Command %r exited %s; stdout=%s; stderr=%s", command, process.returncode, stdout, stderr)
    if process.returncode:
        raise RuntimeError("Command {!r} failed ({}): {}".format(command, process.returncode, stderr.strip()))
    return stdout
