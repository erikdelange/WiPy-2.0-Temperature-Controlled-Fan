import _thread
import json
import time

import logging
import machine
import pycom
import gc

from httpserver import CRLF, MimeType, ResponseHeader, Server, StatusLine, sendfile
from onewire import DS18X20, OneWire

logger = logging.getLogger(__name__)


def nvs_get(key, default_value=0):
    """ Get value for key from NVRAM. Create the key if it does not exist.

    :param str key: get value for this key
    :param int default_value: value to use when key must be created
    :return int: value (note: NVRAM can only store integers)
    """
    if len(key) > 15:
        logger.warning("nvs_get({}): key length is over 15 characters, key truncated".format(key))
        key = key[:15]

    try:
        value = pycom.nvs_get(key)
    except ValueError:  # certain firmware versions throw an (undocumented) ValueError
        value = None
    finally:
        if value is None:
            pycom.nvs_set(key, int(default_value))
            value = int(default_value)

    return value


def nvs_set(key, value):
    """ Local version of pycom.nvs_set which truncates key length to 15 characters """
    pycom.nvs_set(key[:15], value)


class PwmController:

    def __init__(self):
        pwm = machine.PWM(0, frequency=25000)
        self.channel0 = pwm.channel(0, pin="P23", duty_cycle=1.0)
        self.channel1 = pwm.channel(0, pin="P22", duty_cycle=1.0)

        self.temp_in = 0  # inlet water temperature
        self.temp_out = 0  # outlet water temperature

        self.duty_cycle = 0  # unit = %, where 0 if off and 100 is full speed

        self._start_duty_cycle = nvs_get("start_duty_cycle", 100)  # duty cycle at temp_fan_on, unit = %
        self._end_duty_cycle = nvs_get("end_duty_cycle", 20)  # duty cycle at temp_fan_end, unit = %

        self._temp_fan_on = nvs_get("temp_fan_on", 40)  # unit = degrees celsius
        self._temp_fan_end = nvs_get("temp_fan_end", 60)  # unit = degrees celsius

        self._hysteresis = nvs_get("hysteresis", 2)  # unit = degrees celsius

    @property
    def start_duty_cycle(self):
        return self._start_duty_cycle

    @start_duty_cycle.setter
    def start_duty_cycle(self, value):
        self._start_duty_cycle = value
        nvs_set("start_duty_cycle", value)

    @property
    def end_duty_cycle(self):
        return self._end_duty_cycle

    @end_duty_cycle.setter
    def end_duty_cycle(self, value):
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
        self._hysteresis = value
        nvs_set("hysteresis", value)

    def calc_duty_cycle(self, temp):
        """ Convert temperature to corresponding duty cycle

        :param int temp: temperature
        :return int: duty cycle
        """
        if temp < (self.temp_fan_on - self.hysteresis):
            self.duty_cycle = 0

        if temp >= self.temp_fan_on:
            duty_cycle_range = self.end_duty_cycle - self.start_duty_cycle

            if duty_cycle_range == 0:  # every temp has same duty cycle
                self.duty_cycle = self.start_duty_cycle
            else:
                temp_range = self.temp_fan_end - self.temp_fan_on

                if temp_range == 0:  # from nought to 100% in one step
                    self.duty_cycle = self.end_duty_cycle
                else:
                    temp_clipped = min(max(temp - self.temp_fan_on, 0), temp_range)
                    duty_cycle_raw = int(temp_clipped * (duty_cycle_range / temp_range))
                    self.duty_cycle = self.start_duty_cycle + duty_cycle_raw

        return self.duty_cycle

    def set_duty_cycle(self, duty_cycle):
        """ Set the PWM duty cycle for the fans

        :param int duty_cycle: duty cycle as percentage from 0 (stop) to 100 (full speed)
        """
        d = (100 - duty_cycle) / 100  # invert and scale from 0 to 1

        self.channel0.duty_cycle(d)
        self.channel1.duty_cycle(d)


pwm = PwmController()

lock = _thread.allocate_lock()


def controller_daemon():
    """ Measure the temperature at fixed intervals and adjust fan speed """
    ds = DS18X20(OneWire(machine.Pin("P21")))

    if len(ds.roms) == 0:
        logger.error("no temperature sensors found")
        # _thread.exit()
        while True:
            gc.collect()
            time.sleep(30)

    temp = [0 for _ in range(len(ds.roms))]

    while True:
        gc.collect()
        time.sleep(27)  # measure +- every 30 seconds
        for i in range(len(ds.roms)):
            time.sleep_ms(750)
            ds.start_conversion(ds.roms[i])
            time.sleep_ms(750)
            temp[i] = int(ds.read_temp_async(ds.roms[i]))

        with lock:
            pwm.temp_in = max(temp)
            pwm.temp_out = min(temp)

        pwm.calc_duty_cycle(pwm.temp_in)
        pwm.set_duty_cycle(pwm.duty_cycle)


_thread.start_new_thread(controller_daemon, ())

app = Server(timeout=10)


@app.route("GET", "/")
def root(conn, request):
    conn.write(StatusLine.OK_200)
    conn.write(ResponseHeader.CONNECTION_CLOSE)
    conn.write(MimeType.TEXT_HTML)
    conn.write(CRLF)
    sendfile(conn, "index.html")


@app.route("GET", "/favicon.ico")
def favicon(conn, request):
    conn.write(StatusLine.OK_200)
    conn.write(ResponseHeader.CONNECTION_CLOSE)
    conn.write(MimeType.IMAGE_X_ICON)
    conn.write(CRLF)
    sendfile(conn, "favicon.ico")


@app.route("GET", "/api/init")
def init(conn, request):
    settings = dict()
    with lock:
        settings["temp_in"] = pwm.temp_in
        settings["temp_out"] = pwm.temp_out
    settings["duty_cycle"] = pwm.duty_cycle
    settings["end_duty_cycle"] = pwm.end_duty_cycle
    settings["start_duty_cycle"] = pwm.start_duty_cycle
    settings["temp_fan_on"] = pwm.temp_fan_on
    settings["temp_fan_end"] = pwm.temp_fan_end
    settings["hysteresis"] = pwm.hysteresis
    conn.write(StatusLine.OK_200)
    conn.write(ResponseHeader.CONNECTION_CLOSE)
    conn.write(MimeType.APPLICATION_JSON)
    conn.write(CRLF)
    conn.write(json.dumps(settings))


@app.route("GET", "/api/set")
def set(conn, request):
    parameters = request["parameters"]
    if "start_duty_cycle" in parameters:
        pwm.start_duty_cycle = int(parameters["start_duty_cycle"])
    if "end_duty_cycle" in parameters:
        pwm.end_duty_cycle = int(parameters["end_duty_cycle"])
    if "temp_fan_on" in parameters:
        pwm.temp_fan_on = int(parameters["temp_fan_on"])
    if "temp_fan_end" in parameters:
        pwm.temp_fan_end = int(parameters["temp_fan_end"])
    if "hysteresis" in parameters:
        pwm.hysteresis = int(parameters["hysteresis"])
    conn.write(StatusLine.OK_200)
    conn.write(ResponseHeader.CONNECTION_CLOSE)
    conn.write(MimeType.APPLICATION_JSON)
    conn.write(CRLF)
    conn.write(json.dumps(parameters))


@app.route("GET", "/api/status")
def status(conn, request):
    values = dict()
    with lock:
        values["temp_in"] = pwm.temp_in
        values["temp_out"] = pwm.temp_out
    values["duty_cycle"] = pwm.duty_cycle
    values["mem_free"] = gc.mem_free()
    conn.write(StatusLine.OK_200)
    conn.write(ResponseHeader.CONNECTION_CLOSE)
    conn.write(MimeType.APPLICATION_JSON)
    conn.write(CRLF)
    conn.write(json.dumps(values))


@app.route("GET", "/api/stop")
def stop(conn, request):
    conn.write(StatusLine.OK_200)
    conn.write(ResponseHeader.CONNECTION_CLOSE)
    conn.write(CRLF)
    raise Exception("Stop Server")


@app.route("GET", "/api/reset")
def stop(conn, request):
    conn.write(StatusLine.OK_200)
    conn.write(ResponseHeader.CONNECTION_CLOSE)
    conn.write(CRLF)
    time.sleep_ms(500)
    machine.reset()


app.start()  # does not return unless stopped by Exception("Stop Server")
