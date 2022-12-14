# Temperature controlled fan main program
#
# Creates all objects, controller tasks and starts the user interface server.
#
# Copyright 2022 (c) Erik de Lange
# Released under MIT license

import gc
import json
import logging

import machine
import uasyncio as asyncio

import config
from ahttpserver import Server, sendfile
from ahttpserver.response import CRLF, MimeType, ResponseHeader, StatusLine
from fan import FanController
from sensor import Sensor
from wipy2 import color, rgbled

logger = logging.getLogger(__name__)

rgbled.color = color.OFF
rgbled.intensity = 0.1

# Controller
sensor = Sensor(config.DS_PIN)
fan = FanController(sensor, config.PWM_PIN)

# User interface
app = Server()


@app.route("GET", "/")
async def root(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.TEXT_HTML)
    writer.write(CRLF)
    await writer.drain()
    await sendfile(writer, "index.html")


@app.route("GET", "/favicon.ico")
async def favicon(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.IMAGE_X_ICON)
    writer.write(CRLF)
    await writer.drain()
    await sendfile(writer, "favicon.ico")


@app.route("GET", "/api/init")
async def api_init(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.APPLICATION_JSON)
    writer.write(CRLF)
    await writer.drain()
    values = dict()
    values["temp_in"] = sensor.temp_in
    values["temp_out"] = sensor.temp_out
    values["duty_cycle"] = fan.duty_cycle
    values["end_duty_cycle"] = fan.end_duty_cycle
    values["start_duty_cycle"] = fan.start_duty_cycle
    values["temp_fan_on"] = fan.temp_fan_on
    values["temp_fan_end"] = fan.temp_fan_end
    values["hysteresis"] = fan.hysteresis
    values["boost_duty_cycle"] = fan.boost_duty_cycle
    values["sensors"] = f"{sensor.count} temperature sensor(s) found"
    values["boost_minutes_remaining"] = f"{fan.boost_minutes_remaining} minutes remaining"
    values["sensor_status"] = ("measurement active" if sensor.active else "measurement inactive")
    values["free_memory"] = gc.mem_free()
    writer.write(json.dumps(values))


@app.route("GET", "/api/set")
async def api_set(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.APPLICATION_JSON)
    writer.write(CRLF)
    await writer.drain()
    parameters = request.parameters
    if "start_duty_cycle" in parameters:
        fan.start_duty_cycle = int(parameters["start_duty_cycle"])
    if "end_duty_cycle" in parameters:
        fan.end_duty_cycle = int(parameters["end_duty_cycle"])
    if "temp_fan_on" in parameters:
        fan.temp_fan_on = int(parameters["temp_fan_on"])
    if "temp_fan_end" in parameters:
        fan.temp_fan_end = int(parameters["temp_fan_end"])
    if "hysteresis" in parameters:
        fan.hysteresis = int(parameters["hysteresis"])
    if "boost_duty_cycle" in parameters:
        fan.boost_duty_cycle = int(parameters["boost_duty_cycle"])
    writer.write(json.dumps(parameters))  # feedback


@app.route("GET", "/api/click")
async def api_button_low(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.APPLICATION_JSON)
    writer.write(CRLF)
    await writer.drain()
    parameters = request.parameters
    if "button" in parameters:
        value = parameters["button"]
        if value == "10%20Min":
            fan.boost_minutes_remaining = int(value.split("%")[0])
        elif value == "20%20Min":
            fan.boost_minutes_remaining = int(value.split("%")[0])
        elif value == "30%20Min":
            fan.boost_minutes_remaining = int(value.split("%")[0])
        elif value == "Stop":
            fan.boost_minutes_remaining = 0
    writer.write(json.dumps(parameters))  # feedback


@app.route("GET", "/api/status")
async def api_status(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(MimeType.APPLICATION_JSON)
    writer.write(CRLF)
    await writer.drain()
    values = dict()
    values["temp_in"] = sensor.temp_in
    values["temp_out"] = sensor.temp_out
    values["duty_cycle"] = fan.duty_cycle
    values["boost_duty_cycle"] = fan.boost_duty_cycle
    values["boost_minutes_remaining"] = f"{fan.boost_minutes_remaining} minutes remaining"
    values["sensors"] = f"{sensor.count} temperature sensor(s) found"
    values["sensor_status"] = ("measurement active" if sensor.active else "measurement inactive")
    values["free_memory"] = gc.mem_free()
    writer.write(json.dumps(values))


@app.route("GET", "/api/reset")
async def api_reset(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(CRLF)
    await writer.drain()
    await asyncio.sleep_ms(250)
    machine.reset()


@app.route("GET", "/api/stop")
async def stop(reader, writer, request):
    writer.write(StatusLine.OK_200)
    writer.write(ResponseHeader.CONNECTION_CLOSE)
    writer.write(CRLF)
    await writer.drain()
    raise(KeyboardInterrupt)


# End of user interface code

async def check_sensors_task():
    """ Set led color to blue if no sensors are found """
    while True:
        if sensor.count == 0:
            rgbled.color = color.BLUE
        else:
            rgbled.color = color.GREEN
        await asyncio.sleep(1)

async def free_memory_task():
    while True:
        gc.collect()
        gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
        await asyncio.sleep(5)

try:
    def handle_exception(loop, context):
        # uncaught exceptions end up here
        import sys
        logger.exception(context["exception"], "global exception handler")
        sys.exit()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    loop.create_task(check_sensors_task())
    loop.create_task(free_memory_task())
    loop.create_task(app.start())

    rgbled.color = color.GREEN

    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    asyncio.run(app.stop())
    asyncio.new_event_loop()
    rgbled.color = color.RED
