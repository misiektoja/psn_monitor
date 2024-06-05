# psn_monitor release notes

This is a high-level summary of the most important changes. 

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
