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
This example sets up and control an ADXL345 i2c accelerometer.
It will continuously print data the raw xyz data from the device.
"""


# the call back function to print the adxl345 data
async def the_callback(data):
    """

    :param data: [report_type, Device address, device read register, x data pair,
    y data pair, z data pair]
    :return:
    """
    time_stamp = data.pop()
    date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time_stamp))
    print(f'Raw Data:  {data}')
    print(f'ADXL345 Report On: {date}: ')
    print(f'\t\t x-pair={data[4]}, '
          f'{data[5]}  y-pair={data[6]}, '
          f'{data[7]} z-pair={data[8]}, '
          f'{data[9]}')
    print()


async def adxl345(my_board):
    # setup adxl345
    # device address = 83
    await my_board.set_pin_mode_i2c()

    # set up power and control register
    await my_board.i2c_write(83, [45, 0])
    await my_board.i2c_write(83, [45, 8])

    # set up the data format register
    await my_board.i2c_write(83, [49, 8])
    await my_board.i2c_write(83, [49, 3])

    # read_count = 20
    while True:
        # read 6 bytes from the data register
        try:
            await my_board.i2c_read(83, 50, 6, the_callback)
            await asyncio.sleep(.2)

        except (KeyboardInterrupt, RuntimeError, ConnectionResetError) as e:
            if e.args[0] == 'Connection lost':
                print('Is the i2c device connected properly?')
            await my_board.shutdown()
            await asyncio.sleep(1)
            sys.exit(0)

# get the event loop
loop = asyncio.get_event_loop()

# instantiate tmx_nano2040_wifi_aio
board = tmx_nano2040_wifi_aio.TmxNano2040WifiAio(ip_address='192.168.2.246')

try:
    # start the main function
    loop.run_until_complete(adxl345(board))

except KeyboardInterrupt:
    loop.run_until_complete(board.shutdown())
    sys.exit(0)


