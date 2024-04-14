#!/usr/bin/env python3

import datetime as dt
import logging
import time
from threading import Timer

from typing import Any

from .device import Lywsd02
from .device import Lywsd03

# from .device import PyLyConnectError
# from .device import PyLyException
# from .device import PyLyTimeout
# from .device import PyLyValueError
#  from .radioctl import ble_reset

LOGGER: logging.Logger = logging.getLogger(__name__)


class PyLyManager:
    """Class to manage multiple LYWSD03MMC devices.

    * subscribe to device by MAC
    * periodically get data from all devices subscribed to
    * mitigate device errors and take countermeasures centrally
    """

    def __init__(self, debug: bool = False) -> None:
        self.device_db: dict[str, dict] = {}
        self.mgr_debug: bool = debug
        self.mgr_notification_timeout: float = 11.0
        self.mgr_reusable: bool = False

    def subscribe_to(self, mac, name, version=3) -> None:
        """Let the manager subscribe to a device.

        Args:
            mac (str): MAC address of the device
            name (str): Name of the device. This name is used later to refer to the device, so should be unique.
            version (int): If not 3, it is assumed that you want to subscribe to a LYWSD02 device.

        Returns:
            Nothing.
        """
        if version == 3:
            _object: Any = Lywsd03(
                mac=mac,
                notification_timeout=self.mgr_notification_timeout,
                reusable=self.mgr_reusable,
                debug=self.mgr_debug,
            )
        else:
            _object = Lywsd02(
                mac=mac,
                notification_timeout=self.mgr_notification_timeout,
                reusable=self.mgr_reusable,
                debug=self.mgr_debug,
            )
        self.device_db[name] = {
            "mac": mac,
            "object": _object,
            "state": {"mac": mac, "name": name, "quality": 100},
        }

    def get_state_of(self, name: str):
        """Return the last known state of the given device.

        Args:
            name (str): name of the device being requested

        Returns:
            dict containing state information
        """
        return self.device_db[name]["state"]

    def update(self, name: str) -> bool:
        """Update the device's state information.

        Args:
            name: name of the device being updated

        Returns:
            Nothing
        """
        device_data: Any = self.device_db[name]["object"].data
        self.device_db[name]["state"]["temperature"] = device_data.temperature
        self.device_db[name]["state"]["humidity"] = device_data.humidity
        self.device_db[name]["state"]["voltage"] = device_data.voltage
        self.device_db[name]["state"]["datetime"] = dt.datetime.now()
        self.device_db[name]["state"]["epoch"] = int(dt.datetime.now().timestamp())
        self.device_db[name]["state"]["quality"] = 100
        return True

    def update_all(self) -> bool:
        """Update the state of all device_db known to the manager."""
        for device_to_update in self.device_db:
            _succes = self.update(name=device_to_update)
        return _succes


class RepeatedTimer:
    """class to call a timer"""

    def __init__(self, interval: int, function, *args, **kwargs):
        self._timer = None
        self.interval: int = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


def hello(name):
    print(f"Hello {name}!")


if __name__ == "__main__":
    print("starting...")
    rt = RepeatedTimer(1, hello, "World")  # it auto-starts, no need of rt.start()
    try:
        time.sleep(5)  # your long-running job goes here...
    finally:
        rt.stop()  # better in a try/finally block to make sure the program ends!
