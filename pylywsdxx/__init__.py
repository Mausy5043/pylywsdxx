#!/usr/bin/env python3

import logging
import logging.handlers

# isort: off
from .device import Lywsd02
from .device import Lywsd03
from .device import PyLyConnectError
from .device import PyLyException
from .device import PyLyTimeout
from .device import PyLyValueError

# isort: on
from .manager import PyLyManager
from .radioctl import ble_reset

logging.basicConfig(
    level=logging.INFO,
    format="pylywsd.%(module)s.%(funcName)s [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.handlers.SysLogHandler(
            address="/dev/log", facility=logging.handlers.SysLogHandler.LOG_DAEMON
        )
    ],
)
LOGGER: logging.Logger = logging.getLogger(__name__)

__all__: tuple = (
    "Lywsd02",
    "Lywsd03",
    "PyLyException",
    "PyLyTimeout",
    "PyLyConnectError",
    "PyLyValueError",
    "PyLyManager",
    "ble_reset",
)
