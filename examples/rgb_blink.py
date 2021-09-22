"""
 Copyright (c) 2021 Alan Yorinks All rights reserved.

 This program is free software; you can redistribute it and/or
 modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 Version 3 as published by the Free Software Foundation; either
 or (at your option) any later version.
 This library is distributed in the hope that it will be useful,f
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 General Public License for more details.

 You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
 along with this library; if not, write to the Free Software
 Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""

import sys
import asyncio
from tmx_nano2040_wifi_aio import tmx_nano2040_wifi_aio

# pin numbers for the LEDs
LED_G = 25  # green
LED_B = 26  # blue
LED_R = 27  # red


# RGB pins are already established as outputs in the Arduino sketch.
# Blink each LED twice.
async def rgb_blink(the_board):
    for pin in range(LED_G, LED_R + 1):
        for blink in range(2):
            try:
                await the_board.digital_write(pin, 1)
                await asyncio.sleep(1)
                await the_board.digital_write(pin, 0)
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                await the_board.shutdown()
                sys.exit(0)


# get the event loop
loop = asyncio.get_event_loop()

# instantiate tmx_nano2040_wifi_aio
board = tmx_nano2040_wifi_aio.TmxNano2040WifiAio(ip_address='192.168.2.246')
try:
    # start the main function
    loop.run_until_complete(rgb_blink(board))
    loop.run_until_complete(board.shutdown())

except KeyboardInterrupt:
    loop.run_until_complete(board.shutdown())
    sys.exit(0)
