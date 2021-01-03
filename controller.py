import gc
import url
import json
import http
import time
import pycom
import socket
import _thread

from machine import Pin
from machine import PWM
from machine import reset
from onewire import DS18X20
from onewire import OneWire


def nvs_get(key, default_value=0):
    """ Get value for key from NVRAM. Create the key if it does not exist.

    :param str key:
    :param int default_value: value to use when creating the key
    :return value int: (NVRAM can only store integers)
    """
    try:
        value = pycom.nvs_get(key)
    except ValueError:  # certain firmware versions throw an (undocumented) ValueError
        value = None

    if value is None:
        pycom.nvs_set(key, int(default_value))
        value = int(default_value)

    return value


pwm = PWM(0, frequency=25000)
channel0 = pwm.channel(0, pin="P23", duty_cycle=1.0)
channel1 = pwm.channel(0, pin="P22", duty_cycle=1.0)

temp0 = 0
temp1 = 0

dutycycle = 0  # unit = %, where 0 if off and 100 is full speed

start_dutycycle = nvs_get("start_dutycycle", 100)  # duty cycle at temp_fan_on, unit = %
end_dutycycle = nvs_get("end_dutycycle", 20)  # duty cycle at temp_fan_end, unit = %

temp_fan_on = nvs_get("temp_fan_on", 40)  # unit = degrees celsius
temp_fan_end = nvs_get("temp_fan_end", 60)  # unit = degrees celsius

hysteresis = nvs_get("hysteresis", 2)  # unit = degrees celsius

lock = _thread.allocate_lock()


def set_dutycycle(d):
    """ Set the PWM dutycycle for the fans.

    :param int d: dutycycle as percentage from 0 (stop) to 100 (full speed)
    """
    d = (100 - d) / 100  # invert and scale from 0 to 1

    channel0.duty_cycle(d)
    channel1.duty_cycle(d)


def daemon():
    """ Measure the temperature at fixed intervals and adjust fan speed. """
    global temp0, temp1, dutycycle

    ds = DS18X20(OneWire(Pin("P21")))

    if len(ds.roms) == 0:
        print("no temperature sensors found")
        _thread.exit()

    t = 0

    while True:
        # measure +- every 30 seconds
        time.sleep(27)
        for i in range(len(ds.roms)):
            time.sleep_ms(750)
            ds.start_conversion(ds.roms[i])
            time.sleep_ms(750)
            t = int(ds.read_temp_async(ds.roms[i]))
            with lock:
                if i == 0:
                    temp0 = t
                else:
                    temp1 = t

        temp = max(temp0, temp1)  # inlet temperature is highest

        if temp < (temp_fan_on - hysteresis):
            dutycycle = 0

        if temp >= temp_fan_on:
            dutycycle_range = end_dutycycle - start_dutycycle

            if dutycycle_range == 0:  # every temp has same duty cycle
                dutycycle = start_dutycycle
            else:
                temp_range = temp_fan_end - temp_fan_on

                if temp_range == 0:  # from nought to 100% in one step
                    dutycycle = end_dutycycle
                else:
                    temp_clipped = min(max(temp - temp_fan_on, 0), temp_range)
                    dutycycle_raw = int(temp_clipped * (dutycycle_range / temp_range))
                    dutycycle = start_dutycycle + dutycycle_raw

        set_dutycycle(dutycycle)


_thread.start_new_thread(daemon, ())


def server():
    """ Web interface. """
    global temp0, temp1, dutycycle
    global start_dutycycle, end_dutycycle, temp_fan_on, temp_fan_end, hysteresis

    try:
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except Exception as e:
        raise(e)

    try:
        serversocket.bind(socket.getaddrinfo("0.0.0.0", 80)[0][-1])
        serversocket.listen()

        while True:
            gc.collect()   # for devices with limited memory (WiPy 2)
            print(gc.mem_free() / 1024, "Kb free")

            conn, addr = serversocket.accept()
            request_line = conn.readline()

            print("request:", request_line, "from", addr)

            if request_line in [b"", b"\r\n"]:
                print("malformed request")
                conn.close()
                continue

            request = url.request(request_line)
            header = request["header"]

            while True:
                line = conn.readline()
                if line in [b"", b"\r\n"]:
                    break

                # add header fields to dictionary 'header'
                semicolon = line.find(b":")
                if semicolon != -1:
                    key = line[0:semicolon].decode("utf-8")
                    value = line[semicolon+1:-2].lstrip().decode("utf-8")
                    header[key] = value

            conn.write("HTTP/1.1 200 OK\nServer: WiPy\n")
            conn.write("Connection: close\nContent-Type: text/html\n\n")

            path = request["path"]

            if path == "/":
                http.sendfile(conn, "index.html")

            if path == "/favicon.ico":
                http.sendfile(conn, "favicon.ico")

            if path == "/api/stop":  # stop server, for dev purposes
                conn.write("\n")
                conn.close()
                break

            if path == "/api/reset":
                conn.write("\n")
                conn.close()
                reset()

            if path == "/api/init":
                settings = dict()
                with lock:
                    settings["temp0"] = max(temp0, temp1)
                    settings["temp1"] = min(temp0, temp1)
                settings["dutycycle"] = dutycycle
                settings["end_dutycycle"] = end_dutycycle
                settings["start_dutycycle"] = start_dutycycle
                settings["temp_fan_on"] = temp_fan_on
                settings["temp_fan_end"] = temp_fan_end
                settings["hysteresis"] = hysteresis
                conn.write(json.dumps(settings))

            if path == "/api/set":
                parameters = request["parameters"]
                if "end_dutycycle" in parameters:
                    end_dutycycle = int(parameters["end_dutycycle"])
                    pycom.nvs_set("end_dutycycle", end_dutycycle)
                if "start_dutycycle" in parameters:
                    start_dutycycle = int(parameters["start_dutycycle"])
                    pycom.nvs_set("start_dutycycle", start_dutycycle)
                if "temp_fan_on" in parameters:
                    temp_fan_on = int(parameters["temp_fan_on"])
                    pycom.nvs_set("temp_fan_on", temp_fan_on)
                if "temp_fan_end" in parameters:
                    temp_fan_end = int(parameters["temp_fan_end"])
                    pycom.nvs_set("temp_fan_end", temp_fan_end)
                if "hysteresis" in parameters:
                    hysteresis = int(parameters["hysteresis"])
                    pycom.nvs_set("hysteresis", hysteresis)
                conn.write(json.dumps(parameters))

            if path == "/api/status":
                values = dict()
                with lock:
                    values["temp0"] = max(temp0, temp1)
                    values["temp1"] = min(temp0, temp1)
                values["dutycycle"] = dutycycle
                conn.write(json.dumps(values))

            conn.write("\n")
            conn.close()
    except Exception as e:
        serversocket.close()
        raise e
    finally:
        serversocket.close()
