# psn_monitor

Powerful tool for real-time monitoring of **Sony PlayStation (PSN) players' activities**.

## Features

- **Real-time tracking** of PlayStation users' gaming activity, including when a user gets online or offline and which games they play
- **Basic statistics for user activity**: duration in different states, time spent playing a game, overall time and number of games played in a session
- **Detailed user information** display mode covering PlayStation/PSN IDs, online status and availability to play, platform information, PS+ subscription status, verification status, about me section, languages, friendship relation and mutual friends count, profile URL, recently played games with last played date and total play time, and optionally a trophy summary and the last earned trophies
- **Email notifications** for various events: the user gets online or offline, starts, finishes or changes a game, and monitoring errors
- **Webhook notifications** delivered to **Discord** or **ntfy**, switched on per event independently of email
- **Guided setup** with `--setup`, and **preflight diagnostics** with `--doctor`
- **CSV export** of every reported activity, with **status persistence** across restarts
- **Smart session continuity**: short offline interruptions are handled and session statistics are preserved
- **Coloured terminal output** with a configurable theme, switched off automatically when the output is redirected
- **Flexible configuration** through config files, dotenv files, environment variables and command-line arguments
- **Control of the running copy** through signals
- **Functional, procedural Python** with minimal OOP

## Get started

```sh
pip install psn_monitor
```

The guided setup asks a few questions and writes a ready-to-run configuration:

```sh
psn_monitor --setup
```

[Installation](installation.md) covers the requirements and the manual install. [Setup & First Run](setup-and-first-run.md) covers the wizard, the npsso code and the privacy settings the monitored account needs.

## Screenshots

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/assets/psn_monitor.png" alt="psn_monitor_screenshot" width="90%"/>
</p>
