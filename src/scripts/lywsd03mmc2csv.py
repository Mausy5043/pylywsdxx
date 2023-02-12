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
        client = pyly.Lywsd03client(args.mac)
        print(f"Fetching data from {args.mac}")
        data = client.data
        print(f"Temperature: {data.temperature}")
        print(f"Humidity: {data.humidity}%")
        print(f"Battery: {data.battery}%")
        print(f"Device start time: {client.start_time}")
        print()
        print(f"Fetching history from {args.mac}")
        client.enable_history_progress = True
        history = client.history_data
        for i in history:
            c.writerow(history[i])
        print("Done")
    except (Exception,) as e:
        print(e)
