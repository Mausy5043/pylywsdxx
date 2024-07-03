#!/usr/bin/env python3

import collections
import contextlib
import logging
import struct
import sys
import time
from typing import Generator, Literal, Union

# import warnings
from datetime import datetime, timedelta

from bluepy3 import btle

UUID_UNITS = "EBE0CCBE-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _       0x00 - F, 0x01 - C    READ WRITE
UUID_HISTORY = "EBE0CCBC-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _     Last idx 152          READ NOTIFY
UUID_HISTORY_3 = "EBE0CCBC-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _   Last idx 152          READ NOTIFY
UUID_TIME = "EBE0CCB7-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _        5 or 4 bytes          READ WRITE
UUID_DATA = "EBE0CCC1-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _        3 bytes               READ NOTIFY
UUID_BATTERY = "EBE0CCC4-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _     1 byte                READ
UUID_NUM_RECORDS = "EBE0CCB9-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _ 8 bytes               READ
UUID_RECORD_IDX = "EBE0CCBA-7A0A-4B0C-8A1A-6FF2997DA3A6"  # _  4 bytes               READ WRITE

# warnings.filterwarnings(action="always", category=RuntimeWarning)

LOGGER: logging.Logger = logging.getLogger(__name__)


class PyLyException(Exception):
    """Base class for all pylywsdxx exceptions."""

    def __init__(self, message: str):
        self.message: str = message

    def __str__(self) -> str:
        msg: str = f"(pylywsdxx) {self.message}"
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
        self.debug: bool = debug
        if debug:
            if len(LOGGER.handlers) == 0:
                LOGGER.addHandler(logging.StreamHandler(sys.stdout))
            LOGGER.level = logging.DEBUG
        self.reusable: bool = reusable
        btle.Debugging = self.debug
        self._mac: str = mac
        self._peripheral = btle.Peripheral()
        self._notification_timeout: float = notification_timeout
        self._handles: dict = {}
        # self._tz_offset: int = self.tz_offset  # does not work
        self._tz_offset = None
        self._data = SensorData(None, None, None, None)
        self._history_data = collections.OrderedDict()  # type: ignore
        self._context_depth: int = 0

    def _get_history_data(self) -> None:
        with self.connect():
            self._subscribe(UUID_HISTORY, self._process_history_data)

            while True:
                if not self._peripheral.waitForNotifications(self._notification_timeout):
                    LOGGER.debug(f"|-- Timeout waiting for {self._mac}")
                    break

    def _get_sensor_data(self) -> None:
        with self.connect():
            self._subscribe(UUID_DATA, self._process_sensor_data)
            if not self._peripheral.waitForNotifications(self._notification_timeout):
                LOGGER.debug(f"|-- Timeout waiting for {self._mac}")
                raise PyLyTimeout(
                    f"No data from device {self._mac} for {self._notification_timeout} seconds"
                )

    def _process_history_data(self, data) -> None:
        (idx, ts, max_temp, max_hum, min_temp, min_hum) = struct.unpack_from("<IIhBhB", data)

        ts = datetime.fromtimestamp(ts)
        min_temp /= 100
        max_temp /= 100

        self._history_data[idx] = [ts, min_temp, min_hum, max_temp, max_hum]

    def _process_sensor_data(self, data) -> None:
        temperature, humidity = struct.unpack_from("hB", data)
        temperature /= 100.0
        self._data = SensorData(
            temperature=temperature, humidity=humidity, battery=None, voltage=None
        )

    def _subscribe(self, uuid, callback) -> None:
        self._peripheral.setDelegate(self)
        ch = self._peripheral.getCharacteristics(uuid=uuid)[0]
        self._handles[ch.getHandle()] = callback
        desc = ch.getDescriptors(forUUID=0x2902)[0]

        desc.write(0x01.to_bytes(2, byteorder="little"), withResponse=True)

    # why can't the name of this method be changed?
    def handleNotification(self, handle, data) -> None:
        func = self._handles.get(handle)
        if func:
            func(data)

    @contextlib.contextmanager
    def connect(self) -> Generator:  # pylint: disable=R0912
        """Handle device connecting and disconnecting"""
        if self._context_depth == 0:
            LOGGER.debug(f"|-> Connecting to {self._mac}")
            try:
                self._peripheral.connect(addr=self._mac, timeout=self._notification_timeout)
            except (btle.BTLEConnectTimeout, btle.BTLEConnectError) as her:
                message: str = ""
                reraise = PyLyException(f"-- {her} --")
                # set appropriate error message
                if isinstance(her, btle.BTLEConnectError):
                    message = f"Device ({self._mac}) connection failed."
                    reraise = PyLyConnectError(f"-- {her} --")
                if isinstance(her, btle.BTLEConnectTimeout):
                    message = f"Device ({self._mac}) timed out on connect."
                    reraise = PyLyTimeout(f"-- {her} --")
                LOGGER.warning(f"{message}")
                # Try to disconnect to avoid stale connections causing BTLEConnectError later.
                LOGGER.debug(f"|-< Disconnecting from {self._mac}  (forced_1)")
                try:
                    self._peripheral.disconnect()
                except Exception as her2:  # pylint: disable=broad-exception-caught
                    LOGGER.error(f"While disconnecting : {her2}")
                raise reraise from her
            except Exception as her:
                # Non-anticipated exceptions must be raised to draw attention to them
                message = f"Unexpected exception occured for device ({self._mac})."
                reraise = PyLyException(f"-- {her} --")
                LOGGER.error(f"{message}")
                # Try to disconnect to avoid stale connections causing BTLEConnectError later.
                LOGGER.debug(f"|-< Disconnecting from {self._mac}  (forced_unk)")
                try:
                    LOGGER.warning(f"*** Disconnecting from {self._mac}  (forced_unk)")
                    self._peripheral.disconnect()
                except Exception as her2:  # pylint: disable=broad-exception-caught
                    LOGGER.error(f"While disconnecting : {her2}")
                raise reraise from her

        self._context_depth += 1
        try:
            yield self
        except btle.BTLEInternalError as her:
            message = ""
            reraise = PyLyException(f"-- {her} --")
            if isinstance(her, btle.BTLEInternalError):
                message = f"BTLE internal error while talking with device ({self._mac})."
                reraise = PyLyException(f"-- {her} --")
            # self._tries -= 1
            # fmt: off
            LOGGER.warning(f"{message}")
            # fmt: on
            # if self._tries <= 0:
            #     self._resets -= 1
            #     # ble_reset(debug=self.debug)
            #     self._set_tries()
            #     if self._resets <= 0:
            #         # re-raise because apparently resetting the radio doesn't work
            raise reraise from her
        except Exception as her:
            # Non-anticipated exceptions must be raised to draw attention to them
            # We'll reset the radio because it has had results in the past
            # ble_reset(debug=self.debug)
            message = f"Unexpected exception occured for device ({self._mac})."
            reraise = PyLyException(f"-- {her} --")
            LOGGER.error(f"{message}")
            raise reraise from her
        finally:
            self._context_depth -= 1
            if self._context_depth == 0:
                LOGGER.debug(f"|-< Disconnecting from {self._mac} (final)")
                self._peripheral.disconnect()

    @property
    def battery(self) -> float:
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_BATTERY)[0]
            value = ch.read()
        return float(ord(value))

    @property
    def data(self) -> SensorData:
        self._get_sensor_data()
        return self._data

    @property
    def history_data(self) -> dict:
        self._get_history_data()
        return self._history_data

    @property
    def humidity(self) -> float:
        return self.data.humidity

    @property
    def num_stored_entries(self) -> tuple:
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_NUM_RECORDS)[0]
            value = ch.read()
        total_records, current_records = struct.unpack_from("II", value)
        return total_records, current_records

    @property
    def temperature(self) -> float:
        return self.data.temperature

    @property
    def history_index(self) -> Union[tuple, Literal[0]]:
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_RECORD_IDX)[0]
            value = ch.read()
        _idx: Union[tuple, Literal[0]] = 0 if len(value) == 0 else struct.unpack_from("I", value)
        return _idx

    @history_index.setter
    def history_index(self, value) -> None:
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_RECORD_IDX)[0]
            ch.write(struct.pack("I", value), withResponse=True)

    @property
    def time(self) -> tuple[datetime, int]:
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
    def time(self, dt: datetime) -> None:
        data = struct.pack("Ib", int(dt.timestamp()), self.tz_offset)
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_TIME)[0]
            ch.write(data, withResponse=True)

    @property
    def tz_offset(self) -> int:
        if self._tz_offset is not None:
            return self._tz_offset
        if time.daylight:
            return -time.altzone // 3600
        return -time.timezone // 3600  # divide and round down to nearest int

    @tz_offset.setter
    def tz_offset(self, tz_offset: int) -> None:
        self._tz_offset = tz_offset  # type: ignore[assignment]

    @property
    def units(self) -> str:
        with self.connect():
            ch = self._peripheral.getCharacteristics(uuid=UUID_UNITS)[0]
            value = ch.read()
        return self.UNITS[value]

    @units.setter
    def units(self, value: str) -> None:
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

    _MAX_TRIES = 6
    _MAX_RESETS = 3

    # CR2025 / CR2032 maximum theoretical voltage = 3.4 V
    # ref. Table 1;
    #  CR2025: https://www.farnell.com/datasheets/1496883.pdf
    #  CR2032: https://www.farnell.com/datasheets/1496885.pdf
    # Lowest voltage for these batteries is 2.0 V but the BT radio
    # on most devices will stop working somewhere below 2.3 V (YMMV).
    BATTERY_FULL = 3.4
    BATTERY_LOW = 2.21

    # Locally cache the start time of the device.
    # This value won't change, and caching improves the performance getting the history data
    _start_time: datetime = datetime(1970, 1, 1)

    # Getting history data is very slow, so don't output progress updates
    enable_history_progress = False

    # Call the parent init with a bigger notification timeout
    def __init__(self, mac, notification_timeout=12.3, reusable=False, debug=False) -> None:
        super().__init__(
            mac=mac, notification_timeout=notification_timeout, reusable=reusable, debug=debug
        )
        self._latest_record = None

    def _get_history_data(self) -> None:
        # Work out the expected last record we'll be sent from the device.
        # The current hour doesn't appear until the end of the hour, and the time is recorded as
        # the end of hour time
        expected_end = datetime.now() - timedelta(hours=1)

        self._latest_record = None
        with self.connect():
            self._subscribe(UUID_HISTORY_3, self._process_history_data)

            while True:
                if not self._peripheral.waitForNotifications(self._notification_timeout):
                    LOGGER.debug(f"|-- Timeout listening to {self._mac}")
                    break

                # Find the last date we have data for, and check if it's for the current hour
                # noinspection PyTypeChecker
                if self._latest_record and self._latest_record >= expected_end:
                    break

    def _process_history_data(self, data) -> None:
        (idx, ts, max_temp, max_hum, min_temp, min_hum) = struct.unpack_from("<IIhBhB", data)

        # Work out the time of this record by adding the record time to time the
        # device was started
        ts = self.start_time + timedelta(seconds=ts)
        min_temp /= 10
        max_temp /= 10

        self._latest_record = ts
        self._history_data[idx] = [ts, min_temp, min_hum, max_temp, max_hum]
        self.output_history_progress(ts, min_temp, max_temp)

    def _process_sensor_data(self, data) -> None:
        """Process the sensor data.

        Args:
            data (struct): struct containing sensor data

        Returns:
            None
        """
        temperature, humidity, voltage = struct.unpack_from("<hBh", data)
        temperature /= 100
        voltage /= 1000
        # battery (float): Estimate percentage of the battery charge remaining
        battery: float = round(
            ((voltage - self.BATTERY_LOW) / (self.BATTERY_FULL - self.BATTERY_LOW) * 100), 1
        )
        self._data = SensorData(
            temperature=temperature, humidity=humidity, battery=battery, voltage=voltage
        )

    def output_history_progress(self, ts, min_temp, max_temp) -> None:
        if not self.enable_history_progress:
            return
        print(f"|-- {ts}: {min_temp} to {max_temp}")

    @property
    def battery(self) -> float:
        """Battery percentage is calculated from voltage which comes along with the
        temperature and humidity data, so we'll just get it from there.

        Returns:
             guestimate of battery percentage
        """
        return self.data.battery

    @property
    def start_time(self) -> datetime:
        """Work out the start time of the device.
        This is done by taking the current time, subtracting the time
        taken from the device (the run time), and adding the timezone offset.

        Returns:
            datetime: the start time of the device
        """
        if self._start_time == datetime(1970, 1, 1):
            start_time_delta = (
                self.time[0] - datetime(1970, 1, 1) - timedelta(hours=self.tz_offset)
            )
            self._start_time = datetime.now() - start_time_delta
        return self._start_time

    @property
    def time(self) -> tuple[datetime, int]:
        """Fetch datetime and timezone of a LYWSD03MMC device

        Returns:
           Device's current datetime and timezone
        """
        return super().time

    @time.setter
    def time(self, dt: datetime) -> None:  # pylint: disable=W0613
        """Dummy to disable setting the time and timezone.
        LYWSD03MMCs don't have visible clocks.

        Args:
            dt (datetime): Does nothing

        Returns:
            Nothing
        """
        return

    @property
    def tz_offset(self) -> int:
        return super().tz_offset

    @tz_offset.setter
    def tz_offset(self, tz_offset: int) -> None:  # pylint: disable=W0613
        """Disable setting the time and timezone.
        LYWSD03MMCs don't have visible clocks.

        Returns:
            Nothing
        """
        return
