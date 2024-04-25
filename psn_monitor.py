#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.0

Script implementing real-time monitoring of Sony Playstation (PSN) players activity:
https://github.com/misiektoja/psn_monitor/

Python pip3 requirements:

PSNAWP
python-dateutil
pytz
requests
"""

VERSION=1.0

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Login into your PSN account: https://my.playstation.com/
# In another tab, go to: https://ca.account.sony.com/api/v1/ssocookie
# Copy the value of npsso code below
# The refresh token that is generated from npsso should be valid for 2 months
PSN_NPSSO = "your_psn_npsso_code"

# How often do we perform checks for player activity when user is offline; in seconds
PSN_CHECK_INTERVAL=150 # 2.5 min

# How often do we perform checks for player activity when user is online; in seconds
PSN_ACTIVE_CHECK_INTERVAL=60 # 1 min

# Specify your local time zone so we convert PSN API timestamps to your time
LOCAL_TIMEZONE='Europe/Warsaw'

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL=21600 # 6 hours

# Default value for timeouts in alarm signal handler; in seconds
FUNCTION_TIMEOUT=15

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL='http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT=5

# SMTP settings for sending email notifications
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
#SMTP_HOST = "your_smtp_server_plaintext"
#SMTP_PORT = 25
#SMTP_USER = "your_smtp_user"
#SMTP_PASSWORD = "your_smtp_password"
#SMTP_SSL = False
#SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# The name of the .log file; the tool by default will output its messages to psn_monitor_psnid.log file
st_logfile="psn_monitor"

# Value used by signal handlers increasing/decreasing the check for player activity when user is online/away/snooze; in seconds
PSN_ACTIVE_CHECK_SIGNAL_VALUE=30 # 30 seconds

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

TOOL_ALIVE_COUNTER=TOOL_ALIVE_INTERVAL/PSN_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name']

active_inactive_notification=False
game_change_notification=False
status_notification=False

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
import smtplib, ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import csv
import pytz
from psnawp_api import PSNAWP

# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1)

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
    url=CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT)
        print("OK")
        return True
    except Exception as e:
        print("No connectivity, please check your network -", e)
        sys.exit(1)
    return False

# Function to convert absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952), # approximation
        ('months', 2629746), # approximation
        ('weeks', 604800),  # 60 * 60 * 24 * 7
        ('days', 86400),    # 60 * 60 * 24
        ('hours', 3600),    # 60 * 60
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
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'

# Function to calculate time span between two timestamps in seconds
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals=['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1=timestamp1
    ts2=timestamp2

    if type(timestamp1) is int:
        dt1=datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is datetime:
        dt1=timestamp1
        ts1=int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2=datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is datetime:
        dt2=timestamp2
        ts2=int(round(dt2.timestamp()))
    else:
        return ""

    if ts1>=ts2:
        ts_diff=ts1-ts2
    else:
        ts_diff=ts2-ts1
        dt1, dt2 = dt2, dt1

    if ts_diff>0:
        date_diff=relativedelta.relativedelta(dt1, dt2)
        years=date_diff.years
        months=date_diff.months
        weeks=date_diff.weeks
        if not show_weeks:
            weeks=0
        days=date_diff.days
        if weeks > 0:
            days=days-(weeks*7)
        hours=date_diff.hours
        if (not show_hours and ts_diff>86400):
            hours=0
        minutes=date_diff.minutes
        if (not show_minutes and ts_diff>3600):
            minutes=0
        seconds=date_diff.seconds
        if (not show_seconds and ts_diff>60):
            seconds=0
        date_list=[years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval>0:
                name=intervals[index]
                if interval==1:
                    name = name.rstrip('s')
                result.append("{} {}".format(interval, name))
#        return ', '.join(result)
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'

# Function to send email notification
def send_email(subject,body,body_html,use_ssl):

    try:     
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
        smtpObj.login(SMTP_USER,SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] =  Header(subject, 'utf-8')

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
        print("Error sending email -", e)
        return 1
    return 0

# Function to write CSV entry
def write_csv_entry(csv_file_name, timestamp, status, gamename):
    try:
        csv_file=open(csv_file_name, 'a', newline='', buffering=1)
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Date': timestamp, 'Status': status, 'Game name': gamename})
        csv_file.close()
    except Exception as e:
        raise

# Function to convert UTC string returned by PSN API to datetime object in specified timezone
def convert_utc_str_to_tz_datetime(utc_string, timezone):
    utc_string_sanitize=utc_string.split('+', 1)[0]
    utc_string_sanitize=utc_string_sanitize.split('.', 1)[0]
    dt_utc = datetime.strptime(utc_string_sanitize, '%Y-%m-%dT%H:%M:%S')

    old_tz = pytz.timezone("UTC")
    new_tz = pytz.timezone(timezone)
    dt_new_tz = old_tz.localize(dt_utc).astimezone(new_tz)
    return dt_new_tz

# Function to return the timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (str(ts_str) + str(calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]) + ", " + str(datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")))

# Function to print the current timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("-----------------------------------------------------------------------------------")

# Function to return the timestamp in human readable format (long version); eg. Sun, 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    return (str(calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]) + " " + str(datetime.fromtimestamp(ts).strftime("%d %b %Y, %H:%M:%S")))

# Function to return the timestamp in human readable format (short version); eg. Sun 21 Apr 15:08
def get_short_date_from_ts(ts):
    return (str(calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]) + " " + str(datetime.fromtimestamp(ts).strftime("%d %b %H:%M")))

# Function to return the timestamp in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts,show_seconds=False):
    if show_seconds:
        out_strf="%H:%M:%S"
    else:
        out_strf="%H:%M"
    return (str(datetime.fromtimestamp(ts).strftime(out_strf)))

# Function to return the range between two timestamps; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1,ts2,between_sep=" - ", short=False):
    ts1_strf=datetime.fromtimestamp(ts1).strftime("%Y%m%d")
    ts2_strf=datetime.fromtimestamp(ts2).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str=get_short_date_from_ts(ts1) + between_sep + get_hour_min_from_ts(ts2)
        else:
            out_str=get_date_from_ts(ts1) + between_sep + get_hour_min_from_ts(ts2,show_seconds=True)
    else:
        if short:
            out_str=get_short_date_from_ts(ts1) + between_sep + get_short_date_from_ts(ts2)
        else:
            out_str=get_date_from_ts(ts1) + between_sep + get_date_from_ts(ts2)       
    return (str(out_str))

# Signal handler for SIGUSR1 allowing to switch active/inactive email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global active_inactive_notification
    active_inactive_notification=not active_inactive_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active/inactive status changes = {active_inactive_notification}]")
    print_cur_ts("Timestamp:\t\t\t")

# Signal handler for SIGUSR2 allowing to switch played game changes notifications
def toggle_game_change_notifications_signal_handler(sig, frame):
    global game_change_notification
    game_change_notification=not game_change_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [game changes = {game_change_notification}]")
    print_cur_ts("Timestamp:\t\t\t")

# Signal handler for SIGCONT allowing to switch all status changes notifications
def toggle_all_status_changes_notifications_signal_handler(sig, frame):
    global status_notification
    status_notification=not status_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [all status changes = " + str(status_notification) + "]")
    print_cur_ts("Timestamp:\t\t\t")

# Signal handler for SIGTRAP allowing to increase check timer for player activity when user is online by PSN_ACTIVE_CHECK_SIGNAL_VALUE seconds
def increase_active_check_signal_handler(sig, frame):
    global PSN_ACTIVE_CHECK_INTERVAL
    PSN_ACTIVE_CHECK_INTERVAL=PSN_ACTIVE_CHECK_INTERVAL+PSN_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print("* PSN timers: [active check interval: " + display_time(PSN_ACTIVE_CHECK_INTERVAL) + "]")
    print_cur_ts("Timestamp:\t\t\t")

# Signal handler for SIGABRT allowing to decrease check timer for player activity when user is online by PSN_ACTIVE_CHECK_SIGNAL_VALUE seconds
def decrease_active_check_signal_handler(sig, frame):
    global PSN_ACTIVE_CHECK_INTERVAL
    if PSN_ACTIVE_CHECK_INTERVAL-PSN_ACTIVE_CHECK_SIGNAL_VALUE>0:
        PSN_ACTIVE_CHECK_INTERVAL=PSN_ACTIVE_CHECK_INTERVAL-PSN_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print("* PSN timers: [active check interval: " + display_time(PSN_ACTIVE_CHECK_INTERVAL) + "]")
    print_cur_ts("Timestamp:\t\t\t")

# Main function monitoring gaming activity of the specified PSN user
def psn_monitor_user(psnid,error_notification,csv_file_name,csv_exists):

    alive_counter = 0
    status_ts = 0
    status_old_ts = 0
    status_online_start_ts = 0
    game_ts = 0
    game_old_ts = 0
    lastonline_ts = 0
    status = "offline"

    try:
        if csv_file_name:
            csv_file=open(csv_file_name, 'a', newline='', buffering=1)
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print("* Error -", e)
 
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
        psn_user_presence=psn_user.get_presence()
    except Exception as e:
        print("Error - cannot get presence for user " + psnid + ":", e)
        sys.exit(1)

    status=psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("onlineStatus")
    platform=psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("platform")
    platform=str(platform).upper()
    lastonline=psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("lastOnlineDate")
    lastonline_dt=convert_utc_str_to_tz_datetime(str(lastonline),LOCAL_TIMEZONE)
    lastonline_ts=int(lastonline_dt.timestamp())
    lastonline_str=get_date_from_ts(int(lastonline_ts))
    gametitleinfolist=psn_user_presence["basicPresence"].get("gameTitleInfoList")
    gamename=""
    launchplatform=""
    if gametitleinfolist:
        gamename=gametitleinfolist[0].get("titleName")
        launchplatform=gametitleinfolist[0].get("launchPlatform")
        launchplatform=str(launchplatform).upper()

    status_old_ts = int(time.time())
    status_old_ts_bck = status_old_ts

    if status and str(status).lower() != "offline":
        status_online_start_ts=status_old_ts

    psn_last_status_file = "psn_" + str(psnid) + "_last_status.json"
    last_status_read = []
    last_status_ts = 0
    last_status = ""

    try:
        if os.path.isfile(psn_last_status_file):
            with open(psn_last_status_file, 'r') as f:
                last_status_read = json.load(f)
            if last_status_read:
                last_status_ts=last_status_read[0]
                last_status=last_status_read[1]
                psn_last_status_file_mdate_dt=datetime.fromtimestamp(int(os.path.getmtime(psn_last_status_file)))
                psn_last_status_file_mdate=psn_last_status_file_mdate_dt.strftime("%d %b %Y, %H:%M:%S")
                psn_last_status_file_mdate_weekday=str(calendar.day_abbr[(psn_last_status_file_mdate_dt).weekday()])

                print(f"* Last status loaded from file '{psn_last_status_file}' ({psn_last_status_file_mdate_weekday} {psn_last_status_file_mdate})")

                if last_status_ts>0:
                    last_status_dt_str=datetime.fromtimestamp(last_status_ts).strftime("%d %b %Y, %H:%M:%S")
                    last_status_str=str(last_status.upper())
                    last_status_ts_weekday=str(calendar.day_abbr[(datetime.fromtimestamp(last_status_ts)).weekday()])
                    print(f"* Last status read from file: {last_status_str} ({last_status_ts_weekday} {last_status_dt_str})")   

                    if lastonline_ts and str(status).lower()=="offline":
                        if lastonline_ts>=last_status_ts:
                            status_old_ts=lastonline_ts
                        else:
                            status_old_ts=last_status_ts
                    if not lastonline_ts and str(status).lower() == "offline":
                        status_old_ts=last_status_ts
                    if status and str(status).lower() != "offline" and status==last_status:
                        status_online_start_ts=last_status_ts
                        status_old_ts=last_status_ts
                
                if last_status_ts>0 and status!=last_status:
                    last_status_to_save=[]
                    last_status_to_save.append(status_old_ts)
                    last_status_to_save.append(status)
                    with open(psn_last_status_file, 'w') as f:
                        json.dump(last_status_to_save, f, indent=2)                    

    except Exception as e:
        print("Error -", e)

    try: 
        if csv_file_name and (status!=last_status):
            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), status, gamename)
    except Exception as e:
        print("* Cannot write CSV entry -", e)

    print("\nPlaystation ID:\t\t\t" + str(psnid))
    print("PSN account ID:\t\t\t" + str(accountid))
    print("\nLast seen:\t\t\t" + str(lastonline_str))    
    print("Status:\t\t\t\t" + str(status).upper())
    if platform:
        print("Platform:\t\t\t" + str(platform))
    print("PS+ user:\t\t\t" + str(isplus))

    if aboutme:
        print("\nAbout me:\t\t\t" + str(aboutme))

    if gamename:
        print("\nUser is currently in-game:\t" + str(gamename) + " (" + str(launchplatform) + ")")
        game_old_ts = int(time.time())

    if last_status_ts==0:
        if lastonline_ts and status=="offline":
            status_old_ts = lastonline_ts
        last_status_to_save=[]
        last_status_to_save.append(status_old_ts)
        last_status_to_save.append(status)
        with open(psn_last_status_file, 'w') as f:
            json.dump(last_status_to_save, f, indent=2)   

    if status_old_ts!=status_old_ts_bck:
        if status=="offline":
            last_status_dt_str=datetime.fromtimestamp(status_old_ts).strftime("%d %b %Y, %H:%M:%S")
            last_status_str=str(last_status).upper()
            last_status_ts_weekday=str(calendar.day_abbr[(datetime.fromtimestamp(status_old_ts)).weekday()])
            print(f"\n* Last time user was available:\t{last_status_ts_weekday} {last_status_dt_str}")          
        status_str=str(status).upper()
        status_for=calculate_timespan(int(time.time()),int(status_old_ts),show_seconds=False)
        print(f"\n* User is {status_str} for:\t\t{status_for}")       

    status_old=status
    gamename_old=gamename

    print_cur_ts("\nTimestamp:\t\t\t")

    alive_counter=0

    # Main loop
    while True:
        # Sometimes PSN network functions halt, so we use alarm signal functionality to kill it inevitably
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT)        
        try:
            if alive_counter >= (TOOL_ALIVE_COUNTER-1) and (status=="offline" or not status):
                psnawp = PSNAWP(PSN_NPSSO)
                psn_user = psnawp.user(online_id=psnid)
            psn_user_presence=psn_user.get_presence()
            status=psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("onlineStatus")
            gametitleinfolist=psn_user_presence["basicPresence"].get("gameTitleInfoList")
            gamename=""
            launchplatform=""
            if gametitleinfolist:
                gamename=gametitleinfolist[0].get("titleName")
                launchplatform=gametitleinfolist[0].get("launchPlatform")
                launchplatform=str(launchplatform).upper()
            email_sent = False
            signal.alarm(0)
            if not status:
                raise ValueError('PSN user status is empty')                   
        except TimeoutException:
            signal.alarm(0)
            print("psn_user.get_presence() timeout, retrying in", display_time(FUNCTION_TIMEOUT))
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(FUNCTION_TIMEOUT)           
            continue   
        except Exception as e:
            signal.alarm(0)
            if status and str(status).lower() != "offline":
                sleep_interval=PSN_ACTIVE_CHECK_INTERVAL
            else:
                sleep_interval=PSN_CHECK_INTERVAL          
            print("Retrying in", display_time(sleep_interval), ", error -", e)
            if 'npsso' in str(e):
                print("* PSN NPSSO key might not be valid anymore!")
                if error_notification and not email_sent:
                    m_subject="psn_monitor: PSN NPSSO key error! (user: " + str(psnid) + ")"
                    m_body="PSN NPSSO key might not be valid anymore: " + str(e) + get_cur_ts("\n\nTimestamp: ")
                    print("Sending email notification to",RECEIVER_EMAIL)
                    send_email(m_subject,m_body,"",SMTP_SSL)
                    email_sent=True
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(sleep_interval)
            continue

        change = False
        act_inact_flag=False

        # Player status changed
        if status != status_old:
            status_ts = int(time.time())

            last_status_to_save=[]
            last_status_to_save.append(status_ts)
            last_status_to_save.append(status)
            with open(psn_last_status_file, 'w') as f:
                json.dump(last_status_to_save, f, indent=2)                   

            print("PSN user " + psnid + " changed status from " + status_old + " to " + status)
            print("User was " + status_old + " for " + calculate_timespan(int(status_ts),int(status_old_ts)) + " (" + get_range_of_dates_from_tss(int(status_old_ts),int(status_ts),short=True) + ")")

            m_subject_was_since=", was " + status_old + ": " + get_range_of_dates_from_tss(int(status_old_ts),int(status_ts),short=True)
            m_subject_after=calculate_timespan(int(status_ts),int(status_old_ts),show_seconds=False)
            m_body_was_since=" (" + get_range_of_dates_from_tss(int(status_old_ts),int(status_ts),short=True) + ")"
            if status_old=="offline" and status and str(status).lower() != "offline":
                print("*** User got ACTIVE ! (was offline since " + get_date_from_ts(status_old_ts) + ")")
                status_online_start_ts=status_ts
                act_inact_flag=True
            if status_old and str(status_old).lower() != "offline" and status=="offline":
                if status_online_start_ts>0:
                    m_subject_after=calculate_timespan(int(status_ts),int(status_online_start_ts),show_seconds=False)
                    online_since_msg="(after " + calculate_timespan(int(status_ts),int(status_online_start_ts),show_seconds=False) + ": " + get_range_of_dates_from_tss(int(status_online_start_ts),int(status_ts),short=True) + ")"
                    m_subject_was_since=", was available: " + get_range_of_dates_from_tss(int(status_online_start_ts),int(status_ts),short=True)
                    m_body_was_since=" (" + get_range_of_dates_from_tss(int(status_old_ts),int(status_ts),short=True) + ")" + "\n\nUser was available for " + calculate_timespan(int(status_ts),int(status_online_start_ts),show_seconds=False) + " (" + get_range_of_dates_from_tss(int(status_online_start_ts),int(status_ts),short=True) + ")"
                else:
                    online_since_msg=""
                print(f"*** User got OFFLINE ! {online_since_msg}")
                status_online_start_ts=0
                act_inact_flag=True

            user_in_game=""
            if gamename:
                print("User is currently in-game: " + str(gamename) + " (" + str(launchplatform) + ")")
                user_in_game="\n\nUser is currently in-game: " + str(gamename) + " (" + str(launchplatform) + ")"

            change=True

            m_subject="PSN user " + psnid + " is now " + str(status) + " (after " + m_subject_after + m_subject_was_since + ")"
            m_body="PSN user " + psnid + " changed status from " + str(status_old) + " to " + str(status) + "\n\nUser was " + status_old + " for " + calculate_timespan(int(status_ts),int(status_old_ts)) + m_body_was_since + user_in_game + get_cur_ts("\n\nTimestamp: ")
            if status_notification or (active_inactive_notification and act_inact_flag):
                print("Sending email notification to",RECEIVER_EMAIL)
                send_email(m_subject,m_body,"",SMTP_SSL)
            status_old_ts = status_ts
                   
        # Player started/stopped/changed the game        
        if gamename != gamename_old: 
            game_ts = int(time.time())

            if gamename_old and gamename:
                print(f"PSN user " + psnid + " changed game from '" + gamename_old + "' to '" + gamename + "' (" + str(launchplatform) + ") after " + calculate_timespan(int(game_ts),int(game_old_ts)))
                print("User played game from " + get_range_of_dates_from_tss(int(game_old_ts),int(game_ts),short=True,between_sep=" to "))
                m_subject="PSN user " + psnid + " changed game to '" + str(gamename) + "' (" + str(launchplatform) + ", after " + calculate_timespan(int(game_ts),int(game_old_ts),show_seconds=False) + ": " + get_range_of_dates_from_tss(int(game_old_ts),int(game_ts),short=True) + ")"
                m_body="PSN user " + psnid + " changed game from '" + str(gamename_old) + "' to '" + str(gamename) + "' (" + str(launchplatform) + ") after " + calculate_timespan(int(game_ts),int(game_old_ts)) + "\n\nUser played game from " + get_range_of_dates_from_tss(int(game_old_ts),int(game_ts),short=True,between_sep=" to ") + get_cur_ts("\n\nTimestamp: ")
            elif not gamename_old and gamename:
                print("PSN user " + psnid + " started playing '" + gamename + "'" + " (" + str(launchplatform) + ")")
                m_subject="PSN user " + psnid + " now plays '" + str(gamename) + "'" + " (" + str(launchplatform) + ")"
                m_body="PSN user " + psnid + " now plays '" + str(gamename) + "'" + " (" + str(launchplatform) + ")" + get_cur_ts("\n\nTimestamp: ")
            elif gamename_old and not gamename:
                print("PSN user " + psnid + " stopped playing '" + gamename_old + "' after " + calculate_timespan(int(game_ts),int(game_old_ts)))
                print("User played game from " + get_range_of_dates_from_tss(int(game_old_ts),int(game_ts),short=True,between_sep=" to "))
                m_subject="PSN user " + psnid + " stopped playing '" + str(gamename_old) + "' (after " + calculate_timespan(int(game_ts),int(game_old_ts),show_seconds=False) + ": " + get_range_of_dates_from_tss(int(game_old_ts),int(game_ts),short=True) + ")"
                m_body="PSN user " + psnid + " stopped playing '" + str(gamename_old) + "' after " + calculate_timespan(int(game_ts),int(game_old_ts)) + "\n\nUser played game from " + get_range_of_dates_from_tss(int(game_old_ts),int(game_ts),short=True,between_sep=" to ") + get_cur_ts("\n\nTimestamp: ")
 
            change=True

            if game_change_notification:
                print("Sending email notification to",RECEIVER_EMAIL)
                send_email(m_subject,m_body,"",SMTP_SSL)

            game_old_ts = game_ts

        if change:
            alive_counter = 0

            try: 
                if csv_file_name:
                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), status, gamename)
            except Exception as e:
                    print("* Cannot write CSV entry -", e)

            print_cur_ts("Timestamp:\t\t\t")

        status_old=status
        gamename_old=gamename
        alive_counter+=1

        if alive_counter >= TOOL_ALIVE_COUNTER and (status=="offline" or not status):
            print_cur_ts("Alive check, timestamp:\t\t")
            alive_counter = 0

        if status and str(status).lower() != "offline":
            time.sleep(PSN_ACTIVE_CHECK_INTERVAL)
        else:
            time.sleep(PSN_CHECK_INTERVAL)

if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        os.system('clear')
    except:
        print("* Cannot clear the screen contents")

    print("PSN Monitoring Tool",VERSION,"\n")

    parser = argparse.ArgumentParser("psn_monitor")
    parser.add_argument("psnid", nargs="?", default="misiektoja", help="User's PSN ID", type=str)
    parser.add_argument("-b", "--csv_file", help="Write all status & game changes to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-s","--status_notification", help="Send email notification once user changes status", action='store_true')
    parser.add_argument("-g","--game_change_notification", help="Send email notification once user changes played game", action='store_true')
    parser.add_argument("-a","--active_inactive_notification", help="Send email notification once user changes status from active to inactive and vice versa", action='store_true')
    parser.add_argument("-e","--error_notification", help="Disable sending email notifications in case of errors like invalid API key", action='store_false')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks if user is offline, in seconds", type=int)
    parser.add_argument("-k", "--active_check_interval", help="Time between monitoring checks if user is not offline, in seconds", type=int)
    parser.add_argument("-d", "--disable_logging", help="Disable logging to file 'psn_monitor_user.log' file", action='store_true')
    parser.add_argument("-n", "--npsso_key", help="Specify Playstation NPSSO key if not defined within the script", type=str)
    args = parser.parse_args()

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.check_interval:
        PSN_CHECK_INTERVAL=args.check_interval
        TOOL_ALIVE_COUNTER=TOOL_ALIVE_INTERVAL/PSN_CHECK_INTERVAL

    if args.active_check_interval:
        PSN_ACTIVE_CHECK_INTERVAL=args.active_check_interval

    if args.npsso_key:
        PSN_NPSSO=args.npsso_key

    if args.csv_file:
        csv_enabled=True
        csv_exists=os.path.isfile(args.csv_file)
        try:
            csv_file=open(args.csv_file, 'a', newline='', buffering=1)
        except Exception as e:
            print("\n* Error, CSV file cannot be opened for writing -", e)
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled=False
        csv_file=None
        csv_exists=False

    if not args.disable_logging:
        st_logfile = st_logfile + "_" + str(args.psnid) + ".log"
        sys.stdout = Logger(st_logfile)

    active_inactive_notification=args.active_inactive_notification
    game_change_notification=args.game_change_notification
    status_notification=args.status_notification

    print("* PSN timers: [check interval: " + display_time(PSN_CHECK_INTERVAL) + "] [active check interval: " + display_time(PSN_ACTIVE_CHECK_INTERVAL) + "]")
    print("* Email notifications: [all status changes = " + str(status_notification) + "] [game changes = " + str(game_change_notification) + "] [active/inactive status changes = " + str(active_inactive_notification) + "] [errors = " + str(args.error_notification) + "]")
    print("* Output logging disabled:",str(args.disable_logging))
    print("* CSV logging enabled:",str(csv_enabled))

    out = "\nMonitoring user with PSN ID %s" % args.psnid
    print(out)
    print("-" * len(out))

    signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
    signal.signal(signal.SIGUSR2, toggle_game_change_notifications_signal_handler)
    signal.signal(signal.SIGCONT, toggle_all_status_changes_notifications_signal_handler)
    signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
    signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)

    psn_monitor_user(args.psnid,args.error_notification,args.csv_file,csv_exists)

    sys.stdout = stdout_bck
    sys.exit(0)

