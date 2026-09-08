# Configuration

## Configuration File

Most settings can be configured via command-line arguments.

If you want to have them stored persistently, generate a default config template and save it to a file named `psn_monitor.conf`:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
psn_monitor --generate-config > psn_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
psn_monitor --generate-config psn_monitor.conf
```

!!! important
    In Windows PowerShell, do not use `>` for this command. Some PowerShell versions write redirected text as UTF-16, which makes the tool report a "null bytes" error. Pass the filename to `--generate-config` so the tool writes a UTF-8 file itself.

When you include the filename, the template is written directly as UTF-8. This avoids PowerShell changing the file encoding during redirection.

Writing over an existing file asks first and keeps a timestamped `psn_monitor.conf.<timestamp>.bak` copy next to it. Outside an interactive terminal the write is refused instead, and `--force` replaces the file after taking the same backup:

```sh
psn_monitor --generate-config psn_monitor.conf --force
```

!!! note
    The guard only covers the filename form. Shell redirection with `>` empties the file before the tool starts, so nothing can protect it there.

Edit the `psn_monitor.conf` file and change any desired configuration options. Detailed comments are provided for each.

Config files are read as data. Only documented `SETTING = value` lines with plain literal values are accepted, so a config file sitting in the working directory cannot run code. A file that fails to parse names the offending line and leaves every setting at its previous value.

By default, the tool looks for a configuration file named `psn_monitor.conf` in:

 - the current directory
 - the home directory (`~`)
 - the script directory

If you saved it under a different name or in a different directory, specify its location with the `--config-file` flag:

```sh
psn_monitor <psn_user_id> --config-file /path/psn_monitor_new.conf
```

## Target Account

Set `PSN_USER_ID` to save the account you usually watch. A PSN ID passed on the command line always wins over the saved one, and with a saved value you can start monitoring with no arguments at all:

```sh
psn_monitor
```

`PSN_STATUS_FILE` and the `--status-file` flag choose where the last seen status is kept, which otherwise defaults to `psn_<psn_user_id>_last_status.json` in the current directory.

## Time Zone

By default, the time zone is auto-detected using `tzlocal`. You can set it manually in `psn_monitor.conf`:

```ini
LOCAL_TIMEZONE='Europe/Warsaw'
```

You can get the list of all time zones supported by pytz like this:

```sh
python3 -c "import pytz; print('\n'.join(pytz.all_timezones))"
```

## SMTP Settings

If you want to use email notifications functionality, configure SMTP settings in the `psn_monitor.conf` file: `SMTP_HOST`, `SMTP_PORT`, `SMTP_SSL`, `SMTP_USER`, `SENDER_EMAIL` and `RECEIVER_EMAIL`.

Store the password with `psn_monitor --set-smtp-password`, which signs in to your mail server to check it before writing anything and keeps it out of your shell history.

Verify your SMTP settings with the `--send-test-email` flag, which sends a real test message:

```sh
psn_monitor --send-test-email
```

## Webhook Settings

Alerts can also be delivered to a **Discord** channel or an **ntfy** topic. The webhook channel is configured and switched on separately from email, so you can send game changes to Discord while email stays off, or use both.

Save the destination privately, which never puts it in your shell history:

```sh
psn_monitor --set-webhook-url
```

For Discord this is the URL from Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL. For ntfy it is the complete topic URL, such as `https://ntfy.sh/your-private-topic`, or just the topic name when it is hosted on ntfy.sh. The service is detected from the URL, so `WEBHOOK_PROVIDER` only needs setting for a self-hosted ntfy server.

The URL is checked for shape without contacting the service, because the only confirmation Discord or ntfy can give is a delivered notification. The command prints `--send-test-webhook` as the next step, which does deliver one.

Then switch the channel on and choose which events it sends:

```python
WEBHOOK_ENABLED = True
WEBHOOK_PROVIDER = "discord"                    # or "ntfy"
WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = True     # user gets online or offline
WEBHOOK_GAME_CHANGE_NOTIFICATION = True         # game starts, changes or stops
WEBHOOK_ERROR_NOTIFICATION = True               # monitoring errors, enabled by default
```

Discord alerts are sent as an embed built from `WEBHOOK_TEMPLATE`, which supports the `title`, `description`, `version`, `color`, `timestamp`, `username` and `avatar_url` placeholders. Mentions are always disabled, whatever the template says. `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` override the webhook's own display name and picture, and both are ignored by ntfy.

ntfy alerts are sent as a native message with the subject as the title, so no template is involved. Use `WEBHOOK_HEADERS` to add ntfy options such as priority or tags, and `NTFY_ACCESS_TOKEN` when the topic needs authentication:

```python
WEBHOOK_HEADERS = {"Priority": "5", "Tags": "video_game"}
```

`WEBHOOK_TRANSFORMS` applies string methods to the values before they are sent, for example to strip Markdown from the body:

```python
WEBHOOK_TRANSFORMS = [
    ("title", "upper"),
    ("description", "replace", "**", ""),
]
```

Which events actually fire, and how a failed delivery is retried, is covered in [Webhook Notifications](usage.md#webhook-notifications).

## TLS Verification

The tool verifies the TLS certificate of every server it contacts: PlayStation Network, the connectivity check endpoint and, when enabled, the webhook service.

Set `VERIFY_SSL` to `False` only on a network that intercepts TLS with its own certificate authority, such as a corporate proxy. With verification off, an intercepted connection cannot be told apart from the real service.

The [startup summary](usage.md#startup-summary) shows `TLS verification` and `--doctor` reports a warning while it is off.

## Check Intervals

If you want to customize polling intervals, use the `-k` and `-c` flags or the corresponding configuration options:

```sh
psn_monitor <psn_user_id> -k 30 -c 120
```

* `PSN_ACTIVE_CHECK_INTERVAL`, `-k`: check interval when the user is online, in seconds
* `PSN_CHECK_INTERVAL`, `-c`: check interval when the user is offline, in seconds

Intervals that are short enough to be rate limited by PlayStation Network are reported as a warning by `--doctor`.

## Storing Secrets

It is recommended to store secrets like `PSN_NPSSO`, `SMTP_PASSWORD`, `WEBHOOK_URL` or `NTFY_ACCESS_TOKEN` as either an environment variable or in a dotenv file.

The tool can write them for you, so a secret never appears in your shell history or in `ps` output:

```sh
psn_monitor --set-npsso
psn_monitor --set-smtp-password
psn_monitor --set-webhook-url
```

Each asks for the value with the input hidden, checks it before saving anything, then writes it to your dotenv file with permissions that allow only you to read it. `--set-npsso` signs in to PlayStation Network and reports which account the code belongs to. `--set-smtp-password` signs in to your mail server without sending anything. `--set-webhook-url` checks the URL shape without contacting the service. If the check fails, nothing is written, so a working setup is never replaced by a broken one. Replacing a value that is already saved is confirmed first, and an existing `export PSN_NPSSO=...` line is rewritten in place rather than having a second assignment appended below it. All three need an interactive terminal.

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
