# psn_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 1.9.1 (TBD)

Version **1.9.1** fixes two alerting issues: alert delivery messages now stay within the correct check report, while alert channels that still use placeholder configuration values are shown as not configured.

**Bug fixes**:

- **BUGFIX:** **Alert deliveries stay inside their report** - The hourly **`Monitoring degraded`** reminder previously closed the report before sending its alert. This caused lines such as **`Sending email notification to ...`** and webhook delivery messages to appear below the separator in a separate block. The report now closes after the delivery messages, keeping the entire check output together.
- **BUGFIX:** **Unset alert channels are reported as unset** - The verbose startup summary previously treated placeholder configuration values as real alert settings. For example, an unconfigured email channel could appear as **`Email transport: your_smtp_server_ssl:587`** with recipient **`your_receiver_email`**, while the webhook provider could appear as **`Discord`**. These values are now shown as **`Not configured`**, while the channel summary shows **`Off (not configured)`**.

# Changes in 1.9 (18 Sep 2026)

Version **1.9** adds **guided setup**, a read-only **Doctor preflight check**, **Discord and ntfy alerts** and **private credential entry**. **Coloured output**, startup summaries and verbose/debug modes make monitoring easier to follow. It protects saved history and credentials, improves profile reports and adds verifiable downloads. The release requires **PSNAWP 3.0.3 or newer**.

**Features and improvements**:

- **NEW:** **Guided setup** - `--setup` wizard collects the account, intervals, credentials, notifications and output files. Review or edit answers before saving and confirm replacements. Reruns preserve saved settings and move retained credentials to the private dotenv file. A first run without a saved target offers setup
- **NEW:** **Doctor preflight check** - `--doctor` checks configuration, PSN sign-in, target visibility, notifications and output destinations with suggested fixes. It writes no files and sends test notifications only after confirmation
- **NEW:** **Discord and ntfy alerts** - Choose online/offline, game, status and error notifications independently of email. Save the destination with `--set-webhook-url` and check delivery with `--send-test-webhook`. Protected ntfy topics are supported
- **NEW:** **Private credential entry** - `--set-npsso` validates the NPSSO code with PSN. `--set-smtp-password` checks a hidden password with the mail server without sending a message. Both ask before replacing saved values
- **IMPROVE:** **Saved account and status file** - Set `PSN_USER_ID` to start monitoring without arguments. Use `PSN_STATUS_FILE` or `--status-file` to choose where the last seen status is stored
- **IMPROVE:** **Clearer output and diagnostics** - Coloured output and a short startup summary show the active settings. `--verbose` adds operational updates and `--debug` adds technical traces. Secrets are redacted and logs retain the full summary. Copy the updated `grc/conf.monitor_logs` to `~/.grc/` to use the live terminal colours in saved logs
- **IMPROVE:** **Clearer errors and recovery** - Failures include repair guidance, periodic outage reminders and recovery notices. Temporary failures trigger error alerts after five minutes, while expired NPSSO credentials alert immediately
- **IMPROVE:** **Screen width and TLS settings** - `--truncate N` limits screen width while logs retain full lines. It works without `wcwidth`, which improves Unicode width measurements. `VERIFY_SSL` covers outbound certificate checks, including email. Verification is on by default and disabling it produces a warning
- **IMPROVE:** **Notification output** - Subjects omit program-name prefixes. Set `DELIVERY_CONFIRMATIONS = False` to hide delivery confirmations while keeping verbose diagnostics
- **IMPROVE:** **Documentation and verifiable downloads** - A [searchable guide](https://misiektoja.github.io/psn_monitor/) covers setup, usage and troubleshooting. Releases include checksums and signed build attestations

**Bug fixes**:

- **BUGFIX:** **Accurate profile reports** - Reports include PS4 trophies and preserve game-title columns. Failed trophy and recent-game lookups stop with recovery guidance instead of continuing incomplete requests
- **BUGFIX:** **Protected status history** - Damaged status records are reported before replacement. Correct the file or move it aside to start fresh. Timestamps ahead of the clock are retained with corrected timing
- **BUGFIX:** **Safer configuration loading** - Configuration files are read as settings instead of executed as Python. Plain values and references to other settings still work. Replace imports, function calls and calculations with plain settings
- **BUGFIX:** **Safer configuration and secret updates** - `--generate-config FILE` confirms replacement and creates a backup. Non-interactive replacement requires `--force`. Shell redirection with `>` bypasses these protections. Exported secrets work without a dotenv file. Command-line credentials and nonempty startup exports retain priority after `SIGHUP`. Change those values and restart to replace them. Reloads apply changed or removed file-owned secrets
- **BUGFIX:** **Safer email and terminal output** - Mail-server rejection messages redact credentials. Emails accepted by the mail server no longer become false failures if closing the connection fails, avoiding duplicate retries. Upstream text cannot clear or retitle the terminal
- **BUGFIX:** **Reliable long-running monitoring** - PSN session recovery closes old connections. Invalid settings include repair guidance, configured connectivity settings apply and liveness reminders cover online and offline targets

Smaller fixes and development changes are listed in the [full change history](https://github.com/misiektoja/psn_monitor/compare/v1.8.4...v1.9).

# Changes in 1.8.4 (04 Aug 2026)

**Bug fixes**:

- **BUGFIX:** Fixed indentation of ASCII log separators in summary screen

# Changes in 1.8.3 (04 Aug 2026)

Version **1.8.3** makes saved logs easier to read consistently across platforms and prevents Windows PowerShell from creating incompatible configuration files.

**Features and Improvements**:

- **IMPROVE:** **Consistent log alignment** - Tabs are expanded to spaces when saved to log files so columns stay aligned in viewers that render tabs differently. Terminal output is unchanged
- **IMPROVE:** **Portable log separators** - The new `ASCII_LOG_SEPARATORS` setting controls whether separator-only lines saved to log files use ASCII hyphens. `"Auto"` enables them on Windows by default, `"On"` enables them on every operating system and `"Off"` preserves Unicode separators. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.
- **IMPROVE:** **UTF-8 configuration generation** - `psn_monitor --generate-config FILENAME` now writes the template directly to the specified file as UTF-8. In Windows PowerShell, it should be used instead of output redirection to avoid UTF-16 files and `null bytes` errors

# Changes in 1.8.2 (27 Apr 2026)

**Features and Improvements**:

- **NEW:** PSN platform codes are now mapped to human-readable labels in both monitoring mode and user info mode (e.g. `MOBILE_APP` -> `PlayStation App (mobile)`)
- **IMPROVE:** Added detection of PSN Terms of Service/User Agreement re-acceptance errors - when authentication fails due to a pending ToSUA, a specific actionable hint is displayed (and included in email notifications) instead of a generic auth error
- **IMPROVE:** Malformed or unexpected PSN presence responses are now detected and handled gracefully by recreating the PSNAWP session instead of crashing
- **IMPROVE:** Improved the error message when timezone auto-detection fails to hint about the missing optional `tzlocal` library and how to install it

# Changes in 1.8.1 (06 Mar 2026)

**Bug fixes**:

- **BUGFIX:** Fixed `timeout not implemented` crashes caused by a broken upstream `PSNAWP` 3.0.2 release by pinning the dependency to exclude it (fixes [#2](https://github.com/misiektoja/psn_monitor/issues/2))

# Changes in 1.8 (04 Jan 2026)

**Features and Improvements**:

- **IMPROVE:** Suppressed **transient connection error messages** (first 2 occurrences are hidden) to reduce log clutter
- **IMPROVE:** Enhanced startup process and user information display mode with **interactive step-by-step progress updates**

# Changes in 1.7 (29 Dec 2025)

**Features and Improvements**:

- **IMPROVE:** Enhanced PSNAWP session management with better error handling and cooldown logic

# Changes in 1.6 (11 Nov 2025)

**Features and Improvements**:

- **NEW:** Added detailed user information display mode (`-i` / `--info` flag), providing comprehensive PlayStation profile insights including PlayStation/PSN IDs, PS+ status, platform, about me, online status, availability to play, verification status, languages, friendship relation, profile URL and recently played games (name, last played, overall time)
- **NEW:** Added display of trophy summary and last earned trophies in user information display mode (`--trophies` flag, only works with `-i`/`--info`)
- **IMPROVE:** Enhanced user information display in monitoring mode to include availability to play, verification status, languages, friendship relation and profile URL
- **IMPROVE:** Added possibility to disable fetching of recently played games list (`--no-recent-games` flag, only works with `-i`/`--info`)

**Bug fixes**:

- **BUGFIX:** Enhanced connection error handling and notification for NPSSO token expiry
- **BUGFIX:** Added error streak detection to identify silent NPSSO token expiry during monitoring runs

# Changes in 1.5.1 (13 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Fixed config file generation to work reliably on Windows systems

# Changes in 1.5 (22 May 2025)

**Features and Improvements**:

- **NEW:** The tool can now be installed via pip: `pip install psn_monitor`
- **NEW:** Added support for external config files, environment-based secrets and dotenv integration with auto-discovery
- **IMPROVE:** Enhanced startup summary to show loaded config and dotenv file paths
- **IMPROVE:** Simplified and renamed command-line arguments for improved usability
- **NEW:** Implemented SIGHUP handler for dynamic reload of secrets from dotenv files
- **IMPROVE:** Added configuration option to control clearing the terminal screen at startup
- **IMPROVE:** Changed connectivity check to use Sony endpoint for reliability
- **IMPROVE:** Added check for missing pip dependencies with install guidance
- **IMPROVE:** Allow disabling liveness check by setting interval to 0 (default changed to 12h)
- **IMPROVE:** Improved handling of log file creation
- **IMPROVE:** Refactored CSV file initialization and processing
- **IMPROVE:** Added support for `~` path expansion across all file paths
- **IMPROVE:** Added validation for configured time zones
- **IMPROVE:** Refactored code structure to support packaging for PyPI
- **IMPROVE:** Enforced configuration option precedence: code defaults < config file < env vars < CLI flags
- **IMPROVE:** Updated horizontal line for improved output aesthetics
- **IMPROVE:** Email notifications now auto-disable if SMTP config is invalid
- **IMPROVE:** Minimum required Python version increased to 3.10
- **IMPROVE:** Removed short option for `--send-test-email` to avoid ambiguity

**Bug fixes**:

- **BUGFIX:** Re-login PSNAWP on `RemoteDisconnected` errors
- **BUGFIX:** Fixed issue where manually defined `LOCAL_TIMEZONE` wasn't applied correctly
- **BUGFIX:** Improved exception handling to prevent crashes during unexpected errors

# Changes in 1.4 (17 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new parameter (**-z** / **--send_test_email_notification**) which allows to send test email notification to verify SMTP settings defined in the script
- **IMPROVE:** Support for float type of timestamps added in date/time related functions
- **IMPROVE:** Function get_short_date_from_ts() rewritten to display year if show_year == True and current year is different, also can omit displaying hour and minutes if show_hours == False
- **IMPROVE:** Checking if correct version of Python (>=3.9) is installed
- **IMPROVE:** Possibility to define email sending timeout (default set to 15 secs)

**Bug fixes**:

- **BUGFIX:** Fixed "SyntaxError: f-string: unmatched (" issue in older Python versions
- **BUGFIX:** Fixed "SyntaxError: f-string expression part cannot include a backslash" issue in older Python versions

# Changes in 1.3 (23 May 2024)

**Features and Improvements**:

- **NEW:** Feature counting overall time and number of played games in the session
- **NEW:** Support for short offline interruption, so if user gets offline and online again (for example due to rebooting the console) during the next OFFLINE_INTERRUPT seconds (configurable in .py file, by default 7 mins) then we set online start timestamp back to the previous one + we also keep stats from the previous session (like total time and number of played games)
- **IMPROVE:** Information about log file name visible in the start screen
- **IMPROVE:** Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime

# Changes in 1.2 (19 May 2024)

**Features and Improvements**:

- **IMPROVE:** Improvements for running the code in Python under Windows
- **NEW:** Automatic detection of local timezone if you set LOCAL_TIMEZONE variable to 'Auto' (it is default now); requires tzlocal pip module
- **IMPROVE:** Information about time zone is displayed in the start screen now
- **IMPROVE:** Better checking for wrong command line arguments
- **IMPROVE:** Email sending function send_email() has been rewritten to detect invalid SMTP settings
- **IMPROVE:** Strings have been converted to f-strings for better code visibility
- **IMPROVE:** Info about CSV file name in the start screen
- **IMPROVE:** In case of getting an exception in main loop we will send the error email notification only once (until the issue is resolved)
- **IMPROVE:** Exception handling for function converting the timezone
- **IMPROVE:** Last seen info has been removed as it is redundant and already covered by other part of the code (last time user was available)
- **IMPROVE:** Platform info is put into subject of game change emails now
- **IMPROVE:** pep8 style convention corrections

**Bug fixes**:

- **BUGFIX:** Handling situations when JSON file storing info about the last status gets corrupted or when there are issuing saving the state
- **BUGFIX:** Handling situations when platform is returned empty

# Changes in 1.1 (27 Apr 2024)

**Features and Improvements**:

- **IMPROVE:** After some testing it turned out "busy" status is not reported by PSN, so it leaves us only with online & offline; that's why "-s" parameter and corresponding code has been removed

**Bug fixes**:

- **BUGFIX:** Fixes for detecting situations where reported user status is empty
- **BUGFIX:** Cleaning the code related to capitalization of reported user status

# Changes in 1.0 (25 Apr 2024)

**Features and Improvements**:

- **NEW:** Periodic refreshing of PSN NPSSO token
- **IMPROVE:** Additional information in the subject of email notifications

**Bug fixes**:

- **BUGFIX:** Fixes for handling situations where some profile information is not available
