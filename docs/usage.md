# Usage

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

Set `TRUNCATE_CHARS` or use the `--truncate` flag to cut each screen line to a maximum width, which stops long game titles from wrapping. Use `999` to auto-detect the terminal width. The log file always keeps the full line, so the setting is ignored when logging is disabled with `-d`. Truncation needs the optional `wcwidth` library to measure display width. If it is missing, the tool says so at startup and leaves lines untouched.

Names that come from PlayStation Network, such as game titles and profile text, can contain terminal control sequences. They are removed before the text reaches the screen, the log file, the CSV file or an email, so a crafted name cannot clear your screen or overwrite a line that was already printed. Error messages are also checked for your secrets before they are shown or logged.

The tool saves the timestamp and last status after every change, so the last status is available after a restart. Set `PSN_STATUS_FILE` or use the `--status-file` flag to keep it somewhere else:

```sh
psn_monitor <psn_user_id> --status-file ~/psn/last_status.json
```

The status file is written through a temporary file in the same directory, so an interrupted run cannot leave a half-written file behind.

## Startup Summary

Monitoring mode prints the settings that are actually in effect before the first check:

```
* Target:                       misiektoja
* Polling intervals:            [offline: 3 minutes] [online: 1 minute]
* Notifications (email):        On (status changes, game changes, errors)
* Notifications (webhook):      On (status changes, errors)
* Output:                       psn_monitor_misiektoja.log
* Config:                       psn_monitor.conf
* Dotenv:                       .env
* More details:                 use --verbose or --debug
```

Optional features appear once you switch them on, and `TLS verification` appears here whenever certificate checking is off.

`--verbose` or `--debug` replaces this with the complete list, in the order it prints: the tolerated offline gap, the mail server and the masked recipient, the webhook service alerts go to, whether the delivery confirmations are printed, the log file, the liveness interval, the CSV file, the status file, the truncation width, the process id, the Python version, the operating system, the resolved time zone, the install method, which secrets came from the dotenv file, the environment, the configuration file or the command line, whether certificate checking is on, how log separators are written, whether colour is actually in use and the two flags themselves.

The sibling monitors print the same rows in the same order, so a setting sits in the same place whichever of them you are reading.

The log file always receives the complete list, whichever view the terminal was shown, so a log attached to a bug report carries every effective setting.

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

An error alert goes out once the same failure has lasted **5 minutes**, so a short outage or one lost request reaches nobody, while a failure that cannot clear on its own, such as an expired npsso code, is alerted at once. Each kind of failure alerts once per channel, a channel that could not deliver is tried again on the next failing check and a run that recovered alerts again when it fails later. The same rule governs the webhook error alert.

Make sure you defined your [SMTP settings](configuration.md#smtp-settings) first.

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor_email_notifications.png" alt="psn_monitor_email_notifications" width="80%"/>
</p>

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

## CSV Export

If you want to save all reported activities of the PSN user to a CSV file, set `CSV_FILE` or use the `-b` flag:

```sh
psn_monitor <psn_user_id> -b psn_user_id.csv
```

The file is created automatically if it does not exist.

## Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers which allow changing its behavior without restarting it with new configuration options or flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets online or offline (-a) |
| USR2 | Toggle email notifications when user starts/stops/changes the game (-g) |
| TRAP | Increase the check timer for player activity when user is online (by 30 seconds) |
| ABRT | Decrease check timer for player activity when user is online (by 30 seconds) |
| HUP | Reload secrets from .env file |

Send signals with `kill` or `pkill`, for example:

```sh
pkill -USR1 -f "psn_monitor <psn_user_id>"
```

As Windows supports a limited number of signals, this functionality is available only on Linux, Unix and macOS.

## Terminal Colours

Terminal output is coloured by default. Colour switches itself off when the output is not an interactive terminal, when `TERM` is unset or `dumb`, when `NO_COLOR` is set and when the output is piped or redirected, so a log file or a piped run never contains escape sequences.

The `--help` screen is coloured too. Group headings, option names, the values those options take, the example commands and the comments above them each get their own colour, so the screen can be scanned instead of read.

Turn it off for one run:

```sh
psn_monitor <psn_user_id> --no-color
```

Turn it off permanently in the config file:

```python
COLORED_OUTPUT = False
```

On Windows, install [colorama](https://pypi.org/project/colorama/) for colours in the older Command Prompt. Windows Terminal needs nothing extra.

Each part of the output has a logical name, and `COLOR_THEME` in the config file overrides only the names it lists. Combine attributes with spaces or `+`, for example `"bright_cyan bold"` or `"red underline"`. Valid colours are `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` and their `bright_` variants, plus the `bold`, `dim`, `underline` and `blink` attributes. An empty string leaves that part uncoloured.

Generated configuration files ship this block commented out, so the built-in defaults apply and a later change to them reaches you. A configuration file written by an earlier version sets every colour explicitly and therefore keeps the old ones: delete its `COLOR_THEME` block to follow the current defaults, or edit the values you want to keep. Such a file still loads unchanged.

```python
COLOR_THEME = {
    "game": "bright_magenta bold",
    "duration": "cyan",
}
```

| Theme key | Default | What it colours |
| --- | --- | --- |
| `header` | `bright_cyan` | Report and wizard headings, and the tool name in the startup line |
| `section` | `bright_white` | Section names and every command the tool tells you to run |
| `username` | `bright_cyan underline` | The monitored PlayStation ID, the detected install method and wizard menu numbers |
| `id` | `bright_magenta` | The numeric PSN account ID |
| `status_active` | `green` | An online or available presence, and a game that just started |
| `status_inactive` | `red` | A standby or unavailable presence, and a game that just stopped |
| `status_offline` | `red` | An offline presence |
| `status_other` | `white` | A presence value the tool does not recognise |
| `game` | `bright_yellow` | Game titles |
| `platform` | `blue` | Console names and the platform tag beside a game |
| `trophy` | `bright_green` | Trophy level, trophy counts, trophy types and trophy names |
| `duration` | `green` | Time spans such as `3 hours, 21 minutes` |
| `status_change` | `yellow` | The `changed status` and `changed game` part of a change report |
| `timestamp_label` | *(empty)* | The `Timestamp:` label, left uncoloured by default |
| `timestamp_value` | `cyan` | The timestamp itself |
| `info` | `cyan` | `To fix:` lines, notes, prompts and default markers |
| `warning` | `yellow` | The opening `Warning:` word of a `* Warning:` line and `[WARN]` rows. The rest of the line keeps the colours of the values in it |
| `error` | `red` | `* Error:` lines and `[FAIL]` rows |
| `signal` | `yellow` | The name of the signal in a `* Signal ... received` line |
| `email` | `bright_cyan` | Lines reporting an email being sent |
| `webhook` | `bright_blue` | Lines reporting a webhook being sent |
| `date` | `magenta` | Single dates and times |
| `date_range` | `magenta` | Date and time ranges |
| `boolean_true` | `green` | `True`, `Enabled`, `On` and `[PASS]` rows |
| `boolean_false` | `red` | `False`, `Disabled` and `Off` |
| `link` | `blue underline` | URLs |
| `help_heading` | `bright_cyan bold` | The `--help` group headings and example task names |
| `help_usage` | `bright_white bold` | The `usage:` label |
| `help_option` | `bright_green` | Option names such as `--doctor` |
| `help_metavar` | `yellow` | The value each option takes, such as a path or a number of seconds |
| `help_placeholder` | `bright_magenta` | Values to replace in the help examples |
| `help_command` | `bright_white` | The commands in the help examples |
| `help_comment` | `bright_black` | The `#` comment above each help example |
| `help_default` | `bright_black` | The `(default: ...)` notes |

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
