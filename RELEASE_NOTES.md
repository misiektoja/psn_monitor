# psn_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 1.8 (04 Jan 2026)

**Features and Improvements**:

- **IMPROVE:** Suppressed transient connection error messages (first 2 occurrences are hidden) to reduce log clutter
- **IMPROVE:** Enhanced startup process and user information display mode with interactive step-by-step progress updates

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
