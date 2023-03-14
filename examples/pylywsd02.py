#!/usr/bin/env python3

import argparse
from datetime import datetime

import pylywsdxx as pyly  # noqa

parser = argparse.ArgumentParser()
parser.add_argument(
    "action",
    help=(
        "Action to perform, either: "
        "sync - synchronize time with this machine, "
        "read - read current values from device, "
        "setc/setf - set temperature unit on display to Celsius/Fahrenheit"
    ),
    choices=["sync", "read", "setc", "setf"],
)
parser.add_argument("mac", help="MAC address of LYWSD02 device", nargs="+")
args = parser.parse_args()

for mac in args.mac:
    try:
        client = pyly.Lywsd02client(mac)
        if args.action == "sync":
            print(f"Synchronizing time of {mac}")
            client.time = datetime.now()
        elif args.action == "read":
            print(f"Fetching data from {mac}")
            data = client.data
            print(f"Temperature: {data.temperature}°C")
            print(f"Humidity: {data.humidity}%")
            print(f"Battery: {data.battery}%")
            print()
        elif args.action == "setc":
            client.units = "C"
        elif args.action == "setf":
            client.units = "F"
    except (Exception,) as e:
        print(e)
