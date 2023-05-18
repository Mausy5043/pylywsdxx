#!/usr/bin/env python3

import subprocess  # nosec B404
import time


def ble_reset(delay=5.0):
    """Reset the bluetooth hardware by switching the power OFF and ON again.

    Args:
        delay (float): number of seconds between switching OFF and ON

    Returns:
        None
    """

    # Have you tried turning it off and on again?
    args = ["/usr/bin/bluetoothctl", "power", "off"]
    _exit_code = subprocess.check_output(args, shell=False)  # nosec B603

    time.sleep(delay)

    args = ["/usr/bin/bluetoothctl", "power", "on"]
    _exit_code = subprocess.check_output(args, shell=False)  # nosec B603

    # if all else fails...
    # os.system("/usr/bin/sudo /usr/bin/systemctl restart bluetooth.service")
