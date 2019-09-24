"""
Read Plantower PMSx003 sensors

NOTE:
- Sensor are read on passive mode.
- Active mode (sleep/wake) is not supported.
- Should work on a PMS1003 sensor, but has not been tested.
- Should work on a PMS3003 sensor, but has not been tested.
"""

import time
from typing import Callable, Generator
from serial import Serial
from .logging import logger, SensorWarning, SensorWarmingUp
from . import plantower


class PMSerial:
    """Read PMSx003 messages from serial port
    
    The sensor is woken up after opening the serial port,
    and put to sleep when before closing the port.
    While the serial port is open, the sensor is read in passive mode.

    PMS3003 sensors do not accept serial commands, such as wake/sleep
    or passive mode read. Valid messages are extracted from the serail buffer.
    Support for this sensor is experimental.
    """

    def __init__(self, port: str = "/dev/ttyUSB0") -> None:
        """Configure serial port"""
        self.serial = Serial()
        self.serial.port = port
        self.serial.timeout = 0
        self.sensor = plantower.Sensor.Default  # updated later

    def _cmd(self, command: str) -> bytes:
        """Write command to sensor and return answer"""

        # send command
        cmd = self.sensor.command(command)
        if cmd:
            self.serial.write(cmd)
            self.serial.flush()
        elif command.endswith("read"):
            self.serial.reset_input_buffer()

        # wait for answer
        length = self.sensor.answer_length(command)
        while self.serial.in_waiting < length:
            continue

        # return full buffer
        return self.serial.read(self.serial.in_waiting)

    def __enter__(self) -> Callable[[int], Generator[plantower.Data, None, None]]:
        """Open serial port and sensor setup"""
        if not self.serial.is_open:
            self.serial.open()
            self.serial.reset_input_buffer()

        # wake sensor and set passive mode
        buffer = self._cmd("wake") + self._cmd("passive_mode")

        # guess sensor type from answer
        self.sensor = plantower.Sensor.guess(buffer)

        return self

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        """Put sensor to sleep and close serial port"""
        buffer = self._cmd("sleep")
        self.serial.close()

    def __call__(self, interval: int = 0) -> Generator[plantower.Data, None, None]:
        """Passive mode reading at regular intervals"""
        while self.serial.is_open:
            # passive mode read
            buffer = self._cmd("passive_read")

            try:
                obs = self.sensor.decode(buffer)
            except SensorWarmingUp as e:
                logger.debug(e)
                time.sleep(1)
            except SensorWarning as e:
                logger.debug(e)
                self.serial.reset_input_buffer()
            else:
                yield obs
                delay = interval - (time.time() - obs.time)
                if delay > 0:
                    time.sleep(delay)
