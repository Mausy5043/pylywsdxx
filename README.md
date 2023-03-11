# pylywsdxx


[![PyPI version](https://img.shields.io/pypi/v/pylywsdxx.svg?logo=pypi&logoColor=FFE873)](https://pypi.org/project/pylywsdxx)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/pylywsdxx.svg?logo=python&logoColor=FFE873)](https://pypi.org/project/pylywsdxx)
[![PyPI downloads](https://img.shields.io/pypi/dm/pylywsdxx.svg)](https://pypistats.org/packages/pylywsdxx)
[![Code style: Black](https://img.shields.io/badge/code%20style-Black-000000.svg)](https://github.com/psf/black)


This is a Python3 library to allow interrogation of Xiaomi Mijia LYWSD* sensors via Bluetooth (BLE).

**Note**: This is an unofficial project, and is in no way supported or endorsed by Xiaomi.

## Requirements

This module requires [`bluepy3`](https://pypi.org/project/bluepy3/) which should be installed automagically when using the installation instructions below.

## Installation

```bash
pip install pylywsdxx
```

## Usage

Please note that versions prior to 0.1.0 are early alpha and virtually guaranteed to be defective!

```python3
import pylywsdxx as pyly

mac = "A4:C1:38:0D:EA:D0"

client2 = pyly.Lywsd02client(mac)
data2 = client2.data
print(f"Temperature: {data2.temperature}°C")

client3 = pyly.Lywsd03client(mac)
data3 = client3.data
print(f"Temperature: {data3.temperature}°C")
```

Please note that this module has completely and intentionally broken backwards compatibility with previous and existing versions of `lywsd02` and `lywsd03mmc` .

## Acknowledgements

Based on previous work by Mikhail Baranov (`h4`) : [lywsd02](https://github.com/h4/lywsd02)   
and Duncan Barclay (`uduncanu`) : [lywsd03mmc](https://github.com/uduncanu/lywsd03mmc)   

## License

See [LICENSE](LICENSE).
