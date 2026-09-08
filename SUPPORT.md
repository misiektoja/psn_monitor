# Getting help

Start with the [documentation](https://misiektoja.github.io/psn_monitor/). [Installation](https://misiektoja.github.io/psn_monitor/installation/) and [Setup & First Run](https://misiektoja.github.io/psn_monitor/setup-and-first-run/) cover most first-run problems, [Configuration](https://misiektoja.github.io/psn_monitor/configuration/) explains every setting the tool reads and [Troubleshooting](https://misiektoja.github.io/psn_monitor/troubleshooting/) covers what to do when a check fails.

## Check your setup first

Confirm which version you are running and that the notification channel actually works, then include the results when you ask:

```sh
psn_monitor --version
psn_monitor --send-test-email
```

Most reports come down to an expired NPSSO key, a PSN profile whose privacy settings hide the presence the tool reads or an SMTP server that refuses the message. The NPSSO key is the usual answer when the tool worked yesterday and stopped today.

## Where to ask

| You want to | Go to |
| --- | --- |
| Ask a question or discuss an idea | [Discussions](https://github.com/misiektoja/psn_monitor/discussions) |
| Report something broken | [Bug report](https://github.com/misiektoja/psn_monitor/issues/new?template=bug_report.yml) |
| Request a capability | [Feature request](https://github.com/misiektoja/psn_monitor/issues/new?template=feature_request.yml) |
| Report a vulnerability | [Private security advisory](https://github.com/misiektoja/psn_monitor/security/advisories/new), never a public issue |
| Contribute a change | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Before you post

Include the version, how you installed it (PyPI or manual script), your operating system, the monitored PSN ID you passed and what you expected instead. Attach the relevant part of the monitoring log file, which the tool writes unless you pass `--disable-logging`.

Never post your NPSSO key, SMTP passwords, webhook URLs or a complete configuration file. Redact monitored PSN IDs if they matter to you.

## What to expect

This is a project maintained in spare time, so replies are best effort with no response time attached. Only the latest release receives fixes, so reproduce the problem on the current version before reporting it.

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
