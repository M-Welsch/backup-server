import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import List, Optional

from serial import Serial

LOG = logging.getLogger(__name__)


class DockingState(Enum):
    pcu_dockingState_unknown: str = "pcu_dockingState_unknown"
    pcu_dockingState9_inbetween: str = "pcu_dockingState9_inbetween"
    pcu_dockingState0_docked: str = "pcu_dockingState0_docked"
    pcu_dockingState7_12vFloating: str = "pcu_dockingState7_12vFloating"
    pcu_dockingState6_5vFloating: str = "pcu_dockingState6_5vFloating"
    pcu_dockingState5_allDocked5vOn: str = "pcu_dockingState5_allDocked5vOn"
    pcu_dockingState4_allDocked12vOn: str = "pcu_dockingState4_allDocked12vOn"
    pcu_dockingState3_allDockedPwrOn: str = "pcu_dockingState3_allDockedPwrOn"
    pcu_dockingState2_allDockedPwrOff: str = "pcu_dockingState2_allDockedPwrOff"
    pcu_dockingState1_undocked: str = "pcu_dockingState1_undocked"


class WakeupReason(Enum):
    WAKEUP_REASON_POWER_ON: str = "poweron"
    WAKEUP_REASON_USER_REQUEST: str = "requested"
    WAKEUP_REASON_SCHEDULED: str = "scheduled"


class AnalogMeasurement(Enum):
    IMOTOR_PROT: str = "imotor_prot"
    STATOR_SUPPLY_SENSE: str = "stator_supply_sense"
    VIN12_MEAS: str = "vin12_meas"


class cmd:
    class shutdown:
        @staticmethod
        async def init() -> None:
            await _send_command(Commands.shutdown, "init")

        @staticmethod
        async def abort() -> None:
            await _send_command(Commands.shutdown, "abort")

    @staticmethod
    async def dock() -> bool:
        return await _dock_and_verify()

    @staticmethod
    async def undock() -> bool:
        return await _undock_and_verify()

    class power:
        class hdd:
            @staticmethod
            async def on() -> None:
                await power(VoltageRail.hdd, DesiredState.on)

            @staticmethod
            async def off() -> None:
                await power(VoltageRail.hdd, DesiredState.off)

        class fiveV:
            @staticmethod
            async def on() -> None:
                await power(VoltageRail.fiveV, DesiredState.on)

            @staticmethod
            async def off() -> None:
                await power(VoltageRail.fiveV, DesiredState.off)

        class bcu:
            @staticmethod
            async def on() -> None:
                await power(VoltageRail.bcu, DesiredState.on)

            @staticmethod
            async def off() -> None:
                await power(VoltageRail.bcu, DesiredState.off)


class debugcmd:
    @staticmethod
    async def wakeup() -> None:
        await call_pcu("debugcmd wakeup")

    @staticmethod
    async def button_pressed(button_id: int) -> None:
        if button_id < 2:
            await call_pcu(f"debugcmd button_{button_id}_pressed")


class get:
    class date:
        @staticmethod
        async def now() -> datetime:
            return await _get_date(date_kind=DateKind.now)

        @staticmethod
        async def wakeup() -> datetime:
            return await _get_date(date_kind=DateKind.wakeup)

        @staticmethod
        async def backup() -> datetime:
            return await _get_date(date_kind=DateKind.backup)

    @staticmethod
    async def dockingstate() -> DockingState:
        dockingstate = await call_pcu("get dockingstate")
        return DockingState(dockingstate)

    @staticmethod
    async def currentlog() -> List[int]:
        response = await call_pcu("get currentlog")
        currents = [int(c) for c in response if c]
        return currents

    @staticmethod
    async def wakeup_reason() -> WakeupReason:
        wr_raw = await call_pcu("get wakeupreason")
        return WakeupReason(wr_raw)

    class analog:
        @staticmethod
        def stator_supply_sense() -> None:
            raise NotImplementedError

        @staticmethod
        def imotor_prot() -> None:
            raise NotImplementedError

        @staticmethod
        def vin12_meas() -> None:
            raise NotImplementedError

    class digital:
        @staticmethod
        async def endswitch() -> bool:
            return await _get_digital(DigitalMeasurement.UNDOCKED_ENDSWITCH)

        @staticmethod
        async def docked() -> bool:
            return await _get_digital(DigitalMeasurement.DOCKED)

    @staticmethod
    async def temperature() -> float:
        raise NotImplementedError


class set:
    class date:
        @staticmethod
        async def now(timestamp: datetime) -> str:
            return await _set_date(date_kind=DateKind.now, date=timestamp)

        @staticmethod
        async def wakeup(timestamp: datetime) -> str:
            return await _set_date(date_kind=DateKind.wakeup, date=timestamp)

        @staticmethod
        async def backup(timestamp: datetime) -> str:
            return await _set_date(date_kind=DateKind.backup, date=timestamp)

    class display:
        @staticmethod
        async def text(content: str) -> None:
            raise NotImplementedError

        @staticmethod
        async def brightness(percent: float) -> None:
            raise NotImplementedError

    class led:
        @staticmethod
        async def on() -> None:
            raise NotImplementedError

        @staticmethod
        async def off() -> None:
            raise NotImplementedError

        @staticmethod
        async def brightness(percent: float) -> None:
            raise NotImplementedError



async def call_pcu(command: str) -> str:
    LOG.debug(f"calling pcu with {command}")
    command_bytes = (command + "\r\n").encode()
    with Serial("/dev/ttyBASEPCU", baudrate=38400, timeout=1) as ser:  # timeout is critical
        ser.write(command_bytes)
        await asyncio.sleep(0.5)
        output = ser.read_until("ch>")
    output = output.decode().split("\n")
    LOG.debug(f"received {output}")
    output = [o.strip() for o in output]
    filtered = _filter_output_payload(output, command)
    return ", ".join(filtered)


async def _probe() -> str:
    return await call_pcu("probe")


async def handshake() -> None:
    maximum_trials = 3
    trials = 0
    LOG.debug("performing handshake with pcu")
    while not (response := await _probe()) == 'Echo':
        LOG.warning(f"handshake not successful, received {response}, try another time (this is normal for the first time! Change this message after initial test!)")
        trials += 1
        if trials >= maximum_trials:
            raise RuntimeError("Cannot handshake with PCU")


async def _get_analog(measurement: AnalogMeasurement) -> int:
    value_raw = await call_pcu("get analog " + measurement.value)
    try:
        return int(value_raw)
    except ValueError:
        return 0


class DigitalMeasurement(Enum):
    HMI_BUTTON_0: str = "hmi_button_0"
    HMI_BUTTON_1: str = "hmi_button_1"
    UNDOCKED_ENDSWITCH: str = "endswitch"
    DOCKED: str = "docked"


async def _get_digital(measurement: DigitalMeasurement) -> bool:
    result = await call_pcu("get digital " + measurement.value)
    return result == "true"


def _filter_output_payload(pcu_outputs: List[str], command_sent: str) -> List[str]:
    """
    returns the usable string from the overall pcu output

    pcu returns the command sent, its output and a new prompt like this
    [b'get date now\r\n', b'00:00:00:542 - 01-01-2000\n', b'ch> ']
    only the second entry is relevant here

    :param pcu_outputs:
    :return:
    """
    filtered = []
    for pcu_output in pcu_outputs:
        if "ch>" in pcu_output:
            filtered.append(pcu_output.split("ch>")[1])
        elif any(
            [
                command_sent in pcu_output,
            ]
        ):
            continue
        else:
            filtered.append(pcu_output)
    filtered = [filtered_item for filtered_item in filtered if filtered_item]
    return filtered


async def check_messages(timeout_secs: float) -> Optional[List[str]]:
    with Serial("/dev/ttyBASEPCU", baudrate=38400, timeout=timeout_secs) as ser:  # timeout is critical
        output = ser.read_until()
    output = output.decode().split("\n")
    LOG.debug(f"received {output}")
    return [o.strip() for o in output]


class Commands(Enum):
    shutdown: str = "shutdown"
    dock: str = "dock"
    undock: str = "undock"
    power: str = "power"
    wakeup: str = "wakeup"


async def _send_command(command: Commands, *args) -> str:  # type: ignore
    command_str = "cmd " + command.value + " " + " ".join(args)
    output_raw = await call_pcu(command_str)
    if f"{command.value} successful" not in output_raw:
        raise RuntimeError
    return output_raw


async def _dock_and_verify() -> bool:
    result = await call_pcu("cmd dock")
    docked = await _get_digital(DigitalMeasurement.DOCKED)
    return "successful" in result and docked


async def _undock_and_verify() -> bool:
    result = await call_pcu("cmd undock")
    undocked = await _get_digital(DigitalMeasurement.UNDOCKED_ENDSWITCH)
    return "successful" in result and undocked


class DateKind(Enum):
    now: str = "now"
    backup: str = "backup"
    wakeup: str = "wakeup"


def _datetime_to_pcu_timestring(date: datetime) -> str:
    return f"{date.year} {date.month} {date.day} {date.hour} {date.minute}"


def _pcu_timestring_to_datetime(pcu_output: str) -> datetime:
    return datetime.strptime(pcu_output, "%H:%M:%S - %d-%m-%Y")


async def _set_date(date_kind: DateKind, date: datetime) -> str:
    command = f"set date " + date_kind.value + " " + _datetime_to_pcu_timestring(date)
    return await call_pcu(command)


async def _get_date(date_kind: DateKind) -> datetime:
    command = "get date " + date_kind.value
    datestr = await call_pcu(command)
    return _pcu_timestring_to_datetime(datestr)


class VoltageRail(Enum):
    hdd: str = "hdd"
    fiveV: str = "5v"
    bcu: str = "bcu"


class DesiredState(Enum):
    on: str = "on"
    off: str = "off"


async def power(rail: VoltageRail, state: DesiredState) -> None:
    command = "cmd power " + rail.value + " " + state.value
    await call_pcu(command)


async def is_powered() -> bool:
    return await get.dockingstate() == DockingState.pcu_dockingState3_allDockedPwrOn
