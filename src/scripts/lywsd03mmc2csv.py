#!/usr/bin/env python3

import argparse
import csv

import src.pylywsdxx as pyly

parser = argparse.ArgumentParser()
parser.add_argument("mac", help="MAC address of LYWSD03MMC device")
parser.add_argument("--output", help="File to output", default="output.csv")

args = parser.parse_args()

with open(args.output, "w") as csvfile:
    c = csv.writer(csvfile)
    c.writerow(["Time", "Min temperature", "Min humidity", "Max temperature", "Max humidity"])

    try:
        client = pyly.Lywsd03mmcClient(args.mac)
        print("Fetching data from {}".format(args.mac))
        data = client.data
        print("Temperature: {}".format(data.temperature))
        print("Humidity: {}%".format(data.humidity))
        print("Battery: {}%".format(data.battery))
        print("Device start time: {}".format(client.start_time))
        print()
        print("Fetching history from {}".format(args.mac))
        client.enable_history_progress = True
        history = client.history_data
        for i in history:
            c.writerow(history[i])
        print("Done")
    except Exception as e:
        print(e)
