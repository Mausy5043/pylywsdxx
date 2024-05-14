#!/usr/bin/env python3

import datetime as dt
import logging

import time

# from threading import Timer

from typing import Any

from .device import Lywsd02
from .device import Lywsd03

# from .device import PyLyConnectError
# from .device import PyLyException
# from .device import PyLyTimeout
# from .device import PyLyValueError
#  from .radioctl import ble_reset

LOGGER: logging.Logger = logging.getLogger(__name__)

"""
Structure of the dict kept for each device.
The dict `state` is returned to the client. The rest is for internal use.
{
    "state": {
        "mac": mac,             # MAC address provided by the client
        "name": name,           # (optional) device name provided by the client for easier identification
        "quality": 100,         # int 0...100, expresses the devices QoS
        "temperature": degC,    # latest temperature
        "humidity": percent,    # latest humidity
        "voltage": volts,       # latest voltage
        "datetime": datetime,   # timestamp of when the above data was collected (datetime object)
        "epoch": UN*X epoch,    # timestamp of when the above data was collected (UNIX epoch)
        },
    "object": _object,          # Object information (Lywsd02 or Lywsd03)
    "control": {
        "next": 0,
        },
}
"""


class PyLyManager:
    """Class to manage multiple LYWSD03MMC devices.

    * subscribe to device by MAC
    * periodically get data from all devices subscribed to
    * mitigate device errors and take countermeasures centrally
    """

    def __init__(self, debug: bool = False) -> None:
        """Initialise the manager."""
        self.device_db: dict[str, dict[str, Any]] = {}
        self.mgr_debug: bool = debug
        if debug:
            LOGGER.level = logging.DEBUG
        self.mgr_notification_timeout: float = 11.0
        self.mgr_reusable: bool = False
        LOGGER.debug("Initialised pylywsdxx device manager.")

    def subscribe_to(self, mac, name="", version=3) -> None:
        """Let the manager subscribe to a device.

        Args:
            mac (str): MAC address of the device
            name (str): Give the device a unique name. This name is used later to refer to the device.
            version (int): If not 3, it is assumed that you want to subscribe to a LYWSD02 device.

        Returns:
            Nothing.
        """
        if not name:
            name = str(mac)

        if version == 3:
            _object: Any = Lywsd03(
                mac=mac,
                notification_timeout=self.mgr_notification_timeout,
                reusable=self.mgr_reusable,
                debug=self.mgr_debug,
            )
            LOGGER.info(f"Created v3 object for {mac}")
        else:
            _object = Lywsd02(
                mac=mac,
                notification_timeout=self.mgr_notification_timeout,
                reusable=self.mgr_reusable,
                debug=self.mgr_debug,
            )
            LOGGER.info(f"Created v2 object for {mac}")
        self.device_db[name] = {
            "state": {"mac": mac, "name": name, "quality": 100},
            "object": _object,
            "control": {
                "next": 0,
            },
        }

    def get_state_of(self, name: str) -> dict[str, Any]:
        """Return the last known state of the given device.

        Args:
            name (str): name of the device being requested

        Returns:
            dict containing state information
        """
        LOGGER.debug(f"{name}")
        return self.device_db[name]["state"]

    def update(self, name: str):
        """Update the device's state information.

        Args:
            name: name of the device being updated

        Returns:
            nothing. Device info is updated internally.
        """
        LOGGER.debug(f"{name} : ")
        t0 = time.time()
        device_data: Any = self.device_db[name]["object"].data
        self.device_db[name]["state"]["temperature"] = device_data.temperature
        self.device_db[name]["state"]["humidity"] = device_data.humidity
        self.device_db[name]["state"]["voltage"] = device_data.voltage
        self.device_db[name]["state"]["battery"] = device_data.battery
        self.device_db[name]["state"]["datetime"] = dt.datetime.now()
        self.device_db[name]["state"]["epoch"] = int(dt.datetime.now().timestamp())
        self.device_db[name]["state"]["quality"] = time.time() - t0
        LOGGER.debug(f"{self.device_db[name]['state']} ")

    def update_all(self):
        """Update the state of all device_db known to the manager."""
        for device_to_update in self.device_db:
            self.update(name=device_to_update)
