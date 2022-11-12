import neopixel
from machine import Pin
from micropython import const

ANTENNA = const(16)  # int(=0)/ext(=1) antenna selector

INT_ANT = const(0)
EXT_ANT = const(1)

antenna = Pin(ANTENNA, mode=Pin.OUT, value=0)

# helper class for the WS2812 neopixel on Wipy 2.0

RGBLED = const(0)  # GPIO pin connected to WS2812


class color:
    OFF = (0, 0, 0)
    AMBER = (255, 100, 0)
    AQUA = (50, 255, 255)
    BLACK = (0, 0, 0)
    BLUE = (0, 0, 255)
    CYAN = (0, 255, 255)
    GOLD = (255, 222, 30)
    GREEN = (0, 255, 0)
    JADE = (0, 255, 40)
    MAGENTA = (255, 0, 20)
    ORANGE = (255, 40, 0)
    PINK = (242, 90, 255)
    PURPLE = (180, 0, 255)
    RED = (255, 0, 0)
    TEAL = (0, 255, 120)
    WHITE = (255, 255, 255)
    YELLOW = (255, 150, 0)


class RGBled:
    def __init__(self, pin=RGBLED):
        self._led = neopixel.NeoPixel(Pin(pin), 1)
        self._intensity = 0.5
        self.color = color.OFF

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self._setcolor()

    @property
    def intensity(self):
        return self._intensity

    @intensity.setter
    def intensity(self, value):
        self._intensity = max(0, min(1, value))
        self._setcolor()

    def _setcolor(self):
        color = tuple(int(self._intensity * element) for element in self._color)
        self._led[0] = color
        self._led.write()


rgbled = RGBled()
