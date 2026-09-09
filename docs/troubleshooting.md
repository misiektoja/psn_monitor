# Troubleshooting

## Doctor Preflight

`--doctor` checks a setup and prints one report instead of failing at the first problem:

```sh
psn_monitor <psn_user_id> --doctor
```

It writes no files, and it exits `1` if any check failed so you can run it from a script.

The report opens with the detected install method, then six sections, each row marked `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`:

* **Environment**: the Python version against the supported minimum, the required libraries, and the optional ones with what stops working without each
* **Configuration**: the configuration and dotenv files in use, which secrets are loaded and where each came from, the local time zone including whether an `Auto` setting can be detected, whether TLS verification is on and the files the tool would write
* **Authentication**: whether PlayStation Network accepts your npsso code, and which account it signed in as
* **Connectivity**: that the connectivity endpoint answers, using the configured URL, timeout and TLS setting
* **Target**: whether the monitored PlayStation ID exists and shares its presence with your account
* **Notifications**: whether email and webhook alerts can fire. The email row signs in to the configured SMTP server without sending a message, the webhook row checks the destination and headers without contacting the service, and each ready row lists the alert categories that channel would deliver

Every `[WARN]` and `[FAIL]` row carries the `To fix:` line described in [Error Messages and Recovery](#error-messages-and-recovery), indented under the marker it belongs to, plus a `Guide:` link when a documentation page covers that row. A `[SKIP]` row names a check that could not run and says why. Secrets are reported by name and never by value, which makes the whole report safe to paste into a bug report.

If a channel passes and you are on an interactive terminal, the doctor offers to send one real test email and one real test webhook. Each is approved separately, and nothing is delivered without a `y`.

The report ends with a **Next steps** block naming the command that starts monitoring, carrying the same `--config-file` and `--env-file` this run checked. While a check is failing it asks for the failures first.

## Error Messages and Recovery

When something goes wrong, the tool reports what happened and what to do about it:

```
* Error: PlayStation Network did not accept the NPSSO code
To fix: Generate a fresh NPSSO code, then put it in PSN_NPSSO in your dotenv file or pass it directly: psn_monitor <psn_user_id> -n <npsso_code>
Guide: https://misiektoja.github.io/psn_monitor/setup-and-first-run/#psn-npsso-code
```

Every failure is sorted into a category, so an expired npsso code, a hidden profile, a rate limit, an unreachable network and a local file descriptor limit each get their own instructions instead of one generic message. Problems the tool survives, such as a missing optional library, are reported as `* Warning:` and it keeps running.

Commands in the fix text match how you installed the tool: `psn_monitor ...` for a PyPI install and `python3 psn_monitor.py ...` for a downloaded script. It also carries the `--config-file` or `--env-file` you started with, so it can be pasted as it is.

During a long outage the fix is printed once and each retry after that is a single line, until the failure changes or a check succeeds. The raw library error is not shown by default. Add `--debug` to print it as a `Technical detail:` line, with every secret redacted.

## Verbose and Debug Output

Two flags make the tool explain what it is doing. They are independent, so you can use either or both:

```sh
psn_monitor <psn_user_id> --verbose --debug
```

* `VERBOSE_MODE`, `--verbose`: operational events, such as an alert channel switched off because its settings are still placeholders, whether an email was actually delivered, when a run recovers from a failure it reported, and what a liveness banner means. It prints nothing per check, so an uneventful run stays quiet. It also expands the startup summary, which is where the configuration file, dotenv file, time zone and the source of each secret are named
* `DEBUG_MODE`, `--debug`: technical diagnostics, such as every PSN API call, how many settings the configuration file supplied, one line per completed check, the classification and text of each failure, how long the tool will wait before the next check and why, every read and write of the status and CSV files and where each secret was resolved from

A `--debug` run leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen. `--verbose` clears it like an ordinary run.

Debug lines are prefixed with `[DEBUG HH:MM:SS]`, then name the operation and list its details as comma-separated `key=value` fields, matching the sibling monitors:

```
[DEBUG 00:03:02] Connectivity check: url=https://psn.example/probe, timeout=7s
[DEBUG 00:03:02] Connectivity check: url=https://psn.example/probe, outcome=OK
```

Every outbound call reports `outcome=OK` or `outcome=failed` with an `error=` field. Both modes redact every secret, including your npsso code, SMTP password, webhook URL and ntfy access token, and report a secret by name and source rather than by value. The npsso code also reports its length, because a code truncated while copying is the usual reason it stops working. Your SMTP password reports only that it is set.

Both flags take effect before the configuration file is read, so they still work when the problem you are chasing is the configuration file itself. A flag you type always wins over `VERBOSE_MODE` or `DEBUG_MODE` in the configuration file.
