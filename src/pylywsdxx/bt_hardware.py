#!/usr/bin/env python3

import os
import time


def ble_reset(delay=5.0):
    """Reset the bluetooth hardware"""
    # Have you tried turning it off and on again?
    _exit_code = os.system("/usr/bin/bluetoothctl power off")
    time.sleep(delay)
    _exit_code = os.system("/usr/bin/bluetoothctl power on")
    # if all else fails...
    # os.system("/usr/bin/sudo /usr/bin/systemctl restart bluetooth.service")
