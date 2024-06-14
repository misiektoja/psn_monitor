#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.4

Tool implementing real-time tracking of Sony PlayStation (PSN) players activities:
https://github.com/misiektoja/psn_monitor/

Python pip3 requirements:

PSNAWP
python-dateutil
pytz
tzlocal
requests
"""

VERSION = 1.4

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Login into your PSN account: https://my.playstation.com/
# In another tab, go to: https://ca.account.sony.com/api/v1/ssocookie
# Copy the value of npsso code below (or use -n parameter)
# The refresh token that is generated from npsso should be valid for 2 months
PSN_NPSSO = "your_psn_npsso_code"

# SMTP settings for sending email notifications, you can leave it as it is below and no notifications will be sent
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
# SMTP_HOST = "your_smtp_server_plaintext"
# SMTP_PORT = 25
# SMTP_USER = "your_smtp_user"
# SMTP_PASSWORD = "your_smtp_password"
# SMTP_SSL = False
# SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# How often do we perform checks for player activity when user is offline, you can also use -c parameter; in seconds
PSN_CHECK_INTERVAL = 150  # 2.5 min

# How often do we perform checks for player activity when user is online, you can also use -k parameter; in seconds
PSN_ACTIVE_CHECK_INTERVAL = 60  # 1 min

# Specify your local time zone so we convert PSN API timestamps to your time (for example: 'Europe/Warsaw')
# If you leave it as 'Auto' we will try to automatically detect the local timezone
LOCAL_TIMEZONE = 'Auto'

# If user gets offline and online again (for example due to rebooting the console) during the next OFFLINE_INTERRUPT seconds then we set online start timestamp back to the previous one (so called short offline interruption) + we also keep stats from the previous session (like total time and number of played games)
OFFLINE_INTERRUPT = 420  # 7 mins

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL = 21600  # 6 hours

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL = 'http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# The name of the .log file; the tool by default will output its messages to psn_monitor_psnid.log file
PSN_LOGFILE = "psn_monitor"

# Value used by signal handlers increasing/decreasing the check for player activity when user is online/busy; in seconds
PSN_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Default value for timeouts in alarm signal handler; in seconds
FUNCTION_TIMEOUT = 15

TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / PSN_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name']

active_inactive_notification = False
game_change_notification = False

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"


import sys
import time
import string
import json
import os
from datetime import datetime
from dateutil import relativedelta
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
    pass
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


# Function to check internet connectivity
def check_internet():
    url = CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT)
        print("OK")
        return True
    except Exception as e:
        print(f"No connectivity, please check your network - {e}")
        sys.exit(1)
    return False


# Function to convert absolute value of seconds to human readable format
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


# Function to calculate time span between two timestamps in seconds
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if type(timestamp1) is int:
        dt1 = datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is float:
        ts1 = int(round(ts1))
        dt1 = datetime.fromtimestamp(ts1)
    elif type(timestamp1) is datetime:
        dt1 = timestamp1
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2 = datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is float:
        ts2 = int(round(ts2))
        dt2 = datetime.fromtimestamp(ts2)
    elif type(timestamp2) is datetime:
        dt2 = timestamp2
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
        weeks = date_diff.weeks
        if not show_weeks:
            weeks = 0
        days = date_diff.days
        if weeks > 0:
            days = days - (weeks * 7)
        hours = date_diff.hours
        if (not show_hours and ts_diff > 86400):
            hours = 0
        minutes = date_diff.minutes
        if (not show_minutes and ts_diff > 3600):
            minutes = 0
        seconds = date_diff.seconds
        if (not show_seconds and ts_diff > 60):
            seconds = 0
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


# Function to send email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        is_ip = ipaddress.ip_address(str(SMTP_HOST))
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
        email_msg["Subject"] = Header(subject, 'utf-8')

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
        print(f"Error sending email - {e}")
        return 1
    return 0


# Function to write CSV entry
def write_csv_entry(csv_file_name, timestamp, status, game_name):
    try:
        csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Date': timestamp, 'Status': status, 'Game name': game_name})
        csv_file.close()
    except Exception as e:
        raise


# Function to convert UTC string returned by PSN API to datetime object in specified timezone
def convert_utc_str_to_tz_datetime(utc_string, timezone):
    try:
        utc_string_sanitize = utc_string.split('+', 1)[0]
        utc_string_sanitize = utc_string_sanitize.split('.', 1)[0]
        dt_utc = datetime.strptime(utc_string_sanitize, '%Y-%m-%dT%H:%M:%S')

        old_tz = pytz.timezone("UTC")
        new_tz = pytz.timezone(timezone)
        dt_new_tz = old_tz.localize(dt_utc).astimezone(new_tz)
        return dt_new_tz
    except Exception as e:
        return datetime.fromtimestamp(0)


# Function to return the timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]}, {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


# Function to print the current timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("---------------------------------------------------------------------------------------------------------")


# Function to return the timestamp/datetime object in human readable format (long version); eg. Sun, 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime("%d %b %Y, %H:%M:%S")}')


# Function to return the timestamp/datetime object in human readable format (short version); eg.
# Sun 21 Apr 15:08
# Sun 21 Apr 24, 15:08 (if show_year == True and current year is different)
# Sun 21 Apr (if show_hour == False)
def get_short_date_from_ts(ts, show_year=False, show_hour=True):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_hour:
        hour_strftime = " %H:%M"
    else:
        hour_strftime = ""

    if show_year and int(datetime.fromtimestamp(ts_new).strftime("%Y")) != int(datetime.now().strftime("%Y")):
        if show_hour:
            hour_prefix = ","
        else:
            hour_prefix = ""
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b %y{hour_prefix}{hour_strftime}")}')
    else:
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b{hour_strftime}")}')


# Function to return the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_seconds:
        out_strf = "%H:%M:%S"
    else:
        out_strf = "%H:%M"
    return (str(datetime.fromtimestamp(ts_new).strftime(out_strf)))


# Function to return the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False):
    if type(ts1) is datetime:
        ts1_new = int(round(ts1.timestamp()))
    elif type(ts1) is int:
        ts1_new = ts1
    elif type(ts1) is float:
        ts1_new = int(round(ts1))
    else:
        return ""

    if type(ts2) is datetime:
        ts2_new = int(round(ts2.timestamp()))
    elif type(ts2) is int:
        ts2_new = ts2
    elif type(ts2) is float:
        ts2_new = int(round(ts2))
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new).strftime("%Y%m%d")

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
    return (str(out_str))


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


# Main function monitoring gaming activity of the specified PSN user
def psn_monitor_user(psnid, error_notification, csv_file_name, csv_exists):

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
            csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print(f"* Error - {e}")

    try:
        psnawp = PSNAWP(PSN_NPSSO)
        psn_user = psnawp.user(online_id=psnid)
        accountid = psn_user.account_id
        profile = psn_user.profile()
        aboutme = profile.get("aboutMe")
        isplus = profile.get("isPlus")
    except Exception as e:
        print("Error -", e)
        sys.exit(1)

    try:
        psn_user_presence = psn_user.get_presence()
    except Exception as e:
        print(f"Error: cannot get presence for user {psnid} - {e}")
        sys.exit(1)

    status = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("onlineStatus")

    if not status:
        print(f"Error: cannot get status for user {psnid}")
        sys.exit(1)

    status = str(status).lower()

    psn_platform = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("platform")
    psn_platform = str(psn_platform).upper()
    lastonline = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("lastOnlineDate")
    lastonline_dt = convert_utc_str_to_tz_datetime(str(lastonline), LOCAL_TIMEZONE)
    lastonline_ts = int(lastonline_dt.timestamp())
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
            print(f"* Cannot load last status from '{psn_last_status_file}' file - {e}")
        if last_status_read:
            last_status_ts = last_status_read[0]
            last_status = last_status_read[1]
            psn_last_status_file_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(psn_last_status_file)))
            psn_last_status_file_mdate = psn_last_status_file_mdate_dt.strftime("%d %b %Y, %H:%M:%S")
            psn_last_status_file_mdate_weekday = str(calendar.day_abbr[(psn_last_status_file_mdate_dt).weekday()])

            print(f"* Last status loaded from file '{psn_last_status_file}' ({psn_last_status_file_mdate_weekday} {psn_last_status_file_mdate})")

            if last_status_ts > 0:
                last_status_dt_str = datetime.fromtimestamp(last_status_ts).strftime("%d %b %Y, %H:%M:%S")
                last_status_str = str(last_status.upper())
                last_status_ts_weekday = str(calendar.day_abbr[(datetime.fromtimestamp(last_status_ts)).weekday()])
                print(f"* Last status read from file: {last_status_str} ({last_status_ts_weekday} {last_status_dt_str})")

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
            print(f"* Cannot save last status to '{psn_last_status_file}' file - {e}")

    try:
        if csv_file_name and (status != last_status):
            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), status, game_name)
    except Exception as e:
        print(f"* Error: cannot write CSV entry - {e}")

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
            print(f"* Cannot save last status to '{psn_last_status_file}' file - {e}")

    if status_ts_old != status_ts_old_bck:
        if status == "offline":
            last_status_dt_str = datetime.fromtimestamp(status_ts_old).strftime("%d %b %Y, %H:%M:%S")
            last_status_ts_weekday = str(calendar.day_abbr[(datetime.fromtimestamp(status_ts_old)).weekday()])
            print(f"\n* Last time user was available:\t{last_status_ts_weekday} {last_status_dt_str}")
        print(f"\n* User is {str(status).upper()} for:\t\t{calculate_timespan(int(time.time()), int(status_ts_old), show_seconds=False)}")

    status_old = status
    game_name_old = game_name

    print_cur_ts("\nTimestamp:\t\t\t")

    alive_counter = 0
    email_sent = False

    # Main loop
    while True:
        # Sometimes PSN network functions halt, so we use alarm signal functionality to kill it inevitably, not available on Windows
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT)
        try:
            if alive_counter >= (TOOL_ALIVE_COUNTER - 1) and (status == "offline" or not status):
                psnawp = PSNAWP(PSN_NPSSO)
                psn_user = psnawp.user(online_id=psnid)
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
            print(f"Error, retrying in {display_time(sleep_interval)} - {e}")
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
                print(f"* Cannot save last status to '{psn_last_status_file}' file - {e}")

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
                    m_body_short_offline_msg = f"\n\nShort offline interruption ({display_time(status_ts - status_ts_old)}), online start timestamp set back to {get_short_date_from_ts(status_online_start_ts_old)}"
                    print(f"Short offline interruption ({display_time(status_ts - status_ts_old)}), online start timestamp set back to {get_short_date_from_ts(status_online_start_ts_old)}")
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

            if game_change_notification:
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, "", SMTP_SSL)

            game_ts_old = game_ts
            print_cur_ts("Timestamp:\t\t\t")

        if change:
            alive_counter = 0

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), status, game_name)
            except Exception as e:
                print(f"* Error: cannot write CSV entry - {e}")

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

    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except:
        print("* Cannot clear the screen contents")

    print(f"PSN Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser("psn_monitor")
    parser.add_argument("PSN_ID", nargs="?", help="User's PSN ID", type=str)
    parser.add_argument("-n", "--npsso_key", help="PlayStation NPSSO key to override the value defined within the script (PSN_NPSSO)", type=str)
    parser.add_argument("-a", "--active_inactive_notification", help="Send email notification once user changes status from active to inactive and vice versa (online/offline)", action='store_true')
    parser.add_argument("-g", "--game_change_notification", help="Send email notification once user starts/changes/stops playing the game", action='store_true')
    parser.add_argument("-e", "--error_notification", help="Disable sending email notifications in case of errors like invalid NPSSO key", action='store_false')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks if user is offline, in seconds", type=int)
    parser.add_argument("-k", "--active_check_interval", help="Time between monitoring checks if user is NOT offline, in seconds", type=int)
    parser.add_argument("-b", "--csv_file", help="Write all status & game changes to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-d", "--disable_logging", help="Disable logging to file 'psn_monitor_user.log' file", action='store_true')
    parser.add_argument("-z", "--send_test_email_notification", help="Send test email notification to verify SMTP settings defined in the script", action='store_true')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    local_tz = None
    if LOCAL_TIMEZONE == "Auto":
        try:
            local_tz = get_localzone()
        except NameError:
            pass
        if local_tz:
            LOCAL_TIMEZONE = str(local_tz)
        else:
            print("* Error: Cannot detect local timezone, consider setting LOCAL_TIMEZONE to your local timezone manually !")
            sys.exit(1)

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.send_test_email_notification:
        print("* Sending test email notification ...\n")
        if send_email("psn_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
                print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if not args.PSN_ID:
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

    if args.active_check_interval:
        PSN_ACTIVE_CHECK_INTERVAL = args.active_check_interval

    if args.csv_file:
        csv_enabled = True
        csv_exists = os.path.isfile(args.csv_file)
        try:
            csv_file = open(args.csv_file, 'a', newline='', buffering=1, encoding="utf-8")
        except Exception as e:
            print(f"* Error: CSV file cannot be opened for writing - {e}")
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled = False
        csv_file = None
        csv_exists = False

    if not args.disable_logging:
        PSN_LOGFILE = f"{PSN_LOGFILE}_{args.PSN_ID}.log"
        sys.stdout = Logger(PSN_LOGFILE)

    active_inactive_notification = args.active_inactive_notification
    game_change_notification = args.game_change_notification

    print(f"* PSN timers:\t\t\t[check interval: {display_time(PSN_CHECK_INTERVAL)}] [active check interval: {display_time(PSN_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[active/inactive status changes = {active_inactive_notification}] [game changes = {game_change_notification}] [errors = {args.error_notification}]")
    if not args.disable_logging:
        print(f"* Output logging enabled:\t{not args.disable_logging} ({PSN_LOGFILE})")
    else:
        print(f"* Output logging enabled:\t{not args.disable_logging}")
    if csv_enabled:
        print(f"* CSV logging enabled:\t\t{csv_enabled} ({args.csv_file})")
    else:
        print(f"* CSV logging enabled:\t\t{csv_enabled}")
    print(f"* Local timezone:\t\t{LOCAL_TIMEZONE}")

    out = f"\nMonitoring user with PSN ID {args.PSN_ID}"
    print(out)
    print("-" * len(out))

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_game_change_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)

    psn_monitor_user(args.PSN_ID, args.error_notification, args.csv_file, csv_exists)

    sys.stdout = stdout_bck
    sys.exit(0)
