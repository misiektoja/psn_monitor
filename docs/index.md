# psn_monitor

[![GitHub Release](https://img.shields.io/github/v/release/misiektoja/psn_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/psn_monitor/releases)
[![PyPI Version](https://img.shields.io/pypi/v/psn_monitor?style=flat-square&color=teal)](https://pypi.org/project/psn-monitor/)
[![GitHub Stars](https://img.shields.io/github/stars/misiektoja/psn_monitor?style=flat-square&color=magenta)](https://github.com/misiektoja/psn_monitor)
[![Python Versions](https://img.shields.io/badge/python-3.10+-blueviolet?style=flat-square)](https://pypi.org/project/psn-monitor/)
[![License](https://img.shields.io/github/license/misiektoja/psn_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/psn_monitor/blob/main/LICENSE)
[![OpenSSF Scorecard](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Fpsn_monitor&query=%24.score&label=openssf%20scorecard&style=flat-square)](https://scorecard.dev/viewer/?uri=github.com/misiektoja/psn_monitor)
[![Last Commit](https://img.shields.io/github/last-commit/misiektoja/psn_monitor?style=flat-square&color=green)](https://github.com/misiektoja/psn_monitor/commits/main)
[![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square)](https://github.com/misiektoja/psn_monitor)

Powerful tool for real-time monitoring of **Sony PlayStation (PSN) players' activities**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor.png" alt="psn_monitor_screenshot" width="90%"/>
</p>

<a id="quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-check-and-install) first.

Install from PyPI:

```sh
pip install psn_monitor
```

Run the setup wizard:

```sh
psn_monitor --setup
```

The wizard asks for the target, the npsso code and optional notifications. Review the settings before saving them. See [Setup & First Run](setup-and-first-run.md) for how to get the npsso code and the required privacy settings.

For the manual single-file method, dependencies and upgrade commands, see [Installation](installation.md).

<a id="features"></a>
## Features

### 🔍 Activity Tracking

* **Gaming activity**: Detect online and offline status, game starts, finishes and changes.
* **Session statistics**: Measure time in each state, time per game and games played.
* **Session continuity**: Preserve statistics through short offline interruptions.

### 📊 Profile Insights

* **Profile details**: View PSN IDs, status, platform, PS+ membership, bio, languages and friendship details.
* **Recent games**: See recently played titles, last played dates and total playtime.
* **Optional trophies**: Include a trophy summary and recently earned trophies.

### 🔔 Notifications and History

* **Event alerts**: Configure email, Discord and ntfy notifications independently.
* **CSV history**: Save reported activity with timestamps.
* **Saved status**: Resume monitoring with state retained across restarts.

### ⚙️ Setup and Configuration

* **Guided setup**: Configure a target, credentials and alerts with `--setup`, then check them with `--doctor`.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Terminal and runtime controls**: Customize colours and adjust the running monitor through supported signals.
