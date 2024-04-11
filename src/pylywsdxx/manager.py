#!/usr/bin/env python3

import collections
import contextlib
import struct
import time
import warnings
from datetime import datetime, timedelta

from bluepy3 import btle

# from .device import Lywsd02
from .device import Lywsd03
from .device import PyLyConnectError
from .device import PyLyException
from .device import PyLyTimeout
from .device import PyLyValueError
from .radioctl import ble_reset


class PyLyManager:
    """Class to manage multiple PYLYWSD03 devices.

    * subscribe to device by MAC
    * periodically get data from all devices subscribed to
    * mitigate device errors and take countermeasures centrally
    """

    def init(self) -> None:
        pass
