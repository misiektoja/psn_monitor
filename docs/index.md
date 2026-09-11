# psn_monitor

Powerful tool for real-time monitoring of **Sony PlayStation (PSN) players' activities**.

<a id="-quick-install"></a>
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

- **Real-time tracking** of PlayStation users' gaming activity, including when a user gets online or offline and which games they play
- **Basic statistics for user activity**: duration in different states, time spent playing a game, overall time and number of games played in a session
- **Detailed user information** display mode covering PlayStation/PSN IDs, online status and availability to play, platform information, PS+ subscription status, verification status, about me section, languages, friendship relation and mutual friends count, profile URL, recently played games with last played date and total play time, and optionally a trophy summary and the last earned trophies
- **Email notifications** for various events: the user gets online or offline, starts, finishes or changes a game, and monitoring errors
- **Webhook notifications** delivered to **Discord** or **ntfy**, switched on per event independently of email
- **Guided setup** with `--setup`, and **preflight diagnostics** with `--doctor`
- **CSV export** of every reported activity, with **status persistence** across restarts
- **Smart session continuity**: short offline interruptions are handled and session statistics are preserved
- **Coloured terminal output** with a configurable theme, switched off automatically when the output is redirected
- **Flexible configuration** through config files, dotenv files, environment variables and command-line arguments
- **Control of the running copy** through signals
- **Functional, procedural Python** with minimal OOP

## Screenshots

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor.png" alt="psn_monitor_screenshot" width="90%"/>
</p>

<a id="common-commands"></a>
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
