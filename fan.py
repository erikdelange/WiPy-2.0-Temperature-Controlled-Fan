# MicroPython temperature controlled PWM driver
#
# Continuously adjusts speed of PWM controlled fans based on temperature.
# Uses properties and setters to access and change instance variables
# because changed values are immediately stored in ESP32's non volatile
# storage. Based on uasyncio.
#
# Copyright 2022 (c) Erik de Lange
# Released under MIT license

import uasyncio as asyncio
from machine import PWM, Pin

from nvs import nvs_get, nvs_set

# initial values for controller parameters
#
INIT_TEMP_FAN_ON = 30  # unit: degrees
INIT_TEMP_FAN_END = 60  # unit: degrees
INIT_HYSTERESIS = 2  # unit: degrees
INIT_START_DUTY_CYCLE = 20  # duty cycle at temp_fan_on, unit: % (0-100)
INIT_END_DUTY_CYCLE = 80  # duty cycle at temp_fan_end, unit: % (0-100)
INIT_BOOST_DUTY_CYCLE = 80  # unit: degrees


class FanController:
    MAX_DUTY_U16 = 65535

    def __init__(self, sensor, pin):
        """Create fan controller and start the controller task

        :param Sensor sensor: object connecting to the temperature sensor(s)
        :param int pin: output pin number of the PWM controller
        """
        self._pwm = PWM(Pin(pin), freq=25000, duty_u16=FanController.MAX_DUTY_U16)

        self._duty_cycle = 0  # unit: %, where 0 is off and 100 is full speed

        self._temp_fan_on = nvs_get("temp_fan_on", INIT_TEMP_FAN_ON)
        self._temp_fan_end = nvs_get("temp_fan_end", INIT_TEMP_FAN_END)
        self._hysteresis = nvs_get("hysteresis", INIT_HYSTERESIS)

        self._start_duty_cycle = nvs_get("start_duty_cycle", INIT_START_DUTY_CYCLE)
        self._end_duty_cycle = nvs_get("end_duty_cycle", INIT_END_DUTY_CYCLE)

        self._boost_duty_cycle = nvs_get("boost_duty_cycle", INIT_BOOST_DUTY_CYCLE)
        self._boost_minutes_remaining = 0

        asyncio.create_task(self._run(sensor))

    @property
    def start_duty_cycle(self):
        return self._start_duty_cycle

    @start_duty_cycle.setter
    def start_duty_cycle(self, value):
        value = min(max(value, 0), 100)  # limit value to 0 to 100 range
        self._start_duty_cycle = value
        nvs_set("start_duty_cycle", value)

    @property
    def end_duty_cycle(self):
        return self._end_duty_cycle

    @end_duty_cycle.setter
    def end_duty_cycle(self, value):
        value = min(max(value, 0), 100)  # limit value to 0 to 100 range
        self._end_duty_cycle = value
        nvs_set("end_duty_cycle", value)

    @property
    def temp_fan_on(self):
        return self._temp_fan_on

    @temp_fan_on.setter
    def temp_fan_on(self, value):
        self._temp_fan_on = value
        nvs_set("temp_fan_on", value)

    @property
    def temp_fan_end(self):
        return self._temp_fan_end

    @temp_fan_end.setter
    def temp_fan_end(self, value):
        self._temp_fan_end = value
        nvs_set("temp_fan_end", value)

    @property
    def hysteresis(self):
        return self._hysteresis

    @hysteresis.setter
    def hysteresis(self, value):
        value = max(0, value)  # negative hysteresis not allowed
        self._hysteresis = value
        nvs_set("hysteresis", value)

    @property
    def duty_cycle(self):
        return self._duty_cycle

    @duty_cycle.setter
    def duty_cycle(self, value):
        """Set the PWM duty cycle

        :param int value: duty cycle as percentage from 0 (stop) to 100 (full speed)
        """
        value = min(max(value, 0), 100)  # limit value to 0 to 100 (%) range
        self._duty_cycle = value
        d_u16 = FanController.MAX_DUTY_U16 - int(value * (FanController.MAX_DUTY_U16 / 100))
        self._pwm.duty_u16(d_u16)

    @property
    def boost_duty_cycle(self):
        return self._boost_duty_cycle

    @boost_duty_cycle.setter
    def boost_duty_cycle(self, value):
        value = min(max(value, 0), 100)  # limit value to 0 to 100 range
        self._boost_duty_cycle = value
        nvs_set("boost_duty_cycle", value)

    @property
    def boost_minutes_remaining(self):
        return self._boost_minutes_remaining

    @boost_minutes_remaining.setter
    def boost_minutes_remaining(self, value):
        value = max(value, 0)  # no negative waiting time
        self._boost_minutes_remaining = value

    def convert_temp(self, temp):
        """Convert temperature to corresponding duty cycle

        Note: does not set the actual duty cycle value.

        :param float temp: temperature
        :return int: duty cycle between 0 (stop) and 100 (full speed)
        """
        if temp < (self.temp_fan_on - self.hysteresis):
            duty_cycle = 0
        elif temp >= self.temp_fan_on:
            duty_cycle_range = self.end_duty_cycle - self.start_duty_cycle

            if duty_cycle_range == 0:  # situation: every temp has same duty cycle
                self.duty_cycle = self.start_duty_cycle
            else:
                temp_range = self.temp_fan_end - self.temp_fan_on

                if temp_range == 0:  # situation: from nought to 100% in one step
                    self.duty_cycle = self.end_duty_cycle
                else:
                    temp_clipped = min(max(temp - self.temp_fan_on, 0), temp_range)
                    duty_cycle_raw = int(temp_clipped * (duty_cycle_range / temp_range))
                    duty_cycle = self.start_duty_cycle + duty_cycle_raw
        else:
            duty_cycle = self.duty_cycle

        return duty_cycle

    async def _run(self, sensor):
        """Heart of the controller

        Continuously converts the measured inlet temperature to PWM values. A
        manual boost of the fan speed overrides the automatic fan control
        for the specified boost time (in minutes).

        :param Sensor sensor: object connecting to the temperature sensor(s)
        """
        while True:
            if self.boost_minutes_remaining > 0:
                for _ in range(59):
                    self.duty_cycle = self.boost_duty_cycle
                    await asyncio.sleep(1)
                    if self.boost_minutes_remaining == 0:
                        break
                self.boost_minutes_remaining = max(self.boost_minutes_remaining - 1, 0)
            else:
                await asyncio.sleep(2)
                if sensor.active is True:
                    self.duty_cycle = self.convert_temp(sensor.temp_in)
                else:  # temperature measurement stopped, values stale
                    self.duty_cycle = 0  # stop fans
