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
import time
from tmx_nano2040_wifi_aio import tmx_nano2040_wifi_aio

"""
This file demonstrates reading data from IMU. 
"""

# Callback data indices

CB_TIME = 7


async def the_callback(data):
    """
    A callback function to report data changes.

    :param data: [pin_mode, pin, current_reported_value,  timestamp]
    """

    formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[CB_TIME]))
    print(f'IMU_REPORT at {formatted_time}: AX={data[1]} AY={data[2]} AZ={data[3]} GX'
          f'={data[4]}, GY='
          f'{data[5]}, GZ={data[6]}')


async def imu_read(my_board):
    """
    Enable reports from the IMU

    :param my_board: a tmx_nano2040_wifi_aio instance

    """
    await my_board.set_pin_mode_imu(callback=the_callback)

    # run forever waiting for input changes
    try:
        while True:
            await asyncio.sleep(.001)

    except KeyboardInterrupt:
        await my_board.shutdown()
        sys.exit(0)


# get the event loop
loop = asyncio.get_event_loop()

# instantiate tmx_nano2040_wifi_aio
board = tmx_nano2040_wifi_aio.TmxNano2040WifiAio(ip_address='192.168.2.246')

try:
    # start the main function
    loop.run_until_complete(imu_read(board))
    loop.run_until_complete(board.shutdown())

except (KeyboardInterrupt, RuntimeError) as e:
    loop.run_until_complete(board.shutdown())
    sys.exit(0)
