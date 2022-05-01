import pycom
import time
import sys
import gc

pycom.heartbeat(False)

try:
    pycom.rgbled(0x001000)  # green led if server is working
    import controller

    pycom.heartbeat(True)  # flashing blue led if server was stopped normally
except Exception as e:
    pycom.rgbled(0x100000)  # red led if an error occured

    # write exception info to file for debugging purposes
    t = time.localtime()
    filename = "{:04}{:02}{:02}-{:02}{:02}{:02}.txt".format(t[0], t[1], t[2], t[3], t[4], t[5])
    with open(filename, 'w') as output:
        output.write("exception: {}\n".format(repr(e)))
        sys.print_exception(e, output)
        output.write("memory: {} bytes free\n".format(gc.mem_free()))  # WiPy 2 is memory constrained
