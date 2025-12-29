# psn_monitor

psn_monitor is a tool for real-time monitoring of **Sony PlayStation (PSN) players' activities**.

<a id="features"></a>
## Features

- **Real-time tracking** of PlayStation users' gaming activity (including detection when a user gets online/offline or plays games)
- **Basic statistics for user activity** (duration in different states, time spent playing a game, overall time and number of games played in a session etc.)
- **Detailed user information** display mode providing comprehensive PlayStation profile insights, including **PlayStation/PSN IDs**, **online status** and **availability to play**, **platform information**, **PS+ subscription status**, **verification status**, **about me section**, **languages**, **friendship relation** and **mutual friends count**, **profile URL**, **recently played games** with **last played date** and **total play time**, and optionally **trophy summary** and **last earned trophies**
- **Email notifications** for various events (player gets online/offline, starts/finishes/changes a game, errors)
- **Saving all user activities** with timestamps to a **CSV file**
- **Status persistence** - automatically saves last status to JSON file to resume monitoring after restart
- **Smart session continuity** - handles short offline interruptions and preserves session statistics
- **Flexible configuration** - support for config files, dotenv files, environment variables and command-line arguments
- Possibility to **control the running copy** of the script via signals
- **Functional, procedural Python** (minimal OOP)

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor.png" alt="psn_monitor_screenshot" width="90%"/>
</p>

<a id="table-of-contents"></a>
## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
   * [Install from PyPI](#install-from-pypi)
   * [Manual Installation](#manual-installation)
   * [Upgrading](#upgrading)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
   * [Configuration File](#configuration-file)
   * [PSN NPSSO Code](#psn-npsso-code)
   * [User Privacy Settings](#user-privacy-settings)
   * [Time Zone](#time-zone)
   * [SMTP Settings](#smtp-settings)
   * [Storing Secrets](#storing-secrets)
5. [Usage](#usage)
   * [User Information Display Mode](#user-information-display-mode)
   * [Monitoring Mode](#monitoring-mode)
   * [Email Notifications](#email-notifications)
   * [CSV Export](#csv-export)
   * [Check Intervals](#check-intervals)
   * [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix)
   * [Coloring Log Output with GRC](#coloring-log-output-with-grc)
6. [Change Log](#change-log)
7. [License](#license)

<a id="requirements"></a>
## Requirements

* Python 3.10 or higher
* Libraries: [PSNAWP](https://github.com/isFakeAccount/psnawp), `requests`, `python-dateutil`, `pytz`, `tzlocal`, `python-dotenv`

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia, Tahoe
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm, Trixie), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="installation"></a>
## Installation

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install psn_monitor
```

<a id="manual-installation"></a>
### Manual Installation

Download the *[psn_monitor.py](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/psn_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install PSNAWP requests python-dateutil pytz tzlocal python-dotenv
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

<a id="upgrading"></a>
### Upgrading

To upgrade to the latest version when installed from PyPI:

```sh
pip install psn_monitor -U
```

If you installed manually, download the newest *[psn_monitor.py](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/psn_monitor.py)* file to replace your existing installation.

<a id="quick-start"></a>
## Quick Start

- Grab your [PSN npsso code](#psn-npsso-code) and track the `psn_user_id` gaming activities:

```sh
psn_monitor <psn_user_id> -n "your_psn_npsso_code"
```

Or if you installed [manually](#manual-installation):

```sh
python3 psn_monitor.py <psn_user_id> -n "your_psn_npsso_code"
```

To get the list of all supported command-line arguments / flags:

```sh
psn_monitor --help
```

<a id="configuration"></a>
## Configuration

<a id="configuration-file"></a>
### Configuration File

Most settings can be configured via command-line arguments.

If you want to have it stored persistently, generate a default config template and save it to a file named `psn_monitor.conf`:

```sh
psn_monitor --generate-config > psn_monitor.conf

```

Edit the `psn_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

<a id="psn-npsso-code"></a>
### PSN NPSSO Code

Log in to your [My PlayStation](https://my.playstation.com/) account.

In another tab, go to: [https://ca.account.sony.com/api/v1/ssocookie](https://ca.account.sony.com/api/v1/ssocookie)

Copy the value of `npsso` code.

Provide the `PSN_NPSSO` secret using one of the following methods:
 - Pass it at runtime with `-n` / `--npsso-key`
 - Set it as an [environment variable](#storing-secrets) (e.g. `export PSN_NPSSO=...`)
 - Add it to [.env file](#storing-secrets) (`PSN_NPSSO=...`) for persistent use

Fallback:
 - Hard-code it in the code or config file

Tokens expire after 2 months. The tool alerts on expiration.

If you store the `PSN_NPSSO` in a dotenv file you can update its value and send a `SIGHUP` signal to the process to reload the file with the new `npsso` value without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix).

<a id="user-privacy-settings"></a>
### User Privacy Settings

In order to monitor PlayStation user activity, proper privacy settings need to be enabled on the monitored user account.

The user should go to [PlayStation account management](https://www.playstation.com/acct/management).

The value in **Privacy Settings → Personal Info | Messaging → Online Status and Now Playing** should be set set to **Friends only** or **Anyone**.

<a id="time-zone"></a>
### Time Zone

By default, time zone is auto-detected using `tzlocal`. You can set it manually in `psn_monitor.conf`:

```ini
LOCAL_TIMEZONE='Europe/Warsaw'
```

You can get the list of all time zones supported by pytz like this:

```sh
python3 -c "import pytz; print('\n'.join(pytz.all_timezones))"
```

<a id="smtp-settings"></a>
### SMTP Settings

If you want to use email notifications functionality, configure SMTP settings in the `psn_monitor.conf` file.

Verify your SMTP settings by using `--send-test-email` flag (the tool will try to send a test email notification):

```sh
psn_monitor --send-test-email
```

<a id="storing-secrets"></a>
### Storing Secrets

It is recommended to store secrets like `PSN_NPSSO` or `SMTP_PASSWORD` as either an environment variable or in a dotenv file.

Set environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

```sh
export PSN_NPSSO="your_psn_npsso_code"
export SMTP_PASSWORD="your_smtp_password"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

Alternatively store them persistently in a dotenv file (recommended):

```ini
PSN_NPSSO="your_psn_npsso_code"
SMTP_PASSWORD="your_smtp_password"
```

By default the tool will auto-search for dotenv file named `.env` in current directory and then upward from it.

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
psn_monitor <psn_user_id> --env-file /path/.env-psn_monitor
```

 You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
psn_monitor <psn_user_id> --env-file none
```

As a fallback, you can also store secrets in the configuration file or source code.

<a id="usage"></a>
## Usage

<a id="user-information-display-mode"></a>
### User Information Display Mode

The tool provides a detailed user information display mode that shows comprehensive PlayStation profile insights. This mode displays information once and then exits (it does not run continuous monitoring).

To get detailed user information for PlayStation (PSN) user's id (`psn_user_id` in the example below), use the `-i` or `--info` flag:

```sh
psn_monitor <psn_user_id> -i
```

If you have not set `PSN_NPSSO` secret, you can use `-n` flag:

```sh
psn_monitor <psn_user_id> -i -n "your_psn_npsso_code"
```

This displays:
- PlayStation/PSN IDs
- Online status and availability to play
- Platform information
- PS+ subscription status
- Verification status
- About me section
- Languages
- Friendship relation and mutual friends count
- Profile URL
- Recently played games with last played date and total play time

To also display trophy summary and list of most recently earned trophies, add the `--trophies` flag:

```sh
psn_monitor <psn_user_id> -i --trophies
```

To disable fetching the recently played games list (faster execution), use the `--no-recent-games` flag:

```sh
psn_monitor <psn_user_id> -i --no-recent-games
```

You can combine both flags:

```sh
psn_monitor <psn_user_id> -i --trophies --no-recent-games
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor_info.png" alt="psn_monitor_info" width="90%"/>
</p>

<a id="monitoring-mode"></a>
### Monitoring Mode

To monitor specific user activity, just type the PlayStation (PSN) user's id (`psn_user_id` in the example below):

```sh
psn_monitor <psn_user_id>
```

If you have not set `PSN_NPSSO` secret, you can use `-n` flag:

```sh
psn_monitor <psn_user_id> -n "your_psn_npsso_code"
```

By default, the tool looks for a configuration file named `psn_monitor.conf` in:
 - current directory
 - home directory (`~`)
 - script directory

 If you generated a configuration file as described in [Configuration](#configuration), but saved it under a different name or in a different directory, you can specify its location using the `--config-file` flag:


```sh
psn_monitor <psn_user_id> --config-file /path/psn_monitor_new.conf
```

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple PSN players by running multiple instances of the script.

The tool automatically saves its output to `psn_monitor_<psn_user_id>.log` file. It can be changed in the settings via `PSN_LOGFILE` configuration option or disabled completely via `DISABLE_LOGGING` / `-d` flag.

The tool also saves the timestamp and last status (after every change) to `psn_<psn_user_id>_last_status.json` file, so the last status is available after the restart of the tool.

<a id="email-notifications"></a>
### Email Notifications

To enable email notifications when a user gets online or offline:
- set `ACTIVE_INACTIVE_NOTIFICATION` to `True`
- or use the `-a` flag

```sh
psn_monitor <psn_user_id> -a
```

To be informed when a user starts, stops or changes the played game:
- set `GAME_CHANGE_NOTIFICATION` to `True`
- or use the `-g` flag

```sh
psn_monitor <psn_user_id> -g
```

To disable sending an email on errors (enabled by default):
- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
psn_monitor <psn_user_id> -e
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor_email_notifications.png" alt="psn_monitor_email_notifications" width="80%"/>
</p>

<a id="csv-export"></a>
### CSV Export

If you want to save all reported activities of the PSN user to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
psn_monitor <psn_user_id> -b psn_user_id.csv
```

The file will be automatically created if it does not exist.

<a id="check-intervals"></a>
### Check Intervals

If you want to customize polling intervals, use `-k` and `-c` flags (or corresponding configuration options):

```sh
psn_monitor <psn_user_id> -k 30 -c 120
```

* `PSN_ACTIVE_CHECK_INTERVAL`, `-k`: check interval when the user is online (seconds)
* `PSN_CHECK_INTERVAL`, `-c`: check interval when the user is offline (seconds)

<a id="signal-controls-macoslinuxunix"></a>
### Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets online or offline (-a) |
| USR2 | Toggle email notifications when user starts/stops/changes the game (-g) |
| TRAP | Increase the check timer for player activity when user is online (by 30 seconds) |
| ABRT | Decrease check timer for player activity when user is online (by 30 seconds) |
| HUP | Reload secrets from .env file |

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "psn_monitor <psn_user_id>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
### Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to color logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using `grc` tool.

Example:

```sh
grc tail -F -n 100 psn_monitor_<psn_user_id>.log
```

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/psn_monitor/blob/main/RELEASE_NOTES.md) for details.

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/psn_monitor/blob/main/LICENSE).
