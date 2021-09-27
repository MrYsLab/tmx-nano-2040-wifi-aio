# noinspection GrazieInspection
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
import socket
import struct
import sys
import time

# noinspection PyPackageRequirementscd

# noinspection PyUnresolvedReferences
from tmx_nano2040_wifi_aio.private_constants import PrivateConstants
from tmx_nano2040_wifi_aio.telemetrix_aio_socket import TelemetrixAioSocket


# noinspection PyPackageRequirements


# noinspection PyPep8,PyMethodMayBeStatic,GrazieInspection,PyBroadException,PyArgumentList
class TmxNano2040WifiAio:
    """
    This class exposes and implements the telemetrix API for the
    Arduino Nano RP2040 Connect using Python asyncio for concurrency.

    It includes the public API methods as well as
    a set of private methods.

    """

    # noinspection PyPep8,PyPep8,PyPep8
    def __init__(self, arduino_wait=.01,
                 instance_id=1,
                 sleep_tune=0.000001,
                 autostart=True,
                 loop=None,
                 shutdown_on_exception=True,
                 reset_board_on_shutdown=True,
                 close_loop_on_shutdown=True,
                 ip_address=None, ip_port=31335):

        """
        :param arduino_wait: wait time for Arduino to reset itself.
                             The time is specified in seconds. Increase
                             this value if your application does not
                             locate the Nano Connect.

        :param instance_id: value must match the value set in the server. It
                            is used to identify the connected Arduino.

        :param sleep_tune: A tuning parameter (typically not changed by the user)

        :param autostart: If you wish to call the start method within your
                          application manually, then set this to False.

        :param loop: optional user-provided event-loop

        :param shutdown_on_exception: call shutdown before raising
                                      a RunTimeError exception, or
                                      receiving a KeyboardInterrupt exception

        :param reset_board_on_shutdown: if True, a hardware reset  of the board is
                                        performed when the shutdown method is called.

        :param close_loop_on_shutdown: If True, stop and close the event loop
                                       when a shutdown occurs.

        :param ip_address: This parameter is required. It must match the IP
                           assigned to the Arduino Nano RP2040 Connect.

        :param ip_port: IP port of TCP/IP connected device

        """

        self.shutdown_on_exception = shutdown_on_exception

        self.reset_board_on_shutdown = reset_board_on_shutdown

        self.close_loop_on_shutdown = close_loop_on_shutdown

        self.autostart = autostart
        self.ip_address = ip_address
        self.ip_port = ip_port

        # set the event loop
        if loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop

        self.shutdown_on_exception = shutdown_on_exception
        self.close_loop_on_shutdown = close_loop_on_shutdown

        if not ip_address:
            if self.shutdown_on_exception:
                self.shutdown()
            raise RuntimeError('An IP Address MUST BE SPECIFIED')

        # if tcp, this variable is set to the connected socket
        self.sock = None

        self.i2c_active = False

        # valid pins
        # sda = 18 only for i2c (A4)
        # scl = 19 only for i2c (A5)
        # spi miso - D11
        # spi mosi - D12
        # spi clock -D13
        # (CS / SS) - D0-D10,
        # NeoPixel D2 - D
        # digital output pins are 0-17
        # digital input pins are 0-17, 20 and 21
        # analog pins are a0-a7 (a4, a5, a6, a7 are in the WifiNINA chip)
        # RGB are pseudo pins defined in private_constants.py

        self.digital_input_pins = [x for x in range(18)]
        self.digital_input_pins.extend([20, 21])

        self.digital_output_pins = [x for x in range(18)]
        self.digital_output_pins.extend([PrivateConstants.LED_G,
                                         PrivateConstants.LED_B,
                                         PrivateConstants.LED_R])

        self.analog_pins = [x for x in range(8)]

        # map the D pin number to the GPIO pin number
        self.d_to_g_pin_map = {2: 25, 3: 15, 4: 16, 5: 17, 6: 18, 7: 19,
                               8: 20, 9: 21, 10: 5, 11: 7, 12: 4,
                               13: 6, 14: 26, 15: 27, 16: 28, 17: 29}

        # map a gpio pin to a digital pin
        self.g_to_d_pin_map = {25: 2, 15: 3, 16: 4, 17: 5, 18: 6, 19: 7,
                               20: 8, 21: 9, 5: 10, 7: 11, 4: 12,
                               6: 13, 26: 14, 27: 15, 28: 16, 29: 17}

        self.valid_spi_cs_pins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        self.cs_pins_enabled = []

        self.spi_callback = None

        # check to make sure that Python interpreter is version 3.7 or greater
        python_version = sys.version_info
        if python_version[0] >= 3:
            if python_version[1] >= 7:
                pass
            else:
                if self.shutdown_on_exception:
                    self.shutdown()
                raise RuntimeError("ERROR: Python 3.7 or greater is "
                                   "required for use of this program.")

        # save input parameters as instance variables
        self.arduino_wait = arduino_wait
        self.instance_id = instance_id
        self.sleep_tune = sleep_tune
        self.shutdown_on_exception = shutdown_on_exception

        # The report_dispatch dictionary is used to process
        # incoming report messages by looking up the report message
        # and executing its associated processing method.

        self.report_dispatch = {}

        # To add a command to the command dispatch table, append here.
        self.report_dispatch.update(
            {PrivateConstants.LOOP_COMMAND: self._report_loop_data})
        self.report_dispatch.update(
            {PrivateConstants.DEBUG_PRINT: self._report_debug_data})
        self.report_dispatch.update(
            {PrivateConstants.DIGITAL_REPORT: self._digital_message})
        self.report_dispatch.update(
            {PrivateConstants.ANALOG_REPORT: self._analog_message})
        self.report_dispatch.update(
            {PrivateConstants.FIRMWARE_REPORT: self._firmware_message})
        self.report_dispatch.update({PrivateConstants.I_AM_HERE_REPORT: self._i_am_here})
        self.report_dispatch.update(
            {PrivateConstants.SERVO_UNAVAILABLE: self._servo_unavailable})
        self.report_dispatch.update(
            {PrivateConstants.I2C_READ_REPORT: self._i2c_read_report})
        self.report_dispatch.update(
            {PrivateConstants.I2C_TOO_FEW_BYTES_RCVD: self._i2c_too_few})
        self.report_dispatch.update(
            {PrivateConstants.I2C_TOO_MANY_BYTES_RCVD: self._i2c_too_many})
        self.report_dispatch.update(
            {PrivateConstants.SONAR_DISTANCE: self._sonar_distance_report})
        self.report_dispatch.update(
            {PrivateConstants.IMU_REPORT: self._imu_report})
        self.report_dispatch.update(
            {PrivateConstants.MICROPHONE_REPORT: self._microphone_report})
        self.report_dispatch.update(
            {PrivateConstants.DHT_REPORT: self._dht_report})
        self.report_dispatch.update(
            {PrivateConstants.SPI_REPORT: self._spi_report})

        # dictionaries to store the callbacks for each pin
        self.analog_callbacks = {}

        self.digital_callbacks = {}

        self.i2c_callback = None

        # the trigger pin will be the key to retrieve
        # the callback for a specific HC-SR04
        self.sonar_callbacks = {}

        self.sonar_count = 0

        self.dht_callbacks = {}

        self.dht_count = 0

        # imu variables
        self.imu_callback = None
        self.imu_enabled = False

        # microphone variables
        self.microphone_callback = None
        self.mic_type = PrivateConstants.AT_MICROPHONE_MONO
        self.mic_current_channel = 'm'
        self.mic_channel = 0  # flip flop for stereo reports
        self.mic_enabled = False

        # socket for tcp/ip communications
        self.sock = None

        # flag to indicate we are in shutdown mode
        self.shutdown_flag = False

        # debug loop back callback method
        self.loop_back_callback = None

        # firmware version to be stored here
        self.firmware_version = []

        # flag to indicate if spi is initialized
        self.spi_enabled = False

        # generic asyncio task holder
        self.the_task = None

        # flag to indicate we are in shutdown mode
        self.shutdown_flag = False

        # neopixel data
        self.number_of_pixels = None

        self.neopixels_initiated = False

        print(f"TmxNano2040Wifi:  Version {PrivateConstants.TELEMETRIX_VERSION}\n\n"
              f"Copyright (c) 2021 Alan Yorinks All Rights Reserved.\n")
        # wait for arduino to reset
        print(
            f'\nWaiting {self.arduino_wait} seconds(arduino_wait) for Arduino devices to '
            'reset...')
        time.sleep(self.arduino_wait)
        print('Establishing IP connection...')

        if autostart:
            self.loop.run_until_complete(self.start_aio())

    async def start_aio(self):
        """
        This method completes the instantiation of the TmxNano2040WifiAio
        class. If you set autostart to False, then your application decides
        when to complete the instantiation.
        """

        self.sock = TelemetrixAioSocket(self.ip_address, self.ip_port, self.loop)
        await self.sock.start()

        self.the_task = self.loop.create_task(self._arduino_report_dispatcher())

        # getting instance ID
        await self._get_arduino_id()

        # get telemetrix firmware version and print it
        print('\nRetrieving Telemetrix4Connect2040 firmware ID...')
        await self._get_firmware_version()
        if not self.firmware_version:
            await self._get_firmware_version()
            if not self.firmware_version:
                if self.shutdown_on_exception:
                    await self.shutdown()
                    await asyncio.sleep(.3)
                raise RuntimeError(f'Telemetrix4Connect2040 firmware version')

        else:
            print(f'Telemetrix4Connect2040 firmware version: {self.firmware_version[0]}.'
                  f'{self.firmware_version[1]}.{self.firmware_version[2]}')
        command = [PrivateConstants.ENABLE_ALL_REPORTS]
        await self._send_command(command)

    async def analog_write(self, pin, value):
        """
        Set the specified pin to the specified value.

        The maximum value for the Nano RP2040 is 255.


        :param pin: Arduino pin number

        :param value: pin value (maximum is 255)

        """

        if value > 255:
            raise RuntimeError('Maximum value for analog_write is 255')
        command = [PrivateConstants.ANALOG_WRITE, pin, value]
        await self._send_command(command)

    async def digital_write(self, pin, value):
        """
        Set the specified pin to the specified value.

        :param pin: arduino pin number

        :param value: pin value (1 or 0)

        """

        command = [PrivateConstants.DIGITAL_WRITE, pin, value]
        await self._send_command(command)

    async def disable_all_reporting(self):
        """
        Disable reporting for all digital and analog input pins
        """
        command = [PrivateConstants.MODIFY_REPORTING,
                   PrivateConstants.REPORTING_DISABLE_ALL, 0]
        await self._send_command(command)

    async def disable_analog_reporting(self, pin):
        """
        Disables analog reporting for a single analog pin.

        :param pin: Analog pin number. The pin number is specified
                    without the "A" prefix. For example, pin A0
                    is specified as 0.

        """
        command = [PrivateConstants.MODIFY_REPORTING,
                   PrivateConstants.REPORTING_ANALOG_DISABLE, pin]
        await self._send_command(command)

    async def disable_digital_reporting(self, pin):
        """
        Disables digital reporting for a single digital input.

        :param pin: Pin number.

        """
        command = [PrivateConstants.MODIFY_REPORTING,
                   PrivateConstants.REPORTING_DIGITAL_DISABLE, pin]
        await self._send_command(command)

    async def enable_analog_reporting(self, pin):
        """
        Enables analog reporting for the specified pin.

        :param pin: Analog pin number. The pin number is specified
                    without the "A" prefix. For example, pin A0
                    is specified as 0.
        """
        command = [PrivateConstants.MODIFY_REPORTING,
                   PrivateConstants.REPORTING_ANALOG_ENABLE, pin]
        await self._send_command(command)

    async def enable_digital_reporting(self, pin):
        """
        Enable reporting on the specified digital pin.

        :param pin: Pin number.
        """

        command = [PrivateConstants.MODIFY_REPORTING,
                   PrivateConstants.REPORTING_DIGITAL_ENABLE, pin]
        await self._send_command(command)

    async def _get_arduino_id(self):
        """
        Retrieve the server arduino id

        This is a private method.

        """
        command = [PrivateConstants.ARE_U_THERE]
        await self._send_command(command)
        # provide time for the reply
        await asyncio.sleep(.5)
        if self.reported_arduino_id != self.instance_id:
            raise RuntimeError("Client and Server Instance ID's Do Not Match.")
            if self.shutdown_on_exception:
                await self.shutdown()
                await asyncio.sleep(.3)


    async def _get_firmware_version(self):
        """
        This method retrieves the
        server's firmware version

        This is a private method.


        """
        command = [PrivateConstants.GET_FIRMWARE_VERSION]
        await self._send_command(command)
        # provide time for the reply
        await asyncio.sleep(1)

    async def i2c_read(self, address, register, number_of_bytes,
                       callback=None):
        """
        Read the specified number of bytes from the specified register for
        the i2c device.


        :param address: i2c device address

        :param register: i2c register (or None if no register selection is needed)

        :param number_of_bytes: number of bytes to be read

        :param callback: Required callback function to report i2c data as a
                   result of read command

        callback returns a data list:
        [I2C_READ_REPORT, address, register, count of data bytes, data bytes, time-stamp]

        """
        if not self.i2c_active:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError(
                'I2C Write: set_pin_mode i2c never called.')
        await self._i2c_read_request(address, register, number_of_bytes,
                                     callback=callback)

    async def i2c_read_restart_transmission(self, address, register,
                                            number_of_bytes,
                                            callback=None):
        """
        Read the specified number of bytes from the specified register for
        the i2c device and restart transmission after the read. It is
        required for some i2c devices, such as the MMA8452Q accelerometer.


        :param address: i2c device address

        :param register: i2c register (or None if no register
                                                    selection is needed)

        :param number_of_bytes: number of bytes to be read

        :param callback: Required callback function to report i2c data as a
                   result of read command


        callback returns a data list:

        [I2C_READ_REPORT, address, register, count of data bytes, data bytes, time-stamp]

        """

        if not self.i2c_active:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError(
                'I2C Write: set_pin_mode i2c never called.')
        await self._i2c_read_request(address, register, number_of_bytes,
                                     stop_transmission=False,
                                     callback=callback)

    async def _i2c_read_request(self, address, register, number_of_bytes,
                                stop_transmission=True, callback=None):
        """
        This method requests the read of an i2c device. Results are retrieved
        via callback.

        This is a private method.

        :param address: i2c device address

        :param register: register number (or None if no register selection is needed)

        :param number_of_bytes: number of bytes expected to be returned

        :param stop_transmission: stop transmission after read

        :param callback: Required callback function to report i2c data as a
                   result of read command.

        """
        if not callback:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('I2C Read: A callback function must be specified.')

        self.i2c_callback = callback

        if not register:
            register = 0

        # message contains:
        # 1. address
        # 2. register
        # 3. number of bytes
        # 4. restart_transmission - True or False
        # 5. i2c port

        command = [PrivateConstants.I2C_READ, address, register, number_of_bytes,
                   stop_transmission]
        await self._send_command(command)

    async def i2c_write(self, address, args):
        """
        Write data to an i2c device.

        :param address: i2c device address

        :param args: A variable number of bytes to be sent to the device
                     passed in as a list

        """

        if not self.i2c_active:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError(
                'I2C Write: set_pin_mode i2c never called.')

        command = [PrivateConstants.I2C_WRITE, len(args), address]

        for item in args:
            command.append(item)

        await self._send_command(command)

    async def loop_back(self, start_character, callback=None):
        """
        This debugging method sends a character to the Arduino device
        and has the device loop it back.

        :param start_character: The character to loop back. It should be
                                an integer.

        :param callback: Required callback method. The
                         Looped back character is provided to
                         the callback method.

        """
        command = [PrivateConstants.LOOP_COMMAND, ord(start_character)]
        self.loop_back_callback = callback
        await self._send_command(command)

    async def neo_pixel_set_value(self, pixel_number, r=0, g=0, b=0, auto_show=False):
        """
        Set the selected pixel in the pixel array on the Arduino Nano rp2040 to
        the value provided.

        :param pixel_number: pixel number

        :param r: red value 0-255

        :param g: green value 0-255

        :param b: blue value 0-255

        :param auto_show: call show automatically

        """
        if not self.neopixels_initiated:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('You must call set_pin_mode_neopixel first')

        if pixel_number > self.number_of_pixels:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('Pixel number is out of legal range')

        if r and g and b not in range(256):
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('Pixel value must be in the range of 0-255')

        command = [PrivateConstants.SET_NEO_PIXEL, pixel_number, r, g, b, auto_show]
        await self._send_command(command)

        if auto_show:
            await self.neopixel_show()

    async def neopixel_clear(self, auto_show=True):
        """
        Clear all pixels

        :param auto_show: call show automatically

        """
        if not self.neopixels_initiated:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('You must call set_pin_mode_neopixel first')
        command = [PrivateConstants.CLEAR_ALL_NEO_PIXELS, auto_show]
        await self._send_command(command)
        if auto_show:
            await self.neopixel_show()

    async def neopixel_fill(self, r=0, g=0, b=0, auto_show=True):
        """
        Fill all pixels with the specified RGB values.

        :param r: 0-255

        :param g: 0-255

        :param b: 0-255

        :param auto_show: call show automatically
        """
        if not self.neopixels_initiated:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('You must call set_pin_mode_neopixel first')
        if r and g and b not in range(256):
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('Pixel value must be in the range of 0-255')
        command = [PrivateConstants.FILL_ALL_NEO_PIXELS, r, g, b, auto_show]
        await self._send_command(command)

        if auto_show:
            await self.neopixel_show()

    async def neopixel_show(self):
        """
        Write the NeoPixel buffer stored in the server to the NeoPixel strip.

        """
        if not self.neopixels_initiated:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('You must call set_pin_mode_neopixel first')
        command = [PrivateConstants.SHOW_NEO_PIXELS]
        await self._send_command(command)

    async def set_analog_scan_interval(self, interval):
        """
        Set the analog scanning interval.

        :param interval: value of 0 - 255 - milliseconds
        """

        if 0 <= interval <= 255:
            command = [PrivateConstants.SET_ANALOG_SCANNING_INTERVAL, interval]
            await self._send_command(command)
        else:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('Analog interval must be between 0 and 255')

    async def set_pin_mode_analog_output(self, pin_number):
        """
        Set a pin as a pwm (analog output) pin.

        :param pin_number:arduino pin number

        """
        if pin_number not in self.digital_output_pins:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('Illegal pin for analog output')
        await self._set_pin_mode(pin_number, PrivateConstants.AT_OUTPUT)

    async def set_pin_mode_analog_input(self, pin_number, differential=0, callback=None):
        """
        Set a pin as an analog input.

        :param pin_number: arduino pin number

        :param differential: difference in previous to current value before
                             report will be generated

        :param callback: Required callback function.


        callback returns a data list:

        [pin_type, pin_number, pin_value, raw_time_stamp]

        The pin_type for analog input pins = 2

        """
        if pin_number not in self.analog_pins:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('Illegal pin number for analog input.')
        await self._set_pin_mode(pin_number, PrivateConstants.AT_ANALOG, differential,
                                 callback)

    async def set_pin_mode_dht(self, pin, callback=None):
        """

        :param pin: data pin

        :param callback: Required callback function

        Error Callback: [DHT REPORT Type, DHT_ERROR_NUMBER, PIN, Time]

        Valid Data Callback: DHT REPORT Type, DHT_DATA=, PIN, Humidity,
                             Temperature, Time]

        """

        if not callback:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('set_pin_mode_dht: A Callback must be specified')

        if self.dht_count < PrivateConstants.MAX_DHTS:
            self.dht_callbacks[pin] = callback
            self.dht_count += 1

            command = [PrivateConstants.DHT_NEW, pin]
            await self._send_command(command)
        else:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError(
                f'Maximum Number Of DHTs Exceeded - set_pin_mode_dht fails for pin {pin}')

    async def set_pin_mode_digital_input(self, pin_number, callback=None):
        """
        Set a pin as a digital input.

        :param pin_number: arduino pin number

        :param callback: Required callback function.


        callback returns a data list:

        [pin_type, pin_number, pin_value, raw_time_stamp]

        The pin_type for digital input pins = 0

        """
        if pin_number not in self.digital_input_pins:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('Illegal pin number for digital input.')
        await self._set_pin_mode(pin_number, PrivateConstants.AT_INPUT, callback=callback)

    async def set_pin_mode_digital_input_pullup(self, pin_number, callback=None):
        """
        Set a pin as a digital input with pullup enabled.

        :param pin_number: arduino pin number

        :param callback: Required callback function.


        callback returns a data list:

        [pin_type, pin_number, pin_value, raw_time_stamp]

        The pin_type for digital input pins with pullups enabled = 11

        """
        if pin_number not in self.digital_input_pins:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('Illegal pin number for digital input.')
        await self._set_pin_mode(pin_number, PrivateConstants.AT_INPUT_PULLUP,
                                 callback=callback)

    async def set_pin_mode_digital_output(self, pin_number):
        """
        Set a pin as a digital output pin.

        :param pin_number: arduino pin number
        """
        if pin_number not in self.digital_output_pins:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('Illegal pin number for digital output.')
        await self._set_pin_mode(pin_number, PrivateConstants.AT_OUTPUT)

    async def set_pin_mode_i2c(self):
        """
        Establish the standard Arduino i2c pins for i2c utilization.

        NOTES: 1. THIS METHOD MUST BE CALLED BEFORE ANY I2C REQUEST IS MADE
               2. Callbacks are set within the individual i2c read methods of this
              API.

              See i2c_read, or i2c_read_restart_transmission.

        """

        self.i2c_active = True

        command = [PrivateConstants.I2C_BEGIN]
        await self._send_command(command)

    async def set_pin_mode_imu(self, callback=None,
                               enable=True):
        """

        :param callback: Required callback function.

        :param enable: True: start monitoring, False: stop monitoring

         Callback: [IMU REPORT Type, AX, AY, AZ, GX, GY, GZ, Time]
        """
        if enable:
            if not callback:
                if self.shutdown_on_exception:
                    await self.shutdown()
                raise RuntimeError('A callback must be specified for set_pin_mode_imu')

        command = [PrivateConstants.IMU_ENABLE, enable]

        self.imu_callback = callback
        self.imu_enabled = enable
        await self._send_command(command)

    async def set_pin_mode_microphone(self, callback=None, enable=True,
                                      mic_type=PrivateConstants.MICROPHONE_MONO,
                                      frequency=16000):
        """
        :param callback: Required callback function.

        :param enable: True: start monitoring, False: stop monitoring

        :param mic_type: either AT_MICROPHONE_MONO or AT_MICROPHONE_STEREO

        :param frequency: PCM Output frequency

        callback returns [qualifier, sound_value]
                         for mono qualifier = m
                         for stereo qualifier = l or r

        """
        if enable:
            if not callback:
                if self.shutdown_on_exception:
                    await self.shutdown()
                raise RuntimeError(
                    'A callback must be specified for set_pin_mode_microphone')
        self.microphone_callback = callback
        self.mic_type = mic_type
        freq_msb = frequency >> 8
        freq_lsb = frequency & 0xff
        if mic_type == PrivateConstants.AT_MICROPHONE_STEREO:
            self.mic_current_channel = 'l'
        command = [PrivateConstants.MICROPHONE_ENABLE, enable, mic_type, freq_msb,
                   freq_lsb]
        await self._send_command(command)

    async def set_pin_mode_neopixel(self, pin_number=28, num_pixels=8,
                                    fill_r=0, fill_g=0, fill_b=0):
        """
        Initialize the Arduino nano for NeoPixel control. Fill with rgb values specified.

        Default: Set all the pixels to off.

        :param pin_number: neopixel control pin. Must be in the range of 2-17

        :param num_pixels: number of pixels in the strip

        :param fill_r: initial red fill value 0-255

        :param fill_g: initial green fill value 0-255

        :param fill_b: initial blue fill value 0-255


        """
        # check for a valid neopixel pin number
        if not (2 < pin_number <= 17):
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('NeoPixel pin must be in the range of 2 - 17')

        pin = self.d_to_g_pin_map[pin_number]

        if self.neopixels_initiated:
            if self.shutdown_on_exception:
                await self.shutdown()

            raise RuntimeError('Neopixels previously initialized')

        if fill_r or fill_g or fill_g not in range(256):
            if self.shutdown_on_exception:
                await self.shutdown()

            raise RuntimeError('Pixel value must be in the range of 0-255')

        self.number_of_pixels = num_pixels

        command = [PrivateConstants.INITIALIZE_NEO_PIXELS, pin,
                   self.number_of_pixels, fill_r, fill_g, fill_b]

        await self._send_command(command)

        self.neopixels_initiated = True

    # noinspection PyRedundantParentheses
    async def set_pin_mode_servo(self, pin_number, min_pulse=544, max_pulse=2400):
        """

        Attach a pin to a servo motor

        :param pin_number: pin

        :param min_pulse: minimum pulse width

        :param max_pulse: maximum pulse width

        """
        if pin_number not in self.digital_output_pins:
            if self.shutdown_on_exception:
                await self.shutdown()

            raise RuntimeError('Illegal pin number for servo operation.')
        minv = (min_pulse).to_bytes(2, byteorder="big")
        maxv = (max_pulse).to_bytes(2, byteorder="big")

        command = [PrivateConstants.SERVO_ATTACH, pin_number,
                   minv[0], minv[1], maxv[0], maxv[1]]
        await self._send_command(command)

    async def set_pin_mode_sonar(self, trigger_pin, echo_pin,
                                 callback=None):
        """

        :param trigger_pin:

        :param echo_pin:

        :param callback: Required callback function.

        callback data: [PrivateConstants.SONAR_DISTANCE, trigger_pin, distance_value, time_stamp]

        """
        # TBD check for pin in valid range of pins
        if not callback:
            if self.shutdown_on_exception:
                await self.shutdown()

            raise RuntimeError('set_pin_mode_sonar: A Callback must be specified')

        if not 2 < trigger_pin <= 17:
            if self.shutdown_on_exception:
                await self.shutdown()

            raise RuntimeError('Trigger Pin must be between 2 and 17')

        if not 2 < echo_pin <= 17:
            if self.shutdown_on_exception:
                await self.shutdown()

            raise RuntimeError('Trigger Pin must be between 2 and 17')

        trigger = self.d_to_g_pin_map[trigger_pin]
        echo = self.d_to_g_pin_map[echo_pin]

        if self.sonar_count < PrivateConstants.MAX_SONARS - 1:
            self.sonar_callbacks[trigger_pin] = callback
            self.sonar_count += 1

            command = [PrivateConstants.SONAR_NEW, trigger, echo]
            await self._send_command(command)
        else:
            if self.shutdown_on_exception:
                await self.shutdown()

            raise RuntimeError(
                f'Maximum Number Of Sonars Exceeded - set_pin_mode_sonar fails for pin {trigger_pin}')

    async def set_pin_mode_spi(self, chip_select_list=None):
        """
        Specify the list of chip select pins.

        The pins to use are fixed at:
        miso - D11
        mosi - D12
        clock -D13

        Chip select pins may be any GPIO(except for A4 - A7) and D11, D12 and D13

        :param chip_select_list: This is a list of pins to be used for chip-select.
                                 The pins will be configured as output and set to high
                                 for SPI device selection.

                                 NOTE: You must specify the chips select pins here!


        command message: [command, number of cs pins, [cs pins...]]
        """

        if type(chip_select_list) != list:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('chip_select_list must be in the form of a list')
        if not chip_select_list:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('Chip select pins were not specified')

        self.spi_enabled = True

        command = [PrivateConstants.SPI_INIT, len(chip_select_list)]

        for pin in chip_select_list:
            command.append(pin)
            self.cs_pins_enabled.append(pin)
        await self._send_command(command)

    async def servo_write(self, pin_number, angle):
        """

        Set a servo attached to a pin to a given angle.

        :param pin_number: pin

        :param angle: angle (0-180)

        """
        command = [PrivateConstants.SERVO_WRITE, pin_number, angle]
        await self._send_command(command)

    async def servo_detach(self, pin_number):
        """
        Detach a servo for reuse

        :param pin_number: attached pin

        """
        command = [PrivateConstants.SERVO_DETACH, pin_number]
        await self._send_command(command)

    async def spi_cs_control(self, chip_select_pin, select):
        """
        Control an SPI chip select line
        :param chip_select_pin: pin connected to CS

        :param select: 0=select, 1=deselect
        """
        if not self.spi_enabled:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError(f'spi_cs_control: SPI interface is not enabled.')

        if chip_select_pin not in self.cs_pins_enabled:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError(f'spi_cs_control: chip select pin never enabled.')
        command = [PrivateConstants.SPI_CS_CONTROL, chip_select_pin, select]
        await self._send_command(command)

    async def spi_read_blocking(self, register_selection, number_of_bytes_to_read,
                                call_back=None):
        """
        Read the specified number of bytes from the specified SPI port and
        call the callback function with the reported data.

        :param register_selection: Register to be selected for read.

        :param number_of_bytes_to_read: Number of bytes to read

        :param call_back: Required callback function to report spi data as a
                   result of read command


        callback returns a data list:
        [SPI_READ_REPORT, count of data bytes read, data bytes, time-stamp]

        SPI_READ_REPORT = 13

        """

        if not self.spi_enabled:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError(f'spi_read_blocking: SPI interface is not enabled.')

        if not call_back:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('spi_read_blocking: A Callback must be specified')

        self.spi_callback = call_back

        command = [PrivateConstants.SPI_READ_BLOCKING, number_of_bytes_to_read,
                   register_selection]

        await self._send_command(command)

    async def spi_set_format(self, clock_divisor, bit_order, data_mode):
        """
        Configure how the SPI serializes and de-serializes data on the wire.

        See Arduino SPI reference materials for details.

        :param clock_divisor:

        :param bit_order:

                            LSBFIRST = 0

                            MSBFIRST = 1 (default)

        :param data_mode:

                            SPI_MODE0 = 0x00 (default)

                            SPI_MODE1  = 0x04

                            SPI_MODE2 = 0x08

                            SPI_MODE3 = 0x0C

        """

        if not self.spi_enabled:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError(f'spi_set_format: SPI interface is not enabled.')

        command = [PrivateConstants.SPI_SET_FORMAT, clock_divisor, bit_order,
                   data_mode]
        await self._send_command(command)

    async def spi_write_blocking(self, bytes_to_write):
        """
        Write a list of bytes to the SPI device.

        :param bytes_to_write: A list of bytes to write. This must
                                be in the form of a list.

        """

        if not self.spi_enabled:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError(f'spi_write_blocking: SPI interface is not enabled.')

        if type(bytes_to_write) is not list:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('spi_write_blocking: bytes_to_write must be a list.')

        command = [PrivateConstants.SPI_WRITE_BLOCKING, len(bytes_to_write)]

        for data in bytes_to_write:
            command.append(data)

        await self._send_command(command)

    async def _set_pin_mode(self, pin_number, pin_state, differential=0, callback=None):

        """
        A private method to set the various pin modes.

        :param pin_number: arduino pin number

        :param pin_state: INPUT/OUTPUT/ANALOG/PWM/PULLUP
                         For SERVO use: set_pin_mode_servo
                         For DHT   use: set_pin_mode_dht

        :param differential: for analog inputs - threshold
                             value to be achieved for report to
                             be generated

        :param callback: A reference to a required call back function to be
                         called when pin data value changes.

        """

        if callback:
            if pin_state == PrivateConstants.AT_INPUT:
                self.digital_callbacks[pin_number] = callback
            elif pin_state == PrivateConstants.AT_INPUT_PULLUP:
                self.digital_callbacks[pin_number] = callback
            elif pin_state == PrivateConstants.AT_ANALOG:
                self.analog_callbacks[pin_number] = callback
            else:
                print('{} {}'.format('set_pin_mode: callback ignored for '
                                     'pin state:', pin_state))

        if pin_state == PrivateConstants.AT_INPUT:
            command = [PrivateConstants.SET_PIN_MODE, pin_number,
                       PrivateConstants.AT_INPUT, 1]

        elif pin_state == PrivateConstants.AT_INPUT_PULLUP:
            command = [PrivateConstants.SET_PIN_MODE, pin_number,
                       PrivateConstants.AT_INPUT_PULLUP, 1]

        elif pin_state == PrivateConstants.AT_OUTPUT:
            command = [PrivateConstants.SET_PIN_MODE, pin_number,
                       PrivateConstants.AT_OUTPUT]

        elif pin_state == PrivateConstants.AT_ANALOG:
            command = [PrivateConstants.SET_PIN_MODE, pin_number,
                       PrivateConstants.AT_ANALOG,
                       differential >> 8, differential & 0xff, 1]
        else:
            if self.shutdown_on_exception:
                await self.shutdown()

            raise RuntimeError('Unknown pin state')

        if command:
            await self._send_command(command)

    async def shutdown(self):
        """
        This method attempts an orderly shutdown
        If any exceptions are thrown, they are ignored.
        """
        self.shutdown_flag = True

        if self.imu_enabled:
            await self.set_pin_mode_imu(enable=False)
            await asyncio.sleep(.1)
            # let data drain
        if self.mic_enabled:
            await self.set_pin_mode_microphone(enable=False)
            await asyncio.sleep(.21)

        try:

            command = [PrivateConstants.STOP_ALL_REPORTS]
            await self._send_command(command)
            await asyncio.sleep(.1)

            command = [PrivateConstants.RESET, self.reset_board_on_shutdown]
            await self._send_command(command)

            await asyncio.sleep(.3)
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                # self.sock.close_down()
                self.sock.close()
            except Exception:
                pass

            self.the_task.cancel()
            await asyncio.sleep(.5)
            if self.close_loop_on_shutdown:
                self.loop.stop()

        except Exception:  # ignore the exception
            pass

    '''
    report message handlers
    '''

    async def _analog_message(self, data):
        """
        This is a private message handler method.
        It is a message handler for analog messages.

        :param data: message data

        """
        pin = data[0]
        value = (data[1] << 8) + data[2]
        # set the current value in the pin structure
        time_stamp = time.time()
        # self.digital_pins[pin].event_time = time_stamp
        if self.analog_callbacks[pin]:
            message = [PrivateConstants.ANALOG_REPORT, pin, value, time_stamp]
            await self.analog_callbacks[pin](message)

    async def _digital_message(self, data):
        """
        This is a private message handler method.
        It is a message handler for Digital Messages.

        :param data: digital message


        """
        pin = data[0]
        value = data[1]

        time_stamp = time.time()
        if self.digital_callbacks[pin]:
            message = [PrivateConstants.DIGITAL_REPORT, pin, value, time_stamp]
            await self.digital_callbacks[pin](message)

    async def _firmware_message(self, data):
        """
        Server firmware version message. This is a private method.

        :param data: data[0] = major number, data[1] = minor number.

                               data[2] = patch number
        """

        self.firmware_version = [data[0], data[1], data[2]]

    async def _i2c_read_report(self, data):
        """
        Execute callback for i2c reads. This is a private method.

        :param data: [I2C_READ_REPORT, number of bytes read, address, register,
        bytes read..., time-stamp]
        """

        # we receive [# data bytes, address, register, data bytes]
        # number of bytes of data returned

        # data[0] = number of bytes
        # data[1] = number of bytes returned
        # data[2] = address
        # data[3] = register
        # data[4] ... all the data bytes

        cb_list = [PrivateConstants.I2C_READ_REPORT, data[0], data[1]] + data[2:]
        cb_list.append(time.time())

        await self.i2c_callback(cb_list)

    async def _i2c_too_few(self, data):
        """
        I2c reports too few bytes received. This is a private method.

        :param data: data[0] = device address
        """
        if self.shutdown_on_exception:
            await self.shutdown()

        raise RuntimeError(
            f'i2c too few bytes received from i2c port {data[0]} i2c address {data[1]}')

    async def _i2c_too_many(self, data):
        """
        I2c reports too few bytes received. This is a private method.

        :param data: data[0] = device address
        """
        if self.shutdown_on_exception:
            await self.shutdown()

        raise RuntimeError(
            f'i2c too many bytes received from i2c port {data[0]} i2c address {data[1]}')

    async def _i_am_here(self, data):
        """
        Reply to are_u_there message. This is a private method.
        :param data: arduino id
        """
        self.reported_arduino_id = data[0]

    async def _report_debug_data(self, data):
        """
        Print debug data sent from Arduino. This is a private method.
        :param data: data[0] is a byte followed by 2
                     bytes that comprise an integer
        :return:
        """
        value = (data[1] << 8) + data[2]
        print(f'DEBUG ID: {data[0]} Value: {value}')

    async def _report_loop_data(self, data):
        """
        Print data that was looped back. This is a private method.
        :param data: byte of loop back data
        :return:
        """
        if self.loop_back_callback:
            await self.loop_back_callback(data)

    async def _send_command(self, command):
        """
        This is a private utility method.


        :param command:  command data in the form of a list

        :returns: number of bytes sent
        """
        # the length of the list is added at the head
        command.insert(0, len(command))
        send_message = bytes(command)

        await self.sock.write(send_message)

    async def _servo_unavailable(self, report):
        """
        Message if no servos are available for use. This is a private method.
        :param report: pin number
        """
        if self.shutdown_on_exception:
            await self.shutdown()

        raise RuntimeError(
            f'Servo Attach For Pin {report[0]} Failed: No Available Servos')

    async def _sonar_distance_report(self, report):
        """
        This is a private method.

        :param report: data[0] = trigger pin, data[1] and data[2] = distance

        callback report format: [PrivateConstants.SONAR_DISTANCE, trigger_pin,
                                 distance_integer_portion,
                                 distance_fractional_portion, time_stamp]
        """

        # get callback from pin number
        pin = self.g_to_d_pin_map[report[0]]
        cb = self.sonar_callbacks[pin]

        # build report data
        cb_list = [PrivateConstants.SONAR_DISTANCE, pin,
                   float(report[1] + report[2] / 100), time.time()]

        await cb(cb_list)

    async def _imu_report(self, report):
        """
        This is private method.

        :param report: ax, ay, az, gx, gy, gz expressed as integer and fractional
                       values, followed by a positivity flag

        """
        # get callback from pin number
        cb = self.imu_callback

        # imu error reported
        if report[2] == 99:
            if self.shutdown_on_exception:
                await self.shutdown()
            raise RuntimeError('IMU ERROR')

        ax = float(report[10] + report[1] / 100)
        if report[2]:
            ax = ax * -1.0

        ay = float(report[3] + report[4] / 100)
        if report[5]:
            ay = ay * -1.0

        az = float(report[6] + report[7] / 100)
        if report[8]:
            az = az * -1.0

        gx = float(report[9] + report[10] / 100)
        if report[11]:
            gx = gx * -1.0

        gy = float(report[12] + report[13] / 100)
        if report[14]:
            gy = gy * -1.0

        gz = float(report[15] + report[16] / 100)
        if report[17]:
            gz = gz * -1.0

        time_stamp = time.time()
        # build report data
        cb_list = [PrivateConstants.IMU_REPORT, ax, ay, az,
                   gx, gy, gz, time_stamp]

        await cb(cb_list)

    async def _microphone_report(self, report):
        """
        This is a private method.

        :param report: [audio_level_msb, audio_level_lsb]
        """
        cb = self.microphone_callback
        if cb:
            # convert incoming unsigned integer data to a signed value
            value = report[0], report[1]
            value = bytes(value)
            value = struct.unpack(">h", value)
            time_stamp = time.time()
            cb_list = [PrivateConstants.MICROPHONE_REPORT, value[0],
                       self.mic_current_channel, time_stamp]
            if self.mic_type == PrivateConstants.AT_MICROPHONE_STEREO:
                if self.mic_current_channel == 'l':
                    self.mic_current_channel = 'r'
                else:
                    self.mic_current_channel = 'l'

            await cb(cb_list)

    async def _dht_report(self, report):
        """
        This is the dht report handler method.

        :param report:
               data[0] = report error return
                        No Errors = 0

                        Checksum Error = 1

                        Timeout Error = 2

                        Invalid Value = 999

               data[1] = pin number

               data[2] = humidity positivity flag

               data[3] = temperature positivity value

               data[4] = humidity integer

               data[5] = humidity fractional value

               data[6] = temperature integer

               data[7] = temperature fractional value


        """
        if report[0]:  # DHT_ERROR
            # error report
            # data[0] = report sub type, data[1] = pin, data[2] = error message
            if self.dht_callbacks[report[1]]:
                # Callback 0=DHT REPORT, DHT_ERROR, PIN, Time
                message = [PrivateConstants.DHT_REPORT, report[0], report[1], report[2],
                           time.time()]
                self.dht_callbacks[report[1]](message)
        else:
            # got valid data DHT_DATA
            f_humidity = float(report[4] + report[5] / 100)
            if report[2]:
                f_humidity *= -1.0
            f_temperature = float(report[6] + report[7] / 100)
            if report[3]:
                f_temperature *= -1.0
            message = [PrivateConstants.DHT_REPORT, report[0], report[1], report[2],
                       f_humidity, f_temperature, time.time()]

            await self.dht_callbacks[report[1]](message)

    async def _spi_report(self, report):
        """
        This is a private method.
        :param report: report data
        """

        cb_list = [PrivateConstants.SPI_REPORT, report[0]] + report[1:]

        cb_list.append(time.time())

        await self.spi_callback(cb_list)

    async def _arduino_report_dispatcher(self):
        """
        This is a private method.
        It continually accepts and interprets data coming from Telemetrix4Arduino,and then
        dispatches the correct handler to process the data.

        It first receives the length of the packet, and then reads in the rest of the
        packet. A packet consists of a length, report identifier and then the report data.
        Using the report identifier, the report handler is fetched from report_dispatch.

        :returns: This method never returns
        """

        while True:
            if self.shutdown_flag:
                break
            try:
                packet_length = ord(await self.sock.read())
            except TypeError:
                continue

            # get the rest of the packet

            packet = list(await self.sock.read(packet_length))

            report = packet[0]
            # handle all other messages by looking them up in the
            # command dictionary

            await self.report_dispatch[report](packet[1:])
            await asyncio.sleep(self.sleep_tune)
