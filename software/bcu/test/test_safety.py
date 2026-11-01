"""All hardware interfaces are mocked. Real subprocess tests use only Python."""

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import config
import pcu
import storage as storage_module
import storage_worker
from process_ops import run_checked
from recovery import RecoveryState
from storage import Storage
from storage_worker import enter_destination, restore_samples

UUID = "bf117632-4982-44fd-a113-7b4fd682d9be"


def run(coroutine):
    return asyncio.run(coroutine)


def test_checked_subprocess_drains_both_pipes_and_checks_exit():
    with pytest.raises(RuntimeError, match="failure detail"):
        run(run_checked(
            sys.executable, "-c", "import sys; print('out'); print('failure detail', file=sys.stderr); sys.exit(23)"
        ))


def test_checked_subprocess_timeout():
    with pytest.raises(asyncio.TimeoutError):
        run(run_checked(sys.executable, "-c", "import time; time.sleep(60)", timeout=0.05))


@pytest.mark.parametrize("code", [0, 23, 24])
def test_rsync_exit_codes_and_output(bcu, code, caplog):
    disk = SimpleNamespace(verify=AsyncMock())
    script = "import sys; print('stdout'); print('stderr', file=sys.stderr); sys.exit({})".format(code)
    operation = bcu.monitored_transfer([sys.executable, "-c", script], disk, 5)
    if code:
        with pytest.raises(RuntimeError, match="rsync failed: {}".format(code)):
            run(operation)
    else:
        run(operation)
    assert "stderr" in caplog.text


def test_checksum_differences_fail_even_with_exit_zero(bcu):
    disk = SimpleNamespace(verify=AsyncMock())
    with pytest.raises(RuntimeError, match="differences"):
        run(bcu.monitored_transfer([sys.executable, "-c", "print('>fcs....... changed')"], disk, 5, reject_output=True))


def test_disappearance_stops_running_transfer(bcu):
    disk = SimpleNamespace(verify=AsyncMock(side_effect=[None, OSError("device disappeared")]))
    with pytest.raises(OSError, match="disappeared"):
        run(bcu.monitored_transfer([sys.executable, "-c", "import time; time.sleep(60)"], disk, 5, interval=0.01))


def test_transfer_has_absolute_timeout(bcu):
    disk = SimpleNamespace(verify=AsyncMock())
    with pytest.raises(TimeoutError, match="exceeded"):
        run(bcu.monitored_transfer([sys.executable, "-c", "import time; time.sleep(60)"], disk, 0.05))


def test_bad_mount_never_starts_rsync(bcu, monkeypatch):
    disk = SimpleNamespace(verify=AsyncMock(side_effect=RuntimeError("wrong UUID")))
    spawn = AsyncMock()
    monkeypatch.setattr(bcu.asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(RuntimeError, match="wrong UUID"):
        run(bcu.monitored_transfer(["rsync"], disk, 5))
    spawn.assert_not_called()


@pytest.fixture
def fake_storage(tmp_path, monkeypatch):
    disk = Storage({"filesystem_uuid": UUID})
    real_path = Path
    devices = tmp_path / "dev"
    devices.mkdir()
    (devices / UUID).touch()
    kernel = tmp_path / "sys"
    kernel.mkdir()
    drive = tmp_path / "disk"
    drive.mkdir()
    (drive / "diskseq").write_text("7")
    partition = drive / "partition1"
    partition.mkdir()
    (partition / "partition").write_text("1")
    (kernel / "0:0").symlink_to(partition, target_is_directory=True)

    def mapped_path(value):
        if value == "/dev/disk/by-uuid":
            return devices
        if value == "/sys/dev/block":
            return kernel
        return real_path(value)

    monkeypatch.setattr(storage_module, "Path", mapped_path)
    monkeypatch.setattr(storage_module.stat, "S_ISBLK", lambda mode: True)
    mount = {"target": "/media/BackupHDD", "uuid": UUID, "maj:min": "0:0", "options": "rw,relatime"}
    execute = AsyncMock(return_value=json.dumps({"filesystems": [mount]}))
    monkeypatch.setattr(storage_module, "run_checked", execute)
    return disk, mount, execute, drive, devices


def test_mount_uuid_must_match(fake_storage):
    disk, mount, execute, _, _ = fake_storage
    mount["uuid"] = "wrong"
    execute.return_value = json.dumps({"filesystems": [mount]})
    with pytest.raises(RuntimeError, match="UUID/options mismatch"):
        run(disk.verify())


def test_readonly_mount_rejected(fake_storage):
    disk, mount, execute, _, _ = fake_storage
    mount["options"] = "ro,relatime"
    execute.return_value = json.dumps({"filesystems": [mount]})
    with pytest.raises(RuntimeError, match="UUID/options mismatch"):
        run(disk.verify())


def test_reconnected_same_uuid_is_not_original_device(fake_storage):
    disk, _, _, drive, _ = fake_storage
    run(disk.verify())
    (drive / "diskseq").write_text("8")
    with pytest.raises(RuntimeError, match="instance changed"):
        run(disk.verify())


def test_missing_block_device_rejected_despite_stale_mount(fake_storage):
    disk, _, _, _, devices = fake_storage
    (devices / UUID).unlink()
    with pytest.raises(FileNotFoundError):
        run(disk.verify())


def test_mount_device_mismatch_rejected(fake_storage):
    disk, mount, execute, _, _ = fake_storage
    mount["maj:min"] = "8:1"
    execute.return_value = json.dumps({"filesystems": [mount]})
    with pytest.raises(RuntimeError, match="no longer backs"):
        run(disk.verify())


def test_missing_mount_rejected(fake_storage):
    disk, _, execute, _, _ = fake_storage
    execute.return_value = json.dumps({"filesystems": []})
    with pytest.raises(RuntimeError, match="exactly one"):
        run(disk.verify())


def test_pinned_destination_supports_current_symlink(tmp_path):
    mount = tmp_path / "mount"
    target = mount / "backups/snapshot"
    target.mkdir(parents=True)
    (mount / "backups/current").symlink_to("snapshot")
    original = os.open(".", os.O_RDONLY | os.O_DIRECTORY)
    info = target.stat()
    try:
        enter_destination(str(mount), "backups/current", "{}:{}".format(os.major(info.st_dev), os.minor(info.st_dev)))
        assert Path.cwd() == target
        # Rename proves cwd is pinned, not repeatedly resolved through current.
        target.rename(mount / "backups/renamed")
        Path("proof").write_text("safe")
        assert (mount / "backups/renamed/proof").read_text() == "safe"
    finally:
        os.fchdir(original)
        os.close(original)


def test_destination_symlink_outside_mount_is_rejected(tmp_path):
    mount = tmp_path / "mount"
    mount.mkdir()
    (mount / "current").symlink_to(tmp_path)
    with pytest.raises(ValueError):
        enter_destination(str(mount), "current", "0:0")


def test_destination_on_wrong_device_rejected(tmp_path):
    (tmp_path / "current").mkdir()
    with pytest.raises(RuntimeError, match="verified backup device"):
        enter_destination(str(tmp_path), "current", "999:999")


def test_restore_checksums_and_removes_only_staging(tmp_path, monkeypatch):
    source = tmp_path / "backup"
    source.mkdir()
    (source / "file").write_bytes(b"restore proof")
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.chdir(source)

    def fake_rsync(command, **kwargs):
        if "--dry-run" not in command:
            shutil.copyfile(command[-2], command[-1])
        return SimpleNamespace(stdout=b"", stderr=b"")

    execute = Mock(side_effect=fake_rsync)
    monkeypatch.setattr(storage_worker.subprocess, "run", execute)
    result = restore_samples(str(staging), 1, 1024)
    assert result[0]["path"] == "file"
    assert result[0]["bytes"] == 13
    assert list(staging.iterdir()) == []
    assert (source / "file").read_bytes() == b"restore proof"
    assert "--checksum" in execute.call_args.args[0]
    assert "--dry-run" in execute.call_args.args[0]


def test_empty_restore_is_not_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="No eligible"):
        restore_samples(str(tmp_path), 1, 1024)


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync is not installed")
def test_restore_with_real_unprivileged_rsync(tmp_path, monkeypatch):
    source = tmp_path / "backup"
    source.mkdir()
    (source / "colon:name").write_bytes(b"restore proof")
    staging = tmp_path / "staging"
    staging.mkdir()
    real_run = storage_worker.subprocess.run

    def without_sudo(command, **kwargs):
        assert command[:3] == ["sudo", "-n", "rsync"]
        return real_run(command[2:], **kwargs)

    monkeypatch.setattr(storage_worker.subprocess, "run", without_sudo)
    monkeypatch.chdir(source)
    result = restore_samples(str(staging), 1, 1024)
    assert result[0]["path"] == "colon:name"
    assert list(staging.iterdir()) == []


def test_restore_mismatch_is_failure_and_cleans_staging(tmp_path, monkeypatch):
    (tmp_path / "file").write_bytes(b"proof")
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.chdir(tmp_path)

    def fake_rsync(command, **kwargs):
        if "--dry-run" in command:
            return SimpleNamespace(stdout=b">fc........ changed", stderr=b"")
        Path(command[-1]).write_bytes(b"corrupt")
        return SimpleNamespace(stdout=b"", stderr=b"")

    monkeypatch.setattr(storage_worker.subprocess, "run", fake_rsync)
    with pytest.raises(RuntimeError, match="Restore checksum mismatch"):
        restore_samples(str(staging), 1, 1024)
    assert list(staging.iterdir()) == []


def test_persisted_retry_budget_survives_new_instance(tmp_path):
    path = tmp_path / "state.json"
    first = RecoveryState(path)
    first.data.update(reboots=2, last_failure="serial error")
    first.save()
    second = RecoveryState(path)
    assert second.data["reboots"] == 2
    assert second.data["last_failure"] == "serial error"
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("contents", ["broken", '{"reboots": -1}', '{"reboots": "0"}'])
def test_corrupt_state_does_not_reset_retry_budget(tmp_path, contents):
    path = tmp_path / "state.json"
    path.write_text(contents)
    with pytest.raises((ValueError, TypeError)):
        RecoveryState(path)


def test_pcu_payload_parser_preserves_payload_and_strips_echo():
    assert pcu._filter_output_payload(
        ["ch> get dockingstate", "pcu_dockingState1_undocked", "ch>"], "get dockingstate"
    ) == ["pcu_dockingState1_undocked"]


def test_power_requires_acknowledgment(monkeypatch):
    monkeypatch.setattr(pcu, "call_pcu", AsyncMock(return_value="power failed"))
    with pytest.raises(RuntimeError, match="power failed"):
        run(pcu.cmd.power.hdd.off())


def test_power_requires_observable_state(monkeypatch):
    monkeypatch.setattr(
        pcu, "call_pcu", AsyncMock(side_effect=["power successful", "pcu_dockingState3_allDockedPwrOn"])
    )
    with pytest.raises(RuntimeError, match="not confirmed"):
        run(pcu.cmd.power.hdd.off())


def test_invalid_digital_response_is_not_false(monkeypatch):
    monkeypatch.setattr(pcu, "call_pcu", AsyncMock(return_value="serial garbage"))
    with pytest.raises(RuntimeError, match="Invalid PCU digital"):
        run(pcu.get.digital.docked())


def test_dock_requires_final_command_ack_not_debug_message(monkeypatch):
    monkeypatch.setattr(pcu, "call_pcu", AsyncMock(side_effect=["[I] docking successful, dock failed", "true"]))
    assert run(pcu.cmd.dock()) is False


def test_pcu_serial_prompt_and_write_timeout(monkeypatch):
    serial = Mock()
    serial.__enter__ = Mock(return_value=serial)
    serial.__exit__ = Mock(return_value=False)
    serial.write.side_effect = lambda data: len(data)
    serial.in_waiting = 200
    serial.read.return_value = b"probe\r\nEcho\r\nch> "
    factory = Mock(return_value=serial)
    monkeypatch.setattr(pcu, "Serial", factory)
    assert run(pcu.call_pcu("probe")) == "Echo"
    assert factory.call_args.kwargs["timeout"] == 0
    assert factory.call_args.kwargs["write_timeout"] == 1


def test_pcu_partial_response_has_absolute_deadline(monkeypatch):
    serial = Mock()
    serial.__enter__ = Mock(return_value=serial)
    serial.__exit__ = Mock(return_value=False)
    serial.write.side_effect = lambda data: len(data)
    serial.in_waiting = 1
    serial.read.return_value = b"x"
    monkeypatch.setattr(pcu, "Serial", Mock(return_value=serial))
    monkeypatch.setattr(pcu, "COMMAND_TIMEOUT_SECONDS", 0.01)
    with pytest.raises(TimeoutError, match="PCU response timeout"):
        run(pcu.call_pcu("probe"))


@pytest.fixture
def lifecycle(bcu, tmp_path, monkeypatch):
    cfg = {
        "backup": {"filesystem_uuid": UUID},
        "process": {"state_file": str(tmp_path / "state.json"), "maximum_reboots": 2},
    }
    for name in (
        "engage", "backup", "diagnostics", "copy_logs", "shutdown", "wait_before_shutdown",
        "set_wakeup_time", "run_checked",
    ):
        monkeypatch.setattr(bcu, name, AsyncMock())
    monkeypatch.setattr(bcu, "disengage", AsyncMock(return_value=True))
    fake_pcu = SimpleNamespace(
        handshake=AsyncMock(),
        cmd=SimpleNamespace(shutdown=SimpleNamespace(init=AsyncMock(), abort=AsyncMock())),
    )
    monkeypatch.setattr(bcu, "pcu", fake_pcu)
    monkeypatch.setattr(bcu.asyncio, "sleep", AsyncMock())
    return bcu, cfg, Path(cfg["process"]["state_file"])


def test_success_resets_budget_only_after_clean_isolation(lifecycle):
    bcu, cfg, path = lifecycle
    previous = RecoveryState(path)
    previous.data["reboots"] = 2
    previous.save()
    assert run(bcu.run_cycle(cfg)) is True
    assert RecoveryState(path).data["reboots"] == 0
    bcu.disengage.assert_awaited_once()
    bcu.shutdown.assert_awaited_once_with(30, pcu_notified=True)


def test_failed_backup_always_attempts_cleanup_then_reboots(lifecycle):
    bcu, cfg, path = lifecycle
    bcu.backup.side_effect = OSError("USB disappeared")
    assert run(bcu.run_cycle(cfg)) is False
    bcu.disengage.assert_awaited_once()
    state = RecoveryState(path)
    assert state.data["reboots"] == 1
    assert "USB disappeared" in state.data["last_failure"]
    assert bcu.run_checked.call_args.args[-2:] == ("-r", "now")
    bcu.shutdown.assert_not_awaited()


def test_retry_budget_exhaustion_halts_instead_of_rebooting(lifecycle):
    bcu, cfg, path = lifecycle
    previous = RecoveryState(path)
    previous.data["reboots"] = 2
    previous.save()
    bcu.backup.side_effect = OSError("USB disappeared")
    run(bcu.run_cycle(cfg))
    bcu.run_checked.assert_not_awaited()
    bcu.shutdown.assert_awaited_once_with(30)
    assert RecoveryState(path).data["reboots"] == 2


def test_three_failed_invocations_have_only_two_reboots(lifecycle):
    bcu, cfg, path = lifecycle
    bcu.backup.side_effect = RuntimeError("failure")
    for _ in range(3):
        run(bcu.run_cycle(cfg))
    assert bcu.run_checked.await_count == 2
    assert bcu.shutdown.await_count == 1
    assert RecoveryState(path).data["reboots"] == 2


def test_handshake_failure_still_cleans_up_and_retries(lifecycle):
    bcu, cfg, _ = lifecycle
    bcu.pcu.handshake.side_effect = OSError("serial missing")
    run(bcu.run_cycle(cfg))
    bcu.backup.assert_not_awaited()
    bcu.disengage.assert_awaited_once()
    assert bcu.pcu.handshake.await_count == 3
    bcu.run_checked.assert_awaited_once()


def test_cleanup_failure_is_not_success(lifecycle):
    bcu, cfg, path = lifecycle
    bcu.disengage.side_effect = RuntimeError("PCU lost")
    run(bcu.run_cycle(cfg))
    state = RecoveryState(path)
    assert state.data["reboots"] == 1
    assert "PCU lost" in state.data["last_failure"]


def test_emergency_power_cut_is_not_success(lifecycle):
    bcu, cfg, path = lifecycle
    bcu.disengage.return_value = False
    run(bcu.run_cycle(cfg))
    assert "emergency" in RecoveryState(path).data["last_failure"]


def test_corrupt_state_disables_reboots_but_not_cleanup(lifecycle):
    bcu, cfg, path = lifecycle
    path.write_text("broken")
    run(bcu.run_cycle(cfg))
    bcu.disengage.assert_awaited_once()
    bcu.run_checked.assert_not_awaited()
    bcu.shutdown.assert_awaited_once()
    assert path.read_text() == "broken"


def test_no_shutdown_never_reboots_on_failure(lifecycle):
    bcu, cfg, _ = lifecycle
    bcu.backup.side_effect = RuntimeError("failure")
    assert run(bcu.run_cycle(cfg, no_shutdown=True)) is False
    bcu.disengage.assert_awaited_once()
    bcu.run_checked.assert_not_awaited()
    bcu.shutdown.assert_not_awaited()


def test_reboot_failure_falls_back_to_shutdown(lifecycle):
    bcu, cfg, _ = lifecycle
    bcu.backup.side_effect = RuntimeError("failure")
    bcu.run_checked.side_effect = RuntimeError("reboot rejected")
    run(bcu.run_cycle(cfg))
    bcu.shutdown.assert_awaited_once()


def test_shutdown_failure_uses_remaining_retry_budget(lifecycle):
    bcu, cfg, path = lifecycle
    bcu.shutdown.side_effect = RuntimeError("halt rejected")
    run(bcu.run_cycle(cfg))
    assert RecoveryState(path).data["reboots"] == 1
    assert bcu.run_checked.call_args.args[-2:] == ("-r", "now")


def test_state_write_failure_never_reboots(lifecycle, monkeypatch):
    bcu, cfg, _ = lifecycle
    monkeypatch.setattr(bcu.RecoveryState, "save", Mock(side_effect=OSError("read-only root")))
    run(bcu.run_cycle(cfg))
    bcu.run_checked.assert_not_awaited()
    bcu.shutdown.assert_awaited_once()


def test_emergency_cleanup_unmount_failure_still_powers_off_then_undocks(bcu, monkeypatch):
    disk = SimpleNamespace(mounted=AsyncMock(return_value=True), mountpoint="/media/BackupHDD", timeout=1)
    execute = AsyncMock(side_effect=RuntimeError("busy"))
    events = []

    async def power_off():
        events.append("off")

    async def undock():
        events.append("undock")
        return True

    monkeypatch.setattr(bcu, "run_checked", execute)
    monkeypatch.setattr(bcu.pcu.cmd.power.hdd, "off", power_off)
    monkeypatch.setattr(bcu.pcu.cmd, "undock", undock)
    monkeypatch.setattr(bcu.asyncio, "sleep", AsyncMock())
    assert run(bcu.disengage(disk)) is False
    assert events == ["off", "undock"]


def test_unconfirmed_power_off_never_moves_motor(bcu, monkeypatch):
    disk = SimpleNamespace(mounted=AsyncMock(return_value=False))
    off = AsyncMock(side_effect=RuntimeError("no power ack"))
    undock = AsyncMock()
    monkeypatch.setattr(bcu.pcu.cmd.power.hdd, "off", off)
    monkeypatch.setattr(bcu.pcu.cmd, "undock", undock)
    monkeypatch.setattr(bcu.asyncio, "sleep", AsyncMock())
    with pytest.raises(RuntimeError, match="power ack"):
        run(bcu.disengage(disk))
    assert off.await_count == 3
    undock.assert_not_awaited()


def test_valid_configuration():
    config.validate_config({"backup": {"filesystem_uuid": UUID, "rsync_source": "module"}})


@pytest.mark.parametrize("change", [
    {"filesystem_uuid": ""}, {"destination": "../elsewhere"}, {"destination": "/tmp"},
    {"mountpoint": "/"}, {"backup_timeout_seconds": 0}, {"monitor_interval_seconds": -1},
    {"backup_timeout_seconds": float("inf")}, {"backup_timeout_seconds": float("nan")},
])
def test_invalid_storage_configuration_rejected(change):
    cfg = {"backup": {"filesystem_uuid": UUID, "rsync_source": "module", **change}}
    with pytest.raises(ValueError):
        config.validate_config(cfg)


def test_mount_failure_checked_and_bounded(bcu, monkeypatch):
    disk = SimpleNamespace(
        mounted=AsyncMock(return_value=False), mountpoint="/media/BackupHDD", timeout=1, verify=AsyncMock(),
    )
    monkeypatch.setattr(bcu, "pcu_operation", AsyncMock())
    execute = AsyncMock(side_effect=RuntimeError("mount failed: 32"))
    monkeypatch.setattr(bcu, "run_checked", execute)
    monkeypatch.setattr(bcu.asyncio, "sleep", AsyncMock())
    with pytest.raises(RuntimeError, match="mount failed"):
        run(bcu.engage(disk))
    assert execute.await_count == 3
    disk.verify.assert_not_awaited()


def test_existing_mount_is_verified_not_remounted(bcu, monkeypatch):
    disk = SimpleNamespace(mounted=AsyncMock(return_value=True), verify=AsyncMock())
    monkeypatch.setattr(bcu, "pcu_operation", AsyncMock())
    execute = AsyncMock()
    monkeypatch.setattr(bcu, "run_checked", execute)
    monkeypatch.setattr(bcu.asyncio, "sleep", AsyncMock())
    run(bcu.engage(disk))
    execute.assert_not_awaited()
    disk.verify.assert_awaited_once_with(access=True)


def test_clean_unmount_precedes_power_off_and_undock(bcu, monkeypatch):
    disk = SimpleNamespace(
        mounted=AsyncMock(side_effect=[True, False]), mountpoint="/media/BackupHDD", timeout=1,
    )
    events = []

    async def execute(*args, **kwargs):
        events.append(args[0])

    async def off():
        events.append("off")

    async def undock():
        events.append("undock")
        return True

    monkeypatch.setattr(bcu, "run_checked", execute)
    monkeypatch.setattr(bcu.pcu.cmd.power.hdd, "off", off)
    monkeypatch.setattr(bcu.pcu.cmd, "undock", undock)
    monkeypatch.setattr(bcu.asyncio, "sleep", AsyncMock())
    assert run(bcu.disengage(disk)) is True
    assert events == ["umount", "off", "undock"]


def test_pcu_operation_timeout_and_retries_are_bounded(bcu, monkeypatch):
    calls = []

    async def stalled():
        calls.append(True)
        await asyncio.Event().wait()

    monkeypatch.setattr(bcu.asyncio, "sleep", AsyncMock())
    with pytest.raises(asyncio.TimeoutError):
        run(bcu.pcu_operation(stalled, timeout=0.01, attempts=2))
    assert len(calls) == 2


def test_shutdown_halts_pi_even_when_pcu_is_unreachable(bcu, monkeypatch):
    monkeypatch.setattr(bcu, "pcu_operation", AsyncMock(side_effect=OSError("PCU unavailable")))
    execute = AsyncMock()
    monkeypatch.setattr(bcu, "run_checked", execute)
    run(bcu.shutdown())
    execute.assert_awaited_once_with("sudo", "-n", "/sbin/shutdown", "-h", "now", timeout=15)


@pytest.mark.parametrize("recent", [False, True])
def test_periodic_integrity_schedule_and_readonly_comparison(bcu, tmp_path, monkeypatch, recent):
    disk = SimpleNamespace(
        verify=AsyncMock(), worker_command=lambda operation, *args: ["worker", operation, *args],
    )
    state = RecoveryState(tmp_path / "state.json")
    state.data["last_integrity_check"] = bcu.time.time() if recent else 0
    monkeypatch.setattr(bcu, "resolve_ip", AsyncMock(return_value="192.0.2.1"))
    transfer = AsyncMock()
    monkeypatch.setattr(bcu, "monitored_transfer", transfer)
    execute = AsyncMock(return_value='[{"path": "sample", "sha256": "hash"}]')
    monkeypatch.setattr(bcu, "run_checked", execute)
    run(bcu.backup({"rsync_source": "source"}, disk, state))
    assert transfer.await_count == (1 if recent else 2)
    first_command = transfer.await_args_list[0].args[0]
    assert first_command[-1] == "."
    assert "--dry-run" not in first_command
    if not recent:
        comparison = transfer.await_args_list[1]
        assert "--dry-run" in comparison.args[0]
        assert "--checksum" in comparison.args[0]
        assert comparison.kwargs["reject_output"] is True
        assert execute.call_args.args[1] == "restore"
        assert state.data["last_integrity_check"] > 0
    else:
        execute.assert_not_awaited()


def test_failed_verification_does_not_advance_schedule(bcu, tmp_path, monkeypatch):
    disk = SimpleNamespace(
        verify=AsyncMock(), worker_command=lambda operation, *args: ["worker", operation, *args],
    )
    state = RecoveryState(tmp_path / "state.json")
    monkeypatch.setattr(bcu, "resolve_ip", AsyncMock(return_value="192.0.2.1"))
    monkeypatch.setattr(bcu, "monitored_transfer", AsyncMock(side_effect=[None, RuntimeError("different")]))
    with pytest.raises(RuntimeError, match="different"):
        run(bcu.backup({"rsync_source": "source"}, disk, state))
    assert state.data["last_integrity_check"] == 0


def test_date_readback_mismatch_fails(bcu, monkeypatch):
    from datetime import datetime, timedelta

    monkeypatch.setattr(bcu.pcu.set.date, "now", AsyncMock())
    monkeypatch.setattr(bcu.pcu.get.date, "now", AsyncMock(return_value=datetime(2000, 1, 1)))
    with pytest.raises(RuntimeError, match="date verification failed"):
        run(bcu.set_wakeup_time(timedelta(days=1)))


def test_failed_cycle_invalidates_old_verification(lifecycle):
    bcu, cfg, path = lifecycle
    previous = RecoveryState(path)
    previous.data["last_integrity_check"] = bcu.time.time()
    previous.save()
    bcu.backup.side_effect = RuntimeError("USB failure")
    run(bcu.run_cycle(cfg))
    assert RecoveryState(path).data["last_integrity_check"] == 0
