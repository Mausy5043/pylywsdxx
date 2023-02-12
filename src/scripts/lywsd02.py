#!/usr/bin/env python3

import argparse
from datetime import datetime

import src.pylywsdxx as pyly

parser = argparse.ArgumentParser()
parser.add_argument(
    "action",
    help="Action to perform, either: sync - synchronize time with this machine, read - read current values from device, setc/setf - set temperature unit on display to Celsius/Fahrenheit",
    choices=["sync", "read", "setc", "setf"],
)
parser.add_argument("mac", help="MAC address of LYWSD02 device", nargs="+")
args = parser.parse_args()

for mac in args.mac:
    try:
        client = pyly.Lywsd02client(mac)
        if args.action == "sync":
            print("Synchronizing time of {}".format(mac))
            client.time = datetime.now()
        elif args.action == "read":
            print("Fetching data from {}".format(mac))
            data = client.data
            print("Temperature: {}°C".format(data.temperature))
            print("Humidity: {}%".format(data.humidity))
            print("Battery: {}%".format(client.battery))
            print()
        elif args.action == "setc":
            client.units = "C"
        elif args.action == "setf":
            client.units = "F"
    except Exception as e:
        print(e)
