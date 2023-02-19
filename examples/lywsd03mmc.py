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
