#!/usr/bin/env python3

import collections
import contextlib
import struct
import time
import warnings
from datetime import datetime, timedelta

from bluepy3 import btle  # noqa

from .radioctl import ble_reset

UUID_UNITS = "EBE0CCBE-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _       0x00 - F, 0x01 - C    READ WRITE
UUID_HISTORY = "EBE0CCBC-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _     Last idx 152          READ NOTIFY
UUID_HISTORY_3 = "EBE0CCBC-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _   Last idx 152          READ NOTIFY
UUID_TIME = "EBE0CCB7-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _        5 or 4 bytes          READ WRITE
UUID_DATA = "EBE0CCC1-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _        3 bytes               READ NOTIFY
UUID_BATTERY = "EBE0CCC4-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _     1 byte                READ
UUID_NUM_RECORDS = "EBE0CCB9-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _ 8 bytes               READ
UUID_RECORD_IDX = "EBE0CCBA-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _  4 bytes               READ WRITE

warnings.filterwarnings(action="always", category=RuntimeWarning)


class PyLyException(Exception):
    """Base class for all pylywsdxx exceptions."""

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        msg = f"(pylywsdxx) {self.message}"
        return msg


class PyLyTimeout(PyLyException):
    """Class for timeout errors from upstream."""

    def __init__(self, message: str):
        PyLyException.__init__(self, message)


class PyLyConnectError(PyLyException):
    """Class for connection errors from upstream."""

    def __init__(self, message: str):
        PyLyException.__init__(self, message)


class PyLyValueError(PyLyException):
    """Class for value errors."""

    def __init__(self, message: str):
        PyLyException.__init__(self, message)


class SensorData(
    collections.namedtuple("SensorDataBase", ["temperature", "humidity", "battery", "voltage"])
):
    """Class to store sensor data.
    For LYWSD02 devices temperature and humidity readings are available.
    For LYWSD03MMC devices also battery information is available.
    """

    __slots__ = ()


class Lywsd02:  # pylint: disable=R0902
    """Class to communicate with LYWSD02 devices."""

    UNITS = {
        b"\x01": "F",
        b"\xff": "C",
    }
    UNITS_CODES = {
        "C": b"\xff",
        "F": b"\x01",
    }

    _MAX_TRIES = 6
    _MAX_RESETS = 3

    def __init__(
        self,
        mac: str,
        notification_timeout: float = 11.0,
        reusable: bool = False,
        debug: bool = False,
    ):
        """
        Initialise a LYWSD02 device

        Args:
            mac: MAC-adress of the device.
            notification_timeout: number of seconds to wait for a connection to be made.
            reusable: whether an object is reusable or not. Device-objects that are reusable
                      allow for more flexible error-handling when failures occur in the
                      communication with a device.
            debug: whether to provide debugging info output.
        """
        self.debug = debug
        self.reusable = reusable
        btle.Debugging = self.debug
        self._mac = mac
        self._peripheral = btle.Peripheral()
        self._notification_timeout = notification_timeout
        self._handles = {}
        self._tz_offset = None
        self._data = SensorData(None, None, None, None)
        self._history_data = collections.OrderedDict()
        self._context_depth = 0

        # define the number of times a device must cause an error before countermeasures are taken
        self._set_tries()
        # define the number of times a device may cause a countermeasure before we give up
        # and raise an error
        self._set_resets()

    def _set_tries(self):
        """Initialise a retry counter"""
        self._tries = self._MAX_TRIES if self.reusable else 1

    def _set_resets(self):
        """Initialise a reset counter"""
        self._resets = self._MAX_RESETS

    def _tr_msg(self):
        return (
            f"T{self._MAX_TRIES - self._tries}/{self._MAX_TRIES}:"
            f"R{self._MAX_RESETS - self._resets}/{self._MAX_RESETS}"
        )

    def _get_history_data(self):
        with self.connect():
            self._subscribe(UUID_HISTORY, self._process_history_data)

            while True:
                if not self._peripheral.waitForNotifications(self._notification_timeout):
                    if self.debug:
                        print(f"|-- Timeout waiting for {self._mac}")
                    break

    def _get_sensor_data(self):
        with self.connect():
            self._subscribe(UUID_DATA, self._process_sensor_data)

            if not self._peripheral.waitForNotifications(self._notification_timeout):
                if self.debug:
                    print(f"|-- Timeout waiting for {self._mac}")
                raise PyLyTimeout(
                    f"No data from device {self._mac} for {self._notification_timeout} seconds"
                )

    def _process_history_data(self, data):
        (idx, ts, max_temp, max_hum, min_temp, min_hum) = struct.unpack_from("<IIhBhB", data)

        ts = datetime.fromtimestamp(ts)
        min_temp /= 100
        max_temp /= 100

        self._history_data[idx] = [ts, min_temp, min_hum, max_temp, max_hum]

    def _process_sensor_data(self, data):
        temperature, humidity = struct.unpack_from("hB", data)
        temperature /= 100
        self._data = SensorData(
            temperature=temperature, humidity=humidity, battery=None, voltage=None
        )

    def _subscribe(self, uuid, callback):
        self._peripheral.setDelegate(self)
        ch = self._peripheral.getCharacteristics(uuid=uuid)[0]
        self._handles[ch.getHandle()] = callback
        desc = ch.getDescriptors(forUUID=0x2902)[0]

        desc.write(0x01.to_bytes(2, byteorder="little"), withResponse=True)

    # FIXME: why can't the name of this method be changed (?!)
    def handleNotification(self, handle, data):  # noqa
        func = self._handles.get(handle)
        if func:
            func(data)

    @contextlib.contextmanager
    def connect(self):  # pylint: disable=R0912
        """Handle device connecting and disconnecting"""
        if self._context_depth == 0:
            if self.debug:
                print(f"|-> Connecting to {self._mac}")
            try:
                self._peripheral.connect(addr=self._mac, timeout=self._notification_timeout)
            except (btle.BTLEConnectTimeout, btle.BTLEConnectError) as her:
                message = ""
                reraise = PyLyException(f"-- {her} --")
                if isinstance(her, btle.BTLEConnectError):
                    message = f"Device ({self._mac}) connection failed."
                    reraise = PyLyConnectError(f"-- {her} --")
                if isinstance(her, btle.BTLEConnectTimeout):
                    message = f"Device ({self._mac}) timed out on connect."
                    reraise = PyLyTimeout(f"-- {her} --")
                self._tries -= 1
                # fmt: off
                warnings.warn(f"{message} ({self._tr_msg()})", RuntimeWarning, stacklevel=2)
                # fmt: on
                if self._tries <= 0:
                    self._resets -= 1
                    ble_reset(debug=self.debug)
                    self._set_tries()
                    if self._resets <= 0:
                        # re-raise because apparently resetting the radio doesn't work
                        raise reraise from her
            except Exception as her:
                # Non-anticipated exceptions must be raised to draw attention to them
                # We'll reset the radio because it has had results in the past
                ble_reset(debug=self.debug)
                raise PyLyException(f"-- {her} --") from her

        self._context_depth += 1
        try:
            yield self
        except btle.BTLEInternalError as her:
            message = ""
            reraise = PyLyException(f"-- {her} --")
            if isinstance(her, btle.BTLEInternalError):
                message = f"BTLE internal error while talking with device ({self._mac})."
                reraise = PyLyException(f"-- {her} --")
            self._tries -= 1
            # fmt: off
            warnings.warn(f"{message} ({self._tr_msg()})", RuntimeWarning, stacklevel=2)
            # fmt: on
            if self._tries <= 0:
                self._resets -= 1
                ble_reset(debug=self.debug)
                self._set_tries()
                if self._resets <= 0:
                    # re-raise because apparently resetting the radio doesn't work
                    raise reraise from her
        except Exception as her:
            # Non-anticipated exceptions must be raised to draw attention to them
            # We'll reset the radio because it has had results in the past
            ble_reset(debug=self.debug)
            raise PyLyException(f"-- {her} --") from her
        finally:
            self._context_depth -= 1
            if self._context_depth == 0:
                if self.debug:
                    print(f"|-< Disconnecting from {self._mac}")
                self._peripheral.disconnect()

    @property
    def battery(self):
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_BATTERY)[0]
            value = ch.read()
        return ord(value)

    @property
    def data(self):
        self._get_sensor_data()
        return self._data

    @property
    def history_data(self):
        self._get_history_data()
        return self._history_data

    @property
    def humidity(self):
        return self.data.humidity

    @property
    def num_stored_entries(self):
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_NUM_RECORDS)[0]
            value = ch.read()
        total_records, current_records = struct.unpack_from("II", value)
        return total_records, current_records

    @property
    def temperature(self):
        return self.data.temperature

    @property
    def history_index(self):
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_RECORD_IDX)[0]
            value = ch.read()
        _idx = 0 if len(value) == 0 else struct.unpack_from("I", value)
        return _idx

    @history_index.setter
    def history_index(self, value):
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_RECORD_IDX)[0]
            ch.write(struct.pack("I", value), withResponse=True)

    @property
    def time(self):
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_TIME)[0]
            value = ch.read()
        if len(value) == 5:
            ts, tz_offset = struct.unpack("Ib", value)
        else:
            ts = struct.unpack("I", value)[0]
            tz_offset = 0
        return datetime.fromtimestamp(ts), tz_offset

    @time.setter
    def time(self, dt: datetime):
        data = struct.pack("Ib", int(dt.timestamp()), self.tz_offset)
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_TIME)[0]
            ch.write(data, withResponse=True)

    @property
    def tz_offset(self):
        if self._tz_offset is not None:
            return self._tz_offset
        if time.daylight:
            return -time.altzone // 3600
        return -time.timezone // 3600

    @tz_offset.setter
    def tz_offset(self, tz_offset: int):
        self._tz_offset = tz_offset

    @property
    def units(self):
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_UNITS)[0]
            value = ch.read()
        return self.UNITS[value]

    @units.setter
    def units(self, value: str):
        if value.upper() not in self.UNITS_CODES:
            raise PyLyValueError(f"Units value must be one of {self.UNITS_CODES.keys()}")

        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_UNITS)[0]
            ch.write(self.UNITS_CODES[value.upper()], withResponse=True)


class Lywsd03(Lywsd02):
    """Class to communicate with LYWSD03MMC devices."""

    # Temperature units specific to LYWSD03MMC devices
    UNITS = {b"\x01": "F", b"\x00": "C"}
    UNITS_CODES = {"F": b"\x01", "C": b"\x00"}

    # CR2025 / CR2032 maximum theoretical voltage = 3.4 V
    # ref. Table 1;
    #  CR2025: https://www.farnell.com/datasheets/1496883.pdf
    #  CR2032: https://www.farnell.com/datasheets/1496885.pdf
    # Lowest voltage for these batteries is 2.0 V but the BT radio
    # on most devices will stop working when below 2.3 V (YMMV).
    BATTERY_FULL = 3.4
    BATTERY_LOW = 2.1

    # Locally cache the start time of the device.
    # This value won't change, and caching improves the performance getting the history data
    _start_time = False

    # Getting history data is very slow, so don't output progress updates
    enable_history_progress = False

    # Call the parent init with a bigger notification timeout
    def __init__(self, mac, notification_timeout=12.3, reusable=False, debug=False):
        super().__init__(
            mac=mac, notification_timeout=notification_timeout, reusable=reusable, debug=debug
        )
        self._latest_record = None

    def _get_history_data(self):
        # Work out the expected last record we'll be sent from the device.
        # The current hour doesn't appear until the end of the hour, and the time is recorded as
        # the end of hour time
        expected_end = datetime.now() - timedelta(hours=1)

        self._latest_record = None
        with self.connect():
            self._subscribe(UUID_HISTORY_3, self._process_history_data)

            while True:
                if not self._peripheral.waitForNotifications(self._notification_timeout):
                    if self.debug:
                        print(f"|-- Timeout listening to {self._mac}")
                    break

                # Find the last date we have data for, and check if it's for the current hour
                # noinspection PyTypeChecker
                if self._latest_record and self._latest_record >= expected_end:
                    break

    def _process_history_data(self, data):
        (idx, ts, max_temp, max_hum, min_temp, min_hum) = struct.unpack_from("<IIhBhB", data)

        # Work out the time of this record by adding the record time to time the
        # device was started
        ts = self.start_time + timedelta(seconds=ts)
        min_temp /= 10
        max_temp /= 10

        self._latest_record = ts
        self._history_data[idx] = [ts, min_temp, min_hum, max_temp, max_hum]
        self.output_history_progress(ts, min_temp, max_temp)

    def _process_sensor_data(self, data):
        """Process the sensor data.

        Args:
            data (struct): struct containing sensor data
        """
        temperature, humidity, voltage = struct.unpack_from("<hBh", data)
        temperature /= 100
        voltage /= 1000
        # battery (float): Estimate percentage of the battery charge remaining
        battery = round(
            ((voltage - self.BATTERY_LOW) / (self.BATTERY_FULL - self.BATTERY_LOW) * 100), 1
        )
        self._data = SensorData(
            temperature=temperature, humidity=humidity, battery=battery, voltage=voltage
        )

    def output_history_progress(self, ts, min_temp, max_temp):
        if not self.enable_history_progress:
            return
        print(f"|-- {ts}: {min_temp} to {max_temp}")

    @property
    def battery(self):
        """Battery data comes along with the temperature and humidity data, so
           just get it from there.

        Returns:
             guestimate of battery percentage
        """
        return self.data.battery

    @property
    def start_time(self):
        """Work out the start time of the device.
        This is done by taking the current time, subtracting the time
        taken from the device (the run time), and adding the timezone offset.

        Returns:
            datetime: the start time of the device
        """
        if not self._start_time:
            start_time_delta = (
                self.time[0] - datetime(1970, 1, 1) - timedelta(hours=self.tz_offset)
            )
            self._start_time = datetime.now() - start_time_delta
        return self._start_time

    @property
    def time(self):
        """Fetch datetime and timezone of a LYWSD03MMC device

        Returns:
           Device's current datetime and timezone
        """
        return super().time

    @time.setter
    def time(self, dt: datetime):  # pylint: disable=W0613
        """Disable setting the time and timezone.
        LYWSD03MMCs don't have visible clocks.

        Args:
            dt (datetime): Does nothing

        Returns:
            Nothing
        """
        return

    @property
    def tz_offset(self):
        return super().tz_offset

    @tz_offset.setter
    def tz_offset(self, tz_offset: int):  # pylint: disable=W0613
        """Disable setting the time and timezone.
        LYWSD03MMCs don't have visible clocks.

        Returns:
            Nothing
        """
        return
