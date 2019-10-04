"""
Access supported PM sensors from a single object
"""


from datetime import datetime
from enum import Enum, auto
from typing import NamedTuple, Optional
from pms import logger
from . import message, obsdata, commands


class Sensor(Enum):
    """Supported PM sensors"""

    PMSx003 = auto()
    PMS3003 = auto()
    SDS01x = auto()
    SDS198 = auto()
    HPMA115S0 = auto()
    HPMA115C0 = auto()
    SPS30 = auto()

    PMS1003 = PMS5003 = PMS7003 = PMSA003 = PMSx003
    G1, G3, G5, G7, G10 = PMS1003, PMS3003, PMS5003, PMS7003, PMSA003
    SDS011 = SDS018 = SDS021 = SDS01x

    Default = PMSx003

    @property
    def Message(self) -> message.Message:
        return getattr(message, self.name)

    @property
    def Data(self):
        return getattr(obsdata, self.name)

    @property
    def Commands(self) -> commands.Commands:
        return getattr(commands, self.name)

    @property
    def baud(self) -> int:
        return 115200 if self.name == "SPS30" else 9600

    @classmethod
    def guess(cls, buffer: bytes) -> "Sensor":
        """Guess sensor type from buffer contents
        
        Need to issue the correct commands for a given sensor.
        Otherwise, the sensor will not wake up...
        """
        if buffer[-8:] == b"\x42\x4D\x00\x04\xe1\x00\x01\x74":
            sensor = cls.PMSx003
        elif buffer[-10:-4] == b"\xAA\xC5\x02\x01\x01\x00":
            if sensor != cls.SDS198:  # SDS01x/SDS198 use the same commands
                sensor = cls.SDS01x
        elif buffer:
            sensor = cls.PMS3003
        else:
            sensor = cls.PMSx003
            logger.debug(f"Sensor returned empty buffer, assume {sensor.name} on sleep mode")
        logger.debug(f"Guess {sensor.name} from buffer contents")
        return sensor

    @staticmethod
    def now() -> int:
        """current time as seconds since epoch"""
        return int(datetime.now().timestamp())

    def command(self, cmd: str) -> commands.Cmd:
        """Serial command for sensor"""
        return getattr(self.Commands, cmd)

    def decode(self, buffer: bytes, *, time: Optional[int] = None) -> NamedTuple:
        """Exract observations from serial buffer"""
        if not time:
            time = self.now()

        data = self.Message.decode(buffer, self.Commands.passive_read)
        return self.Data(time, *data)
