#!/usr/bin/env python3

import datetime as dt
import logging

import time

# from threading import Timer
import statistics as stat
from typing import Any

from .device import Lywsd02
from .device import Lywsd03

from .radioctl import ble_reset

LOGGER: logging.Logger = logging.getLogger(__name__)

"""
Structure of the dict kept for each device.
The dict `state` is returned to the client. The rest is for internal use.
{
    "state": {
        "mac": mac,             # MAC address provided by the client
        "dev_id": dev_id,           # (optional) device id provided by the client for easier identification
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

    __INITIAL_QOS: int = 33
    __WARNING_QOS: int = 15
    __INITIAL_SOC: int = 50

    def __init__(self, debug: bool = False) -> None:
        """Initialise the manager."""
        LOGGER.info("Initialising pylywsdxx device manager.")
        self.device_db: dict[str, dict[str, Any]] = {}
        self.mgr_debug: bool = debug
        if debug:
            LOGGER.level = logging.DEBUG
            LOGGER.debug("Debugging on.")
        self.mgr_notification_timeout: float = 11.5
        self.mgr_reusable: bool = False
        self.median_response_time: float = 11.5
        self.response_list: list[float] = [self.median_response_time]
        self.radio_state_reset: float = time.time()

    def subscribe_to(self, mac: str, dev_id: str = "", version: int = 3) -> None:
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
            "state": {
                "mac": mac,
                "dev_id": dev_id,
                "quality": self.__INITIAL_QOS,
                "battery": self.__INITIAL_SOC,
            },
            "object": _object,
            "control": {
                "next": time.time(),
                "fail": 0,
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
        LOGGER.debug(f"{dev_id} : {self.device_db[dev_id]['state']}")
        return self.device_db[dev_id]["state"]

    def update(self, dev_id: str) -> None:
        """Update the device's state information.

        Args:
            dev_id: id of the device being updated

        Returns:
            nothing. Device info is updated internally.
        """
        LOGGER.debug(f"{dev_id} : ")
        _t0: float = time.time()
        excepted = False
        valid_data = False
        # fmt: off
        try:
            device_data: Any = self.device_db[dev_id]["object"].data
            self.device_db[dev_id]["state"]["temperature"] = device_data.temperature
            self.device_db[dev_id]["state"]["humidity"] = device_data.humidity
            self.device_db[dev_id]["state"]["voltage"] = device_data.voltage
            self.device_db[dev_id]["state"]["battery"] = device_data.battery
        except Exception as her:  # pylint: disable=W0703
            excepted = True
            LOGGER.error(f"*** While talking to room {dev_id} ({self.device_db[dev_id]['state']['mac']}) {type(her).__name__} {her} ")   # noqa: E501  # pylint: disable=C0301

        # record the time
        self.device_db[dev_id]["state"]["datetime"] = dt.datetime.now()
        self.device_db[dev_id]["state"]["epoch"] = self.device_db[dev_id]["state"]["datetime"].timestamp()

        state_of_charge: float = self.device_db[dev_id]["state"]["battery"]
        previous_qos: int = self.device_db[dev_id]["state"]["quality"]
        response_time: float = time.time() - _t0
        # fmt: on

        # check if we have some data, so the client won't have to bork
        if "temperature" in self.device_db[dev_id]["state"]:
            valid_data = True

        # determine the device's QoS
        self.device_db[dev_id]["state"]["quality"] = self.qos_device(
            dev_id, state_of_charge, response_time, previous_qos, excepted, valid_data
        )
        # check if device is failing (i.e. exception or low QoS)
        if excepted or self.device_db[dev_id]["state"]["quality"] < 6:
            self.device_db[dev_id]["control"]["fail"] += 1
            LOGGER.warning(f"{dev_id} : fail score: {self.device_db[dev_id]['control']['fail']}")
        else:
            _fail: int = self.device_db[dev_id]["control"]["fail"]
            self.device_db[dev_id]["control"]["fail"] = max([0, _fail - 1])
        LOGGER.debug(f"{self.device_db[dev_id]['state']}")

    def update_all(self) -> None:
        """Update the state of all devices known to the manager."""
        for dev, dev_state in self.device_db.items():
            # don't bother to update devices that are on hold
            t_next: float = time.time() - dev_state["control"]["next"]
            if t_next > 0:
                self.update(dev_id=dev)
                dev_state["control"]["next"] = time.time()
        # check radio
        self.handle_fails()

    def qos_device(
        self,
        dev_id: str,
        state_of_charge: float,
        response_time: float,
        previous_q: int,
        excepted: bool,
        valid: bool,
    ) -> int:
        """Determine the device's Quality of Service."""
        if not valid:
            # when there's no data, then there's no need to proceed
            return 0
        q = 1.0
        if excepted:
            # in case of timeout or error there is still old data
            # so we keep that but we value the SoC less
            # eventually this will report a QoS = 0
            q = 0.5
        LOGGER.debug(f"{dev_id} : {state_of_charge}% {response_time:.1f}s {previous_q} {q}")
        #
        self.response_list.append(response_time)
        if len(self.response_list) > 100:
            self.response_list.pop(0)
        self.median_response_time = stat.median(self.response_list)
        LOGGER.debug(f"{dev_id} median RT : {self.median_response_time}")

        # normalise parameters
        soc: float = state_of_charge / 100.0
        rt: float = min(1.0, self.median_response_time / response_time)
        prev_q: float = previous_q / 100.0
        # Determine QoS and log message to report QoS
        new_q: float = stat.mean([prev_q, soc * rt * q])
        msg = f"{dev_id} : q({q:.1f}) * soc({soc:.4f}) * rt({rt:.4f}) :: prev_qos({prev_q}) => QoS({new_q:.4f})"
        if new_q < (self.__WARNING_QOS / 100.0):
            LOGGER.warning(msg)
        else:
            LOGGER.debug(msg)

        return int(new_q * 100.0)

    def handle_fails(self) -> None:
        """Handle failing devices.
        Log a warning when devices have failed to provide data.
        Reset the BT-radio if multiple devices (more than 50%) have failed.
        """
        fail_count = 0
        for _, device_state in self.device_db.items():
            fail_score: int = device_state["control"]["fail"]
            if fail_score > 5:
                # devices that keep failing are put on hold for a while
                LOGGER.warning(f"*** Putting device {device_state['state']['dev_id']} on HOLD!")
                LOGGER.info(device_state)
                device_state["control"]["next"] = time.time() + (3 * 3600.0)
                # decrease the fail_score to prevent an infinite hold
                device_state["control"]["fail"] -= 3
            # count number of devices that are failing
            fail_count += 1 if fail_score else 0

        if not fail_count:
            # skip the rest if everything is okay
            return

        msg: str = f"fail count = {fail_count}"
        dev_cnt: int = len(self.device_db)
        rst_time: float = time.time() - self.radio_state_reset
        if fail_count > int(dev_cnt / 2) and rst_time >= 0:
            LOGGER.error(msg)
            ble_reset()
            # prevent repeated resets of the radio
            self.radio_state_reset = time.time() + 3600.0
            return

        if fail_count > 0:
            LOGGER.warning(msg)
            return
