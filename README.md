# WiPy 2.0 Temperature Controlled Fan
PWM fans with temperature based speed control which can be placed on a central heating convector, with a JavaScript based web interface.

> **Note**
> Although the microcontroller used here is a WiPy 2.0 from Pycom it is running firmware from micropython.org. Pycom was already lagging behind with their firmware, has discontinued the WiPy's, and are in administration since September 2022 so I'm not expecting any updates anymore. I've flashed the WiPy with the latest MicroPython version (1.19.1) which works like a charm.

### Summary
Central heating systems with condensing boilers operate more efficiently if the return water temperature is below 55°C ([Wikipedia](https://en.wikipedia.org/wiki/Condensing_boiler)). One way to extract more heat from a radiator is having fans which blow cold air past it. Not only does this lower the temperature of the return water, it also warms up rooms faster. This project presents a solution where a WiPy is used to control these fans, where the fan speed depends on the temperature of the incoming water. The parameters which control the fan are editable via a web-based user interface.

I have installed this on top of the main convector (which is lowered in a pit) in my living room. Seven PWM controlled fans - normally used for cooling PC's - pull cold air through the convector.

### Operating Principle
The fans should only operate if the central heating is working. Therefor a temperature sensor is attached to the incoming water pipe of the convector. If its temperature is above the threshold temperature the fans start rotating using the start duty cycle. The warmer the incoming water becomes the more the duty cycle moves towards the end duty cycle. Depending on your preference the start duty cycle can be the lowest or the highest value, this solution can handle both. For low temperature heating you want to extract as much warmth from the convector as possible, so set the start duty cycle to the highest value. For a traditional (high temperature) heating system the start duty cycle can be set to the lowest value. When checking if the fans must be stopped a small hysteresis is used to avoid unwanted frequent switching.

![graph.png](https://github.com/erikdelange/WiPy-2.0-Temperature-Controlled-Fan/blob/master/graph.png)

### HTML and JavaScript
The user interface can be found in *index.html*. It consist of four collapsible panels, of which the last two are normally collapsed (for ease of viewing in the image shown in the right column). The status panel shows the actual temperature of the in- and outgoing water in the convector and the current duty cycle of the fans. The boost section allows you to override the fan speed for 10, 20 or 30 minutes. In the settings panel you can change the parameters of the controlling algorithm. Finally the advanced panel shows some information for troubleshooting (are your sensors connected?).

Interaction with the server is done using JavaScript's fetch API. After loading the webpage all fields in the UI are initially filled after a call to /api/init (see *onLoadEvent()*). Every 30 seconds the status fields are refreshed (*setInterval()*) with a call to /api/status. After changing one of the settings fields its new value is sent to the server via /api/set. Every interaction with the server expects a JSON response, except when calling /api/reset or /api/stop.

![ui.png](https://github.com/erikdelange/WiPy-2.0-Temperature-Controlled-Fan/blob/master/ui.png)

Use F12 on Chrome and have a look the messages printed in the console.

The reset button on the UI is useful when a new version of the software has been transferred the WiPy using FTP. It allows you to restart the WiPy from a distance - and thus activate the new software - after it has been uploaded.

### Python Code
The code is based on asyncio. When the Sensor class (*sensor.py*) is instantiated it creates a daemon task which continuously triggers temperature measurements. The same principle applies to the FanController class (*fan.py*). Its daemon continuously retrieves the measured temperatures from the sensor object and uses them to control the fan speed. The FanController uses setters to record the controller parameters. When setting a value it is automatically also stored in the ESP32's non volatile storage (NVS). In *controller.py* an [HTTP server](https://github.com/erikdelange/MicroPython-HTTP-Server) is used to communicate with the UI. Commands are received from the client via the HTTP query string, and responses sent from server to client use JSON. The code for the HTTP server (and for the [logging](https://github.com/erikdelange/MicroPython-Logging) module) is not part of this repository and must be downloaded separately.

Helper module *nvs.py* contains functions to access the NVS, and *wipy2.py* is used to control the WiPy's onboard RGB led.

### Hardware
![circuit.png](https://github.com/erikdelange/WiPy-2.0-Temperature-Controlled-Fan/blob/master/circuit.png)
The heart of the controller is a WiPy 2.0. Attached are two (at least one is mandatory) DS18x20 temperature sensors. One measures the temperature of the incoming water, the other (optional) one the temperature of the outgoing water. The onewire bus is connected to P21 (GPIO26). MicroPythons PWM API is used to control the speed of PWM controlled computer case fans (I've used Arctic PWM PST fans which have an additional connector to allow daisy chaining of fans). As the WiPy cannot drive a PWM fan directly (3V3 vs 5V) a BS170 FET is used as driver. A fan's PWM pin expects an external open collector/drain circuit which can sink 5V. Although a BS170 can officially not be opened completely at a 3V3 gate voltage it did work OK for me. As the fans can be daisy chained only a single PWM output and connector is needed (P23 / GPIO14). Note that the picture shows two driver FETs, but only one is used.

The actual PCB for this project looks like:

![pcb.png](https://github.com/erikdelange/WiPy-2.0-Temperature-Controlled-Fan/blob/master/pcb.png)

The PCB consist mostly of connectors. Note that a 7805 voltage regulator is attached to an aluminum profile for cooling. Bringing down the 12V for the PWM fans to 5V for the WiPy (at some 100mA) does generate some heat. A 5mm jack plug for an external 12V DC power supply is also connected to the aluminum profile, as this provides a sturdy base.

The stripboard design is:

![stripboard.png](https://github.com/erikdelange/WiPy-2.0-Temperature-Controlled-Fan/blob/master/stripboard.png)

I've put the stripboard on a wooden base. This base itself has two neodymium magnets underneath (not visible here) so I can attach it easily to my metal convector.

The three-pin headers connect to the DS18x20 sensors, the four-pin headers to the PWM fans. This is not the most efficient design from space perspective but for me big enough to be handled comfortable, and requires only a limited number of connecting wires.

### My Setup
You need to arrange the connection to the WLAN yourself. I've placed this in *boot.py*. At boot I also start an [FTP server](https://github.com/robert-hh/FTP-Server-for-ESP8266-ESP32-and-PYBD/blob/master/uftpd.py) to be able to upload new software.

### Overkill
Yes, this is absolutely not the lowest cost solution for this problem. A temperature controlled switch like the W1209 is much cheaper and does not require any programming at all. However my solution was - at least to me - more fun as I like programming and had the WiPy in stock anyhow. Remember the law of the instrument: "for a man with a hammer (= a WiPy) every problem looks like a nail" :)

### Using
* WiPy 2.0
* MicroPython 1.19.1
* DS18x20 temperature sensors
* Arctic P14 PWM PST CO fans
* [Logging module](https://github.com/erikdelange/MicroPython-Logging)
* [HTTP server](https://github.com/erikdelange/MicroPython-HTTP-Server) (use ahttpserver, not httpserver)
