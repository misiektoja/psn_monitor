#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.5

Tool implementing real-time tracking of Sony PlayStation (PSN) players activities:
https://github.com/misiektoja/psn_monitor/

Python pip3 requirements:

PSNAWP
python-dateutil
pytz
tzlocal
requests
"""

VERSION = 1.5

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Log in to your PSN account:
# https://my.playstation.com/
#
# In another tab, visit:
# https://ca.account.sony.com/api/v1/ssocookie
#
# Copy the value of the npsso code below (or use the -n parameter)
# The refresh token generated from the npsso should remain valid for about 2 months
PSN_NPSSO = "your_psn_npsso_code"

# SMTP settings for sending email notifications
# If left as-is, no notifications will be sent
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# How often to check for player activity when the user is offline; in seconds
# Can also be set using the -c parameter
PSN_CHECK_INTERVAL = 150  # 2.5 min

# How often to check for player activity when the user is online; in seconds
# Can also be set using the -k parameter
PSN_ACTIVE_CHECK_INTERVAL = 60  # 1 min

# Set your local time zone so that PSN API timestamps are converted accordingly (e.g. 'Europe/Warsaw').
# Use this command to list all time zones supported by pytz:
# python3 -c "import pytz; print('\n'.join(pytz.all_timezones))"
# If set to 'Auto', the tool will try to detect your local time zone automatically
LOCAL_TIMEZONE = 'Auto'

# If the user disconnects (offline) and reconnects (online) within OFFLINE_INTERRUPT seconds,
# the online session start time will be restored to the previous session’s start time (short offline interruption),
# and previous session statistics (like total playtime and number of played games) will be preserved
OFFLINE_INTERRUPT = 420  # 7 mins

# How often to print an "alive check" message to the output; in seconds
TOOL_ALIVE_INTERVAL = 21600  # 6 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://ca.account.sony.com/'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# Base name of the log file. The tool will save its output to psn_monitor_<psnid>.log file
PSN_LOGFILE = "psn_monitor"

# Value used by signal handlers to increase or decrease the online activity check interval (PSN_ACTIVE_CHECK_INTERVAL); in seconds
PSN_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Default value for timeouts in alarm signal handler; in seconds
FUNCTION_TIMEOUT = 15

# Width of horizontal line (─)
HORIZONTAL_LINE = 105

TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / PSN_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name']

active_inactive_notification = False
game_change_notification = False

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"


import sys

if sys.version_info < (3, 10):
    print("* Error: Python version 3.10 or higher required !")
    sys.exit(1)

import time
import string
import json
import os
from datetime import datetime, timezone
from dateutil import relativedelta
from dateutil.parser import isoparse
import calendar
import requests as req
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import csv
import pytz
try:
    from tzlocal import get_localzone
except ImportError:
    get_localzone = None
import platform
import re
import ipaddress
from psnawp_api import PSNAWP


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.logfile.write(message)
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
        pass


# Class used to generate timeout exceptions
class TimeoutException(Exception):
    pass


# Signal handler for SIGALRM when the operation times out
def timeout_handler(sig, frame):
    raise TimeoutException


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)


# Checks internet connectivity
def check_internet(url=CHECK_INTERNET_URL, timeout=CHECK_INTERNET_TIMEOUT):
    try:
        _ = req.get(url, timeout=timeout)
        return True
    except req.RequestException as e:
        print(f"* No connectivity, please check your network:\n\n{e}")
        return False


# Clears the terminal screen
def clear_screen(enabled=True):
    if not enabled:
        return
    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        print("* Cannot clear the screen contents")


# Converts absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952),  # approximation
        ('months', 2629746),  # approximation
        ('weeks', 604800),    # 60 * 60 * 24 * 7
        ('days', 86400),      # 60 * 60 * 24
        ('hours', 3600),      # 60 * 60
        ('minutes', 60),
        ('seconds', 1),
    )
    result = []

    if seconds > 0:
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append(f"{value} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Calculates time span between two timestamps, accepts timestamp integers, floats and datetime objects
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if isinstance(timestamp1, str):
        try:
            timestamp1 = isoparse(timestamp1)
        except Exception:
            return ""

    if isinstance(timestamp1, int):
        dt1 = datetime.fromtimestamp(int(ts1), tz=timezone.utc)
    elif isinstance(timestamp1, float):
        ts1 = int(round(ts1))
        dt1 = datetime.fromtimestamp(ts1, tz=timezone.utc)
    elif isinstance(timestamp1, datetime):
        dt1 = timestamp1
        if dt1.tzinfo is None:
            dt1 = pytz.utc.localize(dt1)
        else:
            dt1 = dt1.astimezone(pytz.utc)
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if isinstance(timestamp2, str):
        try:
            timestamp2 = isoparse(timestamp2)
        except Exception:
            return ""

    if isinstance(timestamp2, int):
        dt2 = datetime.fromtimestamp(int(ts2), tz=timezone.utc)
    elif isinstance(timestamp2, float):
        ts2 = int(round(ts2))
        dt2 = datetime.fromtimestamp(ts2, tz=timezone.utc)
    elif isinstance(timestamp2, datetime):
        dt2 = timestamp2
        if dt2.tzinfo is None:
            dt2 = pytz.utc.localize(dt2)
        else:
            dt2 = dt2.astimezone(pytz.utc)
        ts2 = int(round(dt2.timestamp()))
    else:
        return ""

    if ts1 >= ts2:
        ts_diff = ts1 - ts2
    else:
        ts_diff = ts2 - ts1
        dt1, dt2 = dt2, dt1

    if ts_diff > 0:
        date_diff = relativedelta.relativedelta(dt1, dt2)
        years = date_diff.years
        months = date_diff.months
        days_total = date_diff.days

        if show_weeks:
            weeks = days_total // 7
            days = days_total % 7
        else:
            weeks = 0
            days = days_total

        hours = date_diff.hours if show_hours or ts_diff <= 86400 else 0
        minutes = date_diff.minutes if show_minutes or ts_diff <= 3600 else 0
        seconds = date_diff.seconds if show_seconds or ts_diff <= 60 else 0

        date_list = [years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval > 0:
                name = intervals[index]
                if interval == 1:
                    name = name.rstrip('s')
                result.append(f"{interval} {name}")

        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Sends email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            print("Error sending email - SMTP settings are incorrect (invalid IP address/FQDN in SMTP_HOST)")
            return 1

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("Error sending email - SMTP settings are incorrect (invalid port number in SMTP_PORT)")
        return 1

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        print("Error sending email - SMTP settings are incorrect (invalid email in SENDER_EMAIL or RECEIVER_EMAIL)")
        return 1

    if not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password":
        print("Error sending email - SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD variables)")
        return 1

    if not subject or not isinstance(subject, str):
        print("Error sending email - SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    if not body and not body_html:
        print("Error sending email - SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
        return 1

    try:
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
        smtpObj.login(SMTP_USER, SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] = str(Header(subject, 'utf-8'))

        if body:
            part1 = MIMEText(body, 'plain')
            part1 = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
            email_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            part2 = MIMEText(body_html.encode('utf-8'), 'html', _charset='utf-8')
            email_msg.attach(part2)

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtpObj.quit()
    except Exception as e:
        print(f"Error sending email: {e}")
        return 1
    return 0


# Initializes the CSV file
def init_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
    except Exception as e:
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")


# Writes CSV entry
def write_csv_entry(csv_file_name, timestamp, status, game_name):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Date': timestamp, 'Status': status, 'Game name': game_name})

    except Exception as e:
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")


# Returns current local time without timezone info (naive)
def now_local_naive():
    return datetime.now(pytz.timezone(LOCAL_TIMEZONE)).replace(microsecond=0, tzinfo=None)


# Returns current local time with timezone info (aware)
def now_local():
    return datetime.now(pytz.timezone(LOCAL_TIMEZONE))


# Converts ISO datetime string to localized datetime (aware)
def convert_iso_str_to_datetime(dt_str):
    if not dt_str:
        return None

    try:
        utc_dt = isoparse(dt_str)
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        return utc_dt.astimezone(pytz.timezone(LOCAL_TIMEZONE))
    except Exception:
        return None


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(now_local_naive()).weekday()]}, {now_local_naive().strftime("%d %b %Y, %H:%M:%S")}')


# Prints the current date/time in human readable format with separator; eg. Sun 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("─" * HORIZONTAL_LINE)


# Returns the timestamp/datetime object in human readable format (long version); eg. Sun 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)

    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)

    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)

    else:
        return ""

    return (f'{calendar.day_abbr[ts_new.weekday()]} {ts_new.strftime("%d %b %Y, %H:%M:%S")}')


# Returns the timestamp/datetime object in human readable format (short version); eg.
# Sun 21 Apr 15:08
# Sun 21 Apr 24, 15:08 (if show_year == True and current year is different)
# Sun 21 Apr 25, 15:08 (if always_show_year == True and current year can be the same)
# Sun 21 Apr (if show_hour == False)
# Sun 21 Apr 15:08:32 (if show_seconds == True)
# 21 Apr 15:08 (if show_weekday == False)
def get_short_date_from_ts(ts, show_year=False, show_hour=True, show_weekday=True, show_seconds=False, always_show_year=False):
    tz = pytz.timezone(LOCAL_TIMEZONE)
    if always_show_year:
        show_year = True

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)

    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)

    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)

    else:
        return ""

    if show_hour:
        hour_strftime = " %H:%M:%S" if show_seconds else " %H:%M"
    else:
        hour_strftime = ""

    weekday_str = f"{calendar.day_abbr[ts_new.weekday()]} " if show_weekday else ""

    if (show_year and ts_new.year != datetime.now(tz).year) or always_show_year:
        hour_prefix = "," if show_hour else ""
        return f'{weekday_str}{ts_new.strftime(f"%d %b %y{hour_prefix}{hour_strftime}")}'
    else:
        return f'{weekday_str}{ts_new.strftime(f"%d %b{hour_strftime}")}'


# Returns the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)

    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)

    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)

    else:
        return ""

    out_strf = "%H:%M:%S" if show_seconds else "%H:%M"
    return ts_new.strftime(out_strf)


# Returns the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if isinstance(ts1, datetime):
        ts1_new = int(round(ts1.timestamp()))
    elif isinstance(ts1, int):
        ts1_new = ts1
    elif isinstance(ts1, float):
        ts1_new = int(round(ts1))
    else:
        return ""

    if isinstance(ts2, datetime):
        ts2_new = int(round(ts2.timestamp()))
    elif isinstance(ts2, int):
        ts2_new = ts2
    elif isinstance(ts2, float):
        ts2_new = int(round(ts2))
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new, tz).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new, tz).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new, show_seconds=True)}"
    else:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_short_date_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_date_from_ts(ts2_new)}"

    return str(out_str)


# Checks if the timezone name is correct
def is_valid_timezone(tz_name):
    return tz_name in pytz.all_timezones


# Signal handler for SIGUSR1 allowing to switch active/inactive email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global active_inactive_notification
    active_inactive_notification = not active_inactive_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active/inactive status changes = {active_inactive_notification}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGUSR2 allowing to switch played game changes notifications
def toggle_game_change_notifications_signal_handler(sig, frame):
    global game_change_notification
    game_change_notification = not game_change_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [game changes = {game_change_notification}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGTRAP allowing to increase check timer for player activity when user is online by PSN_ACTIVE_CHECK_SIGNAL_VALUE seconds
def increase_active_check_signal_handler(sig, frame):
    global PSN_ACTIVE_CHECK_INTERVAL
    PSN_ACTIVE_CHECK_INTERVAL = PSN_ACTIVE_CHECK_INTERVAL + PSN_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* PSN timers: [active check interval: {display_time(PSN_ACTIVE_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGABRT allowing to decrease check timer for player activity when user is online by PSN_ACTIVE_CHECK_SIGNAL_VALUE seconds
def decrease_active_check_signal_handler(sig, frame):
    global PSN_ACTIVE_CHECK_INTERVAL
    if PSN_ACTIVE_CHECK_INTERVAL - PSN_ACTIVE_CHECK_SIGNAL_VALUE > 0:
        PSN_ACTIVE_CHECK_INTERVAL = PSN_ACTIVE_CHECK_INTERVAL - PSN_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* PSN timers: [active check interval: {display_time(PSN_ACTIVE_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Main function that monitors gaming activity of the specified PSN user
def psn_monitor_user(psnid, error_notification, csv_file_name):

    alive_counter = 0
    status_ts = 0
    status_ts_old = 0
    status_online_start_ts = 0
    status_online_start_ts_old = 0
    game_ts = 0
    game_ts_old = 0
    lastonline_ts = 0
    status = ""
    game_total_ts = 0
    games_number = 0
    game_total_after_offline_counted = False

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print(f"* Error: {e}")

    try:
        psnawp = PSNAWP(PSN_NPSSO)
        psn_user = psnawp.user(online_id=psnid)
        accountid = psn_user.account_id
        profile = psn_user.profile()
        aboutme = profile.get("aboutMe")
        isplus = profile.get("isPlus")
    except Exception as e:
        print("* Error:", e)
        sys.exit(1)

    try:
        psn_user_presence = psn_user.get_presence()
    except Exception as e:
        print(f"* Error, cannot get presence for user {psnid}: {e}")
        sys.exit(1)

    status = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("onlineStatus")

    if not status:
        print(f"* Error: cannot get status for user {psnid}")
        sys.exit(1)

    status = str(status).lower()

    psn_platform = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("platform")
    psn_platform = str(psn_platform).upper()
    lastonline = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("lastOnlineDate")

    lastonline_dt = convert_iso_str_to_datetime(lastonline)
    if lastonline_dt:
        lastonline_ts = int(lastonline_dt.timestamp())
    else:
        lastonline_ts = 0
    gametitleinfolist = psn_user_presence["basicPresence"].get("gameTitleInfoList")
    game_name = ""
    launchplatform = ""
    if gametitleinfolist:
        game_name = gametitleinfolist[0].get("titleName")
        launchplatform = gametitleinfolist[0].get("launchPlatform")
        launchplatform = str(launchplatform).upper()

    status_ts_old = int(time.time())
    status_ts_old_bck = status_ts_old

    if status and status != "offline":
        status_online_start_ts = status_ts_old
        status_online_start_ts_old = status_online_start_ts

    psn_last_status_file = f"psn_{psnid}_last_status.json"
    last_status_read = []
    last_status_ts = 0
    last_status = ""

    if os.path.isfile(psn_last_status_file):
        try:
            with open(psn_last_status_file, 'r', encoding="utf-8") as f:
                last_status_read = json.load(f)
        except Exception as e:
            print(f"* Cannot load last status from '{psn_last_status_file}' file: {e}")
        if last_status_read:
            last_status_ts = last_status_read[0]
            last_status = last_status_read[1]
            psn_last_status_file_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(psn_last_status_file)), pytz.timezone(LOCAL_TIMEZONE))

            print(f"* Last status loaded from file '{psn_last_status_file}' ({get_short_date_from_ts(psn_last_status_file_mdate_dt, show_weekday=False, always_show_year=True)})")

            if last_status_ts > 0:
                last_status_dt_str = get_short_date_from_ts(last_status_ts, show_weekday=False, always_show_year=True)
                last_status_str = str(last_status.upper())
                print(f"* Last status read from file: {last_status_str} ({last_status_dt_str})")

                if lastonline_ts and status == "offline":
                    if lastonline_ts >= last_status_ts:
                        status_ts_old = lastonline_ts
                    else:
                        status_ts_old = last_status_ts
                if not lastonline_ts and status == "offline":
                    status_ts_old = last_status_ts
                if status and status != "offline" and status == last_status:
                    status_online_start_ts = last_status_ts
                    status_online_start_ts_old = status_online_start_ts
                    status_ts_old = last_status_ts

    if last_status_ts > 0 and status != last_status:
        last_status_to_save = []
        last_status_to_save.append(status_ts_old)
        last_status_to_save.append(status)
        try:
            with open(psn_last_status_file, 'w', encoding="utf-8") as f:
                json.dump(last_status_to_save, f, indent=2)
        except Exception as e:
            print(f"* Cannot save last status to '{psn_last_status_file}' file: {e}")

    try:
        if csv_file_name and (status != last_status):
            write_csv_entry(csv_file_name, now_local_naive(), status, game_name)
    except Exception as e:
        print(f"* Error: {e}")

    print(f"\nPlayStation ID:\t\t\t{psnid}")
    print(f"PSN account ID:\t\t\t{accountid}")

    print(f"\nStatus:\t\t\t\t{str(status).upper()}")
    if psn_platform:
        print(f"Platform:\t\t\t{psn_platform}")
    print(f"PS+ user:\t\t\t{isplus}")

    if aboutme:
        print(f"\nAbout me:\t\t\t{aboutme}")

    if status != "offline" and game_name:
        launchplatform_str = ""
        if launchplatform:
            launchplatform_str = f" ({launchplatform})"
        print(f"\nUser is currently in-game:\t{game_name}{launchplatform_str}")
        game_ts_old = int(time.time())
        games_number += 1

    if last_status_ts == 0:
        if lastonline_ts and status == "offline":
            status_ts_old = lastonline_ts
        last_status_to_save = []
        last_status_to_save.append(status_ts_old)
        last_status_to_save.append(status)
        try:
            with open(psn_last_status_file, 'w', encoding="utf-8") as f:
                json.dump(last_status_to_save, f, indent=2)
        except Exception as e:
            print(f"* Cannot save last status to '{psn_last_status_file}' file: {e}")

    if status_ts_old != status_ts_old_bck:
        if status == "offline":
            last_status_dt_str = get_date_from_ts(status_ts_old)
            print(f"\n* Last time user was available:\t{last_status_dt_str}")
        print(f"\n* User is {str(status).upper()} for:\t\t{calculate_timespan(now_local(), int(status_ts_old), show_seconds=False)}")

    status_old = status
    game_name_old = game_name

    print_cur_ts("\nTimestamp:\t\t\t")

    alive_counter = 0
    email_sent = False

    m_subject = m_body = ""

    if status and status != "offline":
        sleep_interval = PSN_ACTIVE_CHECK_INTERVAL
    else:
        sleep_interval = PSN_CHECK_INTERVAL

    time.sleep(sleep_interval)

    # Main loop
    while True:
        # Sometimes PSN network functions halt, so we use alarm signal functionality to kill it inevitably, not available on Windows
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT)
        try:
            psn_user_presence = psn_user.get_presence()
            status = ""
            status = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("onlineStatus")
            gametitleinfolist = psn_user_presence["basicPresence"].get("gameTitleInfoList")
            game_name = ""
            launchplatform = ""
            if gametitleinfolist:
                game_name = gametitleinfolist[0].get("titleName")
                launchplatform = gametitleinfolist[0].get("launchPlatform")
                launchplatform = str(launchplatform).upper()
            email_sent = False
            if platform.system() != 'Windows':
                signal.alarm(0)
            if not status:
                raise ValueError('PSN user status is empty')
            else:
                status = str(status).lower()
        except TimeoutException:
            if platform.system() != 'Windows':
                signal.alarm(0)
            print(f"psn_user.get_presence() timeout, retrying in {display_time(FUNCTION_TIMEOUT)}")
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(FUNCTION_TIMEOUT)
            continue
        except Exception as e:
            if platform.system() != 'Windows':
                signal.alarm(0)

            if status and status != "offline":
                sleep_interval = PSN_ACTIVE_CHECK_INTERVAL
            else:
                sleep_interval = PSN_CHECK_INTERVAL

            if 'Remote end closed connection' in str(e):
                # print("* Stale HTTP connection detected; re-initializing PSNAWP session ...")
                psnawp = PSNAWP(PSN_NPSSO)
                psn_user = psnawp.user(online_id=psnid)
                print_cur_ts("Timestamp:\t\t\t")
                time.sleep(2)
                continue

            print(f"* Error, retrying in {display_time(sleep_interval)}: {e}")
            if 'npsso' in str(e):
                print("* PSN NPSSO key might not be valid anymore!")
                if error_notification and not email_sent:
                    m_subject = f"psn_monitor: PSN NPSSO key error! (user: {psnid})"
                    m_body = f"PSN NPSSO key might not be valid anymore: {e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)
                    email_sent = True
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(sleep_interval)
            continue

        change = False
        act_inact_flag = False

        status_ts = int(time.time())
        game_ts = int(time.time())

        # Player status changed
        if status != status_old:

            last_status_to_save = []
            last_status_to_save.append(status_ts)
            last_status_to_save.append(status)
            try:
                with open(psn_last_status_file, 'w', encoding="utf-8") as f:
                    json.dump(last_status_to_save, f, indent=2)
            except Exception as e:
                print(f"* Cannot save last status to '{psn_last_status_file}' file: {e}")

            print(f"PSN user {psnid} changed status from {status_old} to {status}")
            print(f"User was {status_old} for {calculate_timespan(int(status_ts), int(status_ts_old))} ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})")

            m_subject_was_since = f", was {status_old}: {get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)}"
            m_subject_after = calculate_timespan(int(status_ts), int(status_ts_old), show_seconds=False)
            m_body_was_since = f" ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})"

            m_body_short_offline_msg = ""

            # Player got online
            if status_old == "offline" and status and status != "offline":
                print(f"*** User got ACTIVE ! (was offline since {get_date_from_ts(status_ts_old)})")
                game_total_after_offline_counted = False
                if (status_ts - status_ts_old) > OFFLINE_INTERRUPT or not status_online_start_ts_old:
                    status_online_start_ts = status_ts
                    game_total_ts = 0
                    games_number = 0
                elif (status_ts - status_ts_old) <= OFFLINE_INTERRUPT and status_online_start_ts_old > 0:
                    status_online_start_ts = status_online_start_ts_old
                    short_offline_msg = f"Short offline interruption ({display_time(status_ts - status_ts_old)}), online start timestamp set back to {get_short_date_from_ts(status_online_start_ts_old)}"
                    m_body_short_offline_msg = f"\n\n{short_offline_msg}"
                    print(short_offline_msg)
                act_inact_flag = True

            m_body_played_games = ""

            # Player got offline
            if status_old and status_old != "offline" and status == "offline":
                if status_online_start_ts > 0:
                    m_subject_after = calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)
                    online_since_msg = f"(after {calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)}: {get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)})"
                    m_subject_was_since = f", was available: {get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)}"
                    m_body_was_since = f" ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})\n\nUser was available for {calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)} ({get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)})"
                else:
                    online_since_msg = ""
                if games_number > 0:
                    if game_name_old and not game_name:
                        game_total_ts += (int(game_ts) - int(game_ts_old))
                        game_total_after_offline_counted = True
                    m_body_played_games = f"\n\nUser played {games_number} games for total time of {display_time(game_total_ts)}"
                    print(f"User played {games_number} games for total time of {display_time(game_total_ts)}")
                print(f"*** User got OFFLINE ! {online_since_msg}")
                status_online_start_ts_old = status_online_start_ts
                status_online_start_ts = 0
                act_inact_flag = True

            m_body_user_in_game = ""
            if status != "offline" and game_name:
                launchplatform_str = ""
                if launchplatform:
                    launchplatform_str = f" ({launchplatform})"
                print(f"User is currently in-game: {game_name}{launchplatform_str}")
                m_body_user_in_game = f"\n\nUser is currently in-game: {game_name}{launchplatform_str}"

            change = True

            m_subject = f"PSN user {psnid} is now {status} (after {m_subject_after}{m_subject_was_since})"
            m_body = f"PSN user {psnid} changed status from {status_old} to {status}\n\nUser was {status_old} for {calculate_timespan(int(status_ts), int(status_ts_old))}{m_body_was_since}{m_body_short_offline_msg}{m_body_user_in_game}{m_body_played_games}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
            if active_inactive_notification and act_inact_flag:
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, "", SMTP_SSL)

            status_ts_old = status_ts
            print_cur_ts("Timestamp:\t\t\t")

        # Player started/stopped/changed the game
        if game_name != game_name_old:

            launchplatform_str = ""
            if launchplatform:
                launchplatform_str = f" ({launchplatform})"

            # User changed the game
            if game_name_old and game_name:
                print(f"PSN user {psnid} changed game from '{game_name_old}' to '{game_name}'{launchplatform_str} after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                print(f"User played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}")
                game_total_ts += (int(game_ts) - int(game_ts_old))
                games_number += 1
                m_body = f"PSN user {psnid} changed game from '{game_name_old}' to '{game_name}'{launchplatform_str} after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                if launchplatform:
                    launchplatform_str = f"{launchplatform}, "
                m_subject = f"PSN user {psnid} changed game to '{game_name}' ({launchplatform_str}after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True)})"

            # User started playing new game
            elif not game_name_old and game_name:
                print(f"PSN user {psnid} started playing '{game_name}'{launchplatform_str}")
                games_number += 1
                m_subject = f"PSN user {psnid} now plays '{game_name}'{launchplatform_str}"
                m_body = f"PSN user {psnid} now plays '{game_name}'{launchplatform_str}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

            # User stopped playing the game
            elif game_name_old and not game_name:
                print(f"PSN user {psnid} stopped playing '{game_name_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                print(f"User played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}")
                if not game_total_after_offline_counted:
                    game_total_ts += (int(game_ts) - int(game_ts_old))
                m_subject = f"PSN user {psnid} stopped playing '{game_name_old}' (after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True)})"
                m_body = f"PSN user {psnid} stopped playing '{game_name_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

            change = True

            if game_change_notification and m_subject and m_body:
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, "", SMTP_SSL)

            game_ts_old = game_ts
            print_cur_ts("Timestamp:\t\t\t")

        if change:
            alive_counter = 0

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, now_local_naive(), status, game_name)
            except Exception as e:
                print(f"* Error: {e}")

        status_old = status
        game_name_old = game_name
        alive_counter += 1

        if alive_counter >= TOOL_ALIVE_COUNTER and (status == "offline" or not status):
            print_cur_ts("Alive check, timestamp:\t\t")
            alive_counter = 0

        if status and status != "offline":
            time.sleep(PSN_ACTIVE_CHECK_INTERVAL)
        else:
            time.sleep(PSN_CHECK_INTERVAL)


if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    clear_screen(CLEAR_SCREEN)

    print(f"PSN Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser(
        prog="psn_monitor",
        description="Monitor a PSN user’s playing status and send customizable email alerts [ https://github.com/misiektoja/psn_monitor/ ]"
    )

    # Positional
    parser.add_argument(
        "psn_id",
        nargs="?",
        metavar="PSN_ID",
        help="User's PSN ID",
        type=str
    )

    # API credentials
    creds = parser.add_argument_group("API credentials")
    creds.add_argument(
        "-n", "--npsso-key",
        dest="npsso_key",
        metavar="PSN_NPSSO",
        type=str,
        help="PlayStation NPSSO key"
    )

    # Notifications
    notify = parser.add_argument_group("Notifications")
    notify.add_argument(
        "-a", "--notify-active-inactive",
        dest="notify_active_inactive",
        action="store_true",
        help="Email when user goes online/offline"
    )
    notify.add_argument(
        "-g", "--notify-game-change",
        dest="notify_game_change",
        action="store_true",
        help="Email on game start/change/stop"
    )
    notify.add_argument(
        "-e", "--no-error-notify",
        dest="notify_errors",
        action="store_false",
        help="Disable email on errors (e.g. invalid NPSSO)"
    )
    notify.add_argument(
        "-z", "--send-test-email",
        dest="send_test_email",
        action="store_true",
        help="Send test email to verify SMTP settings"
    )

    # Intervals & timers
    times = parser.add_argument_group("Intervals & timers")
    times.add_argument(
        "-c", "--check-interval",
        dest="check_interval",
        metavar="SECONDS",
        type=int,
        help="Polling interval when user is offline"
    )
    times.add_argument(
        "-k", "--active-interval",
        dest="active_interval",
        metavar="SECONDS",
        type=int,
        help="Polling interval when user is in game"
    )

    # Features & Output
    opts = parser.add_argument_group("Features & output")
    opts.add_argument(
        "-b", "--csv-file",
        dest="csv_file",
        metavar="CSV_FILENAME",
        type=str,
        help="Write status & game changes to CSV"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        help="Disable logging to psn_monitor_<psn_id>.log"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    local_tz = None
    if LOCAL_TIMEZONE == "Auto":
        if get_localzone is not None:
            try:
                local_tz = get_localzone()
            except Exception:
                pass
        if local_tz:
            LOCAL_TIMEZONE = str(local_tz)
        else:
            print("* Error: Cannot detect local timezone, consider setting LOCAL_TIMEZONE to your local timezone manually !")
            sys.exit(1)
    else:
        if not is_valid_timezone(LOCAL_TIMEZONE):
            print(f"* Error: Configured LOCAL_TIMEZONE '{LOCAL_TIMEZONE}' is not valid. Please use a valid pytz timezone name.")
            sys.exit(1)

    if not check_internet():
        sys.exit(1)

    if args.send_test_email:
        print("* Sending test email notification ...\n")
        if send_email("psn_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if not args.psn_id:
        print("* Error: PSN_ID needs to be defined !")
        sys.exit(1)

    if args.npsso_key:
        PSN_NPSSO = args.npsso_key

    if not PSN_NPSSO or PSN_NPSSO == "your_psn_npsso_code":
        print("* Error: PSN_NPSSO (-n / --npsso_key) value is empty or incorrect")
        sys.exit(1)

    if args.check_interval:
        PSN_CHECK_INTERVAL = args.check_interval
        TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / PSN_CHECK_INTERVAL

    if args.active_interval:
        PSN_ACTIVE_CHECK_INTERVAL = args.active_interval

    if args.csv_file:
        try:
            with open(args.csv_file, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            print(f"* Error, CSV file cannot be opened for writing: {e}")
            sys.exit(1)

    if not args.disable_logging:
        PSN_LOGFILE = f"{PSN_LOGFILE}_{args.psn_id}.log"
        sys.stdout = Logger(PSN_LOGFILE)

    active_inactive_notification = args.notify_active_inactive
    game_change_notification = args.notify_game_change
    error_notification = args.notify_errors

    print(f"* PSN timers:\t\t\t[check interval: {display_time(PSN_CHECK_INTERVAL)}] [active check interval: {display_time(PSN_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[active/inactive status changes = {active_inactive_notification}] [game changes = {game_change_notification}] [errors = {error_notification}]")
    print(f"* Output logging enabled:\t{not args.disable_logging}" + (f" ({PSN_LOGFILE})" if not args.disable_logging else ""))
    print(f"* CSV logging enabled:\t\t{bool(args.csv_file)}" + (f" ({args.csv_file})" if args.csv_file else ""))
    print(f"* Local timezone:\t\t{LOCAL_TIMEZONE}")

    out = f"\nMonitoring user with PSN ID {args.psn_id}"
    print(out)
    print("-" * len(out))

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_game_change_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)

    psn_monitor_user(args.psn_id, args.notify_errors, args.csv_file)

    sys.stdout = stdout_bck
    sys.exit(0)
