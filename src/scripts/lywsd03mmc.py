#!/usr/bin/env python3

import argparse

import src.pylywsdxx as pyly

parser = argparse.ArgumentParser()
parser.add_argument('mac', help='MAC address of LYWSD02 device', nargs='+')
args = parser.parse_args()

for mac in args.mac:
    try:
        client = pyly.Lywsd03mmcClient(mac)
        print('Fetching data from {}'.format(mac))
        data = client.data
        print('Temperature: {}°C'.format(data.temperature))
        print('Humidity: {}%'.format(data.humidity))
        print('Battery: {}%'.format(client.battery))
        print()
    except Exception as e:
        print(e)
