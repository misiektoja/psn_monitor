# Setup & First Run

## Before You Start

Install the tool using [Installation](installation.md). You will need a PlayStation Network online ID and the [PSN NPSSO code](#psn-npsso-code). The wizard collects credentials through hidden prompts.

Open a terminal in the directory where you want to keep the configuration and monitoring output. Later commands should use that directory or explicitly select the same `--config-file` and `--env-file` paths. Manual installations use the [command equivalents](usage.md#command-format).

<a id="setup-wizard"></a>
## Guided Setup

The quickest way to a working setup is the guided one:

```sh
psn_monitor --setup
```

The wizard asks for the account, polling interval, [npsso code](#psn-npsso-code), optional email and webhook alerts and output files.

Durations accept `120`, `2m`, `1.5h`, `1h 30m` or `1d`.

Setup checks your npsso code with PlayStation Network and checks email sign-in without sending a message. Invalid answers can be retried. If the mail server is unreachable, check the saved settings later with `--doctor`.

Review the summary and change any section before choosing **Save settings**. Regular settings go to `psn_monitor.conf` and private values go to `.env`. Setup asks before replacing an existing configuration and keeps a timestamped backup. On a rerun, saved settings provide the defaults. Declining a section disables it, including any previously configured alerts. See [Storing Secrets](configuration.md#storing-secrets) for credential storage and backup details.

Use `--config-file PATH` and `--env-file PATH` or the summary's **File destinations** section to choose other files. Both paths must be writable. `--config-file none` and `--env-file none` are not supported by setup.

After saving, setup offers [Doctor Preflight](troubleshooting.md#doctor-preflight) then can start monitoring if the checks pass.

The wizard needs an interactive terminal. Without one, use `--generate-config` and edit the file by hand.

## Quick Start

To set everything up yourself instead, grab your [npsso code](#psn-npsso-code) and track the `psn_user_id` gaming activities:

```sh
psn_monitor <psn_user_id> -n "your_psn_npsso_code"
```

Or if you installed [manually](installation.md#manual-installation):

```sh
python3 psn_monitor.py <psn_user_id> -n "your_psn_npsso_code"
```

To get the list of all supported command-line arguments and flags:

```sh
psn_monitor --help
```

Run it without arguments to see the few commands worth starting with, including the guided setup and how to check your setup before monitoring. On a terminal it also offers to start the guided setup right there.

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

## User Privacy Settings

In order to monitor PlayStation user activity, proper privacy settings need to be enabled on the monitored user account.

The user should go to [PlayStation account management](https://www.playstation.com/acct/management).

The value in **Privacy Settings → Personal Info | Messaging → Online Status and Now Playing** should be set to **Friends only** or **Anyone**.

If it is set to **Friends only**, the account whose npsso code you use has to be a friend of the monitored account. `--doctor` reports whether the presence is actually visible to you.

## Continue with Usage

Use [Usage](usage.md) for monitoring and output options or [Configuration](configuration.md) to adjust saved settings. If setup or monitoring fails, run [Doctor Preflight](troubleshooting.md#doctor-preflight) and follow the reported recovery steps.
