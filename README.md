# Tmx-Nano-2040-WiFi-AIO

Tmx-nano-2040-wifi-aio is a member of the [Telemetrix](https://mryslab.github.io/telemetrix/) 
family and is a Python asyncio client
specifically tailored to remotely control and monitor
the Arduino Nano RP2040 Connect using Python scripts running on your PC.

When paired with the [Telemetrix4Connect2040](https://github.com/MrYsLab/Telemetrix4Connect2040)
custom Arduino server sketch, control and
monitoring of the Arduino Nano RP2040 Connect accomplished using a Wi-Fi link between the
PC and the Arduino.

This library supports the following features:
* Analog and Digital Input
* Digital Outputs including PWM
* Onboard devices:
    * IMU
    * Microphone
    * RGB LED
* I2C device communications.
* SPI device communications.
* HC-SR04 Type distance sensors.
* DHT Type humidity/temperature sensors.
* Servo motors.
* NeoPixel strips.


A [User's Guide](https://mryslab.github.io/tmx-nano-2040-wifi-aio/) explaining 
installation and use is available online.

The Python API for may be found [here.](https://htmlpreview.github.io/?https://github.com/MrYsLab/tmx-nano-2040-wifi-aio/blob/master/html/tmx_nano2040_wifi_aio/index.html) 

Here is a sample project that blinks the Arduino Board LED:

```
import asyncio
import sys

from tmx_nano2040_wifi_aio import tmx_nano2040_wifi_aio

"""
Setup a pin for digital output and output a signal
and toggle the pin. Do this 4 times.
"""

# some globals
DIGITAL_PIN = 13  # arduino pin number


async def blink(my_board, pin):
    """
    This function toggles a digital pin.

    :param my_board: an tmx_nano2040_wifi_aio instance
    :param pin: pin to be controlled
    """

    # set the pin mode
    await my_board.set_pin_mode_digital_output(pin)

    # toggle the pin 4 times and exit
    for x in range(4):
        print('ON')
        await my_board.digital_write(pin, 0)
        await asyncio.sleep(1)
        print('OFF')
        await my_board.digital_write(pin, 1)
        await asyncio.sleep(1)


# get the event loop
loop = asyncio.get_event_loop()

# instantiate tmx_nano2040_wifi_aio
board = tmx_nano2040_wifi_aio.TmxNano2040WifiAio(ip_address='192.168.2.246')

try:
    # start the main function
    loop.run_until_complete(blink(board, DIGITAL_PIN))
    loop.run_until_complete(board.shutdown())

except KeyboardInterrupt:
    loop.run_until_complete(board.shutdown())
    sys.exit(0)

```