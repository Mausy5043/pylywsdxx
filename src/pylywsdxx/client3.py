#!/usr/bin/env python3

import collections
import struct
from datetime import datetime, timedelta

from .client2 import Lywsd02client

UUID_HISTORY = "EBE0CCBC-7A0A-4B0C-8A1A-6FF2997DA3A6"  # Last idx 152          READ NOTIFY


class Sensor3Data(collections.namedtuple("Sensor3DataBase", ["temperature", "humidity", "battery", "voltage"])):
    """Class to store sensor data.
    For LYWSD03MMC devices also battery information is available.
    """

    __slots__ = ()


class Lywsd03client(Lywsd02client):
    """Class to communicate with LYWSD03MMC devices.
    """

    # Temperature units specific to LYWSD03MMC devices
    UNITS = {b"\x01": "F", b"\x00": "C"}
    UNITS_CODES = {"F": b"\x01", "C": b"\x00"}

    # Locally cache the start time of the device.
    # This value won't change, and caching improves the performance getting the history data
    _start_time = False

    # Getting history data is very slow, so don't output progress updates
    enable_history_progress = False

    # Call the parent init with a bigger notification timeout
    def __init__(self, mac, notification_timeout=15.0):
        super().__init__(mac, notification_timeout)
        self._latest_record = None

    def _process_sensor_data(self, data):
        """
        Process the sensor data.

        Params:
            data (struct): struct containing sensor data

        Returns:
            None
        """
        temperature, humidity, voltage = struct.unpack_from("<hBh", data)
        temperature /= 100
        voltage /= 1000

        # Estimate the battery percentage remaining
        # CR2024 maximum theoretical voltage = 3.400V
        battery = round(((voltage - 2.1) / (3.4 - 2.1) * 100), 1)
        self._data = Sensor3Data(temperature=temperature, humidity=humidity, battery=battery, voltage=voltage)

    # Battery data comes along with the temperature and humidity data, so just get it from there
    @property
    def battery(self):
        """
        Battery data comes along with the temperature and humidity data, so just get it from there
        :return: guestimate of battery percentage
        """
        return self.data.battery

    def _get_history_data(self):
        # FIXME: Get the time the device was first run
        # self.start_time

        # Work out the expected last record we'll be sent from the device.
        # The current hour doesn't appear until the end of the hour, and the time is recorded as
        # the end of hour time
        expected_end = datetime.now() - timedelta(hours=1)

        self._latest_record = None
        with self.connect():
            self._subscribe(UUID_HISTORY, self._process_history_data)

            while True:
                if not self._peripheral.waitForNotifications(self._notification_timeout):
                    break

                # Find the last date we have data for, and check if it's for the current hour
                if self._latest_record and self._latest_record >= expected_end:
                    break

    def _process_history_data(self, data):
        (idx, ts, max_temp, max_hum, min_temp, min_hum) = struct.unpack_from("<IIhBhB", data)

        # Work out the time of this record by adding the record time to time the device was started
        ts = self.start_time + timedelta(seconds=ts)
        min_temp /= 10
        max_temp /= 10

        self._latest_record = ts
        self._history_data[idx] = [ts, min_temp, min_hum, max_temp, max_hum]
        self.output_history_progress(ts, min_temp, max_temp)


    def output_history_progress(self, ts, min_temp, max_temp):
        if not self.enable_history_progress:
            return
        print(f"{ts}: {min_temp} to {max_temp}")


    # Work out the start time of the device by taking the current time, subtracting the time
    # taken from the device (the run time), and adding the timezone offset.
    @property
    def start_time(self):
        """
        Work out the start time of the device by taking the current time, subtracting the time
        taken from the device (the run time), and adding the timezone offset.
        :return: the start time of the device
        """
        if not self._start_time:
            start_time_delta = self.time[0] - datetime(1970, 1, 1) - timedelta(hours=self.tz_offset)
            self._start_time = datetime.now() - start_time_delta
        return self._start_time

    # Disable setting the time and timezone.
    # LYWSD03MMCs don't have visible clocks
    @property
    def time(self):
        """
        Disable setting the time and timezone.
        LYWSD03MMCs don't have visible clocks
        :return:
        """
        return super().time

    @time.setter
    def time(self, dt: datetime):
        return

    @property
    def tz_offset(self):
        return super().tz_offset

    @tz_offset.setter
    def tz_offset(self, tz_offset: int):
        return
