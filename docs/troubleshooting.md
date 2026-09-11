# Troubleshooting

If a dotenv file cannot be opened or is not UTF-8, monitoring stops with the file path and the repair step for that cause. Doctor reports the failed load and continues the remaining checks.

## Doctor Preflight

`--doctor` checks a setup and prints one report instead of failing at the first problem:

```sh
psn_monitor <psn_user_id> --doctor
```

It writes no files, and it exits `1` if any check failed so you can run it from a script.

The report opens with the detected install method, then six sections, each row marked `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]` and colour-coded by status when colour output is on:

* **Environment**: Python and dependencies
* **Configuration**: selected files, secret sources, timezone, TLS verification and output paths
* **Authentication**: npsso validity and the signed-in account
* **Connectivity**: network access
* **Target**: whether the PlayStation ID exists and shares its presence with you
* **Notifications**: email sign-in and webhook settings, without sending a message

Warnings and failures include a `To fix:` action and relevant guide links. `[SKIP]` explains why a check could not run. Secrets are reported by name and source without their values.

If a channel passes and you are on an interactive terminal, the doctor offers to send one real test email and one real test webhook. Each is approved separately, and nothing is delivered without a `y`. Ctrl+C at either prompt ends the run rather than declining one test and asking the next.

Follow the report's **Next steps** after correcting any failed checks. The printed start command uses the configuration and dotenv files you checked.

## Error Messages and Recovery

When something goes wrong, the tool reports what happened and what to do about it:

```
* Error: PlayStation Network did not accept the NPSSO code
To fix: Generate a fresh NPSSO code, then put it in PSN_NPSSO in your dotenv file or pass it directly: psn_monitor <psn_user_id> -n <npsso_code>
Guide: https://misiektoja.github.io/psn_monitor/setup-and-first-run/#psn-npsso-code
```

Errors include instructions for the reported problem, such as an expired npsso code or hidden profile. Warnings, such as a missing optional library, let monitoring continue.

Commands in the fix text match how you installed the tool: `psn_monitor ...` for a PyPI install and `python3 psn_monitor.py ...` for a downloaded script. It also carries the `--config-file` or `--env-file` you started with, so it can be pasted as it is.

During quiet monitoring, `* Monitoring healthy for <psn_user_id>` confirms the tool is still running. `LIVENESS_CHECK_INTERVAL` defaults to 86400 seconds (24 hours). Set it to `0` to disable this reminder.

Failures show an error and a `To fix:` action. A continuing outage produces a `* Monitoring degraded` reminder once an hour, even when liveness reminders are disabled. `* Monitoring recovered` marks recovery. Follow any new instructions if the failure changes. Use `--debug` for technical error details.

## Verbose and Debug Output

Two flags make the tool explain what it is doing. They are independent, so you can use either or both:

```sh
psn_monitor <psn_user_id> --verbose --debug
```

* `VERBOSE_MODE`, `--verbose`: operational events, such as an alert channel switched off because its settings are still placeholders, and whether an email was actually delivered. It prints nothing per check, so an uneventful run stays quiet. It also expands the startup summary, which is where the configuration file, dotenv file, time zone and the source of each secret are named
* `DEBUG_MODE`, `--debug`: technical diagnostics, such as every PSN API call, how many settings the configuration file supplied, one line per completed check, the classification and text of each failure, how long the tool will wait before the next check and why, every read and write of the status and CSV files and where each secret was resolved from

A `--debug` run leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen. `--verbose` clears it like an ordinary run.

Debug lines are prefixed with `[DEBUG HH:MM:SS]`, then name the operation and list its details as comma-separated `key=value` fields, matching the sibling monitors:

```
[DEBUG 00:03:02] Connectivity check: url=https://psn.example/probe, timeout=7s
[DEBUG 00:03:02] Connectivity check: url=https://psn.example/probe, outcome=OK
```

Debug output includes HTTP status, retries and error details. Both modes redact secret values. The npsso length is shown to help identify an incomplete copy.

Both flags take effect before the configuration file is read, so they still work when the problem you are chasing is the configuration file itself. A flag you type always wins over `VERBOSE_MODE` or `DEBUG_MODE` in the configuration file. Set `DELIVERY_CONFIRMATIONS = False` to keep verbose mode without the `* Email sent to ...` and `* Webhook sent through ...` lines, which is worth doing when alerts are frequent.

Delivery confirmations name the email recipient or webhook provider without repeating the subject or message body. `DELIVERY_CONFIRMATIONS = False` hides those optional success receipts. Event output, send attempts and errors remain visible. Explicit notification tests report their result once. Generated email subjects and webhook titles use readable service names without a program-name prefix.

## Installation and Command Problems

If Python or `pip` is missing, use the [Python install walkthrough](installation.md#new-to-python-install-everything).

If `psn_monitor` is not found after installation, close the terminal and open it again. On Windows with Python Install Manager, run `py install --refresh` to refresh command aliases. For a pipx installation, run `pipx ensurepath` then reopen the terminal. If you downloaded the script, use the [manual command](usage.md#command-format) from its directory.

If `pip` reports an externally managed environment, follow the pipx steps in [Installation](installation.md#install-psn-monitor-after-python-check). Use `pipx upgrade psn_monitor` for later upgrades.

If the tool cannot import a dependency, install the dependencies with the same Python interpreter that runs the script. On macOS or Linux use `python3 -m pip install -r requirements.txt`. On Windows use `python -m pip install -r requirements.txt`. Match the requirements file to your downloaded script.

If a new terminal cannot find your saved settings, return to the directory used during setup or pass both `--config-file` and `--env-file` explicitly. Run `psn_monitor --doctor <psn_user_id>` to see which settings are loaded.

## Invalid saved settings and state

If setup fails while saving, the configuration may already have changed. Correct the reported destination problem, rerun `--setup` with the same `--config-file` and `--env-file` paths then run `--doctor` before monitoring. The configuration backup restores non-secret settings only.

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

If a saved status file has an invalid structure, monitoring stops before replacing it. Correct the named file or move it aside to start a fresh baseline. Keep a copy if you need the old history. Older valid records and extra trailing metadata remain accepted.

A saved status dated more than five minutes ahead of the machine clock is a separate case, because the tool wrote that file itself and a clock moved backwards is the usual reason. Monitoring warns, keeps the saved status and times it from the moment it starts, so the run continues. Check the system clock if the warning repeats.

Info lookups stop after a rate limit, authentication failure or service outage instead of continuing to other trophy or recent-game requests. Correct the reported problem or wait before running the command again.

Malformed path settings and color-theme values are reported by Doctor with the setting name. Invalid color values are ignored while rendering help so you can still find the configuration commands.
