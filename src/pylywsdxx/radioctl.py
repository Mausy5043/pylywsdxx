#!/usr/bin/env python3

import subprocess  # nosec B404
import time
import warnings

warnings.filterwarnings("always", category=RuntimeWarning)


def ble_reset(delay=5.0):
    """Reset the bluetooth hardware"""

    warnings.warn("Resetting BT-radio.", RuntimeWarning, stacklevel=2)

    # Have you tried turning it off and on again?
    args = ["/usr/bin/bluetoothctl", "power", "off"]
    _exit_code = subprocess.check_output(args, shell=False)  # nosec B603

    time.sleep(delay)
    args = ["/usr/bin/bluetoothctl", "power", "on"]
    _exit_code = subprocess.check_output(args, shell=False)  # nosec B603

    # if all else fails...
    # os.system("/usr/bin/sudo /usr/bin/systemctl restart bluetooth.service")
