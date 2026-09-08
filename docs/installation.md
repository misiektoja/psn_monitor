# Installation

## Requirements

* Python 3.10 or higher
* Libraries: [PSNAWP](https://codeberg.org/YoshikageKira/psnawp), `requests`, `python-dateutil`, `pytz`, `tzlocal`, `python-dotenv`, `wcwidth`, `colorama` (Windows only, optional)

Tested on:

* **macOS**: Tahoe, Sequoia, Sonoma, Ventura
* **Linux**: Raspberry Pi OS (Trixie, Bookworm, Bullseye), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2026/2025/2024
* **Windows**: 11, 10

It should work on other versions of macOS, Linux, Unix and Windows as well.

## Install from PyPI

```sh
pip install psn_monitor
```

## Manual Installation

Download the *[psn_monitor.py](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/psn_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install PSNAWP requests python-dateutil pytz tzlocal python-dotenv wcwidth
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

A manual install is started as `python3 psn_monitor.py ...` rather than `psn_monitor ...`. The tool detects which way it was started and prints its own commands to match, so the examples in this documentation work either way.

## Upgrading

To upgrade to the latest version when installed from PyPI:

```sh
pip install psn_monitor -U
```

If you installed manually, download the newest *[psn_monitor.py](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/psn_monitor.py)* file to replace your existing installation.
