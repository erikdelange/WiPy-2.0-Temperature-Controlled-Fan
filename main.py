import controller
import pycom


pycom.heartbeat(False)

while True:
    try:
        print("starting server")
        pycom.rgbled(0x001000)  # green led if server is working
        controller.server()
        pycom.heartbeat(True)  # flashing blue led if server was stopped normally
        break
    except Exception as e:
        print("server exception", repr(e))
        pycom.rgbled(0x100000)  # red led if an error occured
        import sys
        sys.print_exception(e)
        break  # dev only, to be replaced by sleep() and machine.reset()
