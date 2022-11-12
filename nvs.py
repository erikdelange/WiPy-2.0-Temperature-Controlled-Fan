# ESP32 non volatile storage access
#
# ESP32's have a small non volatile storage area which
# can be used to store key-value pairs. The functions
# in this module interact with this storage area for
# storing and retrieving 32-bit integer values.

# Copyright 2022 (c) Erik de Lange
# Released under MIT license

from esp32 import NVS

_namespace = "SYSTEM"  # standard namespace used here


def nvs_set(key, value):
    """ Store integer value in non volatile storage

    :param str key: set value for this key
    :param int value: value to store for key
    """
    nvs = NVS(_namespace)
    nvs.set_i32(key[:15], value)
    nvs.commit()


def nvs_get(key, default_value=None):
    """ Get integer value for key from non volatile storage. Create key if it does not exist.

    :param str key: get value for this key
    :param int default_value: value to return when key was not found
    :return int: value if key was found else default_value
    """
    nvs = NVS(_namespace)
    try:
        return nvs.get_i32(key[:15])
    except OSError:
        nvs_set(key, int(default_value))
        return default_value
