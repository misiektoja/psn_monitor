# psn_monitor release notes

This is a high-level summary of the most important changes. 

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
