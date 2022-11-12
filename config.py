# Configuration for temperature controlled fan
#
# This is the only place where the hardware configuration
# is maintained.
#
# Copyright 2022 (c) Erik de Lange
# Released under MIT license

BOARD = "WiPy2"
DS_PIN = 26  # GPIO Pin number to connect to onewire temperature sensors
PWM_PIN = 14  # GPIO PWM out pin number
