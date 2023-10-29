#!/usr/bin/env python3

import argparse

import pylywsdxx as pyly  # noqa

# In these examples we don't care about pylint's W0718
# pylint: disable=broad-exception-caught

parser = argparse.ArgumentParser()
parser.add_argument("mac", help="MAC address of LYWSD02 device", nargs="+")
args = parser.parse_args()

for mac in args.mac:
    try:
        client = pyly.Lywsd03(mac)
        print(f"Fetching data from {mac}")
        data = client.data
        print(f"Temperature: {data.temperature}°C")
        print(f"Humidity: {data.humidity}%")
        print(f"Battery: {data.battery}% ({data.voltage} V)")
        print()
    except (Exception,) as e:
        print(f"An exception of type {type(e).__name__} occured")
        print(e)
