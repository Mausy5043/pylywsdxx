[![PyPI version](https://img.shields.io/pypi/v/pylywsdxx.svg?logo=pypi&logoColor=FFE873)](https://pypi.org/project/pylywsdxx)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/pylywsdxx.svg?logo=python&logoColor=FFE873)](https://pypi.org/project/pylywsdxx)
[![PyPI downloads](https://img.shields.io/pypi/dm/pylywsdxx.svg)](https://pypistats.org/packages/pylywsdxx)
[![Code style: Black](https://img.shields.io/badge/code%20style-Black-000000.svg)](https://github.com/psf/black)

# pylywsdxx

This is a Python3 library to allow interrogation of Xiaomi Mijia LYWSD* sensors via Bluetooth Low Energy (BLE).

**Note**: This is an unofficial project, and is in no way supported or endorsed by Xiaomi.

## Requirements

This module requires [`bluepy3`](https://pypi.org/project/bluepy3/) which should be installed automagically when using the installation instructions below.

## Installation

```
pip install pylywsdxx
```

## Usage

```
import pylywsdxx as pyly

mac = "A4:C1:38:0D:EA:D0"

device2 = pyly.Lywsd02(mac)
data2 = device2.data
print(f"Temperature: {data2.temperature}°C")

device3 = pyly.Lywsd03(mac)
data3 = device3.data
print(f"Temperature: {data3.temperature}°C")
```

Please note that this module has completely and intentionally broken backwards compatibility with previous 
and existing versions of `lywsd02` and `lywsd03mmc` and with v1.* versions of itself.

## Acknowledgements

Based on previous work stolen from Mikhail Baranov (`h4`) : [lywsd02](https://github.com/h4/lywsd02)   
and Duncan Barclay (`uduncanu`) : [lywsd03mmc](https://github.com/uduncanu/lywsd03mmc)   

## License

See [LICENSE](LICENSE).
