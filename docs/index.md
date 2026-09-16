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

<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install psn_monitor
```

Run the setup wizard:

```sh
psn_monitor --setup
```

The wizard asks for the target, authentication, polling intervals and optional notifications. Review the settings before saving them. See [Setup & First Run](setup-and-first-run.md) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](installation.md).

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

## Common Commands

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](usage.md#command-format) for manual-script equivalents.

Replace the target placeholders with a PlayStation Network online ID. Monitoring requires the [PSN NPSSO code](setup-and-first-run.md#psn-npsso-code) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `psn_monitor --setup` |
| Start monitoring with saved credentials | `psn_monitor <psn_user_id>` |
| Check setup before monitoring | `psn_monitor --doctor <psn_user_id>` |
| Enter or replace credentials through hidden prompts | `psn_monitor --set-npsso` |
| Use a specific configuration and secrets file | `psn_monitor --config-file psn_monitor.conf --env-file .env <psn_user_id>` |
| Show profile details once | `psn_monitor <psn_user_id> -i` |
| List every supported command-line option | `psn_monitor --help` |

The monitored account must expose the activity described in [User Privacy Settings](setup-and-first-run.md#user-privacy-settings).

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](usage.md). If a run fails, start with [Doctor Preflight](troubleshooting.md#doctor-preflight).

## Documentation

* [Installation](installation.md) - Python setup, package or manual install and upgrades
* [Setup & First Run](setup-and-first-run.md) - credentials, target selection and the setup wizard
* [Configuration](configuration.md) - settings, notifications and secret storage
* [Usage](usage.md) - monitoring, output and command options
* [Troubleshooting](troubleshooting.md) - Doctor checks and recovery steps
* [Testing](testing.md) - automated checks and documentation builds
* [About](about.md) - contributing, security, licensing and support
