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

**Full documentation: [misiektoja.github.io/psn_monitor](https://misiektoja.github.io/psn_monitor/)**

### 🚀 Quick Install

```sh
pip install psn_monitor
```

The guided setup asks a few questions and writes a ready-to-run configuration:

```sh
psn_monitor --setup
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor.png" alt="psn_monitor_screenshot" width="90%"/>
</p>

## Features

- **Real-time tracking** of PlayStation users' gaming activity, including when a user gets online or offline and which games they play
- **Basic statistics for user activity**: duration in different states, time spent playing a game, overall time and number of games played in a session
- **Detailed user information** display mode covering profile insights, online status, platform, PS+ subscription, recently played games and optionally trophies
- **Email and webhook notifications** through Discord, ntfy and compatible services, configurable per event
- **Guided setup** with `--setup`, and **preflight diagnostics** with `--doctor`
- **CSV export** of every reported activity, with **status persistence** across restarts
- **Coloured terminal output** with a configurable theme, switched off automatically when the output is redirected
- **Flexible configuration** through config files, dotenv files, environment variables and command-line arguments

## Documentation

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/psn_monitor/installation/) | Requirements, installing from PyPI or by hand, upgrading |
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
