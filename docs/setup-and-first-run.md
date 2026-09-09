# Setup & First Run

## Guided Setup

The quickest way to a working setup is the guided one:

```sh
psn_monitor --setup
```

It asks for the account to monitor, how often to check it, your [npsso code](#psn-npsso-code), whether to send email and webhook alerts and where the output goes, then writes a ready-to-run configuration file and a separate dotenv file for the secrets. Both destinations are checked before the first question, so an unwritable path or a directory given by mistake is reported straight away rather than after you have answered everything. `--setup` needs somewhere to put both files, so it refuses `--config-file none` and `--env-file none`.

Durations accept `120`, `2m`, `1.5h`, `1h 30m` or `1d`.

Your npsso code is checked against PlayStation Network before it is saved, so you find out immediately if it was copied incompletely. Any answer setup cannot use is offered again, whether you left it empty or the service refused it. Declining keeps every answer you have already given rather than restarting: an unusable webhook URL switches webhook alerts off and an unanswered mail server setting switches email alerts off. Email setup signs in to the mail server before saving, so a wrong password or an unreachable host is caught during setup instead of at the first alert. No email is sent. A refused sign-in offers the mail server questions again, and if the server was only unreachable the answers are kept so `--doctor` can check them later.

Nothing is written until you choose **Save settings**. A final summary lists every answer and lets you go back and change one section without losing the others, and discarding asks a second time. The summary's **File destinations** section changes where the configuration and dotenv files are written. Moving the dotenv file asks the authentication and notification questions again, since a secret you chose to keep was never going to reach the new file. A configuration file already in place is replaced only after you agree, and setup offers to write somewhere else instead. The replaced file is backed up first. A rebuilt file starts from the settings already in place with your answers applied over them. A section you decline is cleared rather than carried over, so declining email leaves no mail server behind. A secret already in the dotenv file is never replaced without asking, and keeping it leaves the stored value untouched. A saved webhook URL or ntfy access token is offered by name, so it can be kept, replaced or, for the token, switched off, without ever being displayed. At the end it offers to run the [preflight checks](troubleshooting.md#doctor-preflight) and, once they pass, to start monitoring.

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
