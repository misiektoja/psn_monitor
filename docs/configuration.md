# Configuration

Examples on this page use the PyPI command `psn_monitor`. Manual script users should keep the shown options and use the matching prefix under [Command Format by Installation Method](usage.md#command-format-by-installation-method).

<a id="configuration-file"></a>
## Configuration File

You can pass most settings as command-line options or save them in a configuration file for later runs.

The easiest way to create this file is `psn_monitor --setup`.

To edit every available setting yourself, generate a default configuration file:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
psn_monitor --generate-config > psn_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
psn_monitor --generate-config psn_monitor.conf
```

> **Windows PowerShell:** Pass the filename directly to `--generate-config`. PowerShell redirection can write UTF-16, which the tool rejects with a "null bytes" error.

When the named file already exists, `--generate-config` asks before replacing it and keeps a timestamped `.bak` backup next to it. Add `--force` to replace it without the question.

The file contains a short explanation above each setting.

A configuration file is read as data, not executed. The tool accepts only `SETTING = value` lines where the name is one of the documented settings and the value is a plain literal such as a string, number, `True`, `False`, `None`, a list or a dictionary. Comments and blank lines are fine.

Imports, function calls, expressions and unknown settings are rejected with the setting and line number to correct.

If the same setting appears in more than one place, the item later in this list wins:

1. Built-in defaults
2. The discovered or explicitly selected configuration file
3. Values from the selected `.env` file
4. Secret environment variables
5. Command-line options

By default the tool looks for a configuration file named `psn_monitor.conf` in the current directory, the home directory (`~`) and the script directory. Use `--config-file` to name another location or `--config-file none` to disable automatic config discovery for one run.

<a id="monitored-target"></a>
## Monitored Target

The PSN online ID is a positional argument. It is required to start monitoring:

```sh
psn_monitor <psn_user_id>
```

Use the online ID, not the account e-mail address or the real name.

To stop repeating it, save it in the configuration file:

```ini
PSN_USER_ID = "psn_user_id"
```

Then `psn_monitor` alone starts monitoring that user. A positional argument still wins, so you can watch someone else for one run without editing the file:

```sh
psn_monitor other_psn_id
```

<a id="time-zone"></a>
## Time Zone

By default, the time zone is auto-detected using `tzlocal`. You can set it manually in `psn_monitor.conf`:

```ini
LOCAL_TIMEZONE='Europe/Warsaw'
```

You can get the list of all time zones supported by pytz like this:

```sh
python3 -c "import pytz; print('\n'.join(pytz.all_timezones))"
```

<a id="smtp-settings"></a>
## SMTP Settings

Email notifications need SMTP server details for the sending account. Add them to `psn_monitor.conf` or use the setup wizard. Setup checks the login without sending an email. To replace only the password, run `psn_monitor --set-smtp-password`. Password entry is hidden and preserves spaces.

If email alerts are selected but local SMTP settings are missing or invalid, the startup summary shows `Unavailable` with the reason. Automatic email sends are skipped silently until the settings are fixed. `Off` means no email alert types are selected.

Every alert is sent as both HTML and plain text in one message. Mail clients that render HTML show the PlayStation ID, the game, the status and the values that changed in bold. Clients that do not fall back to the plain text, which is unchanged.

Send one test message to verify the settings:

```sh
psn_monitor --send-test-email
```

<a id="webhook-settings"></a>
## Webhook Settings

Alerts can also be delivered to a **Discord** channel or an **ntfy** topic. The webhook channel is configured and switched on separately from email, so you can send game changes to Discord while email stays off or use both.

Save the destination privately, which never puts it in your shell history:

```sh
psn_monitor --set-webhook-url
```

Hidden URL entry recognizes Discord and ntfy URLs. A bare topic name is saved as an ntfy.sh URL. The service is detected from the URL at startup, so `WEBHOOK_PROVIDER` only needs setting for a self-hosted ntfy server. While `WEBHOOK_PROVIDER` is left at its default, that detection is silent and `--verbose` reports it. A warning appears only when your configuration file sets `WEBHOOK_PROVIDER` to a service the URL disagrees with.

The URL is checked for shape without contacting the service, because the only confirmation Discord or ntfy can give is a delivered notification. The command prints `--send-test-webhook` as the next step, which does deliver one.

Then switch the channel on and choose which events it sends:

```python
WEBHOOK_ENABLED = True
WEBHOOK_PROVIDER = "discord"                    # or "ntfy"
WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = True     # user gets online or offline
WEBHOOK_GAME_CHANGE_NOTIFICATION = True         # game starts, changes or stops
WEBHOOK_ERROR_NOTIFICATION = True               # monitoring failures and their recovery, enabled by default
```

If webhook alerts are selected but the URL, provider or other local settings are invalid, the startup summary shows `Unavailable` with the reason. Automatic webhook sends are skipped silently until the settings are fixed. `Off` means the master switch or all webhook alert types are off.

Which events actually fire and how a failed delivery is retried is covered in [Webhook Notifications](usage.md#webhook-notifications).

<a id="ntfy"></a>
### ntfy

For ntfy it is the complete topic URL, such as `https://ntfy.sh/psn-monitor-long-random-value` or just the topic name when it is hosted on ntfy.sh. Set the provider in `psn_monitor.conf` for a self-hosted ntfy server:

```ini
WEBHOOK_PROVIDER = "ntfy"
```

ntfy alerts are sent as a native message with the subject as the title, so no template is involved. Use `WEBHOOK_HEADERS` to add ntfy options such as priority or tags:

```python
WEBHOOK_HEADERS = {"Priority": "5", "Tags": "video_game"}
```

Topics on the public ntfy.sh service are public unless protected through an account reservation. Treat an unprotected topic name like a password. Use `NTFY_ACCESS_TOKEN` when the topic needs authentication:

```ini
NTFY_ACCESS_TOKEN="tk_your_ntfy_access_token"
```

PSN Monitor sends this value as `Authorization: Bearer <token>`. `NTFY_ACCESS_TOKEN` takes precedence over an `Authorization` entry in `WEBHOOK_HEADERS`. Header values support the same placeholders as `WEBHOOK_TEMPLATE` and apply to both Discord and ntfy.

<a id="discord"></a>
### Discord

If you are new to Discord, follow these steps to get your private webhook URL:

1. Open your PSN alerts server and choose the channel that should receive them.
2. Select **Edit Channel**, open **Integrations** then choose **Webhooks**.
3. Select **New Webhook**, choose a name if you want then select **Copy Webhook URL**.
4. Save it with `psn_monitor --set-webhook-url`.

Treat this link like a password because anyone who has it can post through it.

Keep the default provider in `psn_monitor.conf`:

```ini
WEBHOOK_PROVIDER = "discord"
```

Discord alerts are sent as an embed built from `WEBHOOK_TEMPLATE`. Mentions are always disabled, whatever the template says.

Discord alerts carry the same emphasis as the HTML email, since Discord renders markdown in an embed. Bold values stay bold and links stay clickable. Only Discord gets that wording: ntfy receives the plain body, because it would show the markers literally.

<a id="advanced-discord-format-customization"></a>
### Advanced Discord-format customization

`WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` override the webhook's own display name and picture for Discord-format payloads. Both are ignored by ntfy:

```ini
WEBHOOK_USERNAME = "PSN Monitor"
WEBHOOK_AVATAR_URL = "https://example.com/path/avatar.png"
```

`WEBHOOK_TEMPLATE` controls the Discord-format request body. It supports these placeholders:

- `{title}`
- `{description}`
- `{version}`
- `{image_url}`
- `{fields}` and `{fields_str}`
- `{color}`
- `{timestamp}`
- `{username}`
- `{avatar_url}`

Discord templates must produce a JSON object. Use a dictionary or a JSON string encoding an object, including legacy strings with doubled object braces. Lists, non-JSON strings and unsupported placeholders are rejected before delivery. Alert text is kept literal and all payloads replace `allowed_mentions` with `{"parse": []}` so alert text cannot trigger Discord mentions. Reloaded settings apply to the next delivery.

`WEBHOOK_TRANSFORMS` applies string methods to shared placeholder values before the template and headers are rendered:

```ini
WEBHOOK_TRANSFORMS = [
    ("title", "upper"),
    ("description", "replace", "**", ""),
    ("description", "strip"),
]
```

The tuple format is `(field_to_target, method_name, *optional_arguments)`. Invalid templates, avatar URLs, transforms or formatted headers fail before a request is attempted. `WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` apply only to the Discord request format. ntfy continues to use its native publish API while transformations and header placeholders use the same shared title and description values.

<a id="terminal-colours"></a>
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

The built-in colours apply unless you set `COLOR_THEME`. Older configurations may set every colour explicitly. Remove that block to use current defaults or edit individual values to keep a custom theme.

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

<a id="storing-secrets"></a>
## Storing Secrets

It is recommended to store secrets like `PSN_NPSSO`, `SMTP_PASSWORD`, `WEBHOOK_URL` or `NTFY_ACCESS_TOKEN` as either an environment variable or in a dotenv file.

The tool can write them for you, so a secret never appears in your shell history or in `ps` output:

```sh
psn_monitor --set-npsso
psn_monitor --set-smtp-password
psn_monitor --set-webhook-url
```

These commands need an interactive terminal and keep input hidden. `--set-npsso` signs in to PlayStation Network and reports the account. `--set-smtp-password` checks mail sign-in without sending a message. `--set-webhook-url` checks the URL without contacting the service. A failed check leaves the saved value unchanged. Replacements require confirmation and the dotenv file is saved with owner-only permissions.

Use `--env-file` to choose which file they write to.

Set environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

```sh
export PSN_NPSSO="your_psn_npsso_code"
export SMTP_PASSWORD="your_smtp_password"
export WEBHOOK_URL="your_webhook_url"
export NTFY_ACCESS_TOKEN="your_ntfy_access_token"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

Alternatively store them persistently in a dotenv file, which is recommended:

```ini
PSN_NPSSO="your_psn_npsso_code"
SMTP_PASSWORD="your_smtp_password"
WEBHOOK_URL="your_webhook_url"
NTFY_ACCESS_TOKEN="your_ntfy_access_token"
```

By default the tool auto-searches for a dotenv file named `.env` in the current directory and then upward from it.

You can specify a custom file with `DOTENV_FILE` or the `--env-file` flag:

```sh
psn_monitor <psn_user_id> --env-file /path/.env-psn_monitor
```

You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
psn_monitor <psn_user_id> --env-file none
```

A secret exported in the environment wins over the same key in the dotenv file, and exported secrets work with no dotenv file at all. `--verbose` and `--doctor` each name every loaded secret and the source it came from, so a forgotten `export` shadowing your file is visible rather than guessed at.

As a fallback, you can also store secrets in the configuration file or source code.

`--debug` prints the same answer one secret per line, never the value:

```text
[DEBUG 12:00:00] Secret resolution: name=PSN_NPSSO, source=environment, value=set, chars=64
[DEBUG 12:00:00] Secret resolution: name=SMTP_PASSWORD, source=dotenv file, value=set
```

A secret no layer supplied is left out. A secret still holding its `your_...` placeholder counts as unset and is left out too. A run where nothing resolved says so in one line instead. A length appears only for the secrets whose length the provider issues, never for a password you chose.

Secret commands update the selected value without changing other dotenv settings. Clearing a value removes its assignment.

<a id="tls-verification"></a>
## TLS Verification

The tool verifies the TLS certificate of every server it contacts: PlayStation Network, the connectivity check endpoint, the mail server that delivers email alerts and, when enabled, the webhook service.

Set `VERIFY_SSL` to `False` only on a network that intercepts TLS with its own certificate authority, such as a corporate proxy. With verification off, an intercepted connection cannot be told apart from the real service.

The [startup summary](usage.md#terminal-output) shows `TLS verification` and `--doctor` reports a warning while it is off.
