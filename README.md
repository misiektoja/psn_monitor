# psn_monitor

<p align="left">
  <img src="https://img.shields.io/github/v/release/misiektoja/psn_monitor?style=flat-square&color=blue" alt="GitHub Release" />
  <img src="https://img.shields.io/pypi/v/psn_monitor?style=flat-square&color=teal" alt="PyPI Version" />
  <img src="https://img.shields.io/github/stars/misiektoja/psn_monitor?style=flat-square&color=magenta" alt="GitHub Stars" />
  <img src="https://img.shields.io/badge/python-3.10+-blueviolet?style=flat-square" alt="Python Versions" />
  <img src="https://img.shields.io/github/license/misiektoja/psn_monitor?style=flat-square&color=blue" alt="License" />
  <img src="https://img.shields.io/github/last-commit/misiektoja/psn_monitor?style=flat-square&color=green" alt="Last Commit" />
  <img src="https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square" alt="Maintenance" />
</p>

Powerful tool for real-time monitoring of **Sony PlayStation (PSN) players' activities**.

### 🚀 Quick Install
```sh
pip install psn_monitor
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor.png" alt="psn_monitor_screenshot" width="90%"/>
</p>

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
   * [Startup Summary](#startup-summary)
   * [Preflight Checks](#doctor-preflight)
   * [Error Messages and Recovery](#error-messages-and-recovery)
   * [Verbose and Debug Output](#verbose-and-debug-output)
   * [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix)
   * [Coloring Log Output with GRC](#coloring-log-output-with-grc)
6. [Change Log](#change-log)
7. [Contributing](#contributing)
8. [Security](#security)
9. [License](#license)
10. [Support](#support)

<a id="requirements"></a>
## Requirements

* Python 3.10 or higher
* Libraries: [PSNAWP](https://codeberg.org/YoshikageKira/psnawp), `requests`, `python-dateutil`, `pytz`, `tzlocal`, `python-dotenv`, `wcwidth`

Tested on:

* **macOS**: Tahoe, Sequoia, Sonoma, Ventura
* **Linux**: Raspberry Pi OS (Trixie, Bookworm, Bullseye), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2026/2025/2024
* **Windows**: 11, 10

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
pip install PSNAWP requests python-dateutil pytz tzlocal python-dotenv wcwidth
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

Run it without arguments to see the few commands worth starting with, including how to check your setup before monitoring.

<a id="configuration"></a>
## Configuration

<a id="configuration-file"></a>
### Configuration File

Most settings can be configured via command-line arguments.

If you want to have it stored persistently, generate a default config template and save it to a file named `psn_monitor.conf`:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
psn_monitor --generate-config > psn_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
psn_monitor --generate-config psn_monitor.conf
```

> **IMPORTANT**: In Windows PowerShell, do not use `>` for this command. Some PowerShell versions write redirected text as UTF-16, which makes PSN Monitor report a "null bytes" error. Pass the filename to `--generate-config` so PSN Monitor writes a UTF-8 file itself.

When you include the filename, PSN Monitor writes the template directly as UTF-8. This avoids PowerShell changing the file encoding during redirection.

Writing over an existing file asks first and keeps a timestamped `psn_monitor.conf.<timestamp>.bak` copy next to it. Outside an interactive terminal the write is refused instead, and `--force` replaces the file after taking the same backup:

```sh
psn_monitor --generate-config psn_monitor.conf --force
```

> **NOTE**: The guard only covers the filename form. Shell redirection with `>` empties the file before PSN Monitor starts, so nothing can protect it there.

Edit the `psn_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

Set `PSN_USER_ID` to save the account you usually watch. A PSN ID passed on the command line always wins over the saved one, and with a saved value you can start monitoring with no arguments at all:

```sh
psn_monitor
```

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

The tool can write them for you, so a secret never appears in your shell history or in `ps` output:

```sh
psn_monitor --set-npsso
psn_monitor --set-smtp-password
```

Both ask for the value with the input hidden, check it against the live service before saving anything, then write it to your dotenv file with permissions that allow only you to read it. `--set-npsso` signs in to PlayStation Network and reports which account the code belongs to. `--set-smtp-password` signs in to your mail server without sending anything. If the check fails, nothing is written, so a working setup is never replaced by a broken one. Replacing a value that is already saved is confirmed first, and an existing `export PSN_NPSSO=...` line is rewritten in place rather than having a second assignment appended below it. Both commands need an interactive terminal.

Use `--env-file` to choose which file they write to.

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

Set `ASCII_LOG_SEPARATORS` to `"Auto"` (default) to use ASCII separator-only lines on Windows, `"On"` to use them on every operating system or `"Off"` to preserve Unicode separators in logs everywhere. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

Set `TRUNCATE_CHARS` or use the `--truncate` flag to cut each screen line to a maximum width, which stops long game titles from wrapping. Use `999` to auto-detect the terminal width. The log file always keeps the full line, so the setting is ignored when logging is disabled with `-d`. Truncation needs the optional `wcwidth` library to measure display width. If it is missing, the tool says so at startup and leaves lines untouched.

Names that come from PlayStation Network, such as game titles and profile text, can contain terminal control sequences. They are removed before the text reaches the screen, the log file, the CSV file or an email, so a crafted name cannot clear your screen or overwrite a line that was already printed. Error messages are also checked for your NPSSO code and SMTP password before they are shown or logged.

The tool also saves the timestamp and last status (after every change) to `psn_<psn_user_id>_last_status.json` file, so the last status is available after the restart of the tool. Set `PSN_STATUS_FILE` or use the `--status-file` flag to keep it somewhere else:

```sh
psn_monitor <psn_user_id> --status-file ~/psn/last_status.json
```

The status file is written through a temporary file in the same directory, so an interrupted run cannot leave a half-written file behind.

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

<a id="startup-summary"></a>
### Startup Summary

Monitoring mode prints the settings that are actually in effect before the first check:

```
* Polling intervals:            [offline: 3 minutes] [online: 1 minute]
* Notifications (email):        On (status changes, game changes, errors)
* Output:                       psn_monitor_misiektoja.log
* Config:                       psn_monitor.conf
* Dotenv:                       .env
* More details:                 use --verbose or --debug
```

`--verbose` or `--debug` replaces this with the complete list: the log file, the status file, the CSV file, the install method, which secrets came from the dotenv file and which from the environment, the resolved time zone, the liveness interval, the truncation width and the two flags themselves.

The log file always receives the complete list, whichever view the terminal was shown, so a log attached to a bug report carries every effective setting.

<a id="doctor-preflight"></a>
### Preflight Checks

`--doctor` checks a setup and prints one report instead of failing at the first problem:

```sh
psn_monitor <psn_user_id> --doctor
```

It writes no files, and it exits `1` if any check failed so you can run it from a script.

The report opens with the detected install method, then five sections, each row marked `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`:

* **Environment**: the Python version, the required libraries, and the optional ones with what stops working without each
* **Configuration**: the configuration and dotenv files in use, which secrets are loaded and where each came from, the time zone, the check intervals and the files the tool would write
* **Authentication**: whether PlayStation Network accepts your NPSSO code, and which account it signed in as
* **Target**: whether the monitored PlayStation ID exists and shares its presence with your account
* **Notifications**: whether email alerts can fire, and whether the SMTP settings they would use are valid

Rows that are not a pass carry the same `To fix:` and `Guide:` lines described in [Error Messages and Recovery](#error-messages-and-recovery). Secrets are reported by name and never by value.

If SMTP settings pass and you are on an interactive terminal, the doctor offers to send one real test email. It asks first and does nothing without a `y`.

<a id="error-messages-and-recovery"></a>
### Error Messages and Recovery

When something goes wrong, the tool reports what happened and what to do about it:

```
* Error: PlayStation Network did not accept the NPSSO code
To fix: Generate a fresh NPSSO code, then put it in PSN_NPSSO in your dotenv file or pass it directly: psn_monitor <psn_user_id> -n <npsso_code>
Guide: https://github.com/misiektoja/psn_monitor/blob/main/README.md#psn-npsso-code
```

Every failure is sorted into a category, so an expired NPSSO code, a hidden profile, a rate limit, an unreachable network and a local file descriptor limit each get their own instructions instead of one generic message. Problems the tool survives, such as a missing optional library, are reported as `* Warning:` and it keeps running.

Commands in the fix text match how you installed the tool: `psn_monitor ...` for a PyPI install and `python3 psn_monitor.py ...` for a downloaded script.

During a long outage the fix is printed once and each retry after that is a single line, until the failure changes or a check succeeds. The raw library error is not shown by default. Add `--debug` to print it as a `Technical detail:` line, with your NPSSO code and SMTP password redacted.

<a id="verbose-and-debug-output"></a>
### Verbose and Debug Output

Two flags make the tool explain what it is doing. They are independent, so you can use either or both:

```sh
psn_monitor <psn_user_id> --verbose --debug
```

* `VERBOSE_MODE`, `--verbose`: rare operational events, such as which configuration and dotenv files are in use, the resolved time zone, whether an email was actually delivered and when a run recovers after a series of failed checks
* `DEBUG_MODE`, `--debug`: technical diagnostics, such as every PSN API call, the classification and text of each failure, how long the tool will wait before the next check and why, every read and write of the status and CSV files and where each secret was resolved from

Debug lines are prefixed with `[DEBUG HH:MM:SS]`. Both modes redact your NPSSO code and SMTP password, and report secrets only as a length, never as a value.

Both flags take effect before the configuration file is read, so they still work when the problem you are chasing is the configuration file itself. A flag you type always wins over `VERBOSE_MODE` or `DEBUG_MODE` in the configuration file.

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

<a id="contributing"></a>
## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/psn_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/psn_monitor/blob/main/CODE_OF_CONDUCT.md).

<a id="security"></a>
## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/psn_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/psn_monitor/blob/main/SECURITY.md) covers the reporting process, the supported versions and the security posture of stored credentials and configuration loading.

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/psn_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/psn_monitor/blob/main/THIRD_PARTY_NOTICES.md).

<a id="support"></a>
## Support

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/psn_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
