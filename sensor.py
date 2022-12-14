# MicroPython ds18x20 temperature sensor class
#
# Connects to one or more sensors - all on the same pin - and
# continuously triggers temperature measurements on all sensors.
# Stores the temperature values in the Sensor object for access
# by other processes. Based on uasyncio.
#
# Copyright 2022 (c) Erik de Lange
# Released under MIT license

import logging

import ds18x20
import onewire
import uasyncio as asyncio
from machine import Pin
from micropython import const

logger = logging.getLogger("sensor")

class Sensor:
    MAX_STALE_ERRORS = const(12)

    def __init__(self, pin):
        """Create sensor object and schedule the measurement task

        Expects at least two ds18b20 sensors - one for measuring temperature
        of the inlet water and one for the return flow - but does also work
        with a single sensor, in which case both temperatures are the same.

        :param int pin: number of pin where ds18b20's are connected to
        """
        self.temp_in = 0  # inlet water temperature
        self.temp_out = 0  # return water temperature

        ow = onewire.OneWire(Pin(pin))
        self._ds = ds18x20.DS18X20(ow)

        self._roms = self._ds.scan()
        self.count = len(self._roms)  # sensor count
        self._temp = [0.0 for _ in range(self.count)]

        self.active = False  # True if measuring, False if stopped

        if self.count == 0:
            logger.error("no temperature sensors found")
        else:
            logger.info(f"{self.count} temperature sensor(s) found")
            asyncio.create_task(self._run())

    async def _run(self):
        """Measurement task continuously updating Sensor.temp_xxx variables

        In case of a onewire error - for example because the connection to the
        sensors was cut - tries to restart measurements. After MAX_STALE_ERRORS
        attempts the sensor is marked inactive and consumers must consider the
        temperature values as stale. When the connection to the sensors is
        restored the sensor is marked active again.
        """
        errors = 0

        while True:
            try:
                self._ds.convert_temp()
                await asyncio.sleep_ms(1000)  # wait at least 750 ms

                for i, rom in enumerate(self._roms):
                    self._temp[i] = self._ds.read_temp(rom)

                self.temp_in = round(max(self._temp), 1)  # highest assumed inlet
                self.temp_out = round(min(self._temp), 1)  # lowest assumed return

                self.active = True
            except onewire.OneWireError as e:
                await asyncio.sleep(5)
                errors += 1
                if errors == Sensor.MAX_STALE_ERRORS:
                    self.active = False
                    logger.exception(e, "lost connection to sensors")
                errors = min(errors, Sensor.MAX_STALE_ERRORS)  # stop increment to avoid integer overflow
            else:
                errors = 0
