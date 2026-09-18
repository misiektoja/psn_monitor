# psn_monitor

[![GitHub Release](https://img.shields.io/github/v/release/misiektoja/psn_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/psn_monitor/releases)
[![PyPI Version](https://img.shields.io/pypi/v/psn_monitor?style=flat-square&color=teal)](https://pypi.org/project/psn-monitor/)
[![GitHub Stars](https://img.shields.io/github/stars/misiektoja/psn_monitor?style=flat-square&color=magenta)](https://github.com/misiektoja/psn_monitor)
[![Python Versions](https://img.shields.io/badge/python-3.10+-blueviolet?style=flat-square)](https://pypi.org/project/psn-monitor/)
[![License](https://img.shields.io/github/license/misiektoja/psn_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/psn_monitor/blob/main/LICENSE)
[![OpenSSF Scorecard](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Fpsn_monitor&query=%24.score&label=openssf%20scorecard&style=flat-square)](https://scorecard.dev/viewer/?uri=github.com/misiektoja/psn_monitor)
[![Last Commit](https://img.shields.io/github/last-commit/misiektoja/psn_monitor?style=flat-square&color=green)](https://github.com/misiektoja/psn_monitor/commits/main)
[![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square)](https://github.com/misiektoja/psn_monitor)

Powerful tool for real-time monitoring of **Sony PlayStation (PSN) players' activities**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor.png" alt="psn_monitor_screenshot" width="90%"/>
</p>

<a id="quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/psn_monitor/installation/#new-to-python-check-and-install) first.

Install from PyPI:

```sh
pip install psn_monitor
```

Run the setup wizard:

```sh
psn_monitor --setup
```

The wizard asks for the target, the npsso code and optional notifications. Review the settings before saving them. See [Setup & First Run](https://misiektoja.github.io/psn_monitor/setup-and-first-run/) for how to get the npsso code and the required privacy settings.

For the manual single-file method, dependencies and upgrade commands, see [Installation](https://misiektoja.github.io/psn_monitor/installation/).

<a id="features"></a>
## Features

### 🔍 Activity Tracking

* **Gaming activity**: Detect online and offline status, game starts, finishes and changes.
* **Session statistics**: Measure time in each state, time per game and games played.
* **Session continuity**: Preserve statistics through short offline interruptions.

### 📊 Profile Insights

* **Profile details**: View PSN IDs, status, platform, PS+ membership, bio, languages and friendship details.
* **Recent games**: See recently played titles, last played dates and total playtime.
* **Optional trophies**: Include a trophy summary and recently earned trophies.

### 🔔 Notifications and History

* **Event alerts**: Configure email, Discord and ntfy notifications independently.
* **CSV history**: Save reported activity with timestamps.
* **Saved status**: Resume monitoring with state retained across restarts.

### ⚙️ Setup and Configuration

* **Guided setup**: Configure a target, credentials and alerts with `--setup`, then check them with `--doctor`.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Terminal and runtime controls**: Customize colours and adjust the running monitor through supported signals.

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install--run) above for first-time setup. The table uses PyPI commands. For the manual script equivalents, see [Run Individual Commands](https://misiektoja.github.io/psn_monitor/setup-and-first-run/#run-individual-commands).

Replace the target placeholders with a PlayStation Network online ID. Monitoring requires the [PSN NPSSO code](https://misiektoja.github.io/psn_monitor/setup-and-first-run/#psn-npsso-code) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `psn_monitor --setup` |
| Start monitoring with existing authentication | `psn_monitor <psn_user_id>` |
| Check authentication, connectivity and one target | `psn_monitor --doctor <psn_user_id>` |
| Enter or replace securely the npsso code | `psn_monitor --set-npsso` |
| Configure and test webhook alerts | Use the setup wizard or follow [Webhook Settings](https://misiektoja.github.io/psn_monitor/configuration/#webhook-settings) |
| Save an SMTP password for email alerts | `psn_monitor --set-smtp-password` |
| Send a test email | `psn_monitor --send-test-email` |
| Save a new webhook URL | `psn_monitor --set-webhook-url` |
| Send a test webhook | `psn_monitor --send-test-webhook` |
| Show profile details once | `psn_monitor <psn_user_id> -i` |
| Also show the trophy summary | `psn_monitor <psn_user_id> -i --trophies` |
| Write every change to a CSV file | `psn_monitor <psn_user_id> -b changes.csv` |
| Use a specific configuration and secrets file | `psn_monitor --config-file psn_monitor.conf --env-file .env <psn_user_id>` |
| List every supported command-line flag | `psn_monitor --help` |

The monitored account must expose the activity described in [User Privacy Settings](https://misiektoja.github.io/psn_monitor/setup-and-first-run/#user-privacy-settings).

Running the tool with no arguments offers the wizard if you have not saved an account. If an account is already saved, it starts monitoring that account.

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence and run multiple copies to monitor several accounts.

For the npsso code, saved accounts and notification setup, see the [full Setup & First Run guide](https://misiektoja.github.io/psn_monitor/setup-and-first-run/).

For TLS verification, email and webhook setup, see [Configuration](https://misiektoja.github.io/psn_monitor/configuration/). For notification choices, user information commands and output files, see [Usage](https://misiektoja.github.io/psn_monitor/usage/).

If a run fails, start with [Doctor Preflight](https://misiektoja.github.io/psn_monitor/troubleshooting/#doctor-preflight).

<a id="documentation"></a>
## Documentation

Full documentation is available at **[misiektoja.github.io/psn_monitor](https://misiektoja.github.io/psn_monitor/)**:

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/psn_monitor/installation/) | Python walkthrough, PyPI or manual installation, upgrades |
| [Setup & First Run](https://misiektoja.github.io/psn_monitor/setup-and-first-run/) | Setup wizard, the npsso code, privacy settings, the first monitoring run |
| [Configuration](https://misiektoja.github.io/psn_monitor/configuration/) | Config file, SMTP, webhooks, TLS verification, storing secrets, check intervals |
| [Usage](https://misiektoja.github.io/psn_monitor/usage/) | Monitoring mode, user information mode, notifications, CSV export, signals, terminal output |
| [Troubleshooting](https://misiektoja.github.io/psn_monitor/troubleshooting/) | `--doctor` preflight checks, what to do when something fails, `--verbose` and `--debug` output |
| [Testing](https://misiektoja.github.io/psn_monitor/testing/) | Running the offline suite, the linter and the docs build |
| [About](https://misiektoja.github.io/psn_monitor/about/) | Change log, contributing, security, license, support |

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/psn_monitor/blob/main/RELEASE_NOTES.md).

<a id="contributing"></a>
## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/psn_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/psn_monitor/blob/main/CODE_OF_CONDUCT.md).

<a id="security"></a>
## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/psn_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/psn_monitor/blob/main/SECURITY.md) covers the reporting process, the supported versions and the security posture of stored credentials and configuration loading.

<a id="maintainers"></a>
## Maintainers

- **misiektoja** ([@misiektoja](https://github.com/misiektoja))

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/psn_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/psn_monitor/blob/main/THIRD_PARTY_NOTICES.md).

<a id="support"></a>
## Support

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/psn_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
