#!/usr/bin/env python3

import subprocess  # nosec B404
import time
import warnings

warnings.filterwarnings(action="always", category=RuntimeWarning)


def ble_reset(delay: float = 20.0, debug: bool = False):
    """Reset the bluetooth hardware.

    Args:
        delay: time [s] to wait between switching off and back on again.
        debug: whether to provide debugging information.

    """
    warnings.warn(message="Resetting BT-radio.", category=RuntimeWarning, stacklevel=2)

    # Have you tried turning it off and on again?
    args = ["/usr/bin/bluetoothctl", "power", "off"]
    _exit_code_on = subprocess.check_output(args, shell=False)  # nosec B603
    if debug:
        print(f"Radio off ({_exit_code_on})")

    time.sleep(delay)
    args = ["/usr/bin/bluetoothctl", "power", "on"]
    _exit_code_off = subprocess.check_output(args, shell=False)  # nosec B603
    if debug:
        print(f"Radio on ({_exit_code_off})")

    # if all else fails...
    # os.system("/usr/bin/sudo /usr/bin/systemctl restart bluetooth.service")
    return _exit_code_on, _exit_code_off
