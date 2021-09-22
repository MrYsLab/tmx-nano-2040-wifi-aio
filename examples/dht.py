"""
 Copyright (c) 2021 Alan Yorinks All rights reserved.

 This program is free software; you can redistribute it and/or
 modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 Version 3 as published by the Free Software Foundation; either
 or (at your option) any later version.
 This library is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 General Public License for more details.

 You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
 along with this library; if not, write to the Free Software
 Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""

import sys
import time
import asyncio
from tmx_nano2040_wifi_aio import tmx_nano2040_wifi_aio

"""
This program monitors a DHT sensor. 
"""

# indices into callback data for valid data
REPORT_TYPE = 0
PIN = 1
HUMIDITY = 2
TEMPERATURE = 3
TIME = 4

# indices into callback data for error report
REPORT_TYPE = 0
PIN = 1
ERROR_VALUE = 2


# A callback function to display the distance
async def the_callback(data):
    """
    The callback function to display the change in distance
    :param data: [report_type = PrivateConstants.DHT, pin number, humidity, temperature timestamp]
                 if this is an error report:
                 [report_type = PrivateConstants.DHT, pin number, error value timestamp]
    """
    if data[1]:
        # error message
        date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[4]))
        print(f'DHT Error Report:'
              f'Pin: {data[2]}  Error: {data[1]}  Time: {date}')
    else:
        date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[6]))
        print(f'DHT Valid Data Report:'
              f'Pin: {data[2]} Humidity: {data[4]} Temperature:'
              f' {data[5]} Time: {date}')


async def dht(my_board, pins, callback):
    """
    Set the pin mode for a DHT device. Results will appear via the
    callback.

    :param my_board: TmxNano2040WifiAio instance
    :param pins: List of Arduino pin numbers
    :param callback: The callback function
    """

    # set the pin mode for the trigger and echo pins
    for pin in pins:
        await my_board.set_pin_mode_dht(pin, callback)
        await asyncio.sleep(.1)
    # wait forever
    while True:
        try:
            await asyncio.sleep(.01)
        except KeyboardInterrupt:
            await my_board.shutdown()
            sys.exit(0)


# get the event loop
loop = asyncio.get_event_loop()

# instantiate TmxNano2040WifiAio
board = tmx_nano2040_wifi_aio.TmxNano2040WifiAio(ip_address='192.168.2.246')

try:
    # start the main function
    loop.run_until_complete(dht(board, [11, 12],  the_callback))
    try:
        while True:
            # kill time
            time.sleep(.1)
    except (KeyboardInterrupt, RuntimeError) as e:
        loop.run_until_complete(board.shutdown())
        sys.exit(0)
except KeyboardInterrupt:
    loop.run_until_complete(board.shutdown())
    sys.exit(0)
