"""Durable retry budget and verification schedule, stored on the Pi."""

import json
import math
import os
import tempfile
from pathlib import Path


class RecoveryState:
    def __init__(self, filename):
        self.path = Path(filename).expanduser().absolute()
        self.data = {"reboots": 0, "last_integrity_check": 0}
        if self.path.exists():
            self.data.update(json.loads(self.path.read_text()))
        if type(self.data["reboots"]) is not int or self.data["reboots"] < 0:
            raise ValueError("Invalid persisted reboot count")
        timestamp = self.data["last_integrity_check"]
        if type(timestamp) not in (int, float) or not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError("Invalid persisted integrity timestamp")

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".bcu-", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(self.data, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, str(self.path))
            directory = os.open(str(self.path.parent), os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
