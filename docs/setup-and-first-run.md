# Setup & First Run

<a id="run-the-setup-wizard"></a>
## Run the setup wizard

Already installed? Run the setup command below for your installation and follow the prompts. Otherwise, start with [Installation](installation.md).

Setup asks who to monitor, your npsso code, how often to check and which alerts and output files you want. You can review your answers before saving. Regular settings go in `psn_monitor.conf` and private values go in `.env`. Keep `.env` private.

Press Enter to accept a default or Ctrl+C to cancel. Cancelling before saving leaves your files untouched. Cancelling after saving keeps the saved settings. For changes to an existing setup, see [Configuration File](configuration.md#configuration-file).

After saving, follow the offered Doctor checks and monitoring steps.

=== "PyPI"

    ```sh
    psn_monitor --setup
    ```

=== "Manual Python script on macOS or Linux"

    ```sh
    python3 psn_monitor.py --setup
    ```

=== "Manual Python script on Windows"

    ```powershell
    python psn_monitor.py --setup
    ```

A **target** is the PSN ID you want to monitor. The wizard asks for your npsso code and checks it with PlayStation Network. See [PSN NPSSO Code](#psn-npsso-code) for how to get it.

The polling prompts accept plain seconds or the `s`, `m`, `h` and `d` units. They show both the seconds and a readable form of the default.

With a saved target, running PSN Monitor without a target starts monitoring that account. If no target is saved, an interactive no-argument run offers setup.

<a id="before-you-start"></a>
## Before you start

You need three things before the first monitoring run:

1. A PSN target. Use the PlayStation Network online ID of the account you want to monitor.
2. An npsso code from your own PSN account. See [PSN NPSSO Code](#psn-npsso-code).
3. The monitored account must publish its online status. See [User Privacy Settings](#user-privacy-settings).

<a id="psn-npsso-code"></a>
## PSN NPSSO Code

Log in to your [My PlayStation](https://my.playstation.com/) account.

In another tab, go to: [https://ca.account.sony.com/api/v1/ssocookie](https://ca.account.sony.com/api/v1/ssocookie)

Copy the value of the `npsso` code.

Provide the `PSN_NPSSO` secret using one of the following methods:

 - Let the tool store it for you with `psn_monitor --set-npsso`, which keeps it out of your shell history
 - Pass it at runtime with `-n` / `--npsso-key`
 - Set it as an [environment variable](configuration.md#storing-secrets) (e.g. `export PSN_NPSSO=...`)
 - Add it to a [dotenv file](configuration.md#storing-secrets) (`PSN_NPSSO=...`) for persistent use

Fallback:

 - Hard-code it in the code or config file

Tokens expire after 2 months. The tool alerts on expiration.

If you store `PSN_NPSSO` in a dotenv file you can update its value and send a `SIGHUP` signal to the process to reload the file with the new npsso value without restarting the tool. More info in [Storing Secrets](configuration.md#storing-secrets) and [Signal Controls](usage.md#signal-controls-macoslinuxunix).

<a id="user-privacy-settings"></a>
## User Privacy Settings

In order to monitor PlayStation user activity, proper privacy settings need to be enabled on the monitored user account.

The user should go to [PlayStation account management](https://www.playstation.com/acct/management).

The value in **Privacy Settings → Personal Info | Messaging → Online Status and Now Playing** should be set to **Friends only** or **Anyone**.

If it is set to **Friends only**, the account whose npsso code you use has to be a friend of the monitored account. `--doctor` reports whether the presence is actually visible to you.

<a id="not-sure-which-command-you-need"></a>
## Not sure which command you need?

| I want to... | Run this |
| --- | --- |
| Set up PSN Monitor for the first time | Use the setup command for your installation above |
| Start monitoring with existing credentials | `psn_monitor <psn_user_id>` |
| Start the account saved in `PSN_USER_ID` | `psn_monitor --config-file psn_monitor.conf` |
| Check the npsso code, connectivity and one account | `psn_monitor --doctor <psn_user_id>` |
| Most securely enter or replace `PSN_NPSSO` | Run `psn_monitor --set-npsso` and enter the code at the hidden prompt |
| Save an SMTP password for email alerts | Run `psn_monitor --set-smtp-password` |
| Send a test email | Run `psn_monitor --send-test-email` |
| Set up webhook alerts | Run the setup wizard and choose webhook alerts |
| Save a new webhook URL | Run `psn_monitor --set-webhook-url` |
| Send a test webhook | Run `psn_monitor --send-test-webhook` |
| Show detailed account information and exit | `psn_monitor <psn_user_id> -i` |
| Also show the trophy summary | `psn_monitor <psn_user_id> -i --trophies` |
| Write every change to a CSV file | `psn_monitor <psn_user_id> -b changes.csv` |
| List every supported command-line flag | `psn_monitor --help` |

<a id="run-individual-commands"></a>
## Run Individual Commands

The examples below use PyPI. For a manual script, replace `psn_monitor` with `python3 psn_monitor.py` on macOS or Linux. Use `python psn_monitor.py` on Windows and run it from the directory holding the script or give its full path. See [Command Format by Installation Method](usage.md#command-format-by-installation-method).

Throughout this page `<psn_user_id>` means the PlayStation Network online ID you want to monitor.

<a id="save-the-npsso-code"></a>
### Save the npsso code

To configure credentials without the wizard, `--set-npsso` is the recommended and most secure entry method. It reads the code through a hidden prompt, so the value does not appear on screen or in the command line. It checks the code with PlayStation Network before updating only `PSN_NPSSO`. If the check fails, it does not change the `.env` file.

```sh
psn_monitor --set-npsso
```

Use `--env-file PATH` to select another `.env` file. The `-n` and `--npsso-key` options still work, but their values may appear in shell history or process listings.

<a id="save-notification-credentials"></a>
### Save notification credentials

The SMTP password is entered through a hidden prompt, checked against the mail server and saved as `SMTP_PASSWORD` in `.env`:

```sh
psn_monitor --set-smtp-password
```

A webhook URL is the private address used to deliver notifications. Treat it like a password because anyone who has it may be able to post through it. Follow the [webhook setup steps](configuration.md#webhook-settings) then save the link:

```sh
psn_monitor --set-webhook-url
```

The link is entered through a hidden prompt and saved as `WEBHOOK_URL` in `.env`. This command only saves the link. It does not turn on webhook alerts or send a message. See [Webhook Settings](configuration.md#webhook-settings) to choose your alerts then run `psn_monitor --send-test-webhook` to test them.

<a id="start-monitoring"></a>
### Start monitoring

The first example uses a positional account. The second uses a saved `PSN_USER_ID`:

```sh
psn_monitor <psn_user_id>
psn_monitor --config-file psn_monitor.conf
```

For a [manual script](installation.md#install-the-manual-script):

```sh
python3 psn_monitor.py <psn_user_id>
```

To check the setup before the first run, without writing anything:

```sh
psn_monitor --doctor <psn_user_id>
```

See [Doctor Preflight](troubleshooting.md#doctor-preflight) for what it reports.

To see all supported command-line arguments and flags:

```sh
psn_monitor --help
```

<a id="next-step"></a>
## Next Step

Run [Doctor](troubleshooting.md#doctor-preflight) before an unattended run to confirm the npsso code, connectivity and notification settings.

With the npsso code saved and a first run working, continue to [Configuration](configuration.md) for the monitored account, SMTP, webhooks and secrets. See [Usage](usage.md) for command formats, monitoring, listing commands, notifications and output files.
