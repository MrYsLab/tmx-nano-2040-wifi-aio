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

import asyncio
import random
import sys
# import time
from tmx_nano2040_wifi_aio import tmx_nano2040_wifi_aio

"""
This program demonstrates using a NeoPixel strip of 8 pixels.
"""
PIN = 11
NUM_PIXELS = 8

# A list to hold a pixel number and its RBG values
random_pixel_setting = [0, 0, 0, 0]


# get a random pixel number
async def get_pixel_number():
    return random.randint(0, NUM_PIXELS)


# get a random pixel intensity
async def get_pixel_intensity():
    return random.randint(0, 255)


# set the color for a random pixel
async def get_random_pixel_and_color():
    random_pixel_setting[0] = await get_pixel_number()
    random_pixel_setting[1] = await get_pixel_intensity()
    random_pixel_setting[2] = await get_pixel_intensity()
    random_pixel_setting[3] = await get_pixel_intensity()


async def fireworks(board):
    # initialize the neopixel object
    await board.set_pin_mode_neopixel(PIN, NUM_PIXELS)

    # randomly select a pixel and it color and show the pixel.
    # clear the pixels between each showing.

    while True:
        try:
            await get_random_pixel_and_color()

            await board.neo_pixel_set_value(random_pixel_setting[0], random_pixel_setting[1],
                               random_pixel_setting[2],
                               random_pixel_setting[3], True)
            await asyncio.sleep(.1)
            await board.neopixel_clear(True)
            await asyncio.sleep(.1)
        except (KeyboardInterrupt, ConnectionResetError):
            await board.shutdown()
            sys.exit(0)
# get the event loop
loop = asyncio.get_event_loop()

# instantiate a board object
my_board = tmx_nano2040_wifi_aio.TmxNano2040WifiAio(ip_address='192.168.2.246')
try:
    loop.run_until_complete(fireworks(my_board))
except KeyboardInterrupt:
    loop.run_until_complete(my_board.shutdown())
    sys.exit(0)
