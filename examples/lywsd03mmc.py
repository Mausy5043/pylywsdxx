#!/usr/bin/env python3

import argparse

import pylywsdxx as pyly    # noqa

parser = argparse.ArgumentParser()
parser.add_argument("mac", help="MAC address of LYWSD02 device", nargs="+")
args = parser.parse_args()

for mac in args.mac:
    try:
        client = pyly.Lywsd03client(mac)
        print(f"Fetching data from {mac}")
        data = client.data
        print(f"Temperature: {data.temperature}°C")
        print(f"Humidity: {data.humidity}%")
        print(f"Battery: {client.battery}% ({client.voltage} V)")
        print()
    except (Exception,) as e:
        print(e)

"""
$ pylywsdxx/examples/lywsd03mmc.py  A4:C1:38:A5:71:D0
Fetching data from A4:C1:38:A5:71:D0
Temperature: 21.12°C
Humidity: 57%
'Lywsd03client' object has no attribute 'voltage'
"""
