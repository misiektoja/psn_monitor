# Usage

<a id="command-format-by-installation-method"></a>
## Command Format by Installation Method

Examples use the PyPI command. For a downloaded script, run commands from the directory containing `psn_monitor.py` and keep the same arguments:

| Installation | Command |
| --- | --- |
| PyPI or pipx | `psn_monitor [OPTIONS]` |
| Manual script on macOS or Linux | `python3 psn_monitor.py [OPTIONS]` |
| Manual script on Windows | `python psn_monitor.py [OPTIONS]` |

For example, `psn_monitor --setup` becomes `python3 psn_monitor.py --setup` on macOS or Linux. Use `python` on Windows. Replace placeholders such as `<psn_user_id>` with a PlayStation Network online ID.

Activate the tool's virtual environment before running these commands. For a downloaded script, run them from the directory containing `psn_monitor.py`.

For first-time configuration, follow [Setup & First Run](setup-and-first-run.md). Use [Doctor Preflight](troubleshooting.md#doctor-preflight) to check a setup before monitoring.

<a id="user-information-display-mode"></a>
## User Information Display Mode

The tool provides a detailed user information display mode that shows comprehensive PlayStation profile insights. This mode displays information once and then exits. It does not run continuous monitoring.

To get detailed user information for a PlayStation (PSN) user's id, use the `-i` or `--info` flag:

```sh
psn_monitor <psn_user_id> -i
```

If you have not set the `PSN_NPSSO` secret, you can use the `-n` flag:

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

To also display a trophy summary and the list of most recently earned trophies, add the `--trophies` flag:

```sh
psn_monitor <psn_user_id> -i --trophies
```

To disable fetching the recently played games list, which is faster, use the `--no-recent-games` flag:

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
## Monitoring Mode

To monitor a specific user's activity, just type the PlayStation (PSN) user's id:

```sh
psn_monitor <psn_user_id>
```

If you have not set the `PSN_NPSSO` secret, you can use the `-n` flag:

```sh
psn_monitor <psn_user_id> -n "your_psn_npsso_code"
```

The tool runs until interrupted with `Ctrl+C`. Use `tmux` or `screen` for persistence.

You can monitor multiple PSN players by running multiple instances of the tool.

Output is saved to `psn_monitor_<psn_user_id>.log`. This can be changed with the `PSN_LOGFILE` configuration option or disabled completely with `DISABLE_LOGGING` or the `-d` flag.

Set `ASCII_LOG_SEPARATORS` to `"Auto"`, the default, to use ASCII separator-only lines on Windows, `"On"` to use them on every operating system or `"Off"` to preserve Unicode separators in logs everywhere. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

Set `TRUNCATE_CHARS` or use the `--truncate` flag to cut each screen line to a maximum width, which stops long game titles from wrapping. Use `999` to auto-detect the terminal width. The log file always keeps the full line, so the setting is ignored when logging is disabled with `-d`. Install the optional `wcwidth` library for correct widths with wide characters. If it is missing, the tool says so at startup and counts every character as one column.

Names that come from PlayStation Network, such as game titles and profile text, can contain terminal control sequences. They are removed before the text reaches the screen, the log file, the CSV file or an email, so a crafted name cannot clear your screen or overwrite a line that was already printed. Error messages are also checked for your secrets before they are shown or logged.

The tool saves the timestamp and last status after every change, so the last status is available after a restart. Set `PSN_STATUS_FILE` or use the `--status-file` flag to keep it somewhere else:

```sh
psn_monitor <psn_user_id> --status-file ~/psn/last_status.json
```

Interrupted writes leave the previous status file intact. If a saved timestamp is more than five minutes ahead of the machine clock, monitoring warns and starts timing that status again.

<a id="terminal-output"></a>
## Terminal Output

Use `--help` for examples grouped by task and matched to your installation.

Monitoring mode prints the settings that are actually in effect before the first check.

Optional features appear once you switch them on.

Use `--verbose` or `--debug` for the full startup summary, including output paths, notification settings, secret sources and runtime information.

Use `--truncate N` or `TRUNCATE_CHARS` to limit screen line width. Set it to `999` to detect the terminal width automatically. Truncation does not change log files and is ignored when logging is disabled with `-d`.

The tool clears the terminal when monitoring starts. Set `CLEAR_SCREEN` to `False` to keep whatever is already on the screen.

The screen is never cleared when output is redirected to a file or a pipe, in debug mode, or for a command that prints a result and exits, such as `--doctor`, `--help` and the test senders.

Two settings add detail to what a run prints. `VERBOSE_MODE` adds the decisions the run made and `DEBUG_MODE` adds timestamped technical traces. Both are off by default, both are independent of each other and both have a flag that wins over the file, `--verbose` and `--debug`. `DELIVERY_CONFIRMATIONS` is on by default and controls whether verbose mode confirms each delivered email and webhook alert. See [Verbose and Debug Output](troubleshooting.md#verbose-and-debug-output).

<a id="coloured-terminal-output"></a>
### Coloured Terminal Output

PSN Monitor colours live terminal output and help by default. Saved log files stay plain text.

Turn colour off for one run with `--no-color` or permanently with `COLORED_OUTPUT = False`. Colour is also disabled for redirected output, `NO_COLOR` or an unsupported terminal. See [Terminal Colours](configuration.md#terminal-colours) for details and Windows support.

Override individual colours with `COLOR_THEME`. It is merged over the built-in theme, so you only name the parts you want to change:

```ini
COLOR_THEME = { "game": "bright_magenta bold", "username": "green" }
```

See [Terminal Colours](configuration.md#terminal-colours) for every theme key and the accepted colour and style names.

<a id="email-notifications"></a>
## Email Notifications

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

To disable sending an email on errors, which is enabled by default:

- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
psn_monitor <psn_user_id> -e
```

Email and webhook error alerts are sent after **5 minutes** of a continuing failure. Problems that need your action, such as an expired npsso code, alert immediately. Each kind of failure alerts once per channel. Failed deliveries are retried after 5 minutes, with increasing waits up to an hour. Alerts can fire again after monitoring recovers.

Make sure you defined your [SMTP settings](configuration.md#smtp-settings) first.

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor_email_notifications.png" alt="psn_monitor_email_notifications" width="80%"/>
</p>

<a id="webhook-notifications"></a>
## Webhook Notifications

Once the [webhook settings](configuration.md#webhook-settings) name a destination, each event type is switched on separately, the same way email alerts are: the user getting online or offline, a game starting, changing or stopping, and monitoring errors.

The same settings have command-line equivalents for one run. Naming any single alert also switches the channel on:

```sh
psn_monitor <psn_user_id> --webhook-game-change
psn_monitor <psn_user_id> --webhook --no-webhook-error-notify
psn_monitor <psn_user_id> --webhook-url <url>
```

`--webhook-url` leaves the private URL in your shell history, so prefer `--set-webhook-url` for anything permanent.

Verify the destination without starting monitoring:

```sh
psn_monitor --send-test-webhook
```

A failed delivery is retried once, a rate limit waits the delay the service asked for and bounds it, and redirects are never followed. When both channels are enabled, each is delivered independently: an alert that reached Discord is not sent again just because the email failed.

<a id="csv-export"></a>
## CSV Export

If you want to save all reported activities of the PSN user to a CSV file, set `CSV_FILE` or use the `-b` flag:

```sh
psn_monitor <psn_user_id> -b psn_user_id.csv
```

The file is created automatically if it does not exist.

<a id="check-intervals"></a>
## Check Intervals

If you want to customize the polling intervals, use the `-k` and `-c` flags (or the corresponding configuration options):

```sh
psn_monitor <psn_user_id> -k 30 -c 120
```

* `PSN_ACTIVE_CHECK_INTERVAL`, `-k`: check interval when the user is online (seconds)
* `PSN_CHECK_INTERVAL`, `-c`: check interval when the user is offline (seconds)

An active interval below 30 seconds invites the PlayStation Network rate limiter, which stops the tool seeing anything. `--doctor` warns when the configured interval is that short.

<a id="liveness-reminder"></a>
### Liveness Reminder

While nothing changes, the tool prints one reminder that it is still running:

```
* Monitoring healthy for <psn_user_id>. The user is online with no activity change since the last check
Liveness check, timestamp:	Mon 08 Sep 2026, 09:15:05
```

The reminder is timed in seconds, so it arrives at the same rate whichever check interval is in use. Set `LIVENESS_CHECK_INTERVAL` to change it (default: 86400, i.e. 24 hours), or to 0 to switch it off.

Anything the tool prints about the target restarts the countdown, so a busy run stays quiet.

<a id="signal-controls-macoslinuxunix"></a>
## Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets online or offline (-a) |
| USR2 | Toggle email notifications when user starts/stops/changes the game (-g) |
| TRAP | Increase the check timer for player activity when user is online (by 30 seconds) |
| ABRT | Decrease check timer for player activity when user is online (by 30 seconds) |
| HUP | Reload secrets from .env file |

`SIGHUP` keeps command-line credentials and nonempty environment values exported before startup. Change those values and restart to replace them.

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "psn_monitor <psn_user_id>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
## Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to color logs.

The bundled recipe follows the same colors as the live output. It also covers the other monitors in the family, so one copy in `~/.grc/` colors every tool's logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using the `grc` tool.

Example:

```sh
grc tail -F -n 100 psn_monitor_<psn_user_id>.log
```
