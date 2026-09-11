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

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor.png" alt="psn_monitor_screenshot" width="90%"/>
</p>

**Full documentation: [misiektoja.github.io/psn_monitor](https://misiektoja.github.io/psn_monitor/)**

<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/psn_monitor/installation/#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install psn_monitor
```

Run the setup wizard:

```sh
psn_monitor --setup
```

The wizard asks for the target, authentication, polling intervals and optional notifications. Review the settings before saving them. See [Setup & First Run](https://misiektoja.github.io/psn_monitor/setup-and-first-run/) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](https://misiektoja.github.io/psn_monitor/installation/).

## Features

### Activity Tracking

* **Gaming activity**: Detect online and offline status, game starts, finishes and changes.
* **Session statistics**: Measure time in each state, time per game and games played.
* **Session continuity**: Preserve statistics through short offline interruptions.

### Profile Insights

* **Profile details**: View PSN IDs, status, platform, PS+ membership, bio, languages and friendship details.
* **Recent games**: See recently played titles, last played dates and total playtime.
* **Optional trophies**: Include a trophy summary and recently earned trophies.

### Notifications and History

* **Event alerts**: Configure email, Discord and ntfy notifications independently.
* **CSV history**: Save reported activity with timestamps.
* **Saved status**: Resume monitoring with state retained across restarts.

### Setup and Configuration

* **Guided setup**: Configure a target, credentials and alerts with `--setup`, then check them with `--doctor`.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Terminal and runtime controls**: Customize colours and adjust the running monitor through supported signals.

## Common Commands

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](https://misiektoja.github.io/psn_monitor/usage/#command-format) for manual-script equivalents.

Replace the target placeholders with a PlayStation Network online ID. Monitoring requires the [PSN NPSSO code](https://misiektoja.github.io/psn_monitor/setup-and-first-run/#psn-npsso-code) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `psn_monitor --setup` |
| Start monitoring with saved credentials | `psn_monitor <psn_user_id>` |
| Check setup before monitoring | `psn_monitor --doctor <psn_user_id>` |
| Enter or replace credentials through hidden prompts | `psn_monitor --set-npsso` |
| Use a specific configuration and secrets file | `psn_monitor --config-file psn_monitor.conf --env-file .env <psn_user_id>` |
| Show profile details once | `psn_monitor <psn_user_id> -i` |
| List every supported command-line option | `psn_monitor --help` |

The monitored account must expose the activity described in [User Privacy Settings](https://misiektoja.github.io/psn_monitor/setup-and-first-run/#user-privacy-settings).

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](https://misiektoja.github.io/psn_monitor/usage/). If a run fails, start with [Doctor Preflight](https://misiektoja.github.io/psn_monitor/troubleshooting/#doctor-preflight).

## Documentation

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/psn_monitor/installation/) | Python walkthrough, PyPI or manual installation, upgrades |
| [Setup & First Run](https://misiektoja.github.io/psn_monitor/setup-and-first-run/) | The guided wizard, the npsso code, the privacy settings the monitored account needs |
| [Configuration](https://misiektoja.github.io/psn_monitor/configuration/) | Config file, SMTP, webhooks, TLS verification, storing secrets, check intervals |
| [Usage](https://misiektoja.github.io/psn_monitor/usage/) | Monitoring mode, user information mode, notifications, CSV export, signals, terminal colours |
| [Troubleshooting](https://misiektoja.github.io/psn_monitor/troubleshooting/) | `--doctor` preflight checks, what to do when something fails, `--verbose` and `--debug` output |
| [Testing](https://misiektoja.github.io/psn_monitor/testing/) | Running the offline suite, the linter and the docs build |
| [About](https://misiektoja.github.io/psn_monitor/about/) | Change log, contributing, security, license, support |

## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/psn_monitor/blob/main/RELEASE_NOTES.md).

## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/psn_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/psn_monitor/blob/main/CODE_OF_CONDUCT.md).

## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/psn_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/psn_monitor/blob/main/SECURITY.md) covers the reporting process, the supported versions and the security posture of stored credentials and configuration loading.

## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/psn_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/psn_monitor/blob/main/THIRD_PARTY_NOTICES.md).

## Support

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/psn_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
