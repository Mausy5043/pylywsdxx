#!/usr/bin/env python3

import logging
import re
import subprocess  # nosec B404
import sys
import time

# import warnings

# warnings.filterwarnings(action="always", category=RuntimeWarning)
LOGGER: logging.Logger = logging.getLogger(__name__)


# fmt: off
def ble_reset(delay: float = 20.0, debug: bool = False) -> tuple[str, str]:
    """Reset the bluetooth hardware.

    Args:
        delay (float): time [s] to wait between switching off and back on again.
        debug (bool): whether to provide debugging information.
    """
    if debug:
        LOGGER.addHandler(logging.StreamHandler(sys.stdout))
        LOGGER.level = logging.DEBUG

    # fetch state of devices from bluetoothctl
    args: list[str] = ["/usr/bin/bluetoothctl", "devices"]
    _devices: str = subprocess.check_output(args, shell=False).decode(encoding="utf-8")  # nosec B603
    if debug:
        print(f"Known devices: {_devices}")
    LOGGER.info(f"Known devices: {_devices}")

    LOGGER.warning("Resetting BT-radio.")

    # Have you tried turning it off and on again?
    args = ["/usr/bin/bluetoothctl", "power", "off"]
    _exit_code_off: str = subprocess.check_output(args, shell=False).decode(encoding="utf-8").strip()  # nosec B603
    if debug:
        print(f"Radio off : {_exit_code_off}")
    LOGGER.info(f"Radio off : {de_escape_string(_exit_code_off)}")
    time.sleep(delay)

    args = ["/usr/bin/bluetoothctl", "power", "on"]
    _exit_code_on: str = subprocess.check_output(args, shell=False).decode(encoding="utf-8").strip()  # nosec B603
    if debug:
        print(f"Radio on : {_exit_code_on}")
    LOGGER.info(f"Radio on : {de_escape_string(_exit_code_on)}")
    time.sleep(delay)

    # if all else fails...
    args = ["/usr/bin/sudo", "/usr/bin/systemctl", "restart", "bluetooth.service"]
    _restart_result: str = subprocess.check_output(args, shell=False).decode(encoding="utf-8").strip()  # nosec B603
    if debug:
        print(f"Restarted bluetooth service ({_restart_result}")
    LOGGER.info(f"Restarted bluetooth service ({_restart_result}")
    time.sleep(delay)
    return (_exit_code_on, _exit_code_off)
# fmt: on

def de_escape_string(text: str) -> str:
    """Remove ANSI escape sequences using regular expression"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned_text: str = ansi_escape.sub('', text)
    # Remove any remaining \x01 and \x02 characters
    cleaned_text = cleaned_text.replace('\x01', '').replace('\x02', '')
    return cleaned_text

def force_disconnect(device: str) -> None:
    """Name of the function says it all."""
    args: list[str] = ["/usr/bin/bluetoothctl", "disconnect", f"{device}"]
    LOGGER.error(f"Forcing disconnect from device {device}")
    try:
        _result: str = subprocess.check_output(args, shell=False).decode(encoding="utf-8").strip()  # nosec B603
        LOGGER.info(f"{de_escape_string(_result)}")
    except subprocess.CalledProcessError:
        LOGGER.error(f"{de_escape_string(_result)}")
