#!/usr/bin/env python3

import argparse

import pylywsdxx as pyly  # noqa

# In these examples we don't care about pylint's W0718
# pylint: disable=broad-exception-caught

parser = argparse.ArgumentParser()
parser.add_argument("mac", help="MAC address of LYWSDxx device", nargs="+")
args = parser.parse_args()

mymanager = pyly.PyLyManager()

# Tell the manager which devices you want to subscribe to
for mac in args.mac:
    try:
        mymanager.subscribe_to(mac)
        print(f"Added: {mac}")
    except (Exception,) as e:
        print(
            f"An exception of type {type(e).__name__} occured when trying to subscribe to {mac}"
        )
        print(e)

# Ask the manager to fetch the latest state of all subscribed devices
try:
    print("Updating device information...")
    mymanager.update_all()
except (Exception,) as e:
    print(f"An exception of type {type(e).__name__} occured")
    print(e)

#
for mac in args.mac:
    try:
        print(f"Fetching data for {mac}")
        data = mymanager.get_state_of(mac)
        print(f"Temperature: {data['temperature']}°C")
        print(f"Humidity: {data['humidity']}%")
        print(f"Battery: {data['battery']}% ({data['voltage']} V)")
        print(f"Quality: {data['quality']}")
        print()
    except (Exception,) as e:
        print(f"An exception of type {type(e).__name__} occured")
        print(e)
