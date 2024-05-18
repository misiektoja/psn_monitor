# psn_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.2 (19 May 2024)

**Features and Improvements**:

- Improvements for running the code in Python under Windows
- Automatic detection of local timezone if you set LOCAL_TIMEZONE variable to 'Auto' (it is default now); requires tzlocal pip module
- Information about time zone is displayed in the start screen now
- Better checking for wrong command line arguments
- Email sending function send_email() has been rewritten to detect invalid SMTP settings
- Strings have been converted to f-strings for better code visibility
- Info about CSV file name in the start screen
- In case of getting an exception in main loop we will send the error email notification only once (until the issue is resolved)
- Exception handling for function converting the timezone
- Last seen info has been removed as it is redundant and already covered by other part of the code (last time user was available)
- Platform info is put into subject of game change emails now
- pep8 style convention corrections

**Bugfixes**:

- Handling situations when JSON file storing info about the last status gets corrupted or when there are issuing saving the state
- Handling situations when platform is returned empty

# Changes in 1.1 (27 Apr 2024)

**Features and Improvements**:

- After some testing it turned out "busy" status is not reported by PSN, so it leaves us only with online & offline; that's why "-s" parameter and corresponding code has been removed

**Bugfixes**:

- Fixes for detecting situations where reported user status is empty
- Cleaning the code related to capitalization of reported user status

# Changes in 1.0 (25 Apr 2024)

**Features and Improvements**:

- Periodic refreshing of PSN NPSSO token
- Additional information in the subject of email notifications

**Bugfixes**:

- Fixes for handling situations where some profile information is not available
