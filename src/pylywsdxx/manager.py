#!/usr/bin/env python3

import datetime as dt
import logging

import time

# from threading import Timer
import statistics as stat
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
        "id": dev_id,           # (optional) device id provided by the client for easier identification
        "quality": 100,         # (int) 0...100, expresses the devices QoS
        "temperature": degC,    # (float) latest temperature
        "humidity": percent,    # (int) latest humidity
        "voltage": volts,       # (float) latest voltage
        "battery": percent,     # (float) current battery SoC
        "datetime": datetime,   # timestamp of when the above data was collected (datetime object)
        "epoch": UN*X epoch,    # timestamp of when the above data was collected (UNIX epoch)
        },
    "object": _object,          # object information (Lywsd02 or Lywsd03)
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
        self.median_response_time = 10.0
        self.response_list: list[float] = [self.median_response_time]
        LOGGER.debug("Initialised pylywsdxx device manager.")

    def subscribe_to(self, mac, dev_id="", version=3) -> None:
        """Let the manager subscribe to a device.

        Args:
            mac (str): MAC address of the device
            dev_id (str): Give the device a unique id. This id is used later to refer to the device.
            version (int): If not 3, it is assumed that you want to subscribe to a LYWSD02 device.

        Returns:
            Nothing.
        """
        if not dev_id:
            dev_id = str(mac)

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
        self.device_db[dev_id] = {
            "state": {"mac": mac, "dev_id": dev_id, "quality": 100},
            "object": _object,
            "control": {
                "next": 0,
            },
        }
        self.response_list.append(self.median_response_time)

    def get_state_of(self, dev_id: str) -> dict[str, Any]:
        """Return the last known state of the given device.

        Args:
            dev_id (str): id of the device being requested

        Returns:
            dict containing state information
        """
        LOGGER.debug(f"{dev_id}")
        return self.device_db[dev_id]["state"]

    def update(self, dev_id: str):
        """Update the device's state information.

        Args:
            dev_id: id of the device being updated

        Returns:
            nothing. Device info is updated internally.
        """
        LOGGER.debug(f"{dev_id} : ")
        _t0 = time.time()
        device_data: Any = self.device_db[dev_id]["object"].data
        self.device_db[dev_id]["state"]["temperature"] = device_data.temperature
        self.device_db[dev_id]["state"]["humidity"] = device_data.humidity
        self.device_db[dev_id]["state"]["voltage"] = device_data.voltage
        self.device_db[dev_id]["state"]["battery"] = device_data.battery
        self.device_db[dev_id]["state"]["datetime"] = dt.datetime.now()
        self.device_db[dev_id]["state"]["epoch"] = int(dt.datetime.now().timestamp())
        state_of_charge = self.device_db[dev_id]["state"]["battery"]
        previous_qos = self.device_db[dev_id]["state"]["quality"]

        response_time: float = time.time() - _t0
        self.response_list.append(response_time)
        if len(self.response_list) > 100:
            self.response_list.pop(0)
        self.median_response_time = stat.median(self.response_list)
        self.device_db[dev_id]["state"]["quality"] = self.qos(
            state_of_charge, response_time, previous_qos
        )
        LOGGER.debug(f"{self.device_db[dev_id]['state']} ")

    def update_all(self):
        """Update the state of all devices known to the manager."""
        for device_to_update in self.device_db:
            self.update(dev_id=device_to_update)

    def qos(self, state_of_charge: float, response_time: float, previous: int):
        """Determine the device's Quality of Service.
        """
        soc: float = state_of_charge / 100.0
        rt: float = max(1.0, self.median_response_time / response_time)
        prev: float = previous / 100.0
        new: float = stat.mean([prev, soc * rt])
        return int(new * 100.0)
