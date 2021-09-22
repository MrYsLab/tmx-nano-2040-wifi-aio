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

import asyncio
import sys

from tmx_nano2040_wifi_aio import tmx_nano2040_wifi_aio

"""
This example will set a servo to 0, 90 and 180 degree
positions.
"""


async def servo(my_board, pin):
    """
    Set a pin to servo mode and then adjust
    its position.

    :param my_board: board instance
    :param pin: pin to be controlled
    """

    # set the pin mode
    await my_board.set_pin_mode_servo(pin, 1000, 2000)

    await asyncio.sleep(1)

    await my_board.servo_write(pin, 90)
    await asyncio.sleep(1)
    await my_board.servo_write(pin, 0)
    await asyncio.sleep(1)
    await my_board.servo_write(pin, 180)
    await asyncio.sleep(1)
    await my_board.servo_write(pin, 90)
    await my_board.servo_detach(11)

loop = asyncio.get_event_loop()
board = tmx_nano2040_wifi_aio.TmxNano2040WifiAio(ip_address='192.168.2.246')
try:
    loop.run_until_complete(servo(board, 11))
    loop.run_until_complete(board.shutdown())
except KeyboardInterrupt:
    loop.run_until_complete(board.shutdown())
    sys.exit(0)
