#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.9

Tool implementing real-time tracking of Sony PlayStation (PSN) players activities:
https://github.com/misiektoja/psn_monitor/

Python pip3 requirements:

PSNAWP
requests
python-dateutil
pytz
tzlocal (optional)
python-dotenv (optional)
wcwidth (optional, needed by TRUNCATE_CHARS feature)
colorama (optional, for better colours on Windows terminals)
"""

VERSION = "1.9"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
# Optional PSN ID to monitor when none is given on the command line
# A PSN ID passed as an argument always wins over this value
PSN_USER_ID = ""

# Log in to your PSN account:
# https://my.playstation.com/
#
# In another tab, visit:
# https://ca.account.sony.com/api/v1/ssocookie
#
# Copy the value of the npsso code
#
# Provide the PSN_NPSSO secret using one of the following methods:
#   - Pass it at runtime with -n / --npsso-key
#   - Set it as an environment variable (e.g. export PSN_NPSSO=...)
#   - Add it to ".env" file (PSN_NPSSO=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
#
# The refresh token generated from the npsso should remain valid for about 2 months
PSN_NPSSO = "your_psn_npsso_code"

# SMTP settings for sending email notifications
# If left as-is, no notifications will be sent
#
# Provide the SMTP_PASSWORD secret using one of the following methods:
#   - Set it as an environment variable (e.g. export SMTP_PASSWORD=...)
#   - Add it to ".env" file (SMTP_PASSWORD=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# Whether to send an email when user goes online/offline
# Can also be enabled via the -a flag
ACTIVE_INACTIVE_NOTIFICATION = False

# Whether to send an email on game start/change/stop
# Can also be enabled via the -g flag
GAME_CHANGE_NOTIFICATION = False

# Whether to send an email on errors
# Can also be disabled via the -e flag
ERROR_NOTIFICATION = True

# ----------------------------
# Webhook Notifications
# ----------------------------

# Master switch for webhook notifications through Discord or ntfy
# The event settings below select which alerts are sent
# Can also be enabled via the --webhook flag
WEBHOOK_ENABLED = False

# Service used to deliver webhook notifications: "discord" or "ntfy"
# A recognised Discord or ntfy.sh URL corrects a mismatched value at runtime
# Can also be set via the --webhook-provider flag
WEBHOOK_PROVIDER = "discord"

# Private destination used to send webhook notifications
# Discord: Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL
# ntfy: complete topic URL such as https://ntfy.sh/your-private-topic
#
# Provide the WEBHOOK_URL secret using one of the following methods:
#   - Enter it privately with --set-webhook-url
#   - Set it as an environment variable (e.g. export WEBHOOK_URL=...)
#   - Add it to ".env" file (WEBHOOK_URL=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
#
# The --webhook-url flag overrides it for one run, but leaves the private URL in shell history
WEBHOOK_URL = "your_webhook_url"

# Discord display name (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_USERNAME = "PSN Monitor"

# Discord avatar URL (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_AVATAR_URL = ""

# Whether to send a webhook alert when user goes online/offline
# Can also be enabled via the --webhook-active-inactive flag
WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = False

# Whether to send a webhook alert on game start/change/stop
# Can also be enabled via the --webhook-game-change flag
WEBHOOK_GAME_CHANGE_NOTIFICATION = False

# Whether to send a webhook alert on errors
# Can also be enabled via --webhook-errors or disabled via --no-webhook-error-notify
WEBHOOK_ERROR_NOTIFICATION = True

# Optional request headers for advanced webhook integrations
# Values support the same placeholders as WEBHOOK_TEMPLATE
WEBHOOK_HEADERS = {}

# Optional ntfy access token for Bearer authentication
#
# Provide the NTFY_ACCESS_TOKEN secret using one of the following methods:
#   - Set it as an environment variable (e.g. export NTFY_ACCESS_TOKEN=...)
#   - Add it to ".env" file (NTFY_ACCESS_TOKEN=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
NTFY_ACCESS_TOKEN = ""

# ----------------------------
# Advanced Webhook Settings
# ----------------------------

# Discord-format webhook request payload template
# Applies only when WEBHOOK_PROVIDER is "discord". The "ntfy" provider needs no template and ignores this
# value: it sends the alert body as a native ntfy message with the subject as its title. Use WEBHOOK_HEADERS
# to add ntfy options such as priority or tags
# Supported placeholders: title, description, version, color, timestamp, username and avatar_url
WEBHOOK_TEMPLATE = {
    "username": "{username}",
    "avatar_url": "{avatar_url}",
    "allowed_mentions": {
        "parse": [],
    },
    "embeds": [{
        "title": "{title}",
        "description": "{description}",
        "color": "{color}",
        "footer": {
            "text": "PSN Monitor v{version}",
        },
        "timestamp": "{timestamp}",
    }],
}

# Optional transformations applied to WEBHOOK_TEMPLATE and WEBHOOK_HEADERS values
# Tuple format: (field_to_target, method_name, *optional_arguments)
#
# Examples:
#   [
#       ("title", "upper"),
#       ("description", "replace", "**", ""),
#       ("description", "strip"),
#   ]
WEBHOOK_TRANSFORMS = []

# How often to check for player activity when the user is offline; in seconds
# Can also be set using the -c flag
PSN_CHECK_INTERVAL = 180  # 3 min

# How often to check for player activity when the user is online; in seconds
# Can also be set using the -k flag
PSN_ACTIVE_CHECK_INTERVAL = 60  # 1 min

# Set your local time zone so that PSN API timestamps are converted accordingly (e.g. 'Europe/Warsaw').
# Use this command to list all time zones supported by pytz:
#   python3 -c "import pytz; print('\\n'.join(pytz.all_timezones))"
# If set to 'Auto', the tool will try to detect your local time zone automatically (requires tzlocal)
LOCAL_TIMEZONE = 'Auto'

# If the user disconnects (offline) and reconnects (online) within OFFLINE_INTERRUPT seconds,
# the online session start time will be restored to the previous session's start time (short offline interruption),
# and previous session statistics (like total playtime and number of played games) will be preserved
OFFLINE_INTERRUPT = 420  # 7 mins

# How often to print a "liveness check" message to the output; in seconds
# Set to 0 to disable
LIVENESS_CHECK_INTERVAL = 86400  # 24 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://ca.account.sony.com/'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# Whether to verify TLS certificates on every outbound connection, email delivery included
# Only set this to False on a network that intercepts TLS with its own certificate authority
# Switching it off removes the protection against an intercepted connection
VERIFY_SSL = True

# CSV file to write all status & game changes
# Can also be set using the -b flag
CSV_FILE = ""

# File the tool saves the last seen status to, so a restart resumes from the previous session
# Leave empty to use psn_<psn_user_id>_last_status.json in the current directory
# Can also be set using the --status-file flag
PSN_STATUS_FILE = ""

# Location of the optional dotenv file which can keep secrets
# If not specified it will try to auto-search for .env files
# To disable auto-search, set this to the literal string "none"
# Can also be set using the --env-file flag
DOTENV_FILE = ""

# Base name for the log file. Output will be saved to psn_monitor_<psn_user_id>.log
# Can include a directory path to specify the location, e.g. ~/some_dir/psn_monitor
PSN_LOGFILE = "psn_monitor"

# Whether to disable logging to psn_monitor_<psn_user_id>.log
# Can also be disabled via the -d flag
DISABLE_LOGGING = False

# Controls conversion of separator-only log lines to ASCII:
#   "Auto" - enable on Windows only (default)
#   "On"   - enable on every operating system
#   "Off"  - preserve Unicode separators in logs
ASCII_LOG_SEPARATORS = "Auto"

# Whether to show rare operational events such as recoveries, resolved settings and delivery outcomes
# Independent of DEBUG_MODE, so enable both to see everything
# Can also be enabled via the --verbose flag
VERBOSE_MODE = False

# Whether to show technical diagnostics such as API calls, retries and internal state changes
# Secrets are redacted before anything is printed
# Independent of VERBOSE_MODE, so enable both to see everything
# Can also be enabled via the --debug flag
DEBUG_MODE = False

# Max characters per line when printing to screen to avoid line wrapping
# Does not affect log file output
# Set to 999 to auto-detect terminal width
# Applies only when DISABLE_LOGGING is False
# Can also be set via the --truncate flag
TRUNCATE_CHARS = 0

# Width of horizontal line
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# Whether to use coloured output in the terminal (auto-disabled if the terminal
# does not appear to support colours or when output is redirected to a file)
# Can also be disabled via the --no-color flag
COLORED_OUTPUT = True

# Colour theme used for different parts of the output
# Keys are logical names used by the tool, values are colour/style strings
# You can combine multiple attributes with spaces or '+', for example:
#   "bright_cyan bold", "yellow", "red underline", "bright_magenta bold underline", "red bold blink"
# Valid colour names: black, red, green, yellow, blue, magenta, cyan, white,
# and their bright_ variants (bright_red, bright_green, ...).
# The defaults below are what the tool uses while this block stays commented out. Uncomment it to override
# them and keep only the lines you want to change, so the rest keep following the tool's own defaults.
# COLOR_THEME = {
#     # Headings and commands the wizard tells you to run
#     "header": "bright_cyan",
#     "section": "bright_white",
#     # Identity
#     "username": "bright_cyan underline",
#     "id": "bright_magenta",
#     # Presence status values
#     "status_active": "green",
#     "status_inactive": "red",
#     "status_offline": "red",
#     "status_other": "white",
#     # PlayStation info
#     "game": "bright_yellow",
#     "platform": "blue",
#     "trophy": "bright_green",
#     "duration": "green",
#     # Activity info
#     "status_change": "yellow",
#     # Misc
#     "timestamp_label": "",
#     "timestamp_value": "cyan",
#     "info": "cyan",
#     "warning": "yellow",
#     "error": "red",
#     "signal": "yellow",
#     "email": "bright_cyan",
#     "webhook": "bright_blue",
#     # Dates
#     "date": "magenta",
#     "date_range": "magenta",
#     # Boolean values
#     "boolean_true": "green",
#     "boolean_false": "red",
#     "link": "blue underline",
# }

# Value used by signal handlers increasing/decreasing the check for player activity
# when user is online (PSN_ACTIVE_CHECK_INTERVAL); in seconds
PSN_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds
"""

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Default dummy values so linters shut up
# Do not change values below - modify them in the configuration section or config file instead
PSN_USER_ID = ""
PSN_STATUS_FILE = ""
PSN_NPSSO = ""
SMTP_HOST = ""
SMTP_PORT = 0
SMTP_USER = ""
SMTP_PASSWORD = ""
SMTP_SSL = False
SENDER_EMAIL = ""
RECEIVER_EMAIL = ""
ACTIVE_INACTIVE_NOTIFICATION = False
GAME_CHANGE_NOTIFICATION = False
ERROR_NOTIFICATION = False
WEBHOOK_ENABLED = False
WEBHOOK_PROVIDER = ""
WEBHOOK_URL = ""
WEBHOOK_USERNAME = ""
WEBHOOK_AVATAR_URL = ""
WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = False
WEBHOOK_GAME_CHANGE_NOTIFICATION = False
WEBHOOK_ERROR_NOTIFICATION = False
WEBHOOK_HEADERS: dict = {}
WEBHOOK_TEMPLATE: dict = {}
WEBHOOK_TRANSFORMS: list = []
NTFY_ACCESS_TOKEN = ""
PSN_CHECK_INTERVAL = 0
PSN_ACTIVE_CHECK_INTERVAL = 0
LOCAL_TIMEZONE = ""

# How the running timezone was arrived at, so Doctor can name the outcome the way the sibling monitors do
LOCAL_TIMEZONE_STATE = "config"
OFFLINE_INTERRUPT = 0
LIVENESS_CHECK_INTERVAL = 0
CHECK_INTERNET_URL = ""
CHECK_INTERNET_TIMEOUT = 0
VERIFY_SSL = True
CSV_FILE = ""
DOTENV_FILE = ""
PSN_LOGFILE = ""
DISABLE_LOGGING = False
ASCII_LOG_SEPARATORS = "Auto"
VERBOSE_MODE = False
DEBUG_MODE = False

# True once monitoring has printed its header, so a verbose notice after that closes its own block
MONITORING_ACTIVE = False

TRUNCATE_CHARS = 0
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
COLORED_OUTPUT = False
COLOR_THEME: dict = {}
PSN_ACTIVE_CHECK_SIGNAL_VALUE = 0

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "psn_monitor.conf"

# List of secret keys to load from env/config
SECRET_KEYS = ("PSN_NPSSO", "SMTP_PASSWORD", "WEBHOOK_URL", "NTFY_ACCESS_TOKEN")

# Records where each secret was finally resolved from, filled in as the documented precedence is applied.
# The winning source cannot be reconstructed afterwards, because the same key may sit in several places
SECRET_SOURCES = {}

# The closed set of layers a secret can come from, so a typo raises instead of inventing a source
SECRET_SOURCE_ORDER = ("configuration file", "dotenv file", "environment", "command line")

# Secret keys that were already exported when the tool started, so a dotenv file cannot be credited for them
EXPORTED_SECRET_KEYS = frozenset()

# Default value for timeouts in alarm signal handler; in seconds
FUNCTION_TIMEOUT = 15

# Seconds rather than checks, because a failing run usually retries on a different interval than a healthy one
LIVENESS_REMINDER_SECONDS = LIVENESS_CHECK_INTERVAL if LIVENESS_CHECK_INTERVAL > 0 else 0

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name']

CLI_CONFIG_PATH = None

# Set when --config-file none switches discovery off, so no later lookup can find a file the run rejected
CONFIG_DISCOVERY_DISABLED = False

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"

PLATFORM_DISPLAY_NAMES = {
    "PS5": "PlayStation 5",
    "PS4": "PlayStation 4",
    "PS3": "PlayStation 3",
    "PSVITA": "PlayStation Vita",
    "PS_VITA": "PlayStation Vita",
    "PSPC": "PlayStation PC",
    "MOBILE_APP": "PlayStation App (mobile)",
}


STARTUP_BANNER = r"""
 .---------------.    ____  ____  _   _
|       /\       |   |  _ \/ ___|| \ | |
|      /__\      |   | |_) \___ \|  \| |
|   []      ()   |   |  __/ ___) | |\  |
|       ><       |   |_|   |____/|_| \_|
 '---------------'
                      __  __             _ _
                     |  \/  | ___  _ __ (_) |_ ___  _ __
                     | |\/| |/ _ \| '_ \| | __/ _ \| '__|
                     | |  | | (_) | | | | | || (_) | |
                     |_|  |_|\___/|_| |_|_|\__\___/|_|"""


# Held in one place so the startup gate and the doctor Environment check can never disagree
MINIMUM_PYTHON_VERSION = (3, 10)
MINIMUM_PYTHON_VERSION_TEXT = ".".join(str(part) for part in MINIMUM_PYTHON_VERSION)

import sys

if sys.version_info < MINIMUM_PYTHON_VERSION:
    print(f"* Error: Python version {MINIMUM_PYTHON_VERSION_TEXT} or higher required !")
    sys.exit(1)

import time
import json
import os
from datetime import datetime, timezone
from dateutil import relativedelta
from dateutil.parser import isoparse
import calendar
import requests as req
import urllib3
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
import argparse
import ast
import csv
try:
    import pytz
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the pytz library !\n\nTo install it, run:\n    pip3 install pytz\n\nOnce installed, re-run this tool")
try:
    from tzlocal import get_localzone
except ImportError:
    get_localzone = None
import platform
import re
import ipaddress
from urllib.parse import urlsplit
try:
    from psnawp_api import PSNAWP
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the PSNAWP library !\n\nTo install it, run:\n    pip3 install PSNAWP\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://github.com/isFakeAccount/psnawp")
import importlib.util
import shlex
import shutil
import getpass
import subprocess
import tempfile
import textwrap
from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
try:
    from colorama import init as colorama_init  # type: ignore[import]
except ImportError:
    colorama_init = None


# Probes the PSN OAuth endpoint with the given npsso and returns a specific error hint if the redirect carries a recognizable error such as ToSUA re-acceptance, otherwise None
def probe_npsso_auth_error(npsso):
    try:
        import uuid
        from urllib.parse import urlparse, parse_qs
        from psnawp_api.core.authenticator import Authenticator
        from psnawp_api.utils.endpoints import BASE_PATH, API_PATH
    except Exception as diag_exc:
        debug_print("Auth probe unavailable, PSNAWP internals could not be imported", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
        return None
    try:
        md = Authenticator.AUTH_METADATA
        cid = str(uuid.UUID(int=uuid.getnode()))
        headers = {
            "Cookie": f"npsso={npsso}",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "com.scee.psxandroid",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-User": "?1",
        }
        params = {
            "access_type": "offline",
            "cid": cid,
            "client_id": md["CLIENT_ID"],
            "device_base_font_size": "10",
            "device_profile": "mobile",
            "elements_visibility": "no_aclink",
            "enable_scheme_error_code": "true",
            "no_captcha": "true",
            "PlatformPrivacyWs1": "minimal",
            "redirect_uri": md["REDIRECT_URI"],
            "response_type": "code",
            "scope": md["SCOPE"],
            "service_entity": "urn:service-entity:psn",
            "service_logo": "ps",
            "smcid": "psapp:signin",
            "support_scheme": "sneiprls",
            "turnOnTrustedBrowser": "true",
            "ui": "pr",
        }
        debug_print("Auth probe", url=f"{BASE_PATH['base_uri']}{API_PATH['oauth_code']}", timeout="15s")
        resp = req.get(f"{BASE_PATH['base_uri']}{API_PATH['oauth_code']}", headers=headers, params=params, allow_redirects=False, timeout=15, verify=VERIFY_SSL)
        debug_print("Auth probe", status=resp.status_code)
        loc = resp.headers.get("location", "")
        if not loc:
            return None
        q = parse_qs(urlparse(loc).query)
        err = (q.get("error") or [""])[0]
        err_code = (q.get("error_code") or [""])[0]
        err_desc = (q.get("error_description") or [""])[0]
        if not err and not err_code:
            return None
        desc_l = err_desc.lower()
        if err_code == "103" or "tosua" in desc_l or "terms of service" in desc_l or "terms of use" in desc_l:
            return ("PSN Terms of Service / User Agreement must be re-accepted. Log into your account at https://my.account.sony.com or in the PlayStation App to accept the updated Terms of Service and try again.")
        return f"PSN auth rejected (error={err or 'n/a'} error_code={err_code or 'n/a'} error_description={err_desc or 'n/a'})"
    except Exception as diag_exc:
        debug_print("Auth probe against the PSN OAuth endpoint", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
        return None


# Tagged exception raised when a PSN API response does not match the expected shape
class PsnMalformedResponse(ValueError):
    pass


# Yields the exception and each cause/context up to max_depth to walk an exception chain
def iter_exc_chain(ex, max_depth=8):
    cur = ex
    for _ in range(max_depth):
        if cur is None:
            return
        yield cur
        cur = getattr(cur, "__cause__", None) or getattr(cur, "__context__", None)


# Returns True if any exception in the chain indicates too many open files (errno 24)
def is_too_many_open_files(ex):
    for cur in iter_exc_chain(ex):
        if isinstance(cur, OSError) and getattr(cur, "errno", None) == 24:
            return True
        msg = str(cur).lower()
        if "too many open files" in msg or "oserror(24" in msg or "errno 24" in msg:
            return True
    return False


# Documentation the recovery advice points at, kept as README anchors so one file stays the source of truth
DOCS_BASE_URL = "https://misiektoja.github.io/psn_monitor"
INSTALLATION_GUIDE_URL = f"{DOCS_BASE_URL}/installation/"
QUICK_START_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/"
CONFIG_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#configuration-file"
NPSSO_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#psn-npsso-code"
SECRETS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#storing-secrets"
PRIVACY_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#user-privacy-settings"
TIMEZONE_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#time-zone"
SMTP_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#smtp-settings"
TLS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#tls-verification"
WEBHOOK_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#webhook-settings"
INTERVALS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#check-intervals"
DIAGNOSTICS_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#verbose-and-debug-output"

# Installs this tool can be running from. There is no container image, so no container method is detected
INSTALL_METHODS = ("pip", "manual")

# How the positional target may be written. Reused by the welcome screen and by the recovery advice, because
# three hand-written phrasings of the same list is what these tools drift into
PSN_TARGET_FORMS = "PlayStation online ID, not the account e-mail or the real name"


# Returns whether this process was started from the packaged entry point or from a downloaded script
def detect_install_method():
    return "manual" if os.path.basename(sys.argv[0] or "").endswith(".py") else "pip"


# Returns a readable name for one install method
def install_method_display_name(method=None):
    return {"pip": "PyPI install", "manual": "downloaded script"}.get(method or detect_install_method(), "unknown install")


# Returns one command argument quoted for the shell of the host operating system
def quote_command_argument(argument):
    text = str(argument)
    # A <placeholder> is documentation for the reader to replace, so quoting it would only be noise
    if text.startswith("<") and text.endswith(">"):
        return text
    return subprocess.list2cmdline([text]) if platform.system() == "Windows" else shlex.quote(text)


# Returns the command that starts this tool on the detected install, as the argument parts before any option
def install_command_prefix(method=None):
    if (method or detect_install_method()) == "manual":
        return [("python" if platform.system() == "Windows" else "python3"), Path(__file__).name]
    return ["psn_monitor"]


# True when a command writes the dotenv file itself, so it refuses an --env-file that switches dotenv loading off
def command_writes_dotenv(arguments=()):
    return any(str(argument) == "--setup" or str(argument).startswith("--set-") for argument in arguments)


# True when a command writes the config file itself, so it refuses a --config-file that switches discovery off
def command_writes_config(arguments=()):
    return any(str(argument) == "--setup" for argument in arguments)


# Returns the --config-file and --env-file arguments this run was given, skipping any the caller already passed
def active_path_arguments(arguments=()):
    given = {str(argument) for argument in arguments}
    paths = []
    active_config = CLI_CONFIG_PATH or ("none" if CONFIG_DISCOVERY_DISABLED else None)
    # The "none" sentinel is carried so the printed command checks the setup this run checked, except into a
    # command that writes the config file, since those refuse the sentinel at their own argument gate
    if active_config and "--config-file" not in given and not (str(active_config).casefold() == "none" and command_writes_config(arguments)):
        paths.extend(("--config-file", str(active_config)))
    # The "none" sentinel is carried so the printed command checks the setup this run checked, except into a
    # command that writes the dotenv file, since those refuse the sentinel at their own argument gate
    if DOTENV_FILE and "--env-file" not in given and not (str(DOTENV_FILE).casefold() == "none" and command_writes_dotenv(arguments)):
        paths.extend(("--env-file", str(DOTENV_FILE)))
    return paths


# Returns a copy-pasteable command line for this tool, carrying the config and dotenv paths this run was given
def render_command(arguments=None, include_paths=True, *, method=None):
    selected = [str(argument) for argument in (arguments or ())]
    parts = [*install_command_prefix(method), *selected, *(active_path_arguments(selected) if include_paths else ())]
    return " ".join(quote_command_argument(part) for part in parts)


# Stable recovery categories. Every code here is produced somewhere in this file, and nothing else is accepted
RECOVERY_CODES = frozenset({
    "config.missing", "config.invalid", "config.insecure", "dependency.missing", "secret.missing",
    "auth.npsso_invalid", "auth.npsso_expired", "auth.tos_required",
    "network.unavailable", "network.timeout",
    "psn.malformed_response", "psn.rate_limited", "resource.exhausted",
    "target.missing", "target.not_found", "target.not_visible",
    "smtp.invalid", "smtp.authentication", "smtp.connection",
    "webhook.invalid", "webhook.rejected", "webhook.rate_limited", "webhook.connection",
    "file.exists", "file.unreadable", "file.unwritable", "secret.entry", "unknown",
})

# How the monitoring loop retries each category. Anything absent falls back to the unknown policy
RECOVERY_CODE_POLL_KINDS = {
    "resource.exhausted": "exhausted",
    "auth.npsso_invalid": "auth",
    "auth.npsso_expired": "auth",
    "auth.tos_required": "auth",
    "psn.malformed_response": "malformed",
    "network.timeout": "transient",
    "network.unavailable": "transient",
}

# How long the monitoring loop waits before reporting, rebuilding the session and alerting, per retry policy
RECOVERY_POLL_POLICY = {
    "auth": {"report_after": 1, "recreate_after": 1, "alert_after": 1},
    "malformed": {"report_after": 1, "recreate_after": 1, "alert_after": 3},
    "transient": {"report_after": 3, "recreate_after": 3, "alert_after": 20},
    "unknown": {"report_after": 1, "recreate_after": 3, "alert_after": 5},
}

# Categories where asking the PSN OAuth endpoint what it thinks can sharpen a vague library error
PROBE_WORTHY_RECOVERY_CODES = frozenset({"auth.npsso_invalid", "auth.npsso_expired", "psn.malformed_response", "unknown"})


# Carries one recovery category together with guidance that is safe to print
@dataclass(frozen=True)
class RecoveryAdvice:
    code: str
    summary: str
    fix: str
    retryable: bool
    detail: str = ""


# Carries recovery advice across an exception boundary with the original cause attached
class RecoveryError(Exception):
    # Stores the advice and links the original cause so a traceback still points at the real failure
    def __init__(self, advice, cause=None):
        self.advice = advice
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause
        super().__init__(advice.summary)


# Builds one piece of advice, rejecting any code outside the taxonomy and redacting every field
def make_recovery_advice(code, summary, fix, retryable, detail=""):
    if code not in RECOVERY_CODES:
        raise ValueError(f"Unsupported recovery code: {code}")
    return RecoveryAdvice(code, sanitize_error_text(summary), sanitize_error_text(fix), retryable, sanitize_error_text(detail))


# Appends the documentation link that matches the fix, on its own line
def recovery_fix_with_guide(fix, guide_url):
    return f"{fix}\nGuide: {guide_url}"


# Returns the advice a cancelled secret entry reports, worded the same way by every one-shot secret command
def secret_entry_cancelled_advice(subject, flag, guide_url):
    return make_recovery_advice("secret.entry", f"{subject[:1].upper()}{subject[1:]} setup was cancelled and the dotenv file was not changed", recovery_fix_with_guide(f"Run {flag} again when you have the value ready", guide_url), False)


# Returns the advice a declined secret replacement reports, worded the same way by every one-shot secret command
def secret_replacement_declined_advice(subject, flag, guide_url, plural=False):
    kept = "were left as they are" if plural else "was left as it is"
    return make_recovery_advice("secret.entry", f"The saved {subject} {kept} and the dotenv file was not changed", recovery_fix_with_guide(f"Run {flag} again and answer y to replace the saved value", guide_url), False)


# Returns the command that installs one optional library into the interpreter running this tool
def pip_install_command(requirement):
    return " ".join(quote_command_argument(part) for part in (sys.executable or "python3", "-m", "pip", "install", requirement))


# Returns advice for an optional library that is missing, naming the exact install command for this interpreter
def missing_dependency_advice(package, effect, alternative=""):
    fix = f"Install it with: {pip_install_command(package)}"
    if alternative:
        fix = f"{fix}. {alternative}"
    return make_recovery_advice("dependency.missing", f"{effect} because the optional '{package}' library is missing", recovery_fix_with_guide(fix, INSTALLATION_GUIDE_URL), False)


# Returns install-aware guidance for replacing the NPSSO code, which differs once monitoring has started
def npsso_recovery_fix(monitoring=False):
    command = render_command(["<psn_user_id>", "-n", "<npsso_code>"])
    if monitoring:
        return f"Generate a fresh NPSSO code, put it in PSN_NPSSO in your dotenv file then send SIGHUP to this process. To restart instead, run: {command}"
    return f"Generate a fresh NPSSO code, then put it in PSN_NPSSO in your dotenv file or pass it directly: {command}"


# Returns the optional requests and PSNAWP exception types, so a missing library only reduces precision
def recovery_exception_types():
    types = {"timeout": [TimeoutError, TimeoutException], "unavailable": [ConnectionError], "auth": [], "not_found": [], "forbidden": [], "rate_limited": []}
    try:
        from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout as RequestsTimeout, SSLError as RequestsSSLError, ChunkedEncodingError as RequestsChunkedEncodingError
        types["timeout"].append(RequestsTimeout)
        types["unavailable"].extend((RequestsConnectionError, RequestsSSLError, RequestsChunkedEncodingError))
    except Exception as diag_exc:
        debug_print("requests exception types unavailable, transient error detection is reduced", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
    try:
        from psnawp_api.core.psnawp_exceptions import PSNAWPAuthenticationError, PSNAWPForbiddenError, PSNAWPInvalidTokenError, PSNAWPNotFoundError, PSNAWPTooManyRequestsError, PSNAWPUnauthorizedError
        types["auth"].extend((PSNAWPAuthenticationError, PSNAWPUnauthorizedError, PSNAWPInvalidTokenError))
        types["not_found"].append(PSNAWPNotFoundError)
        types["forbidden"].append(PSNAWPForbiddenError)
        types["rate_limited"].append(PSNAWPTooManyRequestsError)
    except Exception as diag_exc:
        debug_print("PSNAWP exception types unavailable, PSN errors fall back to text matching", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
    return {name: tuple(values) for name, values in types.items()}


# Classifies a failure by exception type, then by message, without contacting PSN
def classify_recovery_error_offline(error=None, context="runtime", detail=""):
    safe_detail = sanitize_error_text(detail or error or "")
    # Both are matched, since a caller that adds context would otherwise hide the error text the rules read
    message = " ".join(part for part in (str(detail or ""), str(error or "")) if part).lower()
    monitoring = context == "monitor"

    if error is not None and is_too_many_open_files(error):
        # Repeated auth refreshes against an expired NPSSO are a common way to reach the limit, so say so
        npsso_note = " This can also be a side effect of repeated PSN auth refreshes, so check your NPSSO code once the limit is raised." if ("oauth/token" in message or "authz" in message or "npsso" in message) else ""
        return make_recovery_advice("resource.exhausted", "This process ran out of file descriptors, which is a local limit and not a PlayStation Network problem", recovery_fix_with_guide(f"Raise the file descriptor limit, for example with 'ulimit -n 4096', or set LimitNOFILE= if you run under systemd, then restart the tool.{npsso_note}", DIAGNOSTICS_GUIDE_URL), False, safe_detail)

    if context == "config.missing":
        return make_recovery_advice("config.missing", safe_detail or "The configuration file was not found", recovery_fix_with_guide(f"Check the --config-file path, or create one with: {render_command(['--generate-config', 'psn_monitor.conf'], include_paths=False)}", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "config.invalid":
        return make_recovery_advice("config.invalid", safe_detail or "The configuration file could not be loaded", recovery_fix_with_guide(f"Config files are read as data. Only documented SETTING = value lines with plain literal values are accepted. Correct the reported line, or write a fresh template to a different path with: {render_command(['--generate-config', '<new-file>'], include_paths=False)}", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "secret.missing":
        return make_recovery_advice("secret.missing", safe_detail or "A required credential is missing", recovery_fix_with_guide(npsso_recovery_fix(), SECRETS_GUIDE_URL), False, safe_detail)

    if context == "target.missing":
        return make_recovery_advice("target.missing", safe_detail or "No PlayStation ID was provided", recovery_fix_with_guide(f"Pass the account to watch: {render_command(['<psn_user_id>'])}. Use the {PSN_TARGET_FORMS}", QUICK_START_GUIDE_URL), False, safe_detail)

    if context == "secret.entry":
        return make_recovery_advice("secret.entry", safe_detail or "The value was not entered, so nothing was written", recovery_fix_with_guide("Run the command again from an interactive terminal and enter the value when prompted", SECRETS_GUIDE_URL), False, safe_detail)

    if context == "file.exists":
        return make_recovery_advice("file.exists", safe_detail or "The destination file already exists", recovery_fix_with_guide("Re-run with --force to replace it after a timestamped backup, or write to a different path", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "smtp.settings":
        return make_recovery_advice("smtp.invalid", f"The SMTP settings are incorrect: {safe_detail}" if safe_detail else "The SMTP settings are incorrect", recovery_fix_with_guide(f"Check SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL and RECEIVER_EMAIL then run: {render_command(['--send-test-email'])}", SMTP_GUIDE_URL), False, safe_detail)

    if context == "webhook":
        if "429" in message or "rate limit" in message:
            return make_recovery_advice("webhook.rate_limited", "The webhook service is rate limiting deliveries", recovery_fix_with_guide(f"Enable fewer webhook alert types, or wait until the service accepts deliveries again, then run: {render_command(['--send-test-webhook'])}", WEBHOOK_GUIDE_URL), True, safe_detail)
        # Every configuration problem this tool reports names the setting that has to change, which the
        # text of a rejection from Discord or ntfy never does
        if "webhook_" in message or "ntfy_access_token" in message:
            return make_recovery_advice("webhook.invalid", safe_detail or "The webhook settings cannot be used", recovery_fix_with_guide(f"Correct the reported setting, then run: {render_command(['--send-test-webhook'])}", WEBHOOK_GUIDE_URL), False, safe_detail)
        if any(term in message for term in ("could not be reached", "connection", "timed out", "timeout")):
            return make_recovery_advice("webhook.connection", "The webhook service could not be reached", recovery_fix_with_guide("Check your internet connection, DNS and firewall, then try again", WEBHOOK_GUIDE_URL), True, safe_detail)
        return make_recovery_advice("webhook.rejected", safe_detail or "The webhook service refused the delivery", recovery_fix_with_guide(f"Confirm the webhook still exists and that the saved URL is current, then run: {render_command(['--send-test-webhook'])}", WEBHOOK_GUIDE_URL), False, safe_detail)

    if context == "file.unreadable":
        return make_recovery_advice("file.unreadable", safe_detail or "A file the tool needs could not be read", recovery_fix_with_guide("Check that the path exists and that this user can read it, then retry", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if context == "file.unwritable":
        # The wizard reaches this either because a destination was switched off or because the path cannot be written
        if "nowhere to write the secrets" in message:
            return make_recovery_advice("file.unwritable", safe_detail or "--setup has nowhere to write the secrets", recovery_fix_with_guide("Replace '--env-file none' with a writable path, or drop the flag to write .env in the current directory", SECRETS_GUIDE_URL), False, safe_detail)
        if "nowhere to write the configuration" in message:
            return make_recovery_advice("file.unwritable", safe_detail or "--setup has nowhere to write the configuration", recovery_fix_with_guide(f"Replace '--config-file none' with a writable path, or drop the flag to write {DEFAULT_CONFIG_FILENAME} in the current directory", CONFIG_GUIDE_URL), False, safe_detail)
        return make_recovery_advice("file.unwritable", safe_detail or "A file the tool needs could not be written", recovery_fix_with_guide("Check that the directory exists, that this user can write to it and that there is free space, then retry", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if context == "connectivity":
        # Classified from the error, because the detail names the endpoint rather than the failure
        cause = str(error or "").lower()
        if "timed out" in cause or "timeout" in cause:
            return make_recovery_advice("network.timeout", "The connectivity endpoint did not answer in time", "Check network, DNS, proxy and CHECK_INTERNET_URL settings", True, safe_detail)
        return make_recovery_advice("network.unavailable", "The connectivity endpoint could not be reached", "Check network, DNS, proxy and CHECK_INTERNET_URL settings", True, safe_detail)

    types = recovery_exception_types()

    if context.startswith("smtp"):
        for current in iter_exc_chain(error):
            if isinstance(current, smtplib.SMTPAuthenticationError):
                return make_recovery_advice("smtp.authentication", "The SMTP server rejected the login", recovery_fix_with_guide(f"Check SMTP_USER and SMTP_PASSWORD. Providers such as Gmail need an app password rather than the account password. Then run: {render_command(['--send-test-email'])}", SMTP_GUIDE_URL), False, safe_detail)
            if isinstance(current, smtplib.SMTPException) or isinstance(current, types["timeout"]) or isinstance(current, types["unavailable"]) or isinstance(current, (ssl.SSLError, OSError)):
                return make_recovery_advice("smtp.connection", "The SMTP server could not be reached", recovery_fix_with_guide(f"Check SMTP_HOST, SMTP_PORT and SMTP_SSL, and that the port is not blocked. Then run: {render_command(['--send-test-email'])}", SMTP_GUIDE_URL), True, safe_detail)

    for current in iter_exc_chain(error):
        if isinstance(current, PsnMalformedResponse):
            return make_recovery_advice("psn.malformed_response", "PlayStation Network returned a presence response in an unexpected shape", recovery_fix_with_guide("Nothing to do in most cases, the tool rebuilds its session and retries. If it continues, upgrade PSNAWP and rerun with --debug", DIAGNOSTICS_GUIDE_URL), True, safe_detail)
        if types["rate_limited"] and isinstance(current, types["rate_limited"]):
            return make_recovery_advice("psn.rate_limited", "PlayStation Network is rate limiting this account", recovery_fix_with_guide("Raise PSN_CHECK_INTERVAL and PSN_ACTIVE_CHECK_INTERVAL, or run fewer instances against the same account, then restart", INTERVALS_GUIDE_URL), True, safe_detail)
        if types["not_found"] and isinstance(current, types["not_found"]):
            return make_recovery_advice("target.not_found", "PlayStation Network does not know that PlayStation ID", recovery_fix_with_guide(f"Check the spelling. Use the {PSN_TARGET_FORMS}", QUICK_START_GUIDE_URL), False, safe_detail)
        if types["forbidden"] and isinstance(current, types["forbidden"]):
            return make_recovery_advice("target.not_visible", "That PlayStation profile does not share its activity with this account", recovery_fix_with_guide("Ask the monitored user to set Privacy Settings, Personal Info | Messaging, Online Status and Now Playing to 'Friends only' or 'Anyone', and add this account as a friend if they chose 'Friends only'", PRIVACY_GUIDE_URL), False, safe_detail)
        if types["auth"] and isinstance(current, types["auth"]):
            return make_recovery_advice("auth.npsso_expired" if monitoring else "auth.npsso_invalid", "PlayStation Network rejected the NPSSO code" if monitoring else "PlayStation Network did not accept the NPSSO code", recovery_fix_with_guide(npsso_recovery_fix(monitoring), NPSSO_GUIDE_URL), False, safe_detail)
        if isinstance(current, types["timeout"]):
            return make_recovery_advice("network.timeout", "PlayStation Network took too long to answer", recovery_fix_with_guide("Nothing to do in most cases, the tool retries on its own. If it continues, check your connection and any proxy", DIAGNOSTICS_GUIDE_URL), True, safe_detail)
        if isinstance(current, types["unavailable"]):
            return make_recovery_advice("network.unavailable", "PlayStation Network could not be reached", recovery_fix_with_guide("Nothing to do in most cases, the tool retries on its own. If it continues, check your internet connection, DNS and firewall", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if "too many requests" in message or "rate limit" in message or "429" in message:
        return make_recovery_advice("psn.rate_limited", "PlayStation Network is rate limiting this account", recovery_fix_with_guide("Raise PSN_CHECK_INTERVAL and PSN_ACTIVE_CHECK_INTERVAL, or run fewer instances against the same account, then restart", INTERVALS_GUIDE_URL), True, safe_detail)

    if ("your npsso code has expired" in message or "something went wrong while authenticating" in message or "invalid_grant" in message or "invalid npsso" in message or (("oauth/token" in message or "authz" in message) and ("401" in message or "403" in message or "unauthorized" in message or "forbidden" in message))):
        return make_recovery_advice("auth.npsso_expired" if monitoring else "auth.npsso_invalid", "PlayStation Network rejected the NPSSO code" if monitoring else "PlayStation Network did not accept the NPSSO code", recovery_fix_with_guide(npsso_recovery_fix(monitoring), NPSSO_GUIDE_URL), False, safe_detail)

    if "read timed out" in message or "timeout" in message or "timed out" in message:
        return make_recovery_advice("network.timeout", "PlayStation Network took too long to answer", recovery_fix_with_guide("Nothing to do in most cases, the tool retries on its own. If it continues, check your connection and any proxy", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if "remote end closed connection" in message or "connection reset by peer" in message or "connection aborted" in message or "temporarily unavailable" in message:
        return make_recovery_advice("network.unavailable", "PlayStation Network could not be reached", recovery_fix_with_guide("Nothing to do in most cases, the tool retries on its own. If it continues, check your internet connection, DNS and firewall", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    for current in iter_exc_chain(error):
        if isinstance(current, (AttributeError, TypeError)):
            return make_recovery_advice("psn.malformed_response", "PlayStation Network returned a presence response in an unexpected shape", recovery_fix_with_guide("Nothing to do in most cases, the tool rebuilds its session and retries. If it continues, upgrade PSNAWP and rerun with --debug", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    return make_recovery_advice("unknown", "Something unexpected went wrong", recovery_fix_with_guide(unknown_failure_fix(), DIAGNOSTICS_GUIDE_URL), True, safe_detail)

# Returns the next step for a failure no rule recognized, since a run already printing the technical cause cannot be told to re-run for it
def unknown_failure_fix(): return "Check the technical detail below, then open an issue with this output if the problem continues" if DEBUG_MODE else "Rerun with --debug and check the technical detail it prints. If the problem continues, open an issue with that output"



# Classifies any failure into one stable recovery category, optionally asking PSN to explain a vague error
def classify_recovery_error(error=None, context="runtime", detail="", probe_auth=False):
    if isinstance(error, RecoveryError):
        return error.advice

    advice = classify_recovery_error_offline(error, context, detail)
    if not probe_auth or advice.code not in PROBE_WORTHY_RECOVERY_CODES:
        return advice

    hint = probe_npsso_auth_error(PSN_NPSSO)
    if not hint:
        return advice
    if "terms of service" in hint.lower() or "terms of use" in hint.lower():
        return make_recovery_advice("auth.tos_required", "PlayStation Network needs its Terms of Service accepted again", recovery_fix_with_guide("Sign in at https://my.account.sony.com or in the PlayStation App, accept the updated Terms of Service then retry", NPSSO_GUIDE_URL), False, hint)
    monitoring = context == "monitor"
    return make_recovery_advice("auth.npsso_expired" if monitoring else "auth.npsso_invalid", "PlayStation Network rejected the NPSSO code", recovery_fix_with_guide(npsso_recovery_fix(monitoring), NPSSO_GUIDE_URL), False, hint)


# Returns the retry policy the monitoring loop applies to one piece of advice
def recovery_poll_kind(advice):
    return RECOVERY_CODE_POLL_KINDS.get(advice.code, "unknown")


# Renders one piece of advice, adding the fix paragraph and the technical detail only where they help
def render_recovery_advice(advice, debug=None, retry_note="", with_fix=True, label="Error"):
    lines = [f"* {label}: {advice.summary}" + (f" ({retry_note})" if retry_note else "")]
    if with_fix:
        lines.append(f"To fix: {advice.fix}")
        # A detail that only repeats the summary spends a line saying nothing
        if (DEBUG_MODE if debug is None else debug) and advice.detail and advice.detail != advice.summary:
            lines.append(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return "\n".join(lines)


# Prints one built advice through the shared recovery block and returns it
def print_recovery_advice(advice, debug=None, retry_note="", with_fix=True, label="Error", tracker=None):
    print(render_recovery_advice(advice, debug, retry_note, with_fix and (tracker is None or tracker.should_render(advice)), label))
    return advice


# Classifies one failure and renders it through the shared recovery block
def render_recovery_error(error=None, context="runtime", debug=None, detail="", retry_note="", with_fix=True, label="Error", probe_auth=False):
    return render_recovery_advice(classify_recovery_error(error, context, detail, probe_auth), debug, retry_note, with_fix, label)


# Classifies one failure, prints it through the shared recovery block and returns its stable advice
def print_recovery_error(error=None, context="runtime", debug=None, detail="", retry_note="", with_fix=True, label="Error", tracker=None, probe_auth=False):
    return print_recovery_advice(classify_recovery_error(error, context, detail, probe_auth), debug, retry_note, with_fix, label, tracker)


# Builds the subject line for one recovery notification
def recovery_email_subject(advice, psn_user_id):
    return f"psn_monitor: {advice.summary} (user: {psn_user_id})"


# Builds the body for one recovery notification, repeating the fix the operator sees on screen
def recovery_email_body(advice, error_streak=0):
    lines = [advice.summary, "", f"To fix: {advice.fix}"]
    if error_streak > 1:
        lines.extend(["", f"Failed checks in a row: {error_streak}"])
    if advice.detail:
        lines.extend(["", f"Technical detail: {advice.detail}"])
    return "\n".join(lines) + get_cur_ts("\n\nTimestamp: ")


# Decides how a lasting failure is reported: in full when it is new, then on the liveness cadence while it lasts
class OutageReporter:
    # Starts with no failure recorded, so the first failure of any category is reported in full
    def __init__(self):
        self.code = None
        self.since = 0
        self.reported_at = 0

    # Records one failed check and returns "full" for a new failure, "degraded" once the liveness interval has passed,
    # "repeat" while the liveness banner is switched off or "" while the same failure is merely continuing
    def failed(self, advice, liveness_interval):
        now = int(time.time())
        if advice.code != self.code:
            self.code = advice.code
            self.since = now
            self.reported_at = now
            return "full"
        # With the liveness banner off there is nothing to carry the reminder, so the summary keeps its old cadence
        if not liveness_interval:
            return "repeat"
        # Timed rather than counted, because a failing run usually retries on a different interval than a healthy one
        if now - self.reported_at >= liveness_interval:
            self.reported_at = now
            return "degraded"
        return ""

    # Clears the failure after a successful check and returns how long it lasted, or None when none was active
    def recovered(self):
        if not self.code:
            return None
        lasted = int(time.time()) - self.since
        self.code = None
        self.since = 0
        self.reported_at = 0
        return lasted


# Reports that nothing changed, so a quiet run still says it is alive on the liveness cadence
def print_liveness_banner(message):
    print(f"* {sanitize_error_text(message)}")
    print_cur_ts("Liveness check, timestamp:\t")


# Reports a lasting failure on the liveness cadence, so a broken run still says it is alive without repeating itself
def print_outage_liveness(target, advice, since):
    print(f"* Monitoring degraded for {target}. {advice.summary} since {get_date_from_ts(since)}")
    print_cur_ts("Liveness check, timestamp:\t")


# Reports that a failure cleared, since a throttled failure no longer stops printing when it is over
def print_outage_recovery(target, lasted):
    print(f"* Monitoring recovered for {target} after {display_time(max(1, lasted))}")
    print_cur_ts("Timestamp:\t\t\t")


# Suppresses a repeated fix paragraph until the failure category changes or a check succeeds
class RecoveryHintTracker:
    # Starts with no category recorded, so the first failure is always reported in full
    def __init__(self):
        self.last_code = None

    # Reports whether this category is new and therefore worth printing the fix for again
    def should_render(self, advice):
        if advice.code == self.last_code:
            return False
        self.last_code = advice.code
        return True

    # Clears the suppression after a successful check
    def reset(self):
        self.last_code = None


# Parses a PSN presence response into normalized fields raising PsnMalformedResponse for any unexpected shape
def parse_presence(pres):
    if not isinstance(pres, dict):
        raise PsnMalformedResponse(f"malformed presence response: top-level is {type(pres).__name__}")
    basic = pres.get("basicPresence")
    if not isinstance(basic, dict):
        raise PsnMalformedResponse(f"malformed presence response: basicPresence is {type(basic).__name__}")
    primary = basic.get("primaryPlatformInfo")
    if not isinstance(primary, dict):
        raise PsnMalformedResponse(f"malformed presence response: primaryPlatformInfo is {type(primary).__name__}")
    gtil = basic.get("gameTitleInfoList")
    if gtil is not None and not isinstance(gtil, list):
        raise PsnMalformedResponse(f"malformed presence response: gameTitleInfoList is {type(gtil).__name__}")
    game_entry = None
    if gtil:
        first = gtil[0]
        if not isinstance(first, dict):
            raise PsnMalformedResponse(f"malformed presence response: gameTitleInfoList[0] is {type(first).__name__}")
        game_entry = first
    return {
        "status": primary.get("onlineStatus"),
        "platform": primary.get("platform"),
        "last_online": primary.get("lastOnlineDate"),
        "availability": basic.get("availability"),
        "game_name": (game_entry.get("titleName") if game_entry else None),
        "launch_platform": (game_entry.get("launchPlatform") if game_entry else None),
    }


# Converts a PSN platform code into a readable label while preserving unknown values
def format_platform_display(platform_value):
    if not platform_value:
        return ""
    platform_key = str(platform_value).strip().upper()
    return PLATFORM_DISPLAY_NAMES.get(platform_key, platform_key.replace("_", " "))


# A value shorter than this is an ordinary word at least as often as it is a secret, so replacing it wherever
# it appears would corrupt the text it was added to protect. The assignment, cookie and header patterns below
# still redact a short secret everywhere an error can realistically expose one
MIN_REDACTABLE_SECRET_LENGTH = 12


# Reports whether a secret holds a real value rather than being empty or one of the shipped placeholders
def secret_is_set(value):
    return isinstance(value, str) and bool(value.strip()) and not value.startswith("your_")



# Joins setting names into the phrase a message reads out, for example "SMTP_HOST and SMTP_USER"
def join_setting_names(names, conjunction):
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} {conjunction} {names[-1]}"


# Returns every redactable secret value currently known to the process, longest first so overlaps redact fully
def known_secret_values():
    values = [value for key in SECRET_KEYS for value in (globals().get(key),) if isinstance(value, str) and secret_is_set(value) and len(value) >= MIN_REDACTABLE_SECRET_LENGTH]
    return sorted(set(values), key=len, reverse=True)


# Redacts credentials and secret-bearing assignments from arbitrary text before it is shown, logged or emailed
def sanitize_error_text(value):
    text = str(value or "")
    for secret in known_secret_values():
        text = text.replace(secret, "<redacted>")
    patterns = (
        (r"(?m)(\b(?:PSN_NPSSO|SMTP_PASSWORD|WEBHOOK_URL|NTFY_ACCESS_TOKEN)\b\s*=\s*).*$", r"\1<redacted>"),
        (r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?(?:bearer|basic)\s+)[^\s,;'\"}]+", r"\1<redacted>"),
        (r"(?i)(['\"]?(?:npsso|access_token|refresh_token|smtp_password|webhook_url|ntfy_access_token)['\"]?\s*[:=]\s*['\"]?)[^\s,;'\"}]+", r"\1<redacted>"),
        # A webhook URL is itself the credential, so the whole link is replaced wherever it appears
        (r"(?i)https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api(?:/v[0-9]+)?/webhooks/[0-9]+/[^\s'\"<>]+", "<redacted>"),
        (r"(?i)([?&](?:access_token|auth|token)=)[^&#\s]+", r"\1<redacted>"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


# Secrets whose length is a fixed, published property of the credential itself. A truncated paste is the usual
# way these arrive broken, so the length diagnoses that without revealing anything the format does not already
FIXED_LENGTH_SECRET_KEYS = frozenset(("PSN_NPSSO",))


# Describes a secret in diagnostic output without revealing any part of it. A password the user chose reports
# presence only: its length is a real disclosure in output that ends up pasted into bug reports
def secret_fingerprint(value, key=None):
    fields = secret_fields(value, key)
    return f"{fields['value']}, {fields['chars']} chars" if fields["chars"] else fields["value"]


# Returns the diagnostic fields describing one secret, keeping the length out of the value so a line still splits on ", "
def secret_fields(value, key=None): return {"value": "set" if secret_is_set(value) else "not set", "chars": len(str(value).strip()) if key in FIXED_LENGTH_SECRET_KEYS and secret_is_set(value) else None}


# Records where one secret resolved from, so a later layer replaces the earlier answer instead of adding to it
def record_secret_source(name, source, value=None):
    if source not in SECRET_SOURCE_ORDER:
        raise ValueError(f"Unsupported secret source: {source}")
    # A placeholder is not a value, so it earns neither a source nor a row
    if not secret_is_set(globals().get(name) if value is None else value):
        SECRET_SOURCES.pop(name, None)
        return
    SECRET_SOURCES[name] = source


# Renders one diagnostic line as an operation followed by comma-separated key=value fields, dropping unset ones
def format_diagnostic_line(operation, fields):
    rendered = ", ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    return f"{operation}: {rendered}" if rendered else str(operation)


# Prints a technical diagnostic line, shown only when debug mode is on
def debug_print(_operation, **fields):
    if DEBUG_MODE:
        message = format_diagnostic_line(_operation, fields)
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] {sanitize_error_text(message)}")


# Prints a rare operational event, shown only when verbose mode is on
def verbose_print(message):
    if VERBOSE_MODE:
        print(f"* {sanitize_error_text(message)}")


# Prints verbose-only notices as one block, so a standalone line is not left without the timestamp trailer
def verbose_notice(*messages):
    if not VERBOSE_MODE or not messages:
        return
    for message in messages:
        verbose_print(message)
    # Before monitoring starts the notice belongs to the startup screen, which the monitoring header closes
    if MONITORING_ACTIVE:
        print_cur_ts("Timestamp:\t\t\t")


# Marks the point where output stops being the startup screen, so later notices close their own block
def mark_monitoring_started():
    global MONITORING_ACTIVE
    MONITORING_ACTIVE = True


# Applies the diagnostic flags that were actually typed, leaving the rest to the config file
def apply_diagnostic_cli_overrides(args):
    global VERBOSE_MODE, DEBUG_MODE
    if args.verbose_mode is not None:
        VERBOSE_MODE = args.verbose_mode
    if args.debug_mode is not None:
        DEBUG_MODE = args.debug_mode


# Applies every secret the environment or a loaded dotenv file provides, recording where each value came from.
# Environment variables are a documented alternative to a dotenv file, so they apply even when no file was loaded
def apply_environment_secrets():
    for secret in SECRET_KEYS:
        value = os.getenv(secret)
        if value is not None:
            globals()[secret] = value
            record_secret_source(secret, "environment" if secret in EXPORTED_SECRET_KEYS else "dotenv file")


# Resolves LOCAL_TIMEZONE and the state doctor reports it with, returning advice when no zone could be determined
def resolve_local_timezone():
    global LOCAL_TIMEZONE, LOCAL_TIMEZONE_STATE

    LOCAL_TIMEZONE_STATE = "config"
    timezone_advice = None
    local_tz = None
    if LOCAL_TIMEZONE == "Auto":
        if get_localzone is not None:
            try:
                local_tz = get_localzone()
            except Exception as diag_exc:
                debug_print("Local timezone auto-detection", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
        if local_tz and is_valid_timezone(str(local_tz)):
            LOCAL_TIMEZONE = str(local_tz)
            LOCAL_TIMEZONE_STATE = "auto"
        elif get_localzone is None:
            LOCAL_TIMEZONE_STATE = "auto_unavailable"
            timezone_advice = make_recovery_advice("dependency.missing", "The local timezone could not be detected", recovery_fix_with_guide(f"Install tzlocal with: {pip_install_command('tzlocal')} or set LOCAL_TIMEZONE to a pytz timezone name such as 'Europe/Warsaw'", TIMEZONE_GUIDE_URL), False, "LOCAL_TIMEZONE is Auto but tzlocal is unavailable")
        else:
            LOCAL_TIMEZONE_STATE = "auto_failed"
            timezone_advice = make_recovery_advice("config.invalid", "The local timezone could not be detected", recovery_fix_with_guide("Set LOCAL_TIMEZONE to a pytz timezone name such as 'Europe/Warsaw'", TIMEZONE_GUIDE_URL), False, "tzlocal did not return a supported timezone")
    elif not is_valid_timezone(LOCAL_TIMEZONE):
        LOCAL_TIMEZONE_STATE = "invalid"
        timezone_advice = make_recovery_advice("config.invalid", f"Configured LOCAL_TIMEZONE '{LOCAL_TIMEZONE}' is not valid", recovery_fix_with_guide("Set LOCAL_TIMEZONE to a pytz timezone name such as 'Europe/Warsaw'", TIMEZONE_GUIDE_URL), False, f"Time zone: {LOCAL_TIMEZONE}")
    return timezone_advice


# Applies the webhook options that were actually typed, then reconciles the provider with the destination
def apply_webhook_cli_overrides(args, parser):
    global WEBHOOK_ENABLED, WEBHOOK_PROVIDER, WEBHOOK_URL, WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION, WEBHOOK_GAME_CHANGE_NOTIFICATION, WEBHOOK_ERROR_NOTIFICATION
    if args.webhook_provider is not None:
        WEBHOOK_PROVIDER = str(args.webhook_provider)
    if args.webhook_url is not None:
        if not validate_webhook_url(args.webhook_url):
            parser.error("--webhook-url needs a complete HTTPS link without embedded credentials")
        WEBHOOK_URL = str(args.webhook_url).strip()
        WEBHOOK_ENABLED = True
        record_secret_source("WEBHOOK_URL", "command line", WEBHOOK_URL)
    if args.webhook_enabled is not None:
        WEBHOOK_ENABLED = args.webhook_enabled
    # Naming one alert also switches the channel on, so a single flag is enough to try it out
    if args.webhook_active_inactive is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION = True
    if args.webhook_game_change is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_GAME_CHANGE_NOTIFICATION = True
    if args.webhook_errors is not None:
        WEBHOOK_ERROR_NOTIFICATION = args.webhook_errors
        if args.webhook_errors:
            WEBHOOK_ENABLED = True
    # A recognised URL describes its own service, so it corrects a provider the settings got wrong
    if args.webhook_provider is None:
        detected = detect_webhook_provider(WEBHOOK_URL)
        if detected and detected != normalized_webhook_provider():
            WEBHOOK_PROVIDER = detected
            print(f"* Warning: Configured webhook provider did not match the URL. Using {webhook_provider_display_name(detected)}.")


# Matches every ANSI escape sequence, used to keep colour codes out of files
ANSI_ESCAPE_RE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")

# The only escape sequence this tool emits is an SGR colour or style change, so it is the only one worth keeping
SGR_SEQUENCE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Every other control character is dropped, keeping only tab and newline. A carriage return would let a PSN
# supplied name overwrite an already printed line, and the rest can move the cursor, clear the screen or
# retitle the terminal window
TERMINAL_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


# Removes terminal control sequences that PSN-supplied text could use to drive the terminal, while leaving SGR
# colour sequences intact so this tool's own colouring survives a pass through its own writers
def sanitize_terminal_text(message):
    if not isinstance(message, str) or not message:
        return message
    parts = []
    position = 0
    for match in SGR_SEQUENCE_RE.finditer(message):
        parts.append(TERMINAL_CONTROL_RE.sub("", message[position:match.start()]))
        parts.append(match.group(0))
        position = match.end()
    parts.append(TERMINAL_CONTROL_RE.sub("", message[position:]))
    return "".join(parts)


# Strips every escape sequence and control character, for text going to a file or an email rather than a terminal
def plain_text(message):
    if not isinstance(message, str) or not message:
        return message
    return TERMINAL_CONTROL_RE.sub("", ANSI_ESCAPE_RE.sub("", message))


# Truncates each line to a display width, expanding tabs and counting double-width characters correctly
def truncate_string_per_line(message, truncate_width, tabsize=8):
    try:
        from wcwidth import wcwidth
    except ImportError:
        return message

    truncated_lines = []

    for line in message.split("\n"):
        expanded_line = line.expandtabs(tabsize)
        current_width = 0
        truncated = []
        position = 0

        while position < len(expanded_line):
            # A colour sequence is copied through free of charge, so styling never eats into the visible width
            escape = SGR_SEQUENCE_RE.match(expanded_line, position)
            if escape:
                truncated.append(escape.group(0))
                position = escape.end()
                continue
            char = expanded_line[position]
            char_width = wcwidth(char)
            if char_width is None or char_width < 0:
                char_width = 0
            if current_width + char_width > truncate_width:
                break
            truncated.append(char)
            current_width += char_width
            position += 1

        truncated_lines.append("".join(truncated))

    return "\n".join(truncated_lines)


# Copies an existing file to a timestamped private backup before it is replaced, returning the backup path or None
def create_timestamped_backup(destination, attempts=100):
    destination_path = Path(destination).expanduser()
    if not destination_path.is_file():
        return None
    existing_bytes = destination_path.read_bytes()
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    for attempt in range(attempts):
        suffix = f".{stamp}.bak" if attempt == 0 else f".{stamp}-{attempt}.bak"
        backup_path = destination_path.with_name(destination_path.name + suffix)
        try:
            # O_EXCL so a backup can never overwrite an earlier one, even under a concurrent run
            descriptor = os.open(str(backup_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(descriptor, "wb") as backup_file:
                backup_file.write(existing_bytes)
                backup_file.flush()
                os.fsync(backup_file.fileno())
        except Exception:
            try:
                os.unlink(str(backup_path))
            except OSError as cleanup_error:
                debug_print("Could not remove the failed backup", path=backup_path, outcome="failed", error=f"{type(cleanup_error).__name__}: {cleanup_error}")
            raise
        debug_print("File backed up", path=destination_path, backup=backup_path)
        return str(backup_path)
    raise OSError(f"Could not create a unique backup for '{destination_path}' after {attempts} attempts")


# Writes one file through a temporary file in the same directory, so a crash cannot leave a half-written file
def write_file_atomically(destination, content):
    destination_path = Path(destination).expanduser()
    if destination_path.parent != Path(""):
        destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(str(temporary_path), str(destination_path))
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return str(destination_path)


# Confirms replacing one existing generated config, or requires --force when there is nobody to ask
def confirm_generated_config_replacement(destination, force=False, interactive=None, input_func=input):
    destination_path = Path(destination).expanduser()
    if not destination_path.exists() or force:
        return True
    terminal_is_interactive = bool(sys.stdin.isatty()) if interactive is None else bool(interactive)
    if not terminal_is_interactive:
        raise FileExistsError(f"Config file '{destination_path}' already exists and there is no terminal to confirm replacing it")
    try:
        answer = str(read_interactively(input_func, f"Config file '{destination_path}' exists. Replace it and keep a timestamped backup? [y/N]: ")).strip().casefold()
    except (EOFError, KeyboardInterrupt):
        print()
        answer = ""
    return answer in {"y", "yes"}


# Writes one generated config atomically, backing up whatever was there first
def write_generated_config(output_file, content, force=False, interactive=None, input_func=input):
    destination = Path(os.path.expanduser(str(output_file)))
    if not confirm_generated_config_replacement(destination, force, interactive, input_func):
        return None, False
    backup_path = create_timestamped_backup(destination)
    write_file_atomically(destination, content)
    return backup_path, True


# Returns the file the tool saves the last seen status to, so a restart resumes from it
def resolve_status_file(psn_user_id):
    if PSN_STATUS_FILE:
        return os.path.expanduser(PSN_STATUS_FILE)
    return default_status_file(psn_user_id)


# Returns the status file name a target gets when no path is configured
def default_status_file(psn_user_id):
    return f"psn_{psn_user_id}_last_status.json"


# Saves the last seen status atomically, so an interrupted write cannot strand a half-written status file
def save_last_status(status_file, status_ts, status):
    write_file_atomically(status_file, json.dumps([status_ts, status], indent=2) + "\n")


# Returns the log file path for one monitored user, without creating anything
def resolve_log_path(psn_user_id):
    log_path = Path(os.path.expanduser(PSN_LOGFILE))
    if log_path.suffix == "":
        named = f"{log_path.name}_{psn_user_id}.log"
        log_path = log_path.parent / named if log_path.parent != Path('.') else Path(named)
    return log_path


# Resolves the configured and command line truncation width, expanding the terminal-width sentinel
def resolve_truncate_chars(cli_value, configured_value, logging_disabled):
    truncate_chars = configured_value if cli_value is None else cli_value
    if truncate_chars:
        try:
            import wcwidth  # noqa: F401
        except ImportError:
            print_recovery_advice(missing_dependency_advice("wcwidth", "Screen truncation is disabled"), label="Warning")
            print()
            return 0
    # Truncation shortens the terminal copy only, so without a log file the trimmed text would be lost for good
    if logging_disabled:
        return 0
    if truncate_chars == 999:
        terminal_size = shutil.get_terminal_size()
        print(f"The detected terminal screen width is: {terminal_size.columns} characters\n")
        return terminal_size.columns
    return truncate_chars


# Reports whether separator-only log lines should use ASCII on this system
def ascii_log_separators_enabled():
    mode = str(ASCII_LOG_SEPARATORS).strip().lower()
    if mode not in {"auto", "on", "off"}:
        raise ValueError("ASCII_LOG_SEPARATORS must be 'Auto', 'On' or 'Off'")
    return mode == "on" or (mode == "auto" and platform.system() == "Windows")


# Converts Unicode-only horizontal separator lines to ASCII when configured
def normalize_log_separators(message):
    if not ascii_log_separators_enabled():
        return message
    return re.sub(r"(?m)^─+$", lambda match: match.group(0).replace("─", "-"), message)


# Internal flag and style map for colour handling
COLOR_ENABLED = False
_COLOR_STYLES: dict = {}

# Default built-in colour theme, kept byte-identical to COLOR_THEME in the config template above
DEFAULT_COLOR_THEME = {
    # Headings and commands the wizard tells you to run
    "header": "bright_cyan",
    "section": "bright_white",
    # Identity
    "username": "bright_cyan underline",
    "id": "bright_magenta",
    # Presence status values
    "status_active": "green",
    "status_inactive": "red",
    "status_offline": "red",
    "status_other": "white",
    # PlayStation info
    "game": "bright_yellow",
    "platform": "blue",
    "trophy": "bright_green",
    "duration": "green",
    # Activity info
    "status_change": "yellow",
    # Misc
    "timestamp_label": "",
    "timestamp_value": "cyan",
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "signal": "yellow",
    "email": "bright_cyan",
    "webhook": "bright_blue",
    # Dates
    "date": "magenta",
    "date_range": "magenta",
    # Boolean values
    "boolean_true": "green",
    "boolean_false": "red",
    "link": "blue underline",
}

# COLOR_THEME key names used by older releases. This tool shipped the current names, so there is nothing to alias yet
_THEME_KEY_ALIASES: dict = {}

ANSI_RESET = "\033[0m"

# Mapping of style names to ANSI SGR codes
_STYLE_CODES = {
    "bold": "1",
    "dim": "2",
    "underline": "4",
    "blink": "5",
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}

# Whole-line styles, listed so the palette test can prove no value colour disappears inside one of them.
# Warnings and signals are not on this list: both are yellow, which is the colour of the words reporting an
# activity change, so they mark their own opening words instead of painting the line
BLOCK_STYLE_PARTS = ("error", "email", "webhook", "info")

# Parts that carry a name supplied by PlayStation Network or by the user, or that report a change, which a
# block style must never hide
NAME_STYLE_PARTS = ("username", "id", "game", "platform", "trophy", "status_change", "link")

# Output labels whose value is coloured with one theme style, longest label first so a prefix cannot win
_LABEL_STYLES = (
    (("PlayStation ID:", "PSN ID:", "Target:"), "username"),
    (("PSN account ID:", "Account ID:"), "id"),
    (("User is currently in-game:", "In-game:"), "game"),
    (("Trophies earned:", "Trophy level:"), "trophy"),
    (("Platform:",), "platform"),
)

# Pre-compiled regexes used for line-level colourisation
# The separator is a space in prose and an equals sign in the key=value diagnostic fields. An intervening
# "with PSN ID" belongs to the tag, so the name after it is coloured instead of the connecting words. A bare
# "user" needs the colon or the equals sign, because in prose it is followed by a verb rather than by a name
_USER_TAG_RE = re.compile(r"((?:PSN user|PlayStation user|for user|by user|of user|Monitoring user)(?:[\t ]+with(?:[\t ]+(?:PSN|PlayStation))?[\t ]+ID)?:?|\buser(?::|(?==)))([\t ]+|=)((?!(?:ID|with)\b)[\w.-]+)")

# A quoted value right after "user" or "for" names the monitored account, the same value the "PlayStation ID:"
# row reports. Every "for '<value>'" line this tool prints names either that account or a file
_QUOTED_USER_ID_CONTEXT_RE = re.compile(r"\b(?:user(?:\s+id)?|for)\s+$", re.IGNORECASE)

# The two presence values a status change reports, coloured with the same table the "Status:" row uses
_FROM_TO_STATUS_RE = re.compile(r"(changed status from\s+)(\w+)(\s+to\s+)(\w+)")
_DURATION_RE = re.compile(r"~?\b[0-9]{1,20}[ \t]{1,20}(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b", re.IGNORECASE)
_LONG_DATE_RE = re.compile(r"\b(?:\w{3}\s+)?\d{1,2}\s+\w{3}(?:\s+\d{2,4})?[\s,]*\d{2}:\d{2}(:\d{2})?(\s*[AP]M)?\b", re.IGNORECASE)
_TIME_ONLY_RE = re.compile(r"(?<![\w:])(~?(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?:\s*[AP]M)?)(?![\w:])", re.IGNORECASE)
_SHORT_RANGE_DATE_RE = re.compile(r"\(\w{3}\s+\d{1,2}\s+\w{3}\s+\d{2}:\d{2}(\s*[AP]M)?\s*-\s*\d{2}:\d{2}(\s*[AP]M)?\)", re.IGNORECASE)
_DATE_RANGE_RE = re.compile(r"\b\w{3}\s+\d{1,2}\s+\w{3}\s+\d{2}:\d{2}(\s*[AP]M)?\s*(?:-|to)\s*\d{2}:\d{2}(\s*[AP]M)?\b", re.IGNORECASE)
_HOUR_RANGE_RE = re.compile(r"\b\d{2}:\d{2}(\s*[AP]M)?\s*-\s*\d{2}:\d{2}(\s*[AP]M)?\b", re.IGNORECASE)
_URL_RE = re.compile(r"(https?://[^\s\]]+)")
_BOOLEAN_TRUE_RE = re.compile(r"\bTrue\b|\bEnabled\b")
_BOOLEAN_FALSE_RE = re.compile(r"\bFalse\b|\bDisabled\b")
_NOTIFICATION_SUMMARY_STATE_RE = re.compile(r"^(\* Notifications \((?:email|webhook)\):\s+)(On|Off)(.*)$")

# Every failure this tool reports is printed by the recovery renderer, which always writes its marker at the
# start of the line. Anchoring here instead of scanning for problem words keeps a diagnostic detail such as
# "timeout=15" or a recovery notice from painting its line red
_ERROR_LINE_RE = re.compile(r"^\s*\*\s*(?:error|critical)\b", re.IGNORECASE)
_WARNING_LINE_RE = re.compile(r"^\s*\*\s*(?:warning|caution)\b", re.IGNORECASE)
_INFO_LINE_RE = re.compile(r"^\s*\*\s*(?:info|note)\b", re.IGNORECASE)
_SIGNAL_LINE_RE = re.compile(r"^\s*\*\s*signal\b.*\breceived\b", re.IGNORECASE)

# The opening word of a warning and the name of a reported signal, marked instead of painting the line
_WARNING_LABEL_RE = re.compile(r"^\s*\*+\s*(Warning:|Caution:)")
_SIGNAL_NAME_RE = re.compile(r"(?<=^\* Signal )(\w+)(?= received$)")

# Doctor status markers, coloured with the same theme parts the sibling monitors use for them
_DOCTOR_MARK_RE = re.compile(r"^\[(PASS|WARN|FAIL|SKIP)\]")
_DOCTOR_MARK_STYLES = {"PASS": "boolean_true", "WARN": "warning", "FAIL": "error", "SKIP": "info"}

# One row of the earned-trophy listing: "- <date> | <game> | <trophy type> | <trophy name>"
_TROPHY_ROW_RE = re.compile(r"^- ([^|]+) \| ([^|]+) \| ([A-Z]+) \| (.+)$")

# Quoted names such as game titles. At least one word character is required so a run of punctuation between
# two apostrophes is not read as a name. The closing quote has to be followed by whitespace, punctuation or the
# end of the line, so a title's own apostrophe does not end the name early: "Tom Clancy's Rainbow Six Siege"
_QUOTED_CONTENT_RE = re.compile(r"(')([^\n]*?\w[^\n]*?)(')(?=[\s.,;:!?)\]]|$)")

# Quoted values shaped like a file name or a filesystem path stay plain, since a log or state destination is
# not content. Game titles routinely contain slashes and dots, so only these two shapes are excluded
_QUOTED_FILE_LIKE_RE = re.compile(r"^[~.]?[\\/]|^[A-Za-z]:[\\/]|\.[A-Za-z0-9]{1,8}$")

# A quoted '<name>' inside a printed command is the placeholder the reader has to replace, not a game title
_QUOTED_PLACEHOLDER_RE = re.compile(r"^<[^<>]*>$")

# A quoted command-line option is an instruction to retype, not a name
_QUOTED_OPTION_RE = re.compile(r"^-")

# A quoted piece of a URL, such as the '?code=' or '&state=' a prompt points at. Only a leading '?' or '&' counts,
# so a title may end in a question mark and a title such as 'Ratchet & Clank' is still a name
_QUOTED_URL_PART_RE = re.compile(r"^[?&]|://")

# The console tag printed beside a game, for example "(PS5)"
_LAUNCH_PLATFORM_RE = re.compile(r"\((PS[A-Z0-9_]*|MOBILE_APP)\)")
_TRAILING_PLATFORM_RE = re.compile(r"\s*\((PS[A-Z0-9_]*|MOBILE_APP)\)\s*$")

# Presence keywords the event lines print in capitals
_ACTIVE_WORD_RE = re.compile(r"\b(ACTIVE|ONLINE)\b")
_OFFLINE_WORD_RE = re.compile(r"\b(OFFLINE)\b")
_INACTIVE_WORD_RE = re.compile(r"\b(INACTIVE|STANDBY)\b")

# This tool has no capitalised playback keywords, so the same three activity styles attach to the verbs its
# change reports use instead
_GAME_STARTED_RE = re.compile(r"\bstarted playing\b")
_GAME_STOPPED_RE = re.compile(r"\bstopped playing\b")
_STATUS_CHANGE_RE = re.compile(r"\b(?:changed status|changed game)\b")


# Builds an ANSI escape sequence from a style description string
def _build_ansi_sequence(style_str):
    if not style_str:
        return ""
    parts = re.split(r"[+ ]+", style_str.strip().lower())
    codes = [_STYLE_CODES[part] for part in parts if part in _STYLE_CODES]
    if not codes:
        return ""
    return f"\033[{';'.join(codes)}m"


# Detects whether the given output stream likely supports ANSI colours
def _stream_supports_color(stream):
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if os.getenv("NO_COLOR"):
        return False
    # On Windows with colorama, skip the TERM check since colorama translates the sequences itself and
    # neither Windows Terminal nor Command Prompt sets TERM
    if not (colorama_init and platform.system() == "Windows"):
        if os.getenv("TERM", "").lower() in ("", "dumb", "unknown"):
            return False
    # A piped stdin means the run is part of a pipeline such as tee, where escape codes would end up in a file
    if hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
        return False
    return True


# Initialises colour handling from the resolved settings and the terminal's capabilities
def init_color_output(stream):
    global COLOR_ENABLED, _COLOR_STYLES

    # Done before the support check because colorama is what makes an older Windows console report support
    if colorama_init and platform.system() == "Windows":
        try:
            colorama_init(autoreset=False)
        except Exception:
            pass

    COLOR_ENABLED = bool(globals().get("COLORED_OUTPUT", False)) and _stream_supports_color(stream)

    if not COLOR_ENABLED:
        _COLOR_STYLES = {}
        return

    configured = globals().get("COLOR_THEME")
    user_theme = configured if isinstance(configured, dict) else {}
    theme = {**DEFAULT_COLOR_THEME, **user_theme}

    # A config written against an older key name still wins over the default, unless it also sets the current name
    for legacy_name, current_name in _THEME_KEY_ALIASES.items():
        if legacy_name in user_theme and current_name not in user_theme:
            theme[current_name] = user_theme[legacy_name]

    _COLOR_STYLES = {name: sequence for name, style in theme.items() for sequence in (_build_ansi_sequence(style),) if sequence}


# Applies one configured colour style, by logical part name, to the given text
def colorize(part, text):
    if not COLOR_ENABLED:
        return text
    start = _COLOR_STYLES.get(part)
    if not start:
        return text
    return f"{start}{text}{ANSI_RESET}"


# Returns the coloured form of one PlayStation presence value
def colorize_status(status_text):
    status = (status_text or "").strip().lower()
    if status in ("active", "online", "availabletoplay", "available", "yes"):
        key = "status_active"
    elif status in ("inactive", "standby", "no"):
        key = "status_inactive"
    elif status == "offline":
        key = "status_offline"
    else:
        key = "status_other"
    return colorize(key, status_text)


# Splits a recognized output label from its value without applying a backtracking expression
def _split_output_label(value, labels):
    body = value.rstrip("\n")
    cursor = len(body) - len(body.lstrip())
    if body[cursor:cursor + 1] == "*":
        cursor += 1
        cursor += len(body[cursor:]) - len(body[cursor:].lstrip())
    for label in labels:
        if not body.startswith(label, cursor):
            continue
        value_start = cursor + len(label)
        value_start += len(body[value_start:]) - len(body[value_start:].lstrip())
        if value_start == cursor + len(label):
            return None
        return body[:value_start], body[value_start:]
    return None


# Applies a whole-line style while preserving the highlights already inside the line
def _apply_style_nested(line, style_name):
    start_style = _COLOR_STYLES.get(style_name)
    if not start_style:
        return line
    # Each internal reset returns to the block style instead of to plain, so the line keeps one colour throughout
    line = f"{start_style}{line}{ANSI_RESET}"
    line = line.replace(ANSI_RESET, f"{ANSI_RESET}{start_style}")
    if line.endswith(f"{ANSI_RESET}{start_style}"):
        line = line[:-len(start_style)]
    return line


# Applies one substitution only to the parts of a line that are not already inside a colour span, so a later
# rule cannot reclaim text an earlier rule has already coloured
def _sub_outside_color(pattern, replacement, line):
    if ANSI_RESET not in line:
        return pattern.sub(replacement, line)
    parts = []
    position = 0
    inside = False
    for match in SGR_SEQUENCE_RE.finditer(line):
        segment = line[position:match.start()]
        parts.append(segment if inside else pattern.sub(replacement, segment))
        parts.append(match.group(0))
        inside = match.group(0) != ANSI_RESET
        position = match.end()
    trailing = line[position:]
    parts.append(trailing if inside else pattern.sub(replacement, trailing))
    return "".join(parts)


# Colours one quoted name unless the quoted value is a file name, a path or a command-line option
def _colorize_quoted_name(match, style_name):
    name = match.group(2)
    if _QUOTED_FILE_LIKE_RE.search(name) or _QUOTED_PLACEHOLDER_RE.match(name) or _QUOTED_OPTION_RE.match(name) or _QUOTED_URL_PART_RE.search(name):
        return match.group(0)
    # What sits right before the quote decides the colour, so an account name is not read as a game title
    if _QUOTED_USER_ID_CONTEXT_RE.search(match.string[:match.start()]):
        style_name = "username"
    return f"{match.group(1)}{colorize(style_name, name)}{match.group(3)}"


# Applies the colour rules to a single output line
def _colorize_line(line):
    lowered = line.lower()

    # The notification summary row carries its own On/Off state word
    notification_match = _NOTIFICATION_SUMMARY_STATE_RE.match(line)
    if notification_match:
        prefix, state, suffix = notification_match.groups()
        return f"{prefix}{colorize('boolean_true' if state == 'On' else 'boolean_false', state)}{suffix}"

    # Doctor status markers keep the rest of their line plain so long labels stay readable
    doctor_match = _DOCTOR_MARK_RE.match(line)
    if doctor_match:
        return colorize(_DOCTOR_MARK_STYLES[doctor_match.group(1)], doctor_match.group(0)) + line[doctor_match.end():]

    # Trophy listing rows are a fixed four-column shape, so each column is coloured for what it holds
    trophy_match = _TROPHY_ROW_RE.match(line.rstrip("\n"))
    if trophy_match:
        earned, game, trophy_type, trophy_name = trophy_match.groups()
        colored = f"- {colorize('date', earned)} | {colorize('game', game)} | {colorize('trophy', trophy_type)} | {colorize('trophy', trophy_name)}"
        return colored + ("\n" if line.endswith("\n") else "")

    # Timestamp rows get an uncoloured label and a coloured value
    labeled_value = _split_output_label(line, ("Liveness check, timestamp:", "Timestamp:"))
    if labeled_value:
        label, rest = labeled_value
        return f"{colorize('timestamp_label', label)}{colorize('timestamp_value', rest)}" + ("\n" if line.endswith("\n") else "")

    # Any '<something> URL:' row is a link, checked before the label table so 'Profile URL:' is not read as a name
    if _split_output_label(line, ("URL:",)) or " URL:" in line:
        return _sub_outside_color(_URL_RE, lambda mo: colorize("link", mo.group(0)), line)

    # Presence rows report the monitored account's status
    labeled_value = _split_output_label(line, ("Available to play:", "STATUS:", "Status:"))
    if labeled_value:
        label, status = labeled_value
        return f"{label}{colorize_status(status)}" + ("\n" if line.endswith("\n") else "")

    # Labelled PlayStation rows keep their label plain and colour only the value
    for labels, style_name in _LABEL_STYLES:
        labeled_value = _split_output_label(line, labels)
        if not labeled_value:
            continue
        label, rest = labeled_value
        # The console tag after a game name keeps its own colour instead of disappearing into the title
        trailing_platform = _TRAILING_PLATFORM_RE.search(rest) if style_name == "game" else None
        if trailing_platform:
            colored_value = f"{colorize(style_name, rest[:trailing_platform.start()])} ({colorize('platform', trailing_platform.group(1))})"
        else:
            colored_value = colorize(style_name, rest)
        return f"{label}{colored_value}" + ("\n" if line.endswith("\n") else "")

    # Highlight the PlayStation account named inside a sentence
    line = _sub_outside_color(_USER_TAG_RE, lambda mo: f"{mo.group(1)}{mo.group(2)}{colorize('username', mo.group(3))}", line)

    # Highlight the two presence values a status change reports
    line = _sub_outside_color(_FROM_TO_STATUS_RE, lambda mo: f"{mo.group(1)}{colorize_status(mo.group(2))}{mo.group(3)}{colorize_status(mo.group(4))}", line)

    # Highlight durations
    line = _sub_outside_color(_DURATION_RE, lambda mo: colorize("duration", mo.group(0)), line)

    # Highlight date ranges before single dates so a range is not split into two dates
    line = _sub_outside_color(_SHORT_RANGE_DATE_RE, lambda mo: colorize("date_range", mo.group(0)), line)
    line = _sub_outside_color(_DATE_RANGE_RE, lambda mo: colorize("date_range", mo.group(0)), line)
    line = _sub_outside_color(_HOUR_RANGE_RE, lambda mo: colorize("date_range", mo.group(0)), line)
    line = _sub_outside_color(_LONG_DATE_RE, lambda mo: colorize("date", mo.group(0)), line)
    line = _sub_outside_color(_TIME_ONLY_RE, lambda mo: colorize("date", mo.group(0)), line)

    # Highlight links
    line = _sub_outside_color(_URL_RE, lambda mo: colorize("link", mo.group(0)), line)

    # Highlight quoted names. A line that is only a quoted string is a free-form description, so it stays plain
    if not line.lstrip().startswith("'"):
        line = _sub_outside_color(_QUOTED_CONTENT_RE, lambda mo: _colorize_quoted_name(mo, "game"), line)

    # Highlight the console tag printed beside a game
    line = _sub_outside_color(_LAUNCH_PLATFORM_RE, lambda mo: f"({colorize('platform', mo.group(1))})", line)

    # Highlight boolean values
    line = _sub_outside_color(_BOOLEAN_TRUE_RE, lambda mo: colorize("boolean_true", mo.group(0)), line)
    line = _sub_outside_color(_BOOLEAN_FALSE_RE, lambda mo: colorize("boolean_false", mo.group(0)), line)

    # Highlight presence keywords and the verbs that report an activity change
    line = _sub_outside_color(_ACTIVE_WORD_RE, lambda mo: colorize("status_active", mo.group(0)), line)
    line = _sub_outside_color(_OFFLINE_WORD_RE, lambda mo: colorize("status_offline", mo.group(0)), line)
    line = _sub_outside_color(_INACTIVE_WORD_RE, lambda mo: colorize("status_inactive", mo.group(0)), line)
    line = _sub_outside_color(_GAME_STARTED_RE, lambda mo: colorize("status_active", mo.group(0)), line)
    line = _sub_outside_color(_GAME_STOPPED_RE, lambda mo: colorize("status_inactive", mo.group(0)), line)
    line = _sub_outside_color(_STATUS_CHANGE_RE, lambda mo: colorize("status_change", mo.group(0)), line)

    # Mark the opening word of a warning and the name of a reported signal, rather than painting the whole line
    line = _sub_outside_color(_WARNING_LABEL_RE, lambda mo: mo.group(0)[:mo.start(1) - mo.start(0)] + colorize("warning", mo.group(1)), line)
    line = _sub_outside_color(_SIGNAL_NAME_RE, lambda mo: colorize("signal", mo.group(0)), line)

    # Whole-line styling last, so the colours applied above survive the nesting logic
    if lowered.startswith("to fix:") or _INFO_LINE_RE.match(line):
        line = _apply_style_nested(line, "info")
    elif _ERROR_LINE_RE.match(line):
        line = _apply_style_nested(line, "error")
    elif "sending email" in lowered:
        line = _apply_style_nested(line, "email")
    elif "sending webhook" in lowered:
        line = _apply_style_nested(line, "webhook")

    return line


# Applies colourisation to multi-line text, preserving the line breaks
def apply_color_to_text(text):
    if not COLOR_ENABLED or not isinstance(text, str):
        return text
    parts = []
    for chunk in text.splitlines(keepends=True):
        if chunk.endswith(("\n", "\r")):
            stripped = chunk.rstrip("\r\n")
            parts.append(_colorize_line(stripped) + chunk[len(stripped):])
        else:
            parts.append(_colorize_line(chunk))
    return "".join(parts)


# Sanitizing stdout wrapper installed before the logging policy is known, so early output is covered too
class TerminalStream(object):
    # Stores the wrapped terminal stream
    def __init__(self, stream):
        self.terminal = stream

    # Writes one sanitized and coloured message to the wrapped terminal
    def write(self, message):
        self.terminal.write(apply_color_to_text(sanitize_terminal_text(message)))
        self.terminal.flush()

    # Flushes the wrapped terminal
    def flush(self):
        self.terminal.flush()

    # Forwards every remaining stream attribute to the wrapped terminal
    def __getattr__(self, name):
        return getattr(self.terminal, name)


# Returns the underlying terminal behind any number of sanitizing stream wrappers
def unwrap_terminal_stream(stream):
    while isinstance(stream, TerminalStream):
        stream = stream.terminal
    return stream


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        # The early sanitizing stream is unwrapped so sanitizing and colouring happen exactly once. Writing
        # through it would colourise every line twice, and the second pass no longer sees the label it already
        # coloured, so it would recolour the value with the generic rules
        self.terminal = unwrap_terminal_stream(sys.stdout)
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        message = sanitize_terminal_text(message)
        # The log file stays plain text, so colour codes are stripped and tabs expanded before it is written
        self.logfile.write(normalize_log_separators(ANSI_ESCAPE_RE.sub("", message).expandtabs(8)))
        # Truncation runs before colouring, so escape sequences never count toward the visible width
        if TRUNCATE_CHARS:
            message = truncate_string_per_line(message, TRUNCATE_CHARS)
        self.terminal.write(apply_color_to_text(message))
        self.terminal.flush()
        self.logfile.flush()

    # Writes text the log file should keep but the terminal has already shown, or does not need
    def log_only(self, message):
        self.logfile.write(normalize_log_separators(ANSI_ESCAPE_RE.sub("", sanitize_terminal_text(message)).expandtabs(8)))
        self.logfile.flush()

    # Writes text meant for the reader at the terminal, which the log file has its own version of
    def terminal_only(self, message):
        message = sanitize_terminal_text(message)
        if TRUNCATE_CHARS:
            message = truncate_string_per_line(message, TRUNCATE_CHARS)
        self.terminal.write(apply_color_to_text(message))
        self.terminal.flush()

    def flush(self):
        self.terminal.flush()
        self.logfile.flush()


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


# Reads one answer with Python's default Ctrl+C behavior, so the prompt reports the outcome instead of the signal handler
def read_interactively(reader, *args, **kwargs):
    try:
        previous_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.default_int_handler)
    except (ValueError, OSError):
        # Handlers can only be replaced from the main thread, which is where every prompt runs
        return reader(*args, **kwargs)
    try:
        return reader(*args, **kwargs)
    finally:
        try:
            signal.signal(signal.SIGINT, previous_handler)
        except (ValueError, OSError):
            pass


# Silences the repeated certificate warning once verification is off, so the choice is reported by the summary and the doctor instead of on every request
def apply_tls_verification_setting():
    if not VERIFY_SSL:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Returns the TLS context SMTP uses, unverified while VERIFY_SSL is off so email follows the same switch as every other connection
def smtp_ssl_context():
    context = ssl.create_default_context()
    if not VERIFY_SSL:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


# Returns a PSNAWP client whose session honours the configured TLS verification setting
def psn_client(npsso=None):
    client = PSNAWP(PSN_NPSSO if npsso is None else npsso)
    # Applied after construction because PSNAWP signs in on the first request, so this still covers the token exchange
    try:
        client.authenticator.request_builder.session.verify = VERIFY_SSL
    except AttributeError as diag_exc:
        debug_print("TLS verification could not be applied to the PSNAWP session", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
    return client

# The last connectivity failure, so a quiet caller can classify it instead of the check printing it
LAST_CONNECTIVITY_ERROR = None


# Checks internet connectivity
def check_internet(url=None, timeout=None, quiet=False):
    # Resolved at call time so a config file or dotenv value can change these, which binding them as default
    # arguments prevented
    url = CHECK_INTERNET_URL if url is None else url
    timeout = CHECK_INTERNET_TIMEOUT if timeout is None else timeout
    debug_print("Connectivity check", url=url, timeout=f"{timeout}s")
    try:
        _ = req.get(url, timeout=timeout, verify=VERIFY_SSL)
        debug_print("Connectivity check", url=url, outcome="OK")
        return True
    except req.RequestException as e:
        debug_print("Connectivity check", url=url, outcome="failed", error=f"{type(e).__name__}: {e}")
        global LAST_CONNECTIVITY_ERROR
        LAST_CONNECTIVITY_ERROR = e
        # Quiet callers render the failure themselves, which doctor needs so nothing lands on its progress line
        if not quiet:
            print_recovery_error(e, context="connectivity", detail=f"The connectivity check to {url} failed: {e}")
        return False


# Clears the terminal screen
def clear_screen(enabled=True):
    if not enabled:
        return
    # Don't clear screen if stdout is redirected (not a TTY)
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return
    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception as e:
        debug_print("Clearing the screen", outcome="failed", error=f"{type(e).__name__}: {e}")
        print("* Cannot clear the screen contents")


# Commands that print a one-shot result and exit, so the screen keeps whatever is already on it
KEEP_HISTORY_FLAGS = ("--set-npsso", "--set-smtp-password", "--set-webhook-url", "--doctor", "--send-test-email", "--send-test-webhook", "--help", "-h")


# Returns True when the running command is a one-shot whose output has to stay scrollable
def keep_terminal_history():
    return any(flag in sys.argv for flag in KEEP_HISTORY_FLAGS)


# Prints the ASCII startup banner with its separately aligned version
def print_startup_banner():
    # Each line carries its own colour so the whole banner sits inside a colour span. The line rules skip
    # text that is already coloured, which keeps the ASCII art from being read as quoted names or dates
    print("\n".join(colorize("header", line) if line else line for line in STARTUP_BANNER.splitlines()))
    print(colorize("info", f"{'':21}v{VERSION}") + "\n")


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
        except Exception as diag_exc:
            debug_print("Cannot parse the first timestamp as a date, timespan reported as empty", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
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
        except Exception as diag_exc:
            debug_print("Cannot parse the second timestamp as a date, timespan reported as empty", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
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


# Reports the first unusable email setting as a doctor detail and an action that names the same settings
def email_settings_problem():
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            return ("SMTP_HOST is not a valid IP address or hostname", "Correct SMTP_HOST or turn the email alerts off")

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        return ("SMTP_PORT is not a port number between 1 and 65535", "Correct SMTP_PORT or turn the email alerts off")

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        return ("SENDER_EMAIL or RECEIVER_EMAIL is not an email address", "Correct SENDER_EMAIL and RECEIVER_EMAIL or turn the email alerts off")

    if not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password":
        return ("SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder", "Set SMTP_USER and SMTP_PASSWORD or turn the email alerts off")

    return None


# Returns advice for the first unusable SMTP server setting, or None when they are all present and valid
def validate_smtp_settings():
    problem = email_settings_problem()
    return classify_recovery_error(context="smtp.settings", detail=problem[0]) if problem is not None else None


# Sends email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    settings_advice = validate_smtp_settings()
    if settings_advice is not None:
        print_recovery_advice(settings_advice)
        return 1

    if not subject or not isinstance(subject, str):
        print_recovery_error(context="smtp.settings", detail="the message subject is empty")
        return 1

    if not body and not body_html:
        print_recovery_error(context="smtp.settings", detail="the message body is empty")
        return 1

    # Game and profile names taken from PSN reach the message, so control sequences are removed before a mail
    # client renders them. A terminal is not the only thing that acts on them
    subject = plain_text(subject)
    body = plain_text(body)

    debug_print("SMTP delivery", host=SMTP_HOST, port=SMTP_PORT, starttls=bool(use_ssl), timeout=f"{smtp_timeout}s", user=SMTP_USER)
    try:
        if use_ssl:
            ssl_context = smtp_ssl_context()
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
            email_msg.attach(MIMEText(body, 'plain', _charset='utf-8'))

        if body_html:
            email_msg.attach(MIMEText(body_html, 'html', _charset='utf-8'))

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtpObj.quit()
    except Exception as e:
        print_recovery_error(e, context="smtp", detail=f"Sending the notification to {RECEIVER_EMAIL} failed: {e}")
        return 1
    # Reported separately from the "Sending email notification" line, which only records the attempt
    verbose_print(f"Email delivered to {RECEIVER_EMAIL}: {subject}")
    debug_print("SMTP delivery", recipient=RECEIVER_EMAIL, outcome="OK")
    return 0



# ----------------------------------------------------------
# Webhook notifications, delivered through Discord or ntfy
# ----------------------------------------------------------

# One shared connection pool, so repeated alerts reuse the TLS session instead of reconnecting every time
WEBHOOK_SESSION = req.Session()

# One retry only. An alert that is already late is worth less than a monitoring loop that keeps polling
WEBHOOK_MAX_ATTEMPTS = 2

# The service supplies the rate-limit delay, so it is bounded before it is trusted
WEBHOOK_MAX_RETRY_AFTER_SECONDS = 5.0
WEBHOOK_FALLBACK_RETRY_SECONDS = 1.0
WEBHOOK_TIMEOUT_SECONDS = 10

# Discord rejects an embed longer than these limits and ntfy rejects a message above its byte limit,
# so an over-long alert is trimmed here rather than being refused by the service
WEBHOOK_EMBED_TITLE_LIMIT = 256
WEBHOOK_EMBED_DESCRIPTION_LIMIT = 4096
NTFY_MESSAGE_LIMIT_BYTES = 4095
NTFY_TRUNCATION_SUFFIX = "\n\n[Notification truncated to fit ntfy's 4 KB message limit]"

# The embed colour each alert is drawn in, so a webhook reader can tell them apart at a glance
WEBHOOK_EVENT_COLORS = {"status": 0x0070D1, "game": 0x8957E5, "error": 0xE74C3C}


# Returns whether a webhook URL is a complete private HTTPS link
def validate_webhook_url(url=None):
    selected_url = WEBHOOK_URL if url is None else url
    if not isinstance(selected_url, str) or not selected_url.strip():
        return False
    try:
        parsed = urlsplit(selected_url.strip())
    except ValueError:
        return False
    return parsed.scheme.casefold() == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and bool(parsed.path.strip("/"))


# Returns the webhook destination host on its own, so delivery can be traced without printing the private URL
def webhook_destination_host(url=None):
    try:
        return urlsplit(str(WEBHOOK_URL if url is None else url).strip()).hostname or "unknown host"
    except ValueError:
        return "unknown host"


# Converts a complete ntfy URL or a bare ntfy.sh topic name into a complete HTTPS URL
def normalize_ntfy_topic_url(value):
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if validate_webhook_url(normalized):
        return normalized
    if re.fullmatch(r"[-_A-Za-z0-9]{1,64}", normalized):
        return f"https://ntfy.sh/{normalized}"
    return ""


# Returns the normalized configured webhook provider, or an empty string when it is not one of the supported two
def normalized_webhook_provider(provider=None):
    selected_provider = WEBHOOK_PROVIDER if provider is None else provider
    if not isinstance(selected_provider, str):
        return ""
    normalized = selected_provider.strip().casefold()
    return normalized if normalized in ("discord", "ntfy") else ""


# Returns the user-facing spelling of one webhook provider
def webhook_provider_display_name(provider=None):
    normalized = normalized_webhook_provider(provider)
    if normalized:
        return "Discord" if normalized == "discord" else "ntfy"
    return sanitize_error_text(WEBHOOK_PROVIDER if provider is None else provider)


# Detects Discord and public ntfy destinations from their distinctive URL shapes
def detect_webhook_provider(url):
    if not validate_webhook_url(url):
        return ""
    try:
        parsed = urlsplit(str(url).strip())
    except ValueError:
        return ""
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    if hostname == "ntfy.sh":
        return "ntfy"
    discord_host = hostname in ("discord.com", "discordapp.com") or hostname.endswith(".discord.com") or hostname.endswith(".discordapp.com")
    discord_path = re.match(r"^/api(?:/v[0-9]+)?/webhooks/[0-9]+/[^/]+/?$", parsed.path) is not None
    return "discord" if discord_host and discord_path else ""


# Returns whether one webhook alert is switched on, independently of the matching email setting
def webhook_event_enabled(notification_type):
    settings = {
        "status": WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION,
        "game": WEBHOOK_GAME_CHANGE_NOTIFICATION,
        "error": WEBHOOK_ERROR_NOTIFICATION,
    }
    return bool(WEBHOOK_ENABLED and settings.get(notification_type, False))


# Returns the enabled webhook alert names, in the order the startup summary and doctor print them
def webhook_notification_categories():
    settings = (
        (WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION, "status changes"),
        (WEBHOOK_GAME_CHANGE_NOTIFICATION, "game changes"),
        (WEBHOOK_ERROR_NOTIFICATION, "errors"),
    )
    return [label for enabled, label in settings if enabled]


# Parses a rate-limit delay from the response and bounds an untrusted server value to a short wait
def webhook_retry_after_seconds(response):
    candidates = []
    headers = getattr(response, "headers", {}) or {}
    if hasattr(headers, "get"):
        candidates.append(headers.get("Retry-After"))
    try:
        payload = response.json()
    except Exception as diag_exc:
        debug_print("Webhook retry response has no JSON body", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
        payload = None
    if isinstance(payload, dict):
        candidates.append(payload.get("retry_after"))
    for candidate in candidates:
        if candidate is None or candidate == "":
            continue
        try:
            seconds = float(candidate)
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(candidate))
                seconds = (retry_at - datetime.now(retry_at.tzinfo)).total_seconds()
            except Exception as diag_exc:
                debug_print("Cannot parse the webhook Retry-After value", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
                continue
        return max(0.0, min(seconds, WEBHOOK_MAX_RETRY_AFTER_SECONDS))
    return WEBHOOK_FALLBACK_RETRY_SECONDS


# Substitutes the supported placeholders through a nested webhook template
def format_payload(template, payload):
    if isinstance(template, dict):
        return {key: format_payload(value, payload) for key, value in template.items()}
    if isinstance(template, list):
        return [format_payload(value, payload) for value in template]
    if isinstance(template, tuple):
        return tuple(format_payload(value, payload) for value in template)
    if isinstance(template, str):
        # Discord rejects a colour sent as text, so this one placeholder resolves to the number itself
        if template == "{color}":
            return payload.get("color", WEBHOOK_EVENT_COLORS["status"])
        try:
            return template.format(**payload)
        except KeyError:
            return template
    return template


# Returns a configuration error for unsafe or unsupported webhook customization
def validate_webhook_customization(provider=None):
    selected_provider = normalized_webhook_provider(provider)
    if selected_provider == "discord":
        if not isinstance(WEBHOOK_USERNAME, str):
            return "WEBHOOK_USERNAME must be a string"
        if not isinstance(WEBHOOK_AVATAR_URL, str):
            return "WEBHOOK_AVATAR_URL must be a string"
        if WEBHOOK_AVATAR_URL.strip() and not validate_webhook_url(WEBHOOK_AVATAR_URL):
            return "WEBHOOK_AVATAR_URL must contain a complete HTTPS link without embedded credentials"
        if not isinstance(WEBHOOK_TEMPLATE, (dict, list, str)):
            return "WEBHOOK_TEMPLATE must be a dictionary, list or string"
    if not isinstance(WEBHOOK_TRANSFORMS, (list, tuple)):
        return "WEBHOOK_TRANSFORMS must be a list or tuple"
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        if not isinstance(transform, (list, tuple)) or len(transform) < 2 or not isinstance(transform[0], str) or not isinstance(transform[1], str):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} must contain a field name and a string method name"
        # Only public str methods are reachable, so a template cannot call arbitrary attributes of the value
        if transform[1].startswith("_") or not callable(getattr("", transform[1], None)):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} uses an unsupported string method"
    return None


# Applies the configured string transformations to one webhook value mapping
def apply_webhook_transforms(payload):
    transformed = dict(payload)
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        field = transform[0]
        method_name = transform[1]
        if field not in transformed or not isinstance(transformed[field], str):
            continue
        try:
            transformed[field] = getattr(transformed[field], method_name)(*transform[2:])
        except Exception as exc:
            raise ValueError(f"WEBHOOK_TRANSFORMS entry {index + 1} could not apply {field}.{method_name}") from exc
    return transformed


# Builds the bounded placeholder values shared by the template, the headers and both providers
def build_webhook_values(title, description, notification_type):
    safe_title = re.sub(r"[\r\n]+", " ", sanitize_error_text(title)).strip()[:WEBHOOK_EMBED_TITLE_LIMIT] or "PSN Monitor"
    safe_description = re.sub(r"\r\n?", "\n", sanitize_error_text(description)).strip()[:WEBHOOK_EMBED_DESCRIPTION_LIMIT]
    username = WEBHOOK_USERNAME.strip()[:80] if isinstance(WEBHOOK_USERNAME, str) else ""
    avatar_url = WEBHOOK_AVATAR_URL.strip() if isinstance(WEBHOOK_AVATAR_URL, str) else ""
    payload = {"title": safe_title, "description": safe_description, "version": VERSION, "color": WEBHOOK_EVENT_COLORS.get(notification_type, WEBHOOK_EVENT_COLORS["status"]), "timestamp": datetime.now().astimezone().isoformat(), "username": username, "avatar_url": avatar_url}
    return apply_webhook_transforms(payload)


# Builds one customized Discord-format payload, keeping mentions disabled whatever the template says
def build_webhook_payload(title, description, notification_type, payload_values=None):
    values = build_webhook_values(title, description, notification_type) if payload_values is None else payload_values
    try:
        payload = format_payload(WEBHOOK_TEMPLATE, values)
    except Exception as exc:
        raise ValueError("WEBHOOK_TEMPLATE could not be formatted with the supported placeholders") from exc
    if isinstance(payload, dict):
        # An empty name or avatar means "use the webhook default", which Discord expects as an absent key
        if payload.get("username") == "":
            payload.pop("username")
        if payload.get("avatar_url") == "":
            payload.pop("avatar_url")
        payload["allowed_mentions"] = {"parse": []}
    return payload


# Truncates text to a UTF-8 byte limit without leaving a partial character behind
def truncate_utf8_bytes(text, max_bytes, suffix=""):
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    encoded_suffix = suffix.encode("utf-8")
    if len(encoded_suffix) >= max_bytes:
        return encoded_suffix[:max_bytes].decode("utf-8", errors="ignore")
    return encoded[:max_bytes - len(encoded_suffix)].decode("utf-8", errors="ignore") + suffix


# Builds one bounded ntfy title and message pair
def build_ntfy_webhook_message(title, description):
    safe_title = re.sub(r"[\r\n]+", " ", sanitize_error_text(title)).strip()[:WEBHOOK_EMBED_TITLE_LIMIT] or "PSN Monitor"
    safe_message = truncate_utf8_bytes(sanitize_error_text(description), NTFY_MESSAGE_LIMIT_BYTES, NTFY_TRUNCATION_SUFFIX)
    return safe_title, safe_message


# Returns a safe validation error for one custom webhook header mapping
def _validate_webhook_header_mapping(headers):
    if not isinstance(headers, dict):
        return "WEBHOOK_HEADERS must be a dictionary of string header names and values"
    normalized_names = set()
    for name, value in headers.items():
        if not isinstance(name, str) or not re.fullmatch(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", name):
            return "WEBHOOK_HEADERS contains an invalid HTTP header name"
        normalized_name = name.casefold()
        if normalized_name in normalized_names:
            return "WEBHOOK_HEADERS contains duplicate case-insensitive header names"
        normalized_names.add(normalized_name)
        if not isinstance(value, str):
            return f"WEBHOOK_HEADERS value for {name} must be a string"
        # A line break in a header value would let a configured value inject a second header
        if "\r" in value or "\n" in value:
            return f"WEBHOOK_HEADERS value for {name} must not contain line breaks"
    return None


# Returns a safe configuration error for the custom headers or the ntfy access token
def validate_webhook_headers(provider=None):
    selected_provider = normalized_webhook_provider(provider)
    header_error = _validate_webhook_header_mapping(WEBHOOK_HEADERS)
    if header_error is not None:
        return header_error
    if selected_provider == "ntfy":
        if not isinstance(NTFY_ACCESS_TOKEN, str):
            return "NTFY_ACCESS_TOKEN must be a string"
        token = NTFY_ACCESS_TOKEN.strip()
        if "\r" in token or "\n" in token:
            return "NTFY_ACCESS_TOKEN must not contain line breaks"
        if token.casefold().startswith(("bearer ", "basic ")):
            return "NTFY_ACCESS_TOKEN must contain only the access token, without an Authorization scheme"
    return None


# Builds the provider-specific headers, substituting placeholders and adding the private ntfy authentication
def build_webhook_headers(provider, payload):
    validation_error = validate_webhook_headers(provider)
    if validation_error is not None:
        raise ValueError(validation_error)
    try:
        formatted_headers = format_payload(WEBHOOK_HEADERS, payload)
    except Exception as exc:
        raise ValueError("WEBHOOK_HEADERS could not be formatted with the supported placeholders") from exc
    # Re-checked after substitution, because a placeholder value could carry a line break the template did not
    formatted_error = _validate_webhook_header_mapping(formatted_headers)
    if formatted_error is not None:
        raise ValueError(formatted_error)
    headers = dict(cast("dict[str, str]", formatted_headers))
    if not any(name.casefold() == "user-agent" for name in headers):
        headers["User-Agent"] = f"PSNMonitor/{VERSION}"
    if provider == "ntfy":
        headers = {name: value for name, value in headers.items() if name.casefold() != "content-type"}
        headers["Content-Type"] = "text/plain; charset=utf-8"
        token = NTFY_ACCESS_TOKEN.strip()
        if token:
            headers = {name: value for name, value in headers.items() if name.casefold() != "authorization"}
            headers["Authorization"] = f"Bearer {token}"
    return headers


# Reports one webhook configuration or delivery failure through the shared recovery renderer, so it carries a
# category and a fix line like every other failure this tool prints
def print_webhook_error(message):
    print_recovery_error(context="webhook", detail=str(message))


# Sends one webhook request with the destination, deadline and redirect policy every delivery shares
def post_webhook_request(**request_kwargs):
    destination = str(WEBHOOK_URL or "").strip()
    # Revalidated here because a SIGHUP dotenv reload can replace the destination after the delivery started
    if not validate_webhook_url(destination):
        raise req.exceptions.InvalidURL("WEBHOOK_URL must contain a complete HTTPS link")
    # Redirects are refused, so a moved endpoint cannot forward the alert and its authorization header elsewhere
    return WEBHOOK_SESSION.post(destination, timeout=WEBHOOK_TIMEOUT_SECONDS, verify=VERIFY_SSL, allow_redirects=False, **request_kwargs)


# Sends one webhook through its own bounded retry path, which never shares the PlayStation Network retry policy
def send_webhook(title, description, notification_type="status", force=False, sleeper=None):
    if not force and not webhook_event_enabled(notification_type):
        debug_print("Webhook delivery", outcome="skipped", type=notification_type, reason="alerts are disabled")
        return 1
    if not validate_webhook_url():
        print_webhook_error("WEBHOOK_URL must contain a complete HTTPS link")
        return 1
    provider = normalized_webhook_provider()
    if not provider:
        print_webhook_error("WEBHOOK_PROVIDER must be discord or ntfy")
        return 1
    customization_error = validate_webhook_customization(provider)
    if customization_error is not None:
        print_webhook_error(customization_error)
        return 1
    header_error = validate_webhook_headers(provider)
    if header_error is not None:
        print_webhook_error(header_error)
        return 1
    try:
        webhook_values = build_webhook_values(title, description, notification_type)
        request_headers = build_webhook_headers(provider, webhook_values)
        discord_payload = build_webhook_payload(title, description, notification_type, webhook_values) if provider == "discord" else None
    except ValueError as exc:
        print_webhook_error(exc)
        return 1
    sleep_func = time.sleep if sleeper is None else sleeper
    ntfy_title, ntfy_message = build_ntfy_webhook_message(str(webhook_values["title"]), str(webhook_values["description"])) if provider == "ntfy" else ("", "")
    last_error = None
    for attempt in range(WEBHOOK_MAX_ATTEMPTS):
        attempt_number = attempt + 1
        try:
            debug_print("Webhook delivery", channel=provider, host=webhook_destination_host(), attempt=f"{attempt_number}/{WEBHOOK_MAX_ATTEMPTS}", timeout=f"{WEBHOOK_TIMEOUT_SECONDS}s")
            if provider == "ntfy":
                response = post_webhook_request(data=ntfy_message.encode("utf-8"), params={"title": ntfy_title}, headers=request_headers)
            elif isinstance(discord_payload, str):
                response = post_webhook_request(data=discord_payload, headers=request_headers)
            else:
                response = post_webhook_request(json=discord_payload, headers=request_headers)
            # A rate limit and a server fault are the only answers worth repeating, and only once
            retryable = response.status_code == 429 or 500 <= response.status_code <= 599
            debug_print("Webhook delivery", channel=provider, attempt=f"{attempt_number}/{WEBHOOK_MAX_ATTEMPTS}", status=response.status_code, retryable=retryable)
            if 200 <= response.status_code <= 299:
                verbose_print(f"Webhook delivered through {provider}: {webhook_values['title']}")
                return 0
            last_error = f"HTTP {response.status_code}: {str(getattr(response, 'text', ''))[:200]}"
            if not retryable or attempt_number == WEBHOOK_MAX_ATTEMPTS:
                print_webhook_error(last_error)
                return 1
            delay = webhook_retry_after_seconds(response) if response.status_code == 429 else WEBHOOK_FALLBACK_RETRY_SECONDS
            debug_print("Webhook delivery", channel=provider, retry_in=f"{delay:.1f}s", next_attempt=f"{attempt_number + 1}/{WEBHOOK_MAX_ATTEMPTS}")
            sleep_func(delay)
        except req.RequestException as exc:
            last_error = exc
            debug_print("Webhook delivery", channel=provider, attempt=f"{attempt_number}/{WEBHOOK_MAX_ATTEMPTS}", outcome="failed", error=f"{type(exc).__name__}: {exc}")
            if attempt_number == WEBHOOK_MAX_ATTEMPTS:
                print_webhook_error(exc)
                return 1
            debug_print("Webhook delivery", channel=provider, retry_in=f"{WEBHOOK_FALLBACK_RETRY_SECONDS:.1f}s", next_attempt=f"{attempt_number + 1}/{WEBHOOK_MAX_ATTEMPTS}")
            sleep_func(WEBHOOK_FALLBACK_RETRY_SECONDS)
    print_webhook_error(last_error)
    return 1


# Sends one alert through the email and webhook channels, each switched on independently of the other
def send_notification_channels(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None):
    email_attempted = bool(email_enabled)
    webhook_attempted = webhook_event_enabled(notification_type) if webhook_enabled is None else bool(webhook_enabled)
    email_delivered = False
    webhook_delivered = False
    if email_attempted:
        print(f"Sending email notification to {RECEIVER_EMAIL}")
        email_delivered = send_email(subject, body, body_html, SMTP_SSL) == 0
    if webhook_attempted:
        print("Sending webhook notification")
        webhook_delivered = send_webhook(subject, body, notification_type, force=True) == 0
    # Delivery, not the attempt, so a channel that failed is retried while one that succeeded is not resent
    return email_delivered, webhook_delivered


# Initializes the CSV file
def init_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
    except Exception as e:
        debug_print("CSV initialization", path=csv_file_name, outcome="failed", error=f"{type(e).__name__}: {e}")
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")
    debug_print("CSV initialization", path=csv_file_name, outcome="OK")


# Writes CSV entry
def write_csv_entry(csv_file_name, timestamp, status, game_name):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Date': timestamp, 'Status': status, 'Game name': plain_text(game_name)})

    except Exception as e:
        debug_print("CSV write", path=csv_file_name, outcome="failed", error=f"{type(e).__name__}: {e}")
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")
    debug_print("CSV write", path=csv_file_name, status=status, game=game_name or None, outcome="OK")


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
    except Exception as diag_exc:
        debug_print("Cannot parse ISO timestamp", value=dt_str, outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
        return None


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(now_local_naive()).weekday()]} {now_local_naive().strftime("%d %b %Y, %H:%M:%S")}')


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
        except Exception as diag_exc:
            debug_print("Cannot parse timestamp", value=ts, format="full date", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
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
        except Exception as diag_exc:
            debug_print("Cannot parse timestamp", value=ts, format="short date", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
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
        except Exception as diag_exc:
            debug_print("Cannot parse timestamp", value=ts, format="time", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
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
    global ACTIVE_INACTIVE_NOTIFICATION
    ACTIVE_INACTIVE_NOTIFICATION = not ACTIVE_INACTIVE_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active/inactive status changes = {ACTIVE_INACTIVE_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGUSR2 allowing to switch played game changes notifications
def toggle_game_change_notifications_signal_handler(sig, frame):
    global GAME_CHANGE_NOTIFICATION
    GAME_CHANGE_NOTIFICATION = not GAME_CHANGE_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [game changes = {GAME_CHANGE_NOTIFICATION}]")
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


# Signal handler for SIGHUP allowing to reload secrets from .env
def reload_secrets_signal_handler(sig, frame):
    global WEBHOOK_PROVIDER
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")

    # disable autoscan if DOTENV_FILE set to none
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        # reload .env if python-dotenv is installed
        try:
            from dotenv import load_dotenv, find_dotenv
            if DOTENV_FILE:
                env_path = DOTENV_FILE
            else:
                env_path = find_dotenv()
            if env_path:
                load_dotenv(env_path, override=True)
            else:
                print("* No .env file found, skipping env-var reload")
        except ImportError:
            env_path = None
            print_recovery_advice(missing_dependency_advice("python-dotenv", "The env-var reload was skipped"), label="Warning")

    webhook_url_changed = False
    if env_path:
        for secret in SECRET_KEYS:
            old_val = globals().get(secret)
            val = os.getenv(secret)
            if val is not None and val != old_val:
                globals()[secret] = val
                record_secret_source(secret, "dotenv file")
                if secret == "WEBHOOK_URL":
                    webhook_url_changed = True
                debug_print("Secret reload", name=secret, path=env_path, **secret_fields(val, secret))
                print(f"* Reloaded {secret} from {env_path}")

    # A replacement destination can belong to the other service, which the reloaded URL is the only record of
    if webhook_url_changed:
        detected_provider = detect_webhook_provider(WEBHOOK_URL)
        if detected_provider and detected_provider != normalized_webhook_provider():
            WEBHOOK_PROVIDER = detected_provider
            print(f"* Updated webhook provider to {webhook_provider_display_name(detected_provider)}")

    print_cur_ts("Timestamp:\t\t\t")


# Keeps argparse from colouring its own help, so the help screen is coloured by this tool alone and --no-color is
# not left with a second palette to silence. From Python 3.14 argparse colours the help by default on a terminal
def argparse_color_kwargs() -> dict[str, Any]:
    return {"color": False} if sys.version_info >= (3, 14) else {}


# Finds an optional config file
def find_config_file(cli_path=None):
    """
    Search for an optional config file in:
      1) CLI-provided path (must exist if given)
      2) ./{DEFAULT_CONFIG_FILENAME}
      3) ~/.{DEFAULT_CONFIG_FILENAME}
      4) script-directory/{DEFAULT_CONFIG_FILENAME}
    """

    if cli_path:
        p = Path(os.path.expanduser(cli_path))
        return str(p) if p.is_file() else None

    candidates = [
        Path.cwd() / DEFAULT_CONFIG_FILENAME,
        Path.home() / f".{DEFAULT_CONFIG_FILENAME}",
        Path(__file__).parent / DEFAULT_CONFIG_FILENAME,
    ]

    for p in candidates:
        debug_print("Looking for a config file", path=p)
        if p.is_file():
            return str(p)
    return None


# Returns the --config-file value from the raw arguments, before argparse has run
def early_config_file_argument(arguments=None):
    values = list(sys.argv[1:] if arguments is None else arguments)
    for index, argument in enumerate(values):
        if argument == "--config-file" and index + 1 < len(values):
            return values[index + 1]
        if argument.startswith("--config-file="):
            return argument.split("=", 1)[1]
    return None


# Applies the two settings that decide how the terminal looks before arguments are parsed, leaving every error
# to the real config load. The screen clear and the startup banner both run before argparse, so colour has to
# be resolved here or a configured COLORED_OUTPUT would only take effect after the first output was written
def apply_early_output_config():
    global CLEAR_SCREEN, COLORED_OUTPUT
    try:
        cli_path = early_config_file_argument()
        config_path = find_config_file(os.path.expanduser(cli_path) if cli_path else None)
        if not config_path:
            return
        # Reading a config never runs it, so this early peek cannot have side effects
        values = parse_config_content(Path(config_path).read_text(encoding="utf-8"), str(config_path))
    except Exception:
        # A broken or unreadable config is reported with full detail once the arguments are parsed
        return
    if isinstance(values.get("CLEAR_SCREEN"), bool):
        CLEAR_SCREEN = values["CLEAR_SCREEN"]
    if isinstance(values.get("COLORED_OUTPUT"), bool):
        COLORED_OUTPUT = values["COLORED_OUTPUT"]


# Settings an older version wrote that this version no longer defines, ignored instead of rejected
RETIRED_CONFIG_SETTINGS = frozenset(())

# Settings the template ships commented out so the built-in default applies, still accepted from a config file
COMMENTED_CONFIG_SETTINGS = frozenset({"COLOR_THEME"})


# Collects the setting names the built-in configuration template defines
def _config_allowed_names():
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    return frozenset(statement.targets[0].id for statement in template_tree.body if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name)) | COMMENTED_CONFIG_SETTINGS


# Returns the literal values the built-in config template ships with, used to clear a section the user declined
def _config_template_defaults():
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    defaults = {}
    for statement in template_tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            continue
        try:
            defaults[statement.targets[0].id] = ast.literal_eval(statement.value)
        except ValueError:
            continue
    return defaults


# Parses allowlisted literal config assignments without executing any file content
def parse_config_content(content, filename="<config>", retired_out=None, reference_values=None):
    tree = ast.parse(content, filename, "exec")
    allowed_names = _config_allowed_names()
    parsed_values = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            raise ValueError(f"Line {getattr(statement, 'lineno', '?')}: only NAME = value assignments are allowed")
        name = statement.targets[0].id
        if name in RETIRED_CONFIG_SETTINGS and name not in allowed_names:
            if retired_out is not None and name not in retired_out:
                retired_out.append(name)
            continue
        if name not in allowed_names:
            raise ValueError(f"Line {statement.lineno}: unsupported configuration setting {name!r}")
        # One setting may reuse another, which the built-in template does and existing configs copy
        if isinstance(statement.value, ast.Name):
            referenced = statement.value.id
            if referenced not in allowed_names:
                raise ValueError(f"Line {statement.lineno}: {name} may only reference another configuration setting")
            source = parsed_values if referenced in parsed_values else (reference_values if reference_values is not None else globals())
            if referenced not in source:
                raise ValueError(f"Line {statement.lineno}: {name} references {referenced!r} before it has a value")
            parsed_values[name] = source[referenced]
            continue
        try:
            parsed_values[name] = ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as exc:
            raise ValueError(f"Line {statement.lineno}: {name} must be a plain value such as a number, string, True, False, None, list, tuple or dict") from exc
    return parsed_values


# Validates config content through the same restricted parser used at startup
def validate_config_content(content, filename="<generated-config>"):
    parse_config_content(content, filename)


# Reports settings an older version wrote that this version no longer defines
def describe_retired_settings(names, quoted_path):
    listed = ", ".join(sorted(names))
    return f"Config file {quoted_path} contains settings this version no longer uses, which were ignored: {listed}"


# Loads a config file as data and applies only recognized literal settings
def load_config_file(config_path, namespace=None, report_errors=True, advice_out=None):
    selected_namespace = globals() if namespace is None else namespace
    retired_settings = []
    try:
        content = Path(config_path).read_text(encoding="utf-8")
        # Parsed as data rather than executed, so a config file picked up from the working directory cannot run code
        parsed_values = parse_config_content(content, str(config_path), retired_settings)
        selected_namespace.update(parsed_values)
        debug_print("Configuration applied", path=config_path, settings=len(parsed_values), names=", ".join(sorted(parsed_values)) or "none")
        if retired_settings and report_errors:
            print(f"* Note: {describe_retired_settings(retired_settings, chr(39) + str(config_path) + chr(39))}")
        return True
    except SyntaxError as exc:
        detail = f"Config file '{config_path}' has invalid Python syntax"
        if exc.lineno is not None:
            detail += f" at line {exc.lineno}"
        if exc.text:
            detail += f" | Source: {exc.text.rstrip()}"
        detail += f" | Parser: {exc.msg}"
    # Checked before ValueError because UnicodeDecodeError derives from it
    except UnicodeDecodeError:
        detail = f"Config file '{config_path}' is not valid UTF-8"
    except ValueError as exc:
        detail = f"Config file '{config_path}' contains unsupported content: {exc}"
    except Exception as exc:
        detail = f"Config file '{config_path}' failed with {type(exc).__name__}: {exc}"
    debug_print("Configuration rejected", path=config_path, reason=detail)
    advice = classify_recovery_error(context="config.invalid", detail=detail)
    if advice_out is not None:
        advice_out.append(advice)
    if report_errors:
        print_recovery_advice(advice)
    return False


# Normalizes Unicode punctuation, symbols and spacing in a string to plain ASCII
def normalize_ascii(s):
    if not isinstance(s, str):
        return s
    # punctuation & symbols to ASCII
    s = (s.replace("\u2018", "'").replace("\u2019", "'")  # ‘ ’ -> '
         .replace("\u201C", '"').replace("\u201D", '"')   # “ ” -> "
         .replace("\u2013", "-")                          # – -> -
         .replace("\u2026", "...")                        # … -> ...
         .replace("\u00A0", " "))                         # NBSP -> space
    # remove trademark symbols
    for ch in ("\u00AE", "\u2122"):  # ® ™
        s = s.replace(ch, "")
    # collapse doubled single quotes that often appear after smart-quote normalization
    s = s.replace("''", "'")
    # collapse multiple spaces
    while "  " in s:
        s = s.replace("  ", " ")
    return s.strip()


# Prints the last N earned trophies across titles with game, type and earn date
def print_last_earned_trophies(psn_user, max_items=5, title_limit=15):
    PT = None
    try:
        from psnawp_api.models.trophies import PlatformType as PT  # 3.x
    except Exception as diag_exc:
        debug_print("PSNAWP PlatformType is unavailable, falling back to string platform names", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
        PT = None  # fallback to string platforms later

    def _get(obj, *names, default=None):
        for n in names:
            if hasattr(obj, n):
                v = getattr(obj, n)
                if v is not None:
                    return v
        return default

    def _platforms_to_try(title):
        raw = getattr(title, "platform", None)
        raw_val = getattr(raw, "value", raw)
        s = (str(raw_val).lower() if raw_val else "")
        if PT:
            if "ps5" in s:
                return [PT.PS5, PT.PS4]
            if "ps4" in s:
                return [PT.PS4, PT.PS5]
            return [PT.PS5, PT.PS4]
        # string fallback
        if "ps5" in s:
            return ["ps5", "ps4"]
        if "ps4" in s:
            return ["ps4", "ps5"]
        return ["ps5", "ps4"]

    def _earn_dt(tr):
        return _get(tr, "earned_date_time", "earnedDateTime", default=None)

    def _trophy_type_str(tr):
        raw = _get(tr, "trophy_type", "trophyType", default=None)
        if raw is None:
            return "UNKNOWN"
        if hasattr(raw, "name"):
            return raw.name
        return str(raw).upper()

    # title-name resolver (cache)
    _title_name_cache = {}

    def _resolve_title_name(npcomm, platform):
        key = (npcomm, str(platform))
        if key in _title_name_cache:
            return _title_name_cache[key]

        def _first_name_like(obj):
            # Try common fields first
            for fld in ("trophy_title_name", "trophyTitleName", "title_name", "titleName", "name"):
                if hasattr(obj, fld):
                    val = getattr(obj, fld)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
            # Fallback: scan attributes that look like "*name"
            for attr in dir(obj):
                if attr.startswith("_"):
                    continue
                if "name" in attr.lower():
                    try:
                        val = getattr(obj, attr)
                    except Exception as diag_exc:
                        debug_print("Cannot read attribute while looking for a title name", attribute=attr, outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
                        continue
                    if isinstance(val, str) and val.strip():
                        return val.strip()
            return None

        name = None

        # A) groups often carry the title name
        try:
            for g in psn_user.trophy_groups(np_communication_id=npcomm, platform=platform):
                name = _first_name_like(g)
                if name:
                    break
        except Exception as diag_exc:
            debug_print("PSN API trophy_groups()", npcomm=npcomm, outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

        # B) per-title summary
        if not name:
            try:
                summ = psn_user.trophy_summary(np_communication_id=npcomm, platform=platform)
                name = _first_name_like(summ)
            except Exception as diag_exc:
                debug_print("PSN API trophy_summary()", npcomm=npcomm, outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

        # C) scan titles
        if not name:
            try:
                for tt in psn_user.trophy_titles(limit=title_limit):
                    nc = getattr(tt, "np_communication_id", None) or getattr(tt, "npCommunicationId", None)
                    if nc == npcomm:
                        name = _first_name_like(tt)
                        if name:
                            break
            except Exception as diag_exc:
                debug_print("PSN API trophy_titles()", npcomm=npcomm, context="resolving a title name", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

        if not name:
            name = npcomm  # last resort

        _title_name_cache[key] = name
        return name
    # -------------------------------------

    items = []

    # 1) list titles (no special args for cross-version compat)
    debug_print("PSN API trophy_titles()", limit=title_limit)
    try:
        titles_iter = psn_user.trophy_titles(limit=title_limit)
    except Exception as diag_exc:
        debug_print("PSN API trophy_titles() failed, no trophy titles to scan", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
        titles_iter = []

    for tt in titles_iter:
        npcomm = _get(tt, "np_communication_id", "npCommunicationId", default=None)
        if not npcomm:
            continue

        for plat in _platforms_to_try(tt):
            debug_print("PSN API trophies()", npcomm=npcomm, platform=plat)
            try:
                it = psn_user.trophies(
                    np_communication_id=npcomm,
                    platform=plat,
                    include_progress=True,
                    trophy_group_id="all",
                )
            except Exception as diag_exc:
                debug_print("PSN API trophies()", npcomm=npcomm, platform=plat, outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
                continue

            got_any_for_title = False
            for tr in it:
                got_any_for_title = True
                if not getattr(tr, "earned", False):
                    continue
                dt = _earn_dt(tr)
                if not dt:
                    continue

                game_name = normalize_ascii(_resolve_title_name(npcomm, plat))
                ttype = _trophy_type_str(tr)
                tname = _get(tr, "trophy_name", "trophyName", default=None)
                if not tname:
                    tname = "(hidden)" if getattr(tr, "hidden", False) else "(unknown)"
                tname = normalize_ascii(tname)

                items.append((dt, game_name, ttype, tname))

            if got_any_for_title:
                break  # this platform works for this title

        if len(items) >= max_items:
            break

    if not items:
        print("- (no recent trophies found or trophy visibility is restricted)")
        return

    # 2) sort & print
    try:
        items.sort(key=lambda x: x[0], reverse=True)
    except Exception as diag_exc:
        debug_print("Trophy list could not be sorted by earn date, falling back to a tolerant sort", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
        def _ts(dt):
            try:
                return int(dt.timestamp())
            except Exception as diag_exc:
                debug_print("Cannot read the earn timestamp of a trophy, sorting it last", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
                return -1
        items.sort(key=lambda x: _ts(x[0]), reverse=True)

    for dt, game, ttype, tname in items[:max_items]:
        try:
            ts = int(dt.timestamp())
            dt_fmt = get_date_from_ts(ts)
        except Exception as diag_exc:
            debug_print("Cannot format the earn date of a trophy", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
            dt_fmt = "n/a"
        print(f"- {dt_fmt} | {game} | {ttype} | {tname}")


# Gets detailed user information and displays it (for -i/--info mode)
def get_user_info(psn_user_id, include_trophies=False, show_recent_games=True):
    # Helper to print step message
    def print_step(msg):
        sys.stdout.write(f"- {msg}".ljust(32))
        sys.stdout.flush()

    # Helper to print OK
    def print_ok():
        print("OK")

    print(f"* Fetching details for PlayStation user '{psn_user_id}'...\n")

    debug_print("PSNAWP session init", user=psn_user_id, npsso=secret_fields(PSN_NPSSO)["value"])
    print_step("Authenticating with PSN...")
    try:
        psnawp = psn_client()
        psn_user = psnawp.user(online_id=psn_user_id)
    except Exception as e:
        print()
        print_recovery_error(e, context="startup", probe_auth=True)
        sys.exit(1)
    print_ok()

    debug_print("PSN API profile(), friendship() and get_shareable_profile_link()", user=psn_user_id)
    print_step("Fetching profile info...")
    try:
        accountid = psn_user.account_id
        profile = psn_user.profile()
        aboutme = profile.get("aboutMe")
        isplus = profile.get("isPlus")
        langs = profile.get("languages") or []
        is_verified = profile.get("isOfficiallyVerified")
        fs = psn_user.friendship()
        share = psn_user.get_shareable_profile_link()
    except Exception as e:
        print()
        print_recovery_error(e, context="startup", detail=f"Reading the PSN profile of '{psn_user_id}' failed: {e}", probe_auth=True)
        sys.exit(1)
    print_ok()

    debug_print("PSN API get_presence()", user=psn_user_id)
    print_step("Fetching presence info...")
    try:
        psn_user_presence = psn_user.get_presence()
        parse_presence(psn_user_presence)
    except Exception as e:
        print()
        print_recovery_error(e, context="startup", detail=f"Cannot get presence for user '{psn_user_id}': {e}", probe_auth=True)
        sys.exit(1)
    print_ok()

    print_step("Fetching game title info...")
    try:
        status = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("onlineStatus")

        if not status:
            print()
            print_recovery_error(PsnMalformedResponse(f"Cannot get status for user '{psn_user_id}': the presence payload carries no onlineStatus"), context="startup")
            sys.exit(1)

        status = str(status).lower()

        psn_platform_raw = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("platform")
        psn_platform = format_platform_display(psn_platform_raw)
        lastonline = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("lastOnlineDate")
        availability = psn_user_presence["basicPresence"].get("availability")

        lastonline_dt = convert_iso_str_to_datetime(lastonline)
        if lastonline_dt:
            lastonline_ts = int(lastonline_dt.timestamp())
        else:
            lastonline_ts = 0

        gametitleinfolist = psn_user_presence["basicPresence"].get("gameTitleInfoList")
        game_name = ""
        launchplatform = ""

        if gametitleinfolist:
            game_name_raw = gametitleinfolist[0].get("titleName")
            game_name = normalize_ascii(game_name_raw) if game_name_raw else ""
            launchplatform = gametitleinfolist[0].get("launchPlatform")
            launchplatform = str(launchplatform).upper()
    except Exception as e:
        print()
        print_recovery_error(e, context="startup", detail=f"Reading the game title info of '{psn_user_id}' failed: {e}")
        sys.exit(1)
    print_ok()
    print()

    psn_last_status_file = resolve_status_file(psn_user_id)
    status_ts_old = int(time.time())

    if os.path.isfile(psn_last_status_file):
        try:
            with open(psn_last_status_file, 'r', encoding="utf-8") as f:
                last_status_read = json.load(f)
            debug_print("Saved status read", path=psn_last_status_file)
            if last_status_read:
                last_status_ts = last_status_read[0]
                last_status = last_status_read[1]

                if lastonline_ts and status == "offline":
                    if lastonline_ts >= last_status_ts:
                        status_ts_old = lastonline_ts
                    else:
                        status_ts_old = last_status_ts
                elif not lastonline_ts and status == "offline":
                    status_ts_old = last_status_ts
                elif status and status != "offline" and status == last_status:
                    status_ts_old = last_status_ts
        except Exception as diag_exc:
            debug_print("Cannot reconcile the saved status with the PSN profile, falling back to the last online timestamp", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
            if lastonline_ts and status == "offline":
                status_ts_old = lastonline_ts
    else:
        if lastonline_ts and status == "offline":
            status_ts_old = lastonline_ts

    print(f"PlayStation ID:\t\t\t{psn_user_id}")
    print(f"PSN account ID:\t\t\t{accountid}")
    print(f"\nStatus:\t\t\t\t{str(status).upper()}")
    if availability:
        available_str = "Yes" if availability == "availableToPlay" else "No"
        print(f"Available to play:\t\t{available_str}")

    psn_platform_displayed = False
    if psn_platform:
        print(f"\nPlatform:\t\t\t{psn_platform}")
        psn_platform_displayed = True

    if not psn_platform_displayed:
        print()
    print(f"PS+ user:\t\t\t{isplus}")

    # an official account belonging to a recognised developer, publisher, community manager or another official role
    if is_verified is not None:
        print(f"Verified:\t\t\t{is_verified}")

    newline_needed = False

    if aboutme:
        print(f"\nAbout me:\t\t\t{aboutme}")
        newline_needed = True

    if langs:
        prefix = "\n" if not newline_needed else ""
        print(f"{prefix}Languages:\t\t\t{', '.join(langs)}")

    try:
        relation = fs.get("friendRelation")
        print(f"\nRelation:\t\t\t{relation}")

        if relation == "friend":
            mf = fs.get("mutualFriendsCount")
            if isinstance(mf, int) and mf >= 0:
                print(f"Mutual friends:\t\t\t{mf}")
            elif mf is None:
                print("Mutual friends:\t\t\tunknown")
            else:
                print("Mutual friends:\t\t\thidden")
        else:
            # Don't print mutual friends at all
            pass

    except Exception as diag_exc:
        debug_print("Cannot read the friendship relation from the PSN profile", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

    try:
        print(f"\nProfile URL:\t\t\t{share.get('shareUrl')}")
        # print(f"Profile QR image:\t\t{share.get('shareImageUrl')}")
    except Exception as diag_exc:
        debug_print("Cannot read the shareable profile link from the PSN profile", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

    if status == "offline" and status_ts_old > 0:
        last_status_dt_str = get_date_from_ts(status_ts_old)
        print(f"\n* Last time user was available:\t{last_status_dt_str}")
        print(f"* User is OFFLINE for:\t\t{calculate_timespan(now_local(), int(status_ts_old), show_seconds=False)}")
    elif status != "offline":
        if os.path.isfile(psn_last_status_file):
            try:
                with open(psn_last_status_file, 'r', encoding="utf-8") as f:
                    last_status_read = json.load(f)
                if last_status_read and last_status_read[1] == status:
                    print(f"* User is {str(status).upper()} for:\t\t{calculate_timespan(now_local(), int(last_status_read[0]), show_seconds=False)}")
            except Exception as diag_exc:
                debug_print("Cannot read the saved status file", path=psn_last_status_file, outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

    # Show trophy summary and last earned trophies only if requested
    if include_trophies:
        try:
            print(f"\n* Getting trophy summary ...")
            debug_print("PSN API trophy_summary()", user=psn_user_id)
            ts = psn_user.trophy_summary()
            et = ts.earned_trophies
            prog = int(ts.progress) if ts.progress is not None else 0
            print(f"\nTrophy level:\t\t\t{ts.trophy_level} ({prog}% to next, tier {ts.tier})")
            print(
                "Trophies earned:\t\t"
                f"{et.platinum} Platinum, {et.gold} Gold, {et.silver} Silver, {et.bronze} Bronze "
                f"({et.platinum + et.gold + et.silver + et.bronze} total)"
            )
        except Exception as diag_exc:
            debug_print("PSN API trophy_summary() failed, trophy level is not shown", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

        num_trophies = 5
        try:
            print(f"\n* Getting list of last {num_trophies} earned trophies ...\n")
            print_last_earned_trophies(psn_user, max_items=num_trophies, title_limit=15)
        except Exception as diag_exc:
            debug_print("Cannot list the last earned trophies", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

    # Show recently played games only if requested
    if show_recent_games:
        try:
            # Helper function to compact duration format, convert "X day(s), HH:MM:SS" to "Xd HH:MM:SS"
            def _compact_duration(s):
                if not s:
                    return "0:00:00"
                s = str(s).strip()

                if "day" in s.lower():
                    try:
                        if "," in s:
                            parts = s.split(",", 1)
                            days_part = parts[0].strip()            # "1 day" / "2 days"
                            time_part = parts[1].strip()            # "23:47:54"
                            d = int(days_part.split()[0])
                            return f"{d}d {time_part}"
                        else:
                            # No comma, try to extract days anyway (unlikely but handle it)
                            words = s.split()
                            if len(words) >= 2 and words[1].lower().startswith("day"):
                                d = int(words[0])
                                if len(words) > 2:
                                    time_part = " ".join(words[2:])
                                    return f"{d}d {time_part}"
                                return f"{d}d"
                    except (ValueError, IndexError) as diag_exc:
                        debug_print("Cannot compact the duration", value=s, fallback="original text", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
                        return s  # fallback to original if parsing fails
                return s

            def _shorten_middle(s, max_len, ellipsis="..."):
                if s is None:
                    return ""
                s = str(s)
                if len(s) <= max_len:
                    return s
                keep = max_len - len(ellipsis)
                if keep <= 0:
                    return ellipsis[:max_len]
                left = keep // 2
                right = keep - left
                return f"{s[:left]}{ellipsis}{s[-right:]}"

            recent_entries = []
            print(f"\n* Getting list of recently played games ...")
            debug_print("PSN API title_stats()", user=psn_user_id, limit=10, page_size=50)
            for i, t in enumerate(psn_user.title_stats(limit=10, page_size=50), 1):
                if not t:
                    continue
                name_raw = t.name or "(unknown)"
                name = normalize_ascii(name_raw)
                cat = getattr(getattr(t, "category", None), "name", "UNKNOWN")
                last_played = (
                    get_date_from_ts(int(t.last_played_date_time.timestamp()))
                    if t.last_played_date_time else "n/a"
                )
                total_raw = str(t.play_duration) if t.play_duration else "0:00:00"
                # Compact duration immediately to ensure it fits in the column
                total = _compact_duration(total_raw)
                recent_entries.append(f"Recent #{i}:\t\t\t{name} | {cat} | last played {last_played} | total {total}")

            # Decide column widths based on terminal size
            try:
                import shutil
                term_width = shutil.get_terminal_size(fallback=(100, 24)).columns
            except Exception as diag_exc:
                debug_print("Cannot detect the terminal width, falling back to 100 columns", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
                term_width = 100

            w_num = 3
            w_platform = 8
            w_last = 24
            w_total = 14  # fits "999d 23:59:59" (14 chars) after compacting "X day(s), HH:MM:SS" -> "Xd HH:MM:SS"
            fixed = 1 + w_num + 2 + w_platform + 2 + w_last + 2 + w_total
            w_title = max(24, term_width - fixed)

            # Only print the table if we have entries
            if recent_entries:
                print()
                hdr = f"{'#'.ljust(w_num)}  {'Title'.ljust(w_title)}  {'Platform'.ljust(w_platform)}  {'Last played'.ljust(w_last)}  {'Total'.ljust(w_total)}"
                sep = f"{'-' * w_num}  {'-' * w_title}  {'-' * w_platform}  {'-' * w_last}  {'-' * w_total}"
                print(colorize("section", hdr))
                print(sep)

                for i, entry in enumerate(recent_entries, 1):
                    try:
                        _, rest = entry.split(":", 1)
                        parts = rest.strip().split("|")
                        name = parts[0].strip()
                        cat = parts[1].strip()
                        last_played = parts[2].replace("last played", "").strip()
                        total = _compact_duration(parts[3].replace("total", "").strip())
                    except Exception:
                        # If parsing ever fails, print raw line as a fallback
                        print(entry)
                        continue

                    name_fmt = _shorten_middle(name, w_title)
                    # Coloured here rather than by a line rule: the columns are positional, with no label or
                    # separator a rule could recognize once the values are padded to width
                    row = (
                        f"{str(i).ljust(w_num)}  "
                        f"{colorize('game', name_fmt.ljust(w_title))}  "
                        f"{colorize('platform', cat.ljust(w_platform))}  "
                        f"{colorize('date', last_played.ljust(w_last))}  "
                        f"{colorize('duration', total.ljust(w_total))}"
                    )
                    print(row)
        except Exception as diag_exc:
            debug_print("Cannot render the recently played games table", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

    if game_name:
        launchplatform_str = ""
        if launchplatform:
            launchplatform_str = f" ({launchplatform})"
        print(f"\nUser is currently in-game:\t{game_name}{launchplatform_str}")


# Main function that monitors gaming activity of the specified PSN user
def psn_monitor_user(psn_user_id, csv_file_name):

    mark_monitoring_started()

    alive_since = int(time.time())
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
        print_recovery_error(e, context="file.unwritable", detail=f"Cannot prepare the CSV file '{csv_file_name}': {e}")

    print("Sneaking into PlayStation like a ninja ...\n")

    # Helper to print step message
    def print_step(msg):
        sys.stdout.write(f"- {msg}".ljust(32))
        sys.stdout.flush()

    # Helper to print OK
    def print_ok():
        print("OK")

    debug_print("PSNAWP session init", user=psn_user_id, npsso=secret_fields(PSN_NPSSO)["value"])
    print_step("Authenticating with PSN...")
    try:
        psnawp = psn_client()
        psn_user = psnawp.user(online_id=psn_user_id)
    except Exception as e:
        print()
        print_recovery_error(e, context="startup", probe_auth=True)
        sys.exit(1)
    print_ok()

    debug_print("PSN API profile(), friendship() and get_shareable_profile_link()", user=psn_user_id)
    print_step("Fetching profile info...")
    try:
        accountid = psn_user.account_id
        profile = psn_user.profile()
        aboutme = profile.get("aboutMe")
        isplus = profile.get("isPlus")
        langs = profile.get("languages") or []
        is_verified = profile.get("isOfficiallyVerified")
        fs = psn_user.friendship()
        share = psn_user.get_shareable_profile_link()
    except Exception as e:
        print()
        print_recovery_error(e, context="startup", detail=f"Reading the PSN profile of '{psn_user_id}' failed: {e}", probe_auth=True)
        sys.exit(1)
    print_ok()

    debug_print("PSN API get_presence()", user=psn_user_id)
    print_step("Fetching presence info...")
    try:
        psn_user_presence = psn_user.get_presence()
        parse_presence(psn_user_presence)
    except Exception as e:
        print()
        print_recovery_error(e, context="startup", detail=f"Cannot get presence for user '{psn_user_id}': {e}", probe_auth=True)
        sys.exit(1)
    print_ok()

    print_step("Fetching game title info...")
    try:
        status = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("onlineStatus")

        if not status:
            print()
            print_recovery_error(PsnMalformedResponse(f"Cannot get status for user '{psn_user_id}': the presence payload carries no onlineStatus"), context="startup")
            sys.exit(1)

        status = str(status).lower()

        psn_platform_raw = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("platform")
        psn_platform = format_platform_display(psn_platform_raw)
        lastonline = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("lastOnlineDate")
        availability = psn_user_presence["basicPresence"].get("availability")

        lastonline_dt = convert_iso_str_to_datetime(lastonline)
        if lastonline_dt:
            lastonline_ts = int(lastonline_dt.timestamp())
        else:
            lastonline_ts = 0

        gametitleinfolist = psn_user_presence["basicPresence"].get("gameTitleInfoList")
        game_name = ""
        launchplatform = ""

        if gametitleinfolist:
            game_name_raw = gametitleinfolist[0].get("titleName")
            game_name = normalize_ascii(game_name_raw) if game_name_raw else ""
            launchplatform = gametitleinfolist[0].get("launchPlatform")
            launchplatform = str(launchplatform).upper()
    except Exception as e:
        print()
        print_recovery_error(e, context="startup", detail=f"Reading the game title info of '{psn_user_id}' failed: {e}")
        sys.exit(1)
    print_ok()

    print()

    status_ts_old = int(time.time())
    status_ts_old_bck = status_ts_old

    if status and status != "offline":
        status_online_start_ts = status_ts_old
        status_online_start_ts_old = status_online_start_ts

    psn_last_status_file = resolve_status_file(psn_user_id)
    last_status_read = []
    last_status_ts = 0
    last_status = ""

    if os.path.isfile(psn_last_status_file):
        try:
            with open(psn_last_status_file, 'r', encoding="utf-8") as f:
                last_status_read = json.load(f)
            debug_print("Saved status read", path=psn_last_status_file)
        except Exception as e:
            print_recovery_error(e, context="file.unreadable", detail=f"Cannot load the last saved status from '{psn_last_status_file}': {e}")
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
        try:
            save_last_status(psn_last_status_file, status_ts_old, status)
            debug_print("Saved status written", path=psn_last_status_file, status=status)
        except Exception as e:
            print_recovery_error(e, context="file.unwritable", detail=f"Cannot save the last status to '{psn_last_status_file}': {e}")

    try:
        if csv_file_name and (status != last_status):
            write_csv_entry(csv_file_name, now_local_naive(), status, game_name)
    except Exception as e:
        print_recovery_error(e, context="file.unwritable", detail=f"Cannot write to the CSV file '{csv_file_name}': {e}")

    print(f"\nPlayStation ID:\t\t\t{psn_user_id}")
    print(f"PSN account ID:\t\t\t{accountid}")

    print(f"\nStatus:\t\t\t\t{str(status).upper()}")
    if availability:
        available_str = "Yes" if availability == "availableToPlay" else "No"
        print(f"Available to play:\t\t{available_str}")

    psn_platform_displayed = False
    if psn_platform:
        print(f"\nPlatform:\t\t\t{psn_platform}")
        psn_platform_displayed = True

    if not psn_platform_displayed:
        print()
    print(f"PS+ user:\t\t\t{isplus}")

    # an official account belonging to a recognised developer, publisher, community manager or another official role
    if is_verified is not None:
        print(f"Verified:\t\t\t{is_verified}")

    newline_needed = False

    if aboutme:
        print(f"\nAbout me:\t\t\t{aboutme}")
        newline_needed = True

    if langs:
        prefix = "\n" if not newline_needed else ""
        print(f"{prefix}Languages:\t\t\t{', '.join(langs)}")

    try:
        relation = fs.get("friendRelation")
        print(f"\nRelation:\t\t\t{relation}")

        if relation == "friend":
            mf = fs.get("mutualFriendsCount")
            if isinstance(mf, int) and mf >= 0:
                print(f"Mutual friends:\t\t\t{mf}")
            elif mf is None:
                print("Mutual friends:\t\t\tunknown")
            else:
                print("Mutual friends:\t\t\thidden")
        else:
            # Don't print mutual friends at all
            pass

    except Exception as diag_exc:
        debug_print("Cannot read the friendship relation from the PSN profile", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

    try:
        print(f"\nProfile URL:\t\t\t{share.get('shareUrl')}")
        # print(f"Profile QR image:\t\t{share.get('shareImageUrl')}")
    except Exception as diag_exc:
        debug_print("Cannot read the shareable profile link from the PSN profile", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

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
        try:
            save_last_status(psn_last_status_file, status_ts_old, status)
            debug_print("Saved status written", path=psn_last_status_file, status=status)
        except Exception as e:
            print_recovery_error(e, context="file.unwritable", detail=f"Cannot save the last status to '{psn_last_status_file}': {e}")

    if status_ts_old != status_ts_old_bck:
        if status == "offline":
            last_status_dt_str = get_date_from_ts(status_ts_old)
            print(f"\n* Last time user was available:\t{last_status_dt_str}")
        print(f"\n* User is {str(status).upper()} for:\t\t{calculate_timespan(now_local(), int(status_ts_old), show_seconds=False)}")

    status_old = status
    game_name_old = game_name

    print_cur_ts("\nTimestamp:\t\t\t")

    alive_since = int(time.time())
    error_email_sent = False
    error_webhook_sent = False

    m_subject = m_body = ""
    error_streak = 0
    outage = OutageReporter()
    # A recovery is only worth reporting when the failure it recovers from was reported or alerted on
    failure_announced = False
    # A session rebuild is worth one line per outage, since it repeats on its own cooldown while the failure lasts
    rebuild_announced = False
    last_recreate_ts = 0
    recreate_cooldown = 300  # avoid recreating PSNAWP session too frequently
    last_npsso_seen = PSN_NPSSO

    # Releases the connection pool of a PSNAWP client before it is replaced, so repeated recreations do not leak sockets
    def _close_psnawp_sessions(obj):
        if obj is None:
            return
        already_closed = set()

        def _close(target, label):
            if target is None or not hasattr(target, "close") or id(target) in already_closed:
                return
            already_closed.add(id(target))
            try:
                target.close()
                debug_print("Closed the PSNAWP session", label=label)
            except Exception as diag_exc:
                debug_print("Closing the PSNAWP session", label=label, outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

        try:
            # Where psnawp keeps the requests session, the same attribute psn_client() uses to apply the TLS setting
            authenticator = getattr(obj, "authenticator", None)
            request_builder = getattr(authenticator, "request_builder", None)
            _close(getattr(request_builder, "session", None), "authenticator.request_builder.session")
            # Duck-typed fallbacks, so a psnawp release that moves or wraps the session is still cleaned up
            _close(obj, "client")
            for attr in ("session", "_session", "http", "_http", "client", "_client"):
                _close(getattr(obj, attr, None), f"'{attr}' session")
        except Exception as diag_exc:
            debug_print("Closing PSNAWP sessions", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")

    def get_sleep_interval():
        return PSN_ACTIVE_CHECK_INTERVAL if status and status != "offline" else PSN_CHECK_INTERVAL

    def _recreate_session_rate_limited():
        nonlocal psnawp, psn_user, last_recreate_ts
        now = int(time.time())
        if (now - last_recreate_ts) < recreate_cooldown:
            debug_print("PSNAWP session recreation", outcome="skipped", cooldown_left=display_time(recreate_cooldown - (now - last_recreate_ts)), cooldown=display_time(recreate_cooldown))
            return False
        try:
            _close_psnawp_sessions(psnawp)
        except Exception as diag_exc:
            debug_print("Closing the old PSNAWP session before recreating it", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
        try:
            psnawp = psn_client()
            psn_user = psnawp.user(online_id=psn_user_id)
            last_recreate_ts = now
            verbose_notice("Recreated the PSNAWP session")
            return True
        except Exception as diag_exc:
            debug_print("Recreating the PSNAWP session", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
            return False

    sleep_interval = get_sleep_interval()

    debug_print("Waiting", interval=display_time(sleep_interval), reason="before the first check", status=status or "unknown")
    time.sleep(sleep_interval)

    check_number = 0
    recovery_hints = RecoveryHintTracker()

    # Main loop
    while True:
        check_number += 1
        # If PSN_NPSSO changed (e.g. .env updated + SIGHUP), recreate the PSNAWP session immediately.
        if PSN_NPSSO != last_npsso_seen:
            verbose_notice(f"PSN_NPSSO changed ({secret_fingerprint(PSN_NPSSO, 'PSN_NPSSO')}), recreating the PSNAWP session")
            try:
                _close_psnawp_sessions(psnawp)
            except Exception as diag_exc:
                debug_print("Closing the old PSNAWP session after the NPSSO change", outcome="failed", error=f"{type(diag_exc).__name__}: {diag_exc}")
            try:
                psnawp = psn_client()
                psn_user = psnawp.user(online_id=psn_user_id)
                last_recreate_ts = int(time.time())
                print("* PSN_NPSSO updated - recreated PSNAWP session")
                print_cur_ts("Timestamp:\t\t\t")
            except Exception as e:
                advice = print_recovery_error(e, context="monitor", detail=f"Rebuilding the PSNAWP session after the PSN_NPSSO change failed: {e}", probe_auth=True)
                if (ERROR_NOTIFICATION and not error_email_sent) or (webhook_event_enabled("error") and not error_webhook_sent):
                    email_delivered, webhook_delivered = send_notification_channels("error", recovery_email_subject(advice, psn_user_id), recovery_email_body(advice), email_enabled=ERROR_NOTIFICATION and not error_email_sent, webhook_enabled=webhook_event_enabled("error") and not error_webhook_sent)
                    error_email_sent = error_email_sent or email_delivered
                    error_webhook_sent = error_webhook_sent or webhook_delivered
                print_cur_ts("Timestamp:\t\t\t")
            last_npsso_seen = PSN_NPSSO
            # allow notifications again after token rotation
            error_email_sent = False
            error_webhook_sent = False
            error_streak = 0
            failure_announced = False
            rebuild_announced = False

        # Sometimes PSN network functions halt, so we use alarm signal functionality to kill it inevitably, not available on Windows
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT)
        debug_print("Starting check", check=f"#{check_number}", user=psn_user_id, operation="PSN API get_presence()", timeout=f"{FUNCTION_TIMEOUT}s")
        try:
            psn_user_presence = psn_user.get_presence()
            parsed = parse_presence(psn_user_presence)
            status = parsed["status"]
            game_name_raw = parsed["game_name"]
            game_name = normalize_ascii(game_name_raw) if game_name_raw else ""
            launch_platform_raw = parsed["launch_platform"]
            launchplatform = str(launch_platform_raw).upper() if launch_platform_raw else ""
            if platform.system() != 'Windows':
                signal.alarm(0)
            if not status:
                raise PsnMalformedResponse('onlineStatus is empty')
            else:
                status = str(status).lower()
        except TimeoutException as e:
            if platform.system() != 'Windows':
                signal.alarm(0)
            print_recovery_error(e, context="monitor", detail=f"psn_user.get_presence() did not answer within {display_time(FUNCTION_TIMEOUT)}", tracker=recovery_hints, retry_note=f"retrying in {display_time(FUNCTION_TIMEOUT)}")
            print_cur_ts("Timestamp:\t\t\t")
            debug_print("Waiting", interval=display_time(FUNCTION_TIMEOUT), reason=f"check #{check_number} timed out")
            time.sleep(FUNCTION_TIMEOUT)
            continue

        except Exception as e:
            if platform.system() != 'Windows':
                signal.alarm(0)

            advice = classify_recovery_error(e, context="monitor", probe_auth=True)
            kind = recovery_poll_kind(advice)
            debug_print("Check", check=f"#{check_number}", recovery_code=advice.code, policy=kind, outcome="failed", error=f"{type(e).__name__}: {e}")

            # Local file descriptor exhaustion cannot be recovered inside this process
            if kind == "exhausted":
                print_recovery_advice(advice)
                if (ERROR_NOTIFICATION and not error_email_sent) or (webhook_event_enabled("error") and not error_webhook_sent):
                    send_notification_channels("error", recovery_email_subject(advice, psn_user_id), recovery_email_body(advice), email_enabled=ERROR_NOTIFICATION and not error_email_sent, webhook_enabled=webhook_event_enabled("error") and not error_webhook_sent)
                print_cur_ts("Timestamp:\t\t\t")
                sys.exit(2)

            error_streak += 1
            policy = RECOVERY_POLL_POLICY[kind]
            sleep_interval = FUNCTION_TIMEOUT if kind == "transient" else (get_sleep_interval() if kind == "unknown" else max(60, get_sleep_interval()))
            # A failure nothing here can retry away is worth reporting at once rather than after a streak
            alert_after = policy["alert_after"] if advice.retryable else 1

            # A failure that has not changed is left to the liveness cadence rather than repeated every check
            outage_outcome = outage.failed(advice, LIVENESS_REMINDER_SECONDS) if error_streak >= policy["report_after"] else ""
            printed_this_check = False
            if outage_outcome in ("full", "repeat"):
                print_recovery_advice(advice, recovery_hints, f"retrying in {display_time(sleep_interval)}")
                failure_announced = True
            elif outage_outcome == "degraded":
                print_outage_liveness(psn_user_id, advice, outage.since)
                failure_announced = True

            if error_streak >= policy["recreate_after"] and _recreate_session_rate_limited() and not rebuild_announced:
                print(f"* Rebuilt the PSNAWP session after {error_streak} failed {'check' if error_streak == 1 else 'checks'} in a row")
                rebuild_announced = True
                printed_this_check = True

            if error_streak >= alert_after and ((ERROR_NOTIFICATION and not error_email_sent) or (webhook_event_enabled("error") and not error_webhook_sent)):
                email_delivered, webhook_delivered = send_notification_channels("error", recovery_email_subject(advice, psn_user_id), recovery_email_body(advice, error_streak), email_enabled=ERROR_NOTIFICATION and not error_email_sent, webhook_enabled=webhook_event_enabled("error") and not error_webhook_sent)
                error_email_sent = error_email_sent or email_delivered
                error_webhook_sent = error_webhook_sent or webhook_delivered
                failure_announced = failure_announced or email_delivered or webhook_delivered
                printed_this_check = True

            # A rebuild or a retried alert can reach the screen on a check the outage reporter keeps quiet, and a
            # line with nothing under it reads as a run that stopped there
            if outage_outcome in ("full", "repeat") or printed_this_check:
                print_cur_ts("Timestamp:\t\t\t")
            debug_print("Waiting", interval=display_time(sleep_interval), reason=f"{kind} failure", streak=error_streak)
            time.sleep(sleep_interval)
            continue

        else:
            outage_lasted = outage.recovered()
            if error_streak:
                debug_print("Recovered", streak=error_streak, reported=failure_announced)
                # A streak nobody was told about needs no recovery line, since nothing reported it as broken
                if failure_announced and outage_lasted is not None:
                    print_outage_recovery(psn_user_id, outage_lasted)
                    alive_since = int(time.time())
            recovery_hints.reset()
            error_email_sent = False
            error_webhook_sent = False
            error_streak = 0
            failure_announced = False
            rebuild_announced = False

        finally:
            if platform.system() != 'Windows':
                signal.alarm(0)

        change = False
        act_inact_flag = False

        status_ts = int(time.time())
        game_ts = int(time.time())

        # Player status changed
        if status != status_old:

            try:
                save_last_status(psn_last_status_file, status_ts, status)
                debug_print("Saved status written", path=psn_last_status_file, status=status)
            except Exception as e:
                print_recovery_error(e, context="file.unwritable", detail=f"Cannot save the last status to '{psn_last_status_file}': {e}")

            print(f"PSN user {psn_user_id} changed status from {status_old} to {status}")
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

            m_subject = f"PSN user {psn_user_id} is now {status} (after {m_subject_after}{m_subject_was_since})"
            m_body = f"PSN user {psn_user_id} changed status from {status_old} to {status}\n\nUser was {status_old} for {calculate_timespan(int(status_ts), int(status_ts_old))}{m_body_was_since}{m_body_short_offline_msg}{m_body_user_in_game}{m_body_played_games}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
            webhook_status_enabled = webhook_event_enabled("status") and act_inact_flag
            if (ACTIVE_INACTIVE_NOTIFICATION and act_inact_flag) or webhook_status_enabled:
                send_notification_channels("status", m_subject, m_body, email_enabled=ACTIVE_INACTIVE_NOTIFICATION and act_inact_flag, webhook_enabled=webhook_status_enabled)

            status_ts_old = status_ts
            print_cur_ts("Timestamp:\t\t\t")

        # Player started/stopped/changed the game
        if game_name != game_name_old:

            launchplatform_str = ""
            if launchplatform:
                launchplatform_str = f" ({launchplatform})"

            # User changed the game
            if game_name_old and game_name:
                print(f"PSN user {psn_user_id} changed game from '{game_name_old}' to '{game_name}'{launchplatform_str} after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                print(f"User played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}")
                game_total_ts += (int(game_ts) - int(game_ts_old))
                games_number += 1
                m_body = f"PSN user {psn_user_id} changed game from '{game_name_old}' to '{game_name}'{launchplatform_str} after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                if launchplatform:
                    launchplatform_str = f"{launchplatform}, "
                m_subject = f"PSN user {psn_user_id} changed game to '{game_name}' ({launchplatform_str}after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True)})"

            # User started playing new game
            elif not game_name_old and game_name:
                print(f"PSN user {psn_user_id} started playing '{game_name}'{launchplatform_str}")
                games_number += 1
                m_subject = f"PSN user {psn_user_id} now plays '{game_name}'{launchplatform_str}"
                m_body = f"PSN user {psn_user_id} now plays '{game_name}'{launchplatform_str}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

            # User stopped playing the game
            elif game_name_old and not game_name:
                print(f"PSN user {psn_user_id} stopped playing '{game_name_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                print(f"User played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}")
                if not game_total_after_offline_counted:
                    game_total_ts += (int(game_ts) - int(game_ts_old))
                m_subject = f"PSN user {psn_user_id} stopped playing '{game_name_old}' (after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True)})"
                m_body = f"PSN user {psn_user_id} stopped playing '{game_name_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

            change = True

            if m_subject and m_body and (GAME_CHANGE_NOTIFICATION or webhook_event_enabled("game")):
                send_notification_channels("game", m_subject, m_body, email_enabled=GAME_CHANGE_NOTIFICATION)

            game_ts_old = game_ts
            print_cur_ts("Timestamp:\t\t\t")

        if change:
            alive_since = int(time.time())

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, now_local_naive(), status, game_name)
            except Exception as e:
                print_recovery_error(e, context="file.unwritable", detail=f"Cannot write to the CSV file '{csv_file_name}': {e}")
                print_cur_ts("Timestamp:\t\t\t")

        status_old = status
        game_name_old = game_name

        if LIVENESS_REMINDER_SECONDS and int(time.time()) - alive_since >= LIVENESS_REMINDER_SECONDS:
            print_liveness_banner(f"Monitoring healthy for {psn_user_id}. The user is {status or 'unknown'} with no activity change since the last check")
            alive_since = int(time.time())

        sleep_interval = get_sleep_interval()
        debug_print("Completed check", check=f"#{check_number}", user=psn_user_id, outcome="OK", status=status or "unknown", game=game_name or None, next=display_time(sleep_interval))
        time.sleep(sleep_interval)


# Preflight diagnostics. Every section, marker and summary sentence is shared with the sibling monitors,
# so a user who runs two of them reads one report format rather than two
DOCTOR_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#doctor-preflight"

DOCTOR_SECTIONS = ("Environment", "Configuration", "Authentication", "Connectivity", "Target", "Notifications")

# The theme entry each doctor result marker is drawn in, so a failure reads as one at a glance
DOCTOR_MARK_STYLES = {"PASS": "boolean_true", "WARN": "warning", "FAIL": "error", "SKIP": "info"}

# Delivery results are printed as they happen rather than inside a section, but they still count in the summary
DOCTOR_DELIVERY_SECTION = "Optional delivery tests"

DOCTOR_STATUSES = ("PASS", "WARN", "FAIL", "SKIP")

# Imported without a guard, so the tool cannot start when one of these is missing
DOCTOR_REQUIRED_DEPENDENCIES = (("psnawp_api", "PSNAWP"), ("requests", "requests"), ("dateutil", "python-dateutil"), ("pytz", "pytz"))

# Guarded imports the tool degrades around, with what stops working and what to do instead. The last field
# names the only operating system a row applies to, so a machine it cannot affect is not warned about it
DOCTOR_OPTIONAL_DEPENDENCIES = (
    ("tzlocal", "tzlocal", "Used only to auto-detect the local time zone", "Automatic time zone detection is unavailable", "Or set LOCAL_TIMEZONE to a pytz timezone name in the config file", ""),
    ("dotenv", "python-dotenv", "Used only to read secrets from a dotenv file", "Secrets cannot be read from a dotenv file", "Or export them as environment variables", ""),
    ("wcwidth", "wcwidth", "Used only to measure display width for screen truncation", "Screen truncation is disabled", "", ""),
    ("colorama", "colorama", "Used only for coloured output in the older Windows Command Prompt", "Coloured output may not render in the older Windows Command Prompt", "Or use Windows Terminal, which needs nothing extra", "Windows"),
)

# An active check interval below this invites the PSN rate limiter, which stops the tool seeing anything
DOCTOR_MIN_SAFE_ACTIVE_INTERVAL = 30

# Doctor label for each timezone outcome, kept identical to the sibling monitors
TIMEZONE_CHECK_LABELS = {"config": "Local timezone is valid", "auto": "Local timezone can be detected", "auto_unavailable": "Automatic timezone detection is unavailable", "auto_failed": "Automatic timezone detection failed", "invalid": "Local timezone is invalid"}

# Seconds the passive doctor sign-in waits, shorter than a real delivery so a dead host does not stall the report
DOCTOR_SMTP_TIMEOUT = 5

# Shared doctor labels for the two delivery channels, kept identical to the sibling monitors
SMTP_READY_CHECK_LABEL = "SMTP connection and login succeeded"
WEBHOOK_READY_CHECK_LABEL = "Webhook URL, headers and alert choices look valid"

# The label every sibling monitor uses when email alerts are on but the settings they would use cannot deliver
EMAIL_UNUSABLE_CHECK_LABEL = "Email alerts are enabled but unusable"


# Stores one doctor result before the report is rendered
@dataclass(frozen=True)
class DoctorCheck:
    section: str
    status: str
    label: str
    detail: str = ""
    advice: "RecoveryAdvice | None" = None


# Collects doctor results plus the authenticated session the target checks reuse
@dataclass
class DoctorReport:
    checks: list = field(default_factory=list)
    psnawp: object = None
    email_ready: bool = False
    webhook_ready: bool = False


# Creates one doctor result, refusing a marker outside the shared four and redacting every field it shows
def make_doctor_check(section, status, label, detail="", advice=None):
    if status not in DOCTOR_STATUSES:
        raise ValueError(f"Unsupported doctor status: {status}")
    # A row the user has to act on is useless without an action, so the row is rejected rather than printed bare
    if status in ("WARN", "FAIL") and (advice is None or not advice.fix):
        raise ValueError(f"Doctor {status} rows require a fix")
    safe_label = sanitize_error_text(label)
    safe_detail = sanitize_error_text(detail)
    # Several advice objects carry the same text as their summary, and printing it twice reads as two problems
    return DoctorCheck(section, status, safe_label, "" if safe_detail == safe_label else safe_detail, advice)


# Reports whether one module could be imported, without importing it
def dependency_is_installed(module_name, spec_finder=None):
    finder = importlib.util.find_spec if spec_finder is None else spec_finder
    try:
        return finder(module_name) is not None
    except (ImportError, ValueError):
        return False


# Reports whether a path could be written, without creating anything, so the doctor leaves no files behind
def path_is_writable(path):
    target = Path(os.path.expanduser(str(path)))
    if target.exists():
        return os.access(target, os.W_OK)
    parent = target.parent if str(target.parent) else Path(".")
    return parent.is_dir() and os.access(parent, os.W_OK)


# Checks the interpreter, the dependencies the tool needs and the ones it degrades around
def doctor_check_environment(version_info=None, spec_finder=None):
    checks = []
    selected = tuple(sys.version_info if version_info is None else version_info)
    version_text = ".".join(str(part) for part in selected[:3])
    minimum_detail = f"Minimum supported version: {MINIMUM_PYTHON_VERSION_TEXT}"
    if selected[:2] >= MINIMUM_PYTHON_VERSION:
        checks.append(make_doctor_check("Environment", "PASS", f"Python {version_text} is supported", minimum_detail))
    else:
        advice = make_recovery_advice("dependency.missing", f"Python {version_text} is unsupported", recovery_fix_with_guide(f"Install Python {MINIMUM_PYTHON_VERSION_TEXT} or newer then retry", INSTALLATION_GUIDE_URL), False)
        checks.append(make_doctor_check("Environment", "FAIL", advice.summary, minimum_detail, advice))

    for module_name, package_name in DOCTOR_REQUIRED_DEPENDENCIES:
        if dependency_is_installed(module_name, spec_finder):
            checks.append(make_doctor_check("Environment", "PASS", f"Required dependency {package_name} is installed"))
        else:
            advice = make_recovery_advice("dependency.missing", f"Required dependency {package_name} is missing", recovery_fix_with_guide(f"Install it with: {pip_install_command(package_name)}", INSTALLATION_GUIDE_URL), False)
            checks.append(make_doctor_check("Environment", "FAIL", advice.summary, advice=advice))

    for module_name, package_name, purpose, effect, alternative, only_on in DOCTOR_OPTIONAL_DEPENDENCIES:
        if only_on and platform.system() != only_on:
            continue
        if dependency_is_installed(module_name, spec_finder):
            checks.append(make_doctor_check("Environment", "PASS", f"Optional dependency {package_name} is installed", purpose))
        else:
            advice = missing_dependency_advice(package_name, effect, alternative)
            checks.append(make_doctor_check("Environment", "WARN", f"Optional dependency {package_name} is not installed", f"{effect}. Every other feature is unaffected", advice))

    return checks


# Groups the secrets that are actually set by the source each value was resolved from
def doctor_secret_sources():
    grouped = {}
    for key in SECRET_KEYS:
        if secret_is_set(globals().get(key)):
            grouped.setdefault(SECRET_SOURCES.get(key, "configuration file"), []).append(key)
    return grouped


# Reports which secrets are in effect and where each one came from, by name and never by value
def doctor_secret_checks():
    grouped = doctor_secret_sources()
    if not grouped:
        return [make_doctor_check("Configuration", "PASS", "No secrets loaded", "Nothing was read from a dotenv file, the environment, the configuration file or the command line")]
    return [make_doctor_check("Configuration", "PASS", f"Secrets loaded from the {source}", ", ".join(names)) for source, names in sorted(grouped.items())]


# Returns all type and range errors in settings that control runtime timing or counts
def runtime_configuration_errors():
    errors = []
    positive_numbers = (("PSN_CHECK_INTERVAL", PSN_CHECK_INTERVAL), ("PSN_ACTIVE_CHECK_INTERVAL", PSN_ACTIVE_CHECK_INTERVAL), ("CHECK_INTERNET_TIMEOUT", CHECK_INTERNET_TIMEOUT))
    nonnegative_numbers = (("OFFLINE_INTERRUPT", OFFLINE_INTERRUPT), ("LIVENESS_CHECK_INTERVAL", LIVENESS_CHECK_INTERVAL))
    for name, value in positive_numbers:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            errors.append(f"{name} must be a number greater than zero, not {value!r}")
    for name, value in nonnegative_numbers:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            errors.append(f"{name} must be a number zero or greater, not {value!r}")
    if not isinstance(SMTP_PORT, int) or isinstance(SMTP_PORT, bool) or not 1 <= SMTP_PORT <= 65535:
        errors.append(f"SMTP_PORT must be an integer from 1 through 65535, not {SMTP_PORT!r}")
    return errors


# Reports the effective settings and the files the tool would write, without writing any of them
def doctor_check_configuration(config_path=None, env_path=None, config_advice=None, timezone_advice=None, psn_user_id=None):
    checks = []
    if config_advice is not None:
        checks.append(make_doctor_check("Configuration", "FAIL", config_advice.summary, advice=config_advice))
    elif config_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Configuration file loaded", f"Path: {config_path}"))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No configuration file selected", "Using built-in defaults and command-line overrides"))

    if env_path and os.path.isfile(str(env_path)):
        checks.append(make_doctor_check("Configuration", "PASS", "Dotenv file loaded", f"Path: {env_path}"))
    elif env_path:
        advice = make_recovery_advice("config.missing", "The requested dotenv file was not found", recovery_fix_with_guide("Create the file or select an existing path with --env-file", SECRETS_GUIDE_URL), False, f"Path: {env_path}")
        checks.append(make_doctor_check("Configuration", "WARN", advice.summary, advice.detail, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No dotenv file selected", "Using environment variables and other configured sources"))

    checks.extend(doctor_secret_checks())

    timezone_label = TIMEZONE_CHECK_LABELS[LOCAL_TIMEZONE_STATE]
    if timezone_advice is not None:
        checks.append(make_doctor_check("Configuration", "FAIL", timezone_label, timezone_advice.detail, timezone_advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", timezone_label, f"Time zone: {LOCAL_TIMEZONE}"))

    intervals = f"{display_time(PSN_CHECK_INTERVAL)} while offline, {display_time(PSN_ACTIVE_CHECK_INTERVAL)} while online"
    if PSN_ACTIVE_CHECK_INTERVAL < DOCTOR_MIN_SAFE_ACTIVE_INTERVAL:
        advice = make_recovery_advice("psn.rate_limited", "Check intervals are short enough to be rate limited", recovery_fix_with_guide(f"Raise PSN_ACTIVE_CHECK_INTERVAL to at least {DOCTOR_MIN_SAFE_ACTIVE_INTERVAL} seconds", INTERVALS_GUIDE_URL), True)
        checks.append(make_doctor_check("Configuration", "WARN", "Check intervals are short", intervals, advice))

    if VERIFY_SSL:
        checks.append(make_doctor_check("Configuration", "PASS", "TLS certificate verification is on", "Every outbound request checks the server certificate"))
    else:
        advice = make_recovery_advice("config.insecure", "TLS certificate verification is off", recovery_fix_with_guide("Set VERIFY_SSL back to True unless this network intercepts TLS with its own certificate authority", TLS_GUIDE_URL), False)
        checks.append(make_doctor_check("Configuration", "WARN", "TLS certificate verification is off", "VERIFY_SSL is False, so an intercepted connection cannot be told apart from the real service", advice))

    numeric_errors = runtime_configuration_errors()
    if numeric_errors:
        numeric_detail = "Invalid numeric settings: " + "; ".join(numeric_errors)
        advice = make_recovery_advice("config.invalid", "One or more numeric settings are invalid", recovery_fix_with_guide("Correct the reported settings in the configuration file", CONFIG_GUIDE_URL), False, numeric_detail)
        checks.append(make_doctor_check("Configuration", "FAIL", "One or more numeric settings are invalid", numeric_detail, advice))

    try:
        ascii_log_separators_enabled()
    except ValueError as exc:
        advice = classify_recovery_error(context="config.invalid", detail=str(exc))
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))

    if DISABLE_LOGGING:
        checks.append(make_doctor_check("Configuration", "PASS", "Output logging is disabled"))
    else:
        # A name with an extension is used as it is, so only a bare base name has to wait for the target
        log_path = resolve_log_path(psn_user_id) if (psn_user_id or Path(os.path.expanduser(PSN_LOGFILE)).suffix) else ""
        if not log_path:
            checks.append(make_doctor_check("Configuration", "PASS", "Log destination will be finalized after a target is selected", f"Base path: {Path(os.path.expanduser(PSN_LOGFILE))}"))
        elif path_is_writable(log_path):
            checks.append(make_doctor_check("Configuration", "PASS", "Log destination appears writable", f"Path: {log_path}"))
        else:
            advice = classify_recovery_error(context="file.unwritable", detail=f"Log destination is not writable: {log_path}")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))

    if CSV_FILE:
        csv_path = os.path.expanduser(CSV_FILE)
        if path_is_writable(csv_path):
            checks.append(make_doctor_check("Configuration", "PASS", "CSV destination appears writable", f"Path: {csv_path}"))
        else:
            advice = classify_recovery_error(context="file.unwritable", detail=f"CSV destination is not writable: {csv_path}")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "CSV logging is disabled"))

    # A configured path is fixed, so it stays checkable without a target. The default name carries the target
    status_path = os.path.expanduser(PSN_STATUS_FILE) if PSN_STATUS_FILE else (resolve_status_file(psn_user_id) if psn_user_id else "")
    if not status_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Status file will be finalized after a target is selected", "Base name: psn_<psn_user_id>_last_status.json in the working directory"))
    elif path_is_writable(status_path):
        checks.append(make_doctor_check("Configuration", "PASS", "Status destination appears writable", f"Path: {status_path}"))
    else:
        advice = classify_recovery_error(context="file.unwritable", detail=f"Status destination is not writable: {status_path}")
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))
    return checks


# Confirms the endpoint the tool checks at startup answers, using the configured URL, timeout and TLS setting
def doctor_check_connectivity():
    global LAST_CONNECTIVITY_ERROR
    LAST_CONNECTIVITY_ERROR = None
    if check_internet(quiet=True):
        return [make_doctor_check("Connectivity", "PASS", "The connectivity endpoint is reachable", f"Endpoint: {CHECK_INTERNET_URL}")]
    advice = classify_recovery_error(LAST_CONNECTIVITY_ERROR, context="connectivity", detail=f"Could not reach {CHECK_INTERNET_URL}")
    return [make_doctor_check("Connectivity", "FAIL", "The connectivity endpoint could not be reached", f"Endpoint: {CHECK_INTERNET_URL}", advice)]


# Authenticates once and keeps the session, so the target checks do not sign in a second time
def doctor_check_authentication(report):
    if not secret_is_set(PSN_NPSSO):
        advice = classify_recovery_error(context="secret.missing", detail="PSN_NPSSO is not set")
        return [make_doctor_check("Authentication", "FAIL", advice.summary, advice=advice)]
    try:
        psnawp = psn_client()
        signed_in = psnawp.me().online_id
    except Exception as exc:
        advice = classify_recovery_error(exc, context="startup", probe_auth=True)
        return [make_doctor_check("Authentication", "FAIL", advice.summary, advice=advice)]
    report.psnawp = psnawp
    return [make_doctor_check("Authentication", "PASS", "PlayStation Network accepted the NPSSO code", f"Signed in as {signed_in}")]


# Checks the monitored profile can be found and that it shares the activity the tool reads
def doctor_check_target(report, psn_user_id=None):
    if not psn_user_id:
        advice = classify_recovery_error(context="target.missing", detail="No PlayStation ID was provided")
        return [make_doctor_check("Target", "WARN", advice.summary, "Nothing will be monitored until one is given", advice)]
    if report.psnawp is None:
        return [make_doctor_check("Target", "SKIP", "The monitored profile was not checked", "Sign-in did not succeed, so no lookup was attempted")]
    try:
        psn_user = report.psnawp.user(online_id=psn_user_id)
        account_id = psn_user.account_id
    except Exception as exc:
        advice = classify_recovery_error(exc, context="startup")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice=advice)]
    checks = [make_doctor_check("Target", "PASS", f"PlayStation ID {psn_user_id} was found", f"Account ID: {account_id}")]
    try:
        parsed = parse_presence(psn_user.get_presence())
    except Exception as exc:
        advice = classify_recovery_error(exc, context="startup")
        checks.append(make_doctor_check("Target", "FAIL", advice.summary, advice=advice))
        return checks
    checks.append(make_doctor_check("Target", "PASS", "Presence is visible to this account", f"Current status: {str(parsed['status'] or 'unknown').lower()}"))
    return checks


# Returns the doctor row for email alerts whose settings cannot deliver, worded the same way by every sibling monitor
def doctor_email_unusable_check(detail, fix):
    advice = make_recovery_advice("smtp.invalid", EMAIL_UNUSABLE_CHECK_LABEL, recovery_fix_with_guide(fix, SMTP_GUIDE_URL), False, detail)
    return make_doctor_check("Notifications", "WARN", EMAIL_UNUSABLE_CHECK_LABEL, detail, advice)


# Reports whether email alerts can fire at all, then whether the settings they would use are usable
def doctor_check_email_notifications(report):
    problem = email_settings_problem()
    # An error alert is on by default, so on its own it cannot make a fresh install look configured
    deliberate = ACTIVE_INACTIVE_NOTIFICATION or GAME_CHANGE_NOTIFICATION
    if not deliberate and problem is not None:
        return [make_doctor_check("Notifications", "PASS", "Email notifications are disabled", "No SMTP connection was attempted and no email was sent")]
    if problem is not None:
        return [doctor_email_unusable_check(*problem)]
    if not deliberate and not ERROR_NOTIFICATION:
        advice = make_recovery_advice("smtp.invalid", "Email is configured but no alert types are selected", recovery_fix_with_guide("Turn on at least one email alert in the configuration file", SMTP_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be emailed", advice)]
    try:
        smtp_sign_in(SMTP_PASSWORD, timeout=DOCTOR_SMTP_TIMEOUT)
    except RecoveryError as exc:
        return [make_doctor_check("Notifications", "FAIL", exc.advice.summary, exc.advice.detail, exc.advice)]
    alerts = ", ".join(name for name, enabled in (("status changes", ACTIVE_INACTIVE_NOTIFICATION), ("game changes", GAME_CHANGE_NOTIFICATION), ("errors", ERROR_NOTIFICATION)) if enabled)
    report.email_ready = True
    return [make_doctor_check("Notifications", "PASS", SMTP_READY_CHECK_LABEL, f"Alerts: {alerts}. No email was sent during this passive check")]


# Reports whether webhook alerts can fire at all, then whether the destination and customization are usable
def doctor_check_webhook_notifications(report):
    selected = webhook_notification_categories()
    # An error alert is on by default, so on its own it cannot make a fresh install look configured
    deliberate = WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION or WEBHOOK_GAME_CHANGE_NOTIFICATION
    if not WEBHOOK_ENABLED:
        if not deliberate:
            return [make_doctor_check("Notifications", "PASS", "Webhook alerts are disabled")]
        advice = make_recovery_advice("webhook.invalid", "Webhook alert types are selected but webhooks are switched off", recovery_fix_with_guide("Set WEBHOOK_ENABLED to True, or turn the alert types off", WEBHOOK_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be delivered", advice)]
    provider = normalized_webhook_provider()
    if not provider:
        advice = classify_recovery_error(context="webhook", detail="WEBHOOK_PROVIDER must be discord or ntfy")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not validate_webhook_url():
        advice = classify_recovery_error(context="webhook", detail="WEBHOOK_URL must contain a complete HTTPS link")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    for validation_error in (validate_webhook_customization(provider), validate_webhook_headers(provider)):
        if validation_error is not None:
            advice = classify_recovery_error(context="webhook", detail=validation_error)
            return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not selected:
        advice = make_recovery_advice("webhook.invalid", "Webhook alerts are on but no alert types are selected", recovery_fix_with_guide("Turn on at least one webhook alert in the configuration file, or set WEBHOOK_ENABLED to False", WEBHOOK_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be delivered", advice)]
    report.webhook_ready = True
    return [make_doctor_check("Notifications", "PASS", f"{WEBHOOK_READY_CHECK_LABEL} for {webhook_provider_display_name()}", f"Alerts: {', '.join(selected)}. The private link was not displayed. No webhook was sent during this passive check")]


# Reports both delivery channels, each one switched on and diagnosed independently of the other
def doctor_check_notifications(report):
    return doctor_check_email_notifications(report) + doctor_check_webhook_notifications(report)


# Returns the raw terminal stream, so the transient progress line is not captured by the log writer
def doctor_terminal_stream():
    stream = sys.stdout
    while isinstance(stream, (Logger, TerminalStream)):
        stream = stream.terminal
    return stream


# Width of the progress line currently on screen, which is what erasing it needs to know
DOCTOR_PROGRESS_WIDTH = 0


# Shows one transient step only on an interactive terminal, erased by overwriting its own width
# The line stays uncoloured on purpose: it is erased by writing exactly len(line) spaces, and an escape
# sequence would make that width wrong and leave a styled remnant behind
def doctor_progress(label):
    global DOCTOR_PROGRESS_WIDTH
    terminal = doctor_terminal_stream()
    if terminal.isatty():
        doctor_progress_clear()
        line = f"* Checking {plain_text(label)} ..."
        DOCTOR_PROGRESS_WIDTH = len(line)
        terminal.write("\r" + line)
        terminal.flush()


# Clears the transient progress line, so nothing of it survives into the report
def doctor_progress_clear():
    global DOCTOR_PROGRESS_WIDTH
    terminal = doctor_terminal_stream()
    if terminal.isatty() and DOCTOR_PROGRESS_WIDTH:
        terminal.write("\r" + (" " * DOCTOR_PROGRESS_WIDTH) + "\r")
        terminal.flush()
        DOCTOR_PROGRESS_WIDTH = 0


# Runs every section in order, reporting each step while it is still running
def build_doctor_report(psn_user_id=None, config_path=None, env_path=None, config_advice=None, timezone_advice=None, progress=None):
    report = DoctorReport()
    steps = (
        ("environment", lambda: doctor_check_environment()),
        ("configuration", lambda: doctor_check_configuration(config_path, env_path, config_advice, timezone_advice, psn_user_id)),
        ("connectivity", lambda: doctor_check_connectivity()),
        ("authentication", lambda: doctor_check_authentication(report)),
        ("the monitored profile", lambda: doctor_check_target(report, psn_user_id)),
        ("notifications", lambda: doctor_check_notifications(report)),
    )
    for label, run_step in steps:
        if progress is not None:
            progress(label)
        report.checks.extend(run_step())
    return report



# Renders one doctor result marker in the colour its status calls for
def render_doctor_marker(status):
    return colorize(DOCTOR_MARK_STYLES.get(status, "info"), f"[{status}]")


# Prints the notice that has to be true before anything runs
def render_doctor_notice():
    print("Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval.\n")


# Renders the heading and every non-empty section, with a fix line on the rows that are not a pass
def render_doctor_sections(report):
    # The install method is context rather than a check: it cannot fail, so it is stated once here
    # instead of occupying a result row that no marker describes. The raw key is what support reports use
    lines = [colorize("header", "Doctor"), f"Detected install method: {colorize('username', detect_install_method())}"]
    for section in DOCTOR_SECTIONS:
        section_checks = [check for check in report.checks if check.section == section]
        if not section_checks:
            continue
        lines.extend(("", colorize("section", section)))
        for check in section_checks:
            lines.append(f"{render_doctor_marker(check.status)} {check.label}")
            if check.detail:
                lines.append(f"  {check.detail}")
            if check.advice is not None and check.status != "PASS":
                # The fix carries its own guide line, so each line is indented and styled on its own rather
                # than leaving one colour sequence open across the newline
                lines.extend(f"  {colorize('info', advice_line)}" for advice_line in f"To fix: {check.advice.fix}".splitlines())
    return sanitize_error_text("\n".join(lines))


# Renders the one sentence that says whether the setup is usable, and where to read more
def render_doctor_summary(checks):
    failures = sum(check.status == "FAIL" for check in checks)
    warnings = sum(check.status == "WARN" for check in checks)
    if failures:
        sentence = colorize("error", f"  {failures} check(s) failed, {warnings} warning(s). Fix the failures above before relying on the tool.")
    elif warnings:
        sentence = colorize("warning", f"  All critical checks passed with {warnings} warning(s). Review the warnings above.")
    else:
        sentence = colorize("boolean_true", "  All checks passed. You are good to go!")
    return "\n".join(("", colorize("header", "Summary"), sentence, "", colorize("info", f"Guide: {DOCTOR_GUIDE_URL}")))


# Asks for delivery consent, treating a closed or interrupted input as no
def ask_yes_no(question, default=False):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = read_interactively(input, colorize("info", f"{question} {hint}: ")).strip().casefold()
        except EOFError:
            print("\nDelivery test skipped.")
            return False
        except KeyboardInterrupt:
            # Ctrl+C ends the run here the way it does anywhere else, rather than only declining this one test
            signal_handler(signal.SIGINT, None)
            raise
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Prints one result the way the report renders it, so a row printed after the report matches the rows above it
def print_doctor_check(check):
    print(f"{render_doctor_marker(check.status)} {check.label}")
    if check.detail:
        print(f"  {check.detail}")


# Offers a real delivery test for each channel that already passed, approved separately from the other
def offer_doctor_delivery_tests(report):
    if not (report.email_ready or report.webhook_ready) or not sys.stdin.isatty() or not sys.stdout.isatty():
        return []
    print("\n" + colorize("section", "Optional delivery tests") + "\n")
    print("Doctor will not write files. Each approved test sends one real message.\n")
    offered = []
    if report.email_ready:
        if ask_yes_no("Send one test email now? This will deliver a real message"):
            delivered = send_email("psn_monitor: doctor test email", "This test email was sent after approval in --doctor. Your SMTP delivery settings work.", "", SMTP_SSL, smtp_timeout=5) == 0
            if delivered:
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS", "Doctor test email delivered", "One real test email was sent after confirmation")
            else:
                advice = make_recovery_advice("smtp.connection", "Doctor test email delivery failed", recovery_fix_with_guide("Review the SMTP error above and correct the email settings", SMTP_GUIDE_URL), True)
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "FAIL", advice.summary, "The approved test email could not be delivered", advice)
        else:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", "Test email was not sent", "You declined the real delivery test. Run doctor again and approve the email test when ready")
        offered.append(check)
        # Recorded on the report so the summary sentence and the exit code cannot disagree about the same run
        report.checks.append(check)
        print_doctor_check(check)
    if report.webhook_ready:
        provider = webhook_provider_display_name()
        if ask_yes_no(f"Send one test webhook through {provider} now? This will publish a real notification"):
            delivered = send_webhook("psn_monitor: doctor test webhook", "This test notification was sent after approval in --doctor. Your webhook delivery settings work.", "status", force=True) == 0
            if delivered:
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS", f"Doctor test webhook through {provider} delivered", "One real test webhook was sent after confirmation")
            else:
                advice = make_recovery_advice("webhook.connection", f"Doctor test webhook through {provider} delivery failed", recovery_fix_with_guide("Review the webhook error above and correct the destination settings", WEBHOOK_GUIDE_URL), True)
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "FAIL", advice.summary, "The approved test webhook could not be delivered", advice)
        else:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", f"Test webhook through {provider} was not sent", "You declined the real delivery test. Run doctor again and approve the webhook test when ready")
        offered.append(check)
        report.checks.append(check)
        print_doctor_check(check)
    return offered


# Runs the preflight report plus any approved delivery test and returns the process exit code
def run_doctor(psn_user_id=None, config_path=None, env_path=None, config_advice=None, timezone_advice=None):
    render_doctor_notice()
    progress = doctor_progress if doctor_terminal_stream().isatty() else None
    try:
        report = build_doctor_report(psn_user_id, config_path, env_path, config_advice, timezone_advice, progress)
    finally:
        doctor_progress_clear()
    print(render_doctor_sections(report))
    offer_doctor_delivery_tests(report)
    print(render_doctor_summary(report.checks))
    return 1 if any(check.status == "FAIL" for check in report.checks) else 0


# One startup summary setting, routed to the concise view, the full view or both. The log keeps the full view
StartupSummaryRow = namedtuple("StartupSummaryRow", ["label", "value", "concise", "full"])
StartupSummaryRow.__new__.__defaults__ = (False, True)


# Reports whether the reader asked for the complete startup summary rather than the concise one
def full_startup_summary_enabled():
    return bool(VERBOSE_MODE or DEBUG_MODE)


# Returns the email alert rollup, naming what is switched on rather than printing three separate booleans
def startup_notification_state():
    enabled = [name for name, on in (("status changes", ACTIVE_INACTIVE_NOTIFICATION), ("game changes", GAME_CHANGE_NOTIFICATION), ("errors", ERROR_NOTIFICATION)) if on]
    return "On (" + ", ".join(enabled) + ")" if enabled else "Off"


# Returns the webhook alert rollup, which reads Off whenever the channel itself is switched off
def startup_webhook_notification_state():
    enabled = webhook_notification_categories() if WEBHOOK_ENABLED else []
    return f"On ({', '.join(enabled)}) through {webhook_provider_display_name()}" if enabled else "Off"


# Builds every summary row, deciding per row whether it belongs in the concise view, the full view and the log
def build_startup_summary(psn_user_id=None, config_path=None, env_path=None, log_path=None):
    supplied = doctor_secret_sources()
    from_dotenv = sorted(supplied.get("dotenv file", ()))
    from_environment = sorted(supplied.get("environment", ()))
    # Bucketed by exact source rather than by "everything else", so a command-line secret is not filed as config
    from_config = sorted(supplied.get("configuration file", ()))
    from_command_line = sorted(supplied.get("command line", ()))
    output_state = str(log_path) if log_path else "Terminal only (logging disabled)"
    return [
        StartupSummaryRow("Target", str(psn_user_id) if psn_user_id else "None", concise=True),
        StartupSummaryRow("Polling intervals", f"[offline: {display_time(PSN_CHECK_INTERVAL)}] [online: {display_time(PSN_ACTIVE_CHECK_INTERVAL)}]", concise=True),
        StartupSummaryRow("Notifications (email)", startup_notification_state(), concise=True),
        StartupSummaryRow("Notifications (webhook)", startup_webhook_notification_state(), concise=True),
        StartupSummaryRow("Output", output_state, concise=True, full=False),
        StartupSummaryRow("Output logging", str(log_path) if log_path else "Disabled"),
        StartupSummaryRow("Config", str(config_path) if config_path else "None", concise=True),
        StartupSummaryRow("Dotenv", str(env_path) if env_path else "None", concise=True),
        # Each optional feature earns a concise row only once it is actually switched on
        StartupSummaryRow("Liveness output", display_time(LIVENESS_CHECK_INTERVAL) if LIVENESS_CHECK_INTERVAL else "Disabled", concise=bool(LIVENESS_CHECK_INTERVAL)),
        StartupSummaryRow("CSV output", CSV_FILE or "Disabled", concise=bool(CSV_FILE)),
        StartupSummaryRow("Status file", resolve_status_file(psn_user_id) if psn_user_id else "None"),
        StartupSummaryRow("Terminal truncation", f"{TRUNCATE_CHARS} chars" if TRUNCATE_CHARS else "Disabled", concise=bool(TRUNCATE_CHARS)),
        StartupSummaryRow("Local timezone", LOCAL_TIMEZONE),
        StartupSummaryRow("Install method", install_method_display_name()),
        StartupSummaryRow("Secrets from dotenv", ", ".join(from_dotenv) if from_dotenv else "None"),
        StartupSummaryRow("Secrets from environment", ", ".join(from_environment) if from_environment else "None"),
        StartupSummaryRow("Secrets from config file", ", ".join(from_config) if from_config else "None"),
        StartupSummaryRow("Secrets from command line", ", ".join(from_command_line) if from_command_line else "None"),
        StartupSummaryRow("TLS verification", "On" if VERIFY_SSL else "Off, server certificates are not checked", concise=not VERIFY_SSL),
        StartupSummaryRow("ASCII log separators", f"{ascii_log_separators_enabled()} (mode: {ASCII_LOG_SEPARATORS})"),
        # The resolved state, not the setting: colour also switches itself off when the output is not a terminal
        StartupSummaryRow("Coloured output", f"{COLOR_ENABLED} (setting: {COLORED_OUTPUT})"),
        StartupSummaryRow("Verbose mode", str(VERBOSE_MODE), concise=bool(VERBOSE_MODE)),
        StartupSummaryRow("Debug mode", str(DEBUG_MODE), concise=bool(DEBUG_MODE)),
        # Points at the two modes for a reader who does not know they exist, so the full view drops it
        StartupSummaryRow("More details", "use --verbose or --debug", concise=True, full=False),
    ]


# Formats one summary row with an aligned value column, wrapping only the rollup that grows long
def format_startup_summary_row(row):
    prefix = f"* {(row.label + ':'):<30}"
    if row.label in ("Notifications (email)", "Notifications (webhook)"):
        return textwrap.fill(str(row.value), width=100, initial_indent=prefix, subsequent_indent=" " * len(prefix), break_long_words=False, break_on_hyphens=False) + "\n"
    return f"{prefix}{row.value}\n"


# Prints the summary, showing the concise rows unless the full view was asked for. The log file always keeps
# the complete set, so a bug report made from a log carries every effective setting whatever the terminal showed
def emit_startup_summary(rows, show_full=False, stream=None):
    destination = sys.stdout if stream is None else stream
    # A stream that does not split its output has no log file to hold the full view, so those writes go nowhere
    write_log = getattr(destination, "log_only", lambda line: None)
    write_terminal = getattr(destination, "terminal_only", None)
    if write_terminal is None:
        write_terminal = destination.write
    for row in rows:
        line = format_startup_summary_row(row)
        if row.full:
            write_log(line)
        if row.full if show_full else row.concise:
            write_terminal(line)
    write_log("\n")
    write_terminal("\n")
    destination.flush()


# Reads only the persisted target from a config file, so a printed command can omit a positional the config already supplies
def config_file_target(config_path):
    if not config_path or str(config_path).casefold() == "none":
        return ""
    namespace = {}
    if not load_config_file(config_path, namespace=namespace, report_errors=False):
        return ""
    return str(namespace.get("PSN_USER_ID") or "")


# Returns the targets for the printed doctor and monitoring commands, dropping one the effective config already supplies
def command_targets(explicit_target=None, saved_target=None, placeholder="<psn_user_id>"):
    saved = str(saved_target or "")
    known = str(explicit_target or "") or saved
    if not known:
        # Monitoring cannot run without a target, so it keeps the placeholder while the doctor reports the gap itself
        return None, placeholder
    printed = None if known == saved else known
    return printed, printed


# Prints one labelled command on its own indented line, the shared shape across these tools
def print_labelled_command(label, command, suffix=""):
    print(label)
    print(f"    {colorize('section', command)}{colorize('info', suffix) if suffix else ''}\n")


# Prints the command that starts monitoring with the files this run checked, so a report read on its own
# ends with the next action rather than leaving the reader to assemble the command
def print_doctor_next_steps(psn_user_id=None, saved_target=None, doctor_exit=0):
    print("\n" + colorize("header", "Next steps") + "\n")
    label = "After Doctor passes, start monitoring:" if doctor_exit else "Start monitoring:"
    monitor_target = command_targets(psn_user_id, saved_target)[1]
    print_labelled_command(label, render_command([*([monitor_target] if monitor_target else [])]))
    # No trailing blank line: the command printer already left one and the report must not end on two
    print(f"Guide: {QUICK_START_GUIDE_URL}")




# A PlayStation online ID is 3 to 16 characters and never contains an at sign or a space
PSN_ONLINE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,15}$")


# Returns the online ID from whatever was pasted, naming the two mistakes that shape catches
def normalize_psn_target(value):
    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        raise ValueError(f"Enter the {PSN_TARGET_FORMS}")
    if "://" in text or text.startswith("www."):
        text = text.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
    if "@" in text:
        raise ValueError(f"That looks like an e-mail address. Use the {PSN_TARGET_FORMS}")
    if not PSN_ONLINE_ID_RE.match(text):
        raise ValueError("A PlayStation online ID is 3 to 16 characters, using letters, digits, hyphens and underscores")
    return text


# Parses the duration formats people actually type, returning whole seconds or None when nothing valid was given
def parse_duration_input(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    if not isinstance(value, str):
        return None
    text = value.strip().casefold().replace(",", ".")
    if not text:
        return None
    units = {"s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
             "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
             "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
             "d": 86400, "day": 86400, "days": 86400}
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*([a-z]*)", text)
    # Anything the pattern did not consume is rejected, so "5x" or "abc" cannot read as a bare number
    if not matches or re.sub(r"(\d+(?:\.\d+)?)\s*([a-z]*)", "", text).strip():
        return None
    total = 0.0
    for amount, unit in matches:
        if unit and unit not in units:
            return None
        total += float(amount) * units.get(unit, 1)
    seconds = int(round(total))
    return seconds if seconds > 0 else None


# Returns a value fit to show as a prompt default, hiding the shipped placeholders
def _wizard_default(value):
    text = str(value or "")
    return text if text and not text.startswith("your_") else ""


# Prints the shared line telling the user how defaults and cancelling work
def _wizard_print_default_guidance():
    print("Press Enter to accept the shown default. Ctrl+C cancels.\n")


# Reads one setup line. Cancelling propagates to the one handler in run_setup_wizard, which reports
# that nothing was written
def _wizard_input(prompt_text, input_func=None):
    prompt = input if input_func is None else input_func
    try:
        return read_interactively(prompt, colorize("info", prompt_text))
    except (EOFError, KeyboardInterrupt):
        # The interrupted prompt owns the line break, so every handler prints its message alone
        print()
        raise


# Asks one free-text question, returning the shown default when the answer is empty
def _wizard_ask_text(question, default="", required=False, input_func=None):
    suffix = f" [{default}]" if default else ""
    while True:
        answer = _wizard_input(f"{question}{suffix}: ", input_func=input_func).strip()
        if not answer:
            answer = default
        if answer or not required:
            return answer
        print("  This value is required.")
        if not _wizard_offer_retry(question, input_func=input_func):
            return ""


# Asks one yes or no question with a visible default
def _wizard_ask_yes_no(question, default=True, input_func=None):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = _wizard_input(f"{question} {hint}: ", input_func=input_func).strip().casefold()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Offers the one way out after an entry the wizard cannot use, so declining keeps every answer already given
def _wizard_offer_retry(label, consequence="", input_func=None):
    if consequence:
        return not _wizard_ask_yes_no(f"Continue without the {label}? {consequence}", default=False, input_func=input_func)
    return _wizard_ask_yes_no(f"Try entering the {label} again?", default=True, input_func=input_func)


# Asks one numbered multiple-choice question and returns the chosen index
def _wizard_ask_choice(question, options, default_index=0, input_func=None):
    print()
    print(question)
    for index, (label, description) in enumerate(options, 1):
        marker = " (default)" if index - 1 == default_index else ""
        print(f"  {colorize('username', str(index))}. {label}{colorize('info', marker) if marker else ''}")
        if description:
            for line in description.splitlines():
                print(f"     {line}")
    while True:
        answer = _wizard_input(f"Choose [1-{len(options)}]: ", input_func=input_func).strip()
        if not answer:
            return default_index
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"  Enter a number between 1 and {len(options)}.")


# Trims the parenthetical hint from a question, so the retry offer that repeats it stays one readable line
def _wizard_retry_label(question):
    return question.split(" (")[0].strip()


# Asks until the answer is a positive whole number or the default is accepted
def _wizard_ask_positive_int(question, default, maximum=None, input_func=None):
    while True:
        answer = _wizard_ask_text(question, default=str(default), required=True, input_func=input_func)
        # An empty answer means the retry offer was declined, so the default stands instead of asking again
        if not answer:
            return int(default)
        try:
            parsed = int(answer)
        except ValueError:
            parsed = 0
        if parsed > 0 and (maximum is None or parsed <= maximum):
            return parsed
        print(f"  Enter a whole number from 1 through {maximum}." if maximum is not None else "  Enter a positive whole number.")
        # A value the helper cannot use is a rejected entry, so it gets the same way out an empty one gets
        if not _wizard_offer_retry(_wizard_retry_label(question), input_func=input_func):
            print(f"  Keeping {default}.")
            return int(default)


# Renders a duration as raw seconds plus a readable form, so the value that reaches the config stays visible
def _wizard_format_duration(seconds):
    remaining = int(seconds)
    parts = []
    for suffix, count in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        value, remaining = divmod(remaining, count)
        if value:
            parts.append(f"{value}{suffix}")
    raw = f"{int(seconds)}s"
    readable = " ".join(parts) or raw
    return raw if readable == raw else f"{raw} - {readable}"


# Asks one duration, accepting the formats people actually type
def _wizard_ask_duration(question, default, input_func=None):
    prompt_text = f"{question} [{_wizard_format_duration(default)}]: "
    while True:
        answer = _wizard_input(prompt_text, input_func=input_func).strip()
        if not answer:
            return default
        seconds = parse_duration_input(answer)
        if seconds is not None:
            return seconds
        print("  Enter a positive duration such as 120, 2m, 1.5h, 1h 30m or 1d.")
        if not _wizard_offer_retry(_wizard_retry_label(question), input_func=input_func):
            print(f"  Keeping {_wizard_format_duration(default)}.")
            return default


# Asks one secret through a hidden prompt with debug output off, so it never reaches the screen, the shell history or the debug stream
def _wizard_ask_secret(question, getpass_func=None):
    global DEBUG_MODE
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    previous_debug_mode = DEBUG_MODE
    DEBUG_MODE = False
    try:
        # Colorized like the visible prompts, so a hidden answer does not look like a different question
        return str(read_interactively(hidden_prompt, colorize("info", f"{question}: "))).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise
    finally:
        DEBUG_MODE = previous_debug_mode


# Renders one setting for the generated config, keeping a mapping readable instead of on one very long line
def render_config_value(value):
    if isinstance(value, dict) and value:
        return "{\n" + "".join(f"    {key!r}: {item!r},\n" for key, item in value.items()) + "}"
    return repr(value)


# Renders one configuration file from the built-in template with the chosen values substituted in
def generate_config_with_current_values(config_values):
    tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    replacements = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            continue
        name = statement.targets[0].id
        # A secret belongs in the dotenv file, so its template placeholder stays even when the running values hold the real one
        if name not in config_values or name in SECRET_KEYS:
            continue
        replacements[name] = (statement.lineno, getattr(statement, "end_lineno", statement.lineno), render_config_value(config_values[name]))
    lines = CONFIG_BLOCK.strip("\n").split("\n")
    # The template keeps its own leading blank line, so template line numbers are one ahead of this list
    offset = 1 if CONFIG_BLOCK.startswith("\n") else 0
    skip_until = 0
    output = []
    for number, line in enumerate(lines, 1):
        template_line = number + offset
        if template_line < skip_until:
            continue
        replaced = next((name for name, (start, _end, _value) in replacements.items() if start == template_line), None)
        if replaced is None:
            output.append(line)
            continue
        start, end, rendered = replacements[replaced]
        output.append(f"{replaced} = {rendered}")
        skip_until = end + 1
    return "\n".join(output) + "\n"


# Walks up to the first directory that exists, so a destination under a missing folder can still be judged
def nearest_existing_parent(path):
    candidate = Path(path).expanduser()
    if candidate.exists():
        return candidate if candidate.is_dir() else candidate.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


# Checks one setup destination without creating or modifying it, so an unwritable path is caught before any question
def _wizard_validate_destination(path, label):
    destination = Path(path).expanduser().resolve()
    if destination.exists() and destination.is_dir():
        raise ValueError(f"{label} must be a file path, not a directory")
    parent = nearest_existing_parent(destination)
    if not parent.is_dir():
        raise ValueError(f"{label} does not have a usable parent directory")
    if not os.access(str(parent), os.W_OK):
        raise ValueError(f"{label} is not writable through parent '{parent}'")
    return destination


# Resolves both setup destinations, refusing the disabled settings that leave nowhere to write
def _wizard_destinations(config_file=None, env_file=None):
    if config_file is not None and str(config_file).casefold() == "none":
        raise ValueError("--setup has nowhere to write the configuration")
    if env_file is not None and str(env_file).casefold() == "none":
        raise ValueError("--setup has nowhere to write the secrets")
    config_path = Path(config_file).expanduser() if config_file is not None else Path.cwd() / DEFAULT_CONFIG_FILENAME
    env_path = Path(env_file).expanduser() if env_file is not None else Path.cwd() / ".env"
    return _wizard_validate_destination(config_path, "Configuration destination"), _wizard_validate_destination(env_path, "Dotenv destination")


# Confirms replacing an existing config before any question is asked, so a long run cannot end in a surprise
def _wizard_choose_config_destination(config_path, input_func=None):
    selected = Path(config_path)
    while selected.exists() and not _wizard_ask_yes_no(f"Configuration file '{selected}' exists. A timestamped backup is kept. Rebuild it from your answers, starting from its current settings?", default=False, input_func=input_func):
        alternative = _wizard_ask_text("Another config destination or leave empty to cancel", input_func=input_func)
        if not alternative:
            return None
        try:
            selected = _wizard_validate_destination(alternative, "Configuration destination")
        except ValueError as exc:
            print(f"  {exc}.")
    return selected


# Queues one secret for the save step, asking first when the dotenv file already assigns it
def _wizard_queue_secret(state, key, value, input_func=None):
    if not value:
        return False
    if _dotenv_contains_key(state.env_path, key) and not _wizard_ask_yes_no(f"The dotenv file already contains {key}. Replace that value?", default=False, input_func=input_func):
        print(f"  Existing {key} will be retained without being displayed or rewritten.")
        return False
    state.secret_updates[key] = value
    return True


# Holds every wizard answer until the user explicitly saves, so nothing is written during questioning
class WizardSetupState:
    # Starts from the values already in effect, which become both the defaults and the revert target
    def __init__(self, config_path, env_path, baseline_values):
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self.baseline_values = dict(baseline_values)
        self.config_values = dict(baseline_values)
        self.secret_updates = {}
        self.target = ""
        self.persist_target = True


# The mail server settings the wizard collects, and how long its sign-in check waits for the server
WIZARD_SMTP_CONFIG_KEYS = ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL")
WIZARD_SMTP_TIMEOUT = 5

# The email alert settings the wizard offers, in the order the questions are asked
WIZARD_EMAIL_NOTIFICATION_KEYS = ("ACTIVE_INACTIVE_NOTIFICATION", "GAME_CHANGE_NOTIFICATION", "ERROR_NOTIFICATION")

# The webhook alert settings the wizard offers, in the order the questions are asked
WIZARD_WEBHOOK_NOTIFICATION_KEYS = ("WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", "WEBHOOK_GAME_CHANGE_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION")

# Each editable section: internal name, menu label and description, then the keys reverted when it is re-entered
WIZARD_SECTIONS = (
    ("Target", "Target", "Change the PlayStation account that is monitored.", ("PSN_USER_ID",), ()),
    ("Polling", "Polling interval", "Change how often PlayStation Network is checked.", ("PSN_CHECK_INTERVAL", "PSN_ACTIVE_CHECK_INTERVAL"), ()),
    ("Authentication", "Authentication", "Enter the NPSSO code again.", (), ("PSN_NPSSO",)),
    ("Email", "Email notifications", "Change SMTP details and email events.", WIZARD_SMTP_CONFIG_KEYS + WIZARD_EMAIL_NOTIFICATION_KEYS, ("SMTP_PASSWORD",)),
    ("Webhook", "Webhook alerts", "Change Discord or ntfy details and events.", ("WEBHOOK_ENABLED", "WEBHOOK_PROVIDER") + WIZARD_WEBHOOK_NOTIFICATION_KEYS, ("WEBHOOK_URL", "NTFY_ACCESS_TOKEN")),
    ("Output", "Output files", "Change the log, CSV and status file destinations.", ("DISABLE_LOGGING", "CSV_FILE", "PSN_STATUS_FILE"), ()),
    ("Destinations", "File destinations", "Change the configuration or dotenv output path.", (), ()),
)


# Restores one section to the values setup started with and drops any secret it had queued
def _wizard_reset_section(state, config_keys, secret_keys):
    for key in config_keys:
        if key in state.baseline_values:
            state.config_values[key] = state.baseline_values[key]
        else:
            state.config_values.pop(key, None)
    for key in secret_keys:
        state.secret_updates.pop(key, None)


# Returns one declined section to the built-in template values, so nothing the user turned down is written
def _wizard_clear_section(state, config_keys, secret_keys=()):
    defaults = _config_template_defaults()
    for key in config_keys:
        if key in defaults:
            state.config_values[key] = defaults[key]
        else:
            state.config_values.pop(key, None)
    for key in secret_keys:
        state.secret_updates.pop(key, None)


# Asks which account to watch, accepting the online ID or a profile link and rejecting the e-mail mistake
def _wizard_collect_target_section(state, initial_target=None, input_func=None):
    question = "PlayStation online ID to monitor"
    while True:
        answer = _wizard_ask_text(question, default=str(initial_target or state.target or ""), required=True, input_func=input_func)
        if not answer:
            # The question already offered another attempt and it was declined, so the section ends instead of asking again
            break
        try:
            state.target = normalize_psn_target(answer)
        except ValueError as exc:
            print(f"  {exc}")
            if not _wizard_offer_retry(question, input_func=input_func):
                break
            continue
        break
    if not state.target:
        print("  No target selected. Nothing can be monitored until one is set. Run --setup again or pass the target on the command line.")
        _wizard_apply_target(state)
        return
    state.persist_target = _wizard_ask_yes_no("Persist this target in the generated config?", default=state.persist_target, input_func=input_func)
    _wizard_apply_target(state)


# Mirrors the settled target into the config values, so an unsaved target is left out of the file
def _wizard_apply_target(state):
    state.config_values["PSN_USER_ID"] = state.target if state.persist_target and state.target else ""


# Asks how often the tool checks, in whichever duration format the user prefers
def _wizard_collect_polling_section(state, input_func=None):
    state.config_values["PSN_CHECK_INTERVAL"] = _wizard_ask_duration("Polling interval while the user is offline (seconds or use s/m/h/d)", int(state.config_values.get("PSN_CHECK_INTERVAL") or PSN_CHECK_INTERVAL), input_func=input_func)
    state.config_values["PSN_ACTIVE_CHECK_INTERVAL"] = _wizard_ask_duration("Polling interval while the user is online (seconds or use s/m/h/d)", int(state.config_values.get("PSN_ACTIVE_CHECK_INTERVAL") or PSN_ACTIVE_CHECK_INTERVAL), input_func=input_func)


# Asks for the NPSSO code through a hidden prompt and checks it against PSN before accepting it
def _wizard_collect_auth_section(state, input_func=None, getpass_func=None, validator=None):
    print(f"Sign in at https://my.playstation.com then copy the npsso value from: {NPSSO_SOURCE_URL}")
    if secret_is_set(state.config_values.get("PSN_NPSSO")) and not _wizard_ask_yes_no("Replace the NPSSO code already configured?", default=False, input_func=input_func):
        return
    validate = validate_npsso_code if validator is None else validator
    while True:
        npsso = _wizard_ask_secret("NPSSO code", getpass_func=getpass_func)
        if not npsso:
            # Monitoring cannot run without it, so leaving it unset has to be a decision rather than a fallthrough
            if not _wizard_offer_retry("NPSSO code", "Nothing can be monitored until one is set", input_func=input_func):
                return
            continue
        # PSN exchanges the code for a token before it answers, which takes long enough to look like a hang
        print("  Checking the NPSSO code with PlayStation Network ...")
        try:
            account = validate(npsso)
        except RecoveryError as exc:
            print(f"  {exc.advice.summary}. {exc.advice.fix}")
            # A code PSN keeps rejecting cannot be corrected from inside the loop, so the wizard must be leavable here too
            if not _wizard_offer_retry("NPSSO code", input_func=input_func):
                return
            continue
        _wizard_queue_secret(state, "PSN_NPSSO", npsso, input_func=input_func)
        print(f"  PlayStation Network accepted the code, signed in as {account}.")
        return


# Reports whether the saved settings already send email, so a rerun proposes keeping the channel it has
def _wizard_email_enabled(config_values):
    # The error alert ships switched on, so on its own it counts only once a mail server has been named
    for key in WIZARD_EMAIL_NOTIFICATION_KEYS:
        if key != "ERROR_NOTIFICATION" and bool(config_values.get(key)):
            return True
    return bool(config_values.get("ERROR_NOTIFICATION")) and secret_is_set(config_values.get("SMTP_HOST"))


# Asks whether to send email alerts and collects only the settings that choice needs
def _wizard_collect_email_section(state, input_func=None, getpass_func=None):
    if not _wizard_ask_yes_no("Configure email notifications?", default=_wizard_email_enabled(state.config_values), input_func=input_func):
        _wizard_disable_email(state)
        return
    while True:
        state.config_values["SMTP_HOST"] = _wizard_ask_text("SMTP host", default=_wizard_default(state.config_values.get("SMTP_HOST")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SMTP_HOST"):
            return
        state.config_values["SMTP_PORT"] = _wizard_ask_positive_int("SMTP port", int(state.config_values.get("SMTP_PORT") or 587), maximum=65535, input_func=input_func)
        state.config_values["SMTP_SSL"] = _wizard_ask_yes_no("Enable TLS/SSL for SMTP?", default=bool(state.config_values.get("SMTP_SSL")), input_func=input_func)
        state.config_values["SMTP_USER"] = _wizard_ask_text("SMTP username", default=_wizard_default(state.config_values.get("SMTP_USER")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SMTP_USER"):
            return
        state.config_values["SENDER_EMAIL"] = _wizard_ask_text("Sender email", default=_wizard_default(state.config_values.get("SENDER_EMAIL")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SENDER_EMAIL"):
            return
        state.config_values["RECEIVER_EMAIL"] = _wizard_ask_text("Receiver email", default=_wizard_default(state.config_values.get("RECEIVER_EMAIL")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "RECEIVER_EMAIL"):
            return
        password = _wizard_ask_secret("SMTP password", getpass_func=getpass_func)
        if password:
            _wizard_queue_secret(state, "SMTP_PASSWORD", password, input_func=input_func)
        outcome = _wizard_smtp_sign_in_accepted({name: state.config_values[name] for name in WIZARD_SMTP_CONFIG_KEYS}, password, input_func=input_func)
        if outcome is None:
            _wizard_disable_email(state)
            return
        if outcome:
            break
    preset = _wizard_ask_choice("Which email notifications should be enabled?", [
        ("Status and errors, recommended", "Online and offline changes, game changes and monitoring errors."),
        ("Custom", "Choose each notification type separately."),
    ], input_func=input_func)
    if preset == 0:
        selected = {name: True for name in WIZARD_EMAIL_NOTIFICATION_KEYS}
    else:
        print()
        questions = (
            ("ACTIVE_INACTIVE_NOTIFICATION", "Email when the user goes online or offline?"),
            ("GAME_CHANGE_NOTIFICATION", "Email when the user starts, changes or stops a game?"),
            ("ERROR_NOTIFICATION", "Email on monitoring errors?"),
        )
        selected = {name: _wizard_ask_yes_no(question, default=False, input_func=input_func) for name, question in questions}
    state.config_values.update(selected)


# Signs in to the collected mail server without sending anything, so a refused login is caught during setup
def _wizard_verify_smtp(values, password):
    names = WIZARD_SMTP_CONFIG_KEYS + ("SMTP_PASSWORD",)
    previous = {name: globals()[name] for name in names}
    try:
        globals().update(values)
        # A blank answer keeps the password already stored, which is the one the sign-in must then prove
        smtp_sign_in(password or previous["SMTP_PASSWORD"], timeout=WIZARD_SMTP_TIMEOUT)
        return None
    except RecoveryError as exc:
        return exc.advice
    except Exception as exc:
        return classify_recovery_error(exc, context="smtp")
    finally:
        globals().update(previous)


# Reports the outcome of the sign-in check: True to continue, False to ask again, None to switch email off
def _wizard_smtp_sign_in_accepted(values, password, input_func=None):
    print("  Checking the sign-in with the mail server ...")
    advice = _wizard_verify_smtp(values, password)
    if advice is None:
        print("  The mail server accepted the sign-in. No email was sent.")
        return True
    print(f"  {advice.summary}: {advice.detail}" if advice.detail else f"  {advice.summary}")
    print(f"  To fix: {advice.fix}")
    if _wizard_offer_retry("mail server settings", input_func=input_func):
        return False
    if advice.retryable:
        # Being offline is the usual reason a correct setup fails here, so the answers are kept rather than discarded
        print("  The settings were kept without being checked. Run --doctor to check the sign-in again.")
        return True
    print("  Email notifications stay off until the mail server accepts the settings.")
    return None


# Switches every email alert off together, so an abandoned answer cannot leave half a mail server configured
def _wizard_disable_email(state):
    _wizard_clear_section(state, WIZARD_SMTP_CONFIG_KEYS, ("SMTP_PASSWORD",))
    for key in WIZARD_EMAIL_NOTIFICATION_KEYS:
        state.config_values[key] = False


# Reports whether one required mail server answer was abandoned, switching the channel off when it was
def _wizard_email_answer_missing(state, key):
    if state.config_values.get(key):
        return False
    print("  Email notifications stay off until every mail server setting is answered.")
    _wizard_disable_email(state)
    return True


# Reports whether a usable secret is already saved, without reading its value into the transcript
def _wizard_existing_secret(key, env_path):
    value = None
    if Path(env_path).is_file():
        try:
            from dotenv import dotenv_values

            value = dotenv_values(str(env_path), interpolate=False).get(key)
        except Exception as exc:
            debug_print("Reading the dotenv file for an existing secret", path=str(env_path), key=key, outcome="failed", error=f"{type(exc).__name__}: {exc}")
            value = None
    if value is None:
        value = os.environ.get(key)
    return secret_is_set(value)


# Collects an optional ntfy access token without displaying it or contacting the service
def _wizard_collect_ntfy_access_token(state, input_func=None, getpass_func=None):
    if _wizard_existing_secret("NTFY_ACCESS_TOKEN", state.env_path):
        choice = _wizard_ask_choice("Which ntfy authentication should be used?", [
            ("Keep the saved access token", "Keeps the private value without displaying or changing it."),
            ("Paste a new access token", "Uses a hidden prompt then saves the replacement in .env."),
            ("Do not use an access token", "Disables the saved token. Authentication in the topic URL still works."),
        ], input_func=input_func)
        if choice == 0:
            return
        if choice == 2:
            state.secret_updates["NTFY_ACCESS_TOKEN"] = ""
            print("  The saved ntfy access token will be disabled without being displayed.")
            return
    elif not _wizard_ask_yes_no("Authenticate this ntfy topic with a separate access token?", default=False, input_func=input_func):
        print("  No separate access token selected. Authentication already present in the topic URL still works.")
        return
    while True:
        token = _wizard_ask_secret("Paste the ntfy access token only", getpass_func=getpass_func)
        if not token or ("\r" not in token and "\n" not in token and not token.casefold().startswith(("bearer ", "basic "))):
            if token:
                state.secret_updates["NTFY_ACCESS_TOKEN"] = token
            return
        print("  Paste only the access token without a Bearer or Basic prefix.")
        if not _wizard_offer_retry("ntfy access token", input_func=input_func):
            return


# Asks whether to send webhook alerts and collects only the settings that choice needs
def _wizard_collect_webhook_section(state, input_func=None, getpass_func=None):
    if not _wizard_ask_yes_no("Set up webhook alerts (Discord, ntfy etc.)?", default=bool(state.config_values.get("WEBHOOK_ENABLED")), input_func=input_func):
        _wizard_disable_webhook(state)
        return
    choice = _wizard_ask_choice("Which webhook service should receive alerts?", [
        ("Discord", "Sends a Discord embed to one channel webhook."),
        ("ntfy", "Sends a native notification to one ntfy topic URL."),
    ], input_func=input_func)
    provider = "discord" if choice == 0 else "ntfy"
    state.config_values["WEBHOOK_PROVIDER"] = provider
    if provider == "discord":
        print("  In Discord: Edit Channel > Integrations > Webhooks > New Webhook > Copy Webhook URL.")
    else:
        print("  In ntfy: choose a hard-to-guess topic. Paste its complete topic URL, or just the topic name when it is hosted on ntfy.sh.")
    replace_webhook = True
    if _wizard_existing_secret("WEBHOOK_URL", state.env_path):
        url_choice = _wizard_ask_choice("Which webhook URL should be used?", [
            ("Keep the saved URL", "Keeps the private value without displaying or changing it."),
            ("Paste a new URL", "Uses a hidden prompt then saves the new private value in .env."),
        ], input_func=input_func)
        replace_webhook = url_choice == 1
    if replace_webhook:
        while True:
            entered = _wizard_ask_secret("Paste the Discord webhook URL" if provider == "discord" else "Paste the ntfy topic URL or ntfy.sh topic name", getpass_func=getpass_func)
            webhook_url = normalize_ntfy_topic_url(entered) if provider == "ntfy" else str(entered).strip()
            if validate_webhook_url(webhook_url):
                state.secret_updates["WEBHOOK_URL"] = webhook_url
                break
            # Nothing can be delivered without a destination, so giving up has to stay reachable from the prompt.
            # The branch is chosen by what was typed rather than by the normalized value, since a rejected ntfy
            # topic normalizes to an empty string and would otherwise be reported as nothing entered
            if not str(entered).strip():
                if not _wizard_offer_retry("webhook URL", "Webhook alerts stay off until one is set", input_func=input_func):
                    _wizard_disable_webhook(state)
                    return
                continue
            if provider == "ntfy":
                print("  Enter a complete HTTPS ntfy topic URL or a topic name containing up to 64 letters, numbers, dashes or underscores.")
            else:
                print("  That does not look like a complete HTTPS webhook URL. Copy it from the webhook service and try again.")
            if not _wizard_offer_retry("webhook URL", input_func=input_func):
                _wizard_disable_webhook(state)
                return
    if provider == "ntfy":
        _wizard_collect_ntfy_access_token(state, input_func=input_func, getpass_func=getpass_func)
    state.config_values["WEBHOOK_ENABLED"] = True
    preset = _wizard_ask_choice("Which webhook alerts should be sent?", [
        ("Status and errors, recommended", "Online and offline changes, game changes and monitoring errors."),
        ("Custom", "Choose each webhook alert separately."),
    ], input_func=input_func)
    if preset == 0:
        selected = {name: True for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS}
    else:
        print()
        questions = (
            ("WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", "Send a webhook alert when the user goes online or offline?"),
            ("WEBHOOK_GAME_CHANGE_NOTIFICATION", "Send a webhook alert when the user starts, changes or stops a game?"),
            ("WEBHOOK_ERROR_NOTIFICATION", "Send a webhook alert on monitoring errors?"),
        )
        selected = {name: _wizard_ask_yes_no(question, default=False, input_func=input_func) for name, question in questions}
    state.config_values.update(selected)


# Switches the channel and every alert it owns off together, so a half-configured webhook cannot be written
def _wizard_disable_webhook(state):
    _wizard_clear_section(state, ("WEBHOOK_PROVIDER",), ("WEBHOOK_URL", "NTFY_ACCESS_TOKEN"))
    state.config_values["WEBHOOK_ENABLED"] = False
    for key in WIZARD_WEBHOOK_NOTIFICATION_KEYS:
        state.config_values[key] = False


# Adds the .csv extension when the answer carries none, so a bare name still names a CSV file
def _wizard_normalize_csv_path(answer):
    text = str(answer).strip()
    if not text or Path(text).suffix:
        return text
    return text + ".csv"


# Adds the .json extension when the answer carries none, so a bare name still names the JSON status file
def _wizard_normalize_status_path(answer):
    text = str(answer).strip()
    if not text or Path(text).suffix:
        return text
    return text + ".json"


# Collects the files monitoring would write
def _wizard_collect_output_section(state, input_func=None):
    state.config_values["DISABLE_LOGGING"] = not _wizard_ask_yes_no("Write the normal per-target log file?", default=not bool(state.config_values.get("DISABLE_LOGGING")), input_func=input_func)
    state.config_values["CSV_FILE"] = _wizard_normalize_csv_path(_wizard_ask_text("Optional CSV output path (blank disables it)", default=str(state.config_values.get("CSV_FILE") or ""), input_func=input_func))
    state.config_values["PSN_STATUS_FILE"] = _wizard_normalize_status_path(_wizard_ask_text("Optional status file path (blank uses the default name in the working directory)", default=str(state.config_values.get("PSN_STATUS_FILE") or ""), input_func=input_func))


# Changes where setup writes, re-asking the sections that hold secrets when the dotenv destination moves
def _wizard_collect_destination_section(state, input_func=None, getpass_func=None):
    while True:
        config_text = _wizard_ask_text("Configuration file destination", default=str(state.config_path), required=True, input_func=input_func)
        try:
            selected_config = _wizard_validate_destination(config_text, "Configuration destination")
            break
        except ValueError as exc:
            print(f"  {exc}.")
    # Both sides are compared resolved, so an unchanged answer written a different way is not read as a move
    if selected_config != Path(state.config_path).expanduser().resolve():
        chosen_config = _wizard_choose_config_destination(selected_config, input_func=input_func)
        # Giving up on every offered path keeps the current destination rather than cancelling the whole setup
        if chosen_config is not None:
            state.config_path = chosen_config
    while True:
        env_text = _wizard_ask_text("Dotenv file destination", default=str(state.env_path), required=True, input_func=input_func)
        if env_text.casefold() == "none":
            print("  Setup needs a writable dotenv file and cannot use 'none'.")
            continue
        try:
            selected_env = _wizard_validate_destination(env_text, "Dotenv destination")
        except ValueError as exc:
            print(f"  {exc}.")
            continue
        # One file cannot hold both, since saving the configuration would overwrite the secrets beside it
        if selected_env == Path(state.config_path).expanduser().resolve():
            print("  The dotenv file has to be a different file from the configuration.")
            continue
        break
    state.config_values["DOTENV_FILE"] = str(selected_env)
    if selected_env == Path(state.env_path).expanduser().resolve():
        return
    state.env_path = selected_env
    # A secret kept rather than retyped was never queued, so it would be missing from a dotenv file that just moved
    print("  The dotenv destination changed. Re-enter authentication and notification settings that may contain secrets.")
    _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func)
    print()
    _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func)
    print()
    _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func)


# Runs one editable section again after resetting only the keys it owns
def _wizard_edit_setup_section(state, input_func=None, getpass_func=None):
    options = [(label, description) for _name, label, description, _config_keys, _secret_keys in WIZARD_SECTIONS]
    options.append(("Return to summary", "Keep every current answer."))
    choice = _wizard_ask_choice("Which setup section should be changed?", options, input_func=input_func)
    if choice == len(WIZARD_SECTIONS):
        return
    name, _label, _description, config_keys, secret_keys = WIZARD_SECTIONS[choice]
    _wizard_reset_section(state, config_keys, secret_keys)
    if name == "Target":
        state.target = ""
    print()
    collectors = {
        "Target": lambda: _wizard_collect_target_section(state, input_func=input_func),
        "Polling": lambda: _wizard_collect_polling_section(state, input_func=input_func),
        "Authentication": lambda: _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func),
        "Email": lambda: _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func),
        "Webhook": lambda: _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func),
        "Output": lambda: _wizard_collect_output_section(state, input_func=input_func),
        "Destinations": lambda: _wizard_collect_destination_section(state, input_func=input_func, getpass_func=getpass_func),
    }
    collectors[name]()


# The theme part each setup summary row draws its value in, for rows whose value has a known kind
WIZARD_SUMMARY_VALUE_STYLES = {"Target": "username", "Polling interval while offline": "duration", "Polling interval while online": "duration"}


# Colours one setup summary value from its row label
def _wizard_summary_value(label, value):
    text = str(value)
    part = WIZARD_SUMMARY_VALUE_STYLES.get(label)
    if part:
        return colorize(part, text)
    if text.startswith("enabled") or text == "complete":
        return colorize("boolean_true", text)
    if text in ("disabled", "incomplete"):
        return colorize("boolean_false", text)
    return text


# Prints one aligned label and value block, so every summary row lines up
def _wizard_print_summary_rows(rows):
    width = max(len(label) for label, _ in rows) + 1
    for label, value in rows:
        print(f"  {(label + ':'):<{width}} {_wizard_summary_value(label, value)}")


# Shows everything that is about to be written, by name and never by secret value
def _wizard_print_setup_summary(state):
    email_labels = {"ACTIVE_INACTIVE_NOTIFICATION": "online/offline", "GAME_CHANGE_NOTIFICATION": "game", "ERROR_NOTIFICATION": "errors"}
    webhook_labels = {"WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION": "online/offline", "WEBHOOK_GAME_CHANGE_NOTIFICATION": "game", "WEBHOOK_ERROR_NOTIFICATION": "errors"}
    enabled_email = [email_labels[name] for name in WIZARD_EMAIL_NOTIFICATION_KEYS if state.config_values.get(name)]
    enabled_webhook = [webhook_labels[name] for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS if state.config_values.get(name)] if state.config_values.get("WEBHOOK_ENABLED") else []
    npsso_set = "PSN_NPSSO" in state.secret_updates or secret_is_set(state.config_values.get("PSN_NPSSO"))
    rows = [
        ("Target", state.target or "not set"),
        ("Persist target", "yes" if state.persist_target else "no"),
        ("Polling interval while offline", _wizard_format_duration(int(state.config_values.get("PSN_CHECK_INTERVAL") or 0))),
        ("Polling interval while online", _wizard_format_duration(int(state.config_values.get("PSN_ACTIVE_CHECK_INTERVAL") or 0))),
        ("Authentication status", "complete" if npsso_set else "incomplete"),
        ("Email", "enabled" if enabled_email else "disabled"),
        ("Email notifications", ", ".join(enabled_email) if enabled_email else "none"),
        ("Webhook", f"enabled ({webhook_provider_display_name(state.config_values.get('WEBHOOK_PROVIDER'))})" if state.config_values.get("WEBHOOK_ENABLED") else "disabled"),
        ("Webhook alerts", ", ".join(enabled_webhook) if enabled_webhook else "none"),
        ("Output log", "disabled" if state.config_values.get("DISABLE_LOGGING") else "enabled"),
        ("CSV output", state.config_values.get("CSV_FILE") or "disabled"),
        ("Status file", state.config_values.get("PSN_STATUS_FILE") or (default_status_file(state.target) if state.target else "psn_<psn_user_id>_last_status.json")),
        ("Config destination", state.config_path),
        ("Dotenv destination", state.env_path),
        ("Install method", install_method_display_name()),
    ]
    print("\n" + colorize("header", "Setup summary") + "\n")
    _wizard_print_summary_rows(rows)


# Loops on the summary until the user saves or explicitly discards, so nothing is written by accident
def _wizard_review_setup(state, input_func=None, getpass_func=None):
    while True:
        _wizard_print_setup_summary(state)
        action = _wizard_ask_choice("What would you like to do?", [
            ("Save settings", "Write the displayed settings to the selected files."),
            ("Review or change settings", "Edit one section without losing the other answers."),
            ("Discard answers and exit", "Leave the destination files unchanged."),
        ], input_func=input_func)
        if action == 0:
            return True
        if action == 1:
            _wizard_edit_setup_section(state, input_func=input_func, getpass_func=getpass_func)
            continue
        print()
        if _wizard_ask_yes_no("Discard all entered answers and exit?", default=False, input_func=input_func):
            return False
        print("  Setup answers retained.")


# Prints where setup will write and which install method the printed commands are written for
def _wizard_print_setup_destinations(config_path, env_path):
    print(f"Detected install method: {colorize('username', detect_install_method())}")
    print(f"Configuration:          {config_path}")
    print(f"Dotenv:                 {env_path}\n")


# Puts the values setup just saved into effect, so doctor checks the written files instead of the earlier state.
# Returns the timezone advice, since the saved config can name a zone the startup resolution never saw
def _wizard_apply_saved_values(state, env_path=None):
    # Config values first: they carry the unset placeholders for every secret, which would otherwise
    # overwrite the secrets applied below and make doctor report a working setup as unconfigured
    globals().update(state.config_values)
    if env_path:
        try:
            from dotenv import load_dotenv

            load_dotenv(str(env_path), override=True)
        except Exception as exc:
            debug_print("Reading the dotenv file back after setup", path=env_path, outcome="failed", error=f"{type(exc).__name__}: {exc}")
    # The shared resolver rather than a local loop, so doctor names the same source it would after a restart
    apply_environment_secrets()
    # Secrets exported before startup keep winning here, exactly as they will when monitoring runs
    for key, value in state.secret_updates.items():
        if key not in EXPORTED_SECRET_KEYS and not secret_is_set(globals().get(key)):
            globals()[key] = value
            record_secret_source(key, "dotenv file")
    return resolve_local_timezone()


# Builds the exact local command that starts this monitor, used when setup offers to launch it
def _wizard_local_command_args(target=None, config_path=None, env_path=None):
    executable = sys.executable or ("python" if platform.system() == "Windows" else "python3")
    arguments = [executable, str(Path(__file__).resolve())]
    if target:
        arguments.append(str(target))
    if config_path:
        arguments.extend(["--config-file", str(config_path)])
    if env_path:
        arguments.extend(["--env-file", str(env_path)])
    return arguments


# Hands the terminal to the monitor, replacing this process where the platform allows it
def _wizard_launch_monitor(arguments):
    command = [str(argument) for argument in arguments]
    if platform.system() == "Windows":
        try:
            return subprocess.run(command, check=False).returncode
        except KeyboardInterrupt:
            return 0
    os.execv(command[0], command)
    return 0


# Runs the guided setup, holding every answer until the user saves
def run_setup_wizard(initial_target=None, config_file=None, env_file=None, input_func=None, getpass_func=None, interactive=None):
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else bool(interactive)
    if not terminal_is_interactive:
        print("The setup wizard needs an interactive terminal (TTY).")
        print("Run --setup from an interactive shell or use --generate-config and edit the files manually.")
        print(f"Guide: {QUICK_START_GUIDE_URL}")
        return 1

    try:
        config_path, env_path = _wizard_destinations(config_file, env_file)
    except ValueError as exc:
        print_recovery_error(context="file.unwritable", detail=str(exc))
        return 1

    print(colorize("header", "Setup Wizard") + "\n")
    print("This asks a few questions and writes a ready-to-run configuration.")
    _wizard_print_default_guidance()
    print("Secrets go to the dotenv file. Non-secret settings go to the config file.\n")
    _wizard_print_setup_destinations(config_path, env_path)

    baseline_values = {name: value for name, value in globals().items() if name in _config_allowed_names()}
    state = WizardSetupState(config_path, env_path, baseline_values)
    state.config_values["DOTENV_FILE"] = str(env_path)

    try:
        # Asked before anything else, so a config that has to be replaced is agreed to rather than discovered at Save
        config_existed = Path(config_path).exists()
        chosen_config = _wizard_choose_config_destination(config_path, input_func=input_func)
        if chosen_config is None:
            print("\n" + colorize("warning", "Setup cancelled. Destination files were not changed."))
            return 1
        state.config_path = chosen_config
        # A destination nothing was asked about printed nothing, so the separator would leave a blank gap
        if config_existed:
            print()
        _wizard_collect_target_section(state, initial_target, input_func=input_func)
        print()
        _wizard_collect_polling_section(state, input_func=input_func)
        print()
        _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_output_section(state, input_func=input_func)
        saved = _wizard_review_setup(state, input_func=input_func, getpass_func=getpass_func)
    except (EOFError, KeyboardInterrupt):
        print(colorize("warning", "Setup cancelled. Destination files were not changed."))
        return 1

    if not saved:
        print("\n" + colorize("warning", "Setup cancelled. Destination files were not changed."))
        return 1

    # Everything above only filled the state, so this is the first and only point anything reaches disk
    try:
        config_backup, _written = write_generated_config(state.config_path, generate_config_with_current_values(state.config_values), force=True)
    except Exception as exc:
        print_recovery_error(exc, context="file.unwritable", detail=f"Could not write the configuration to '{state.config_path}': {exc}")
        return 1
    secrets_written = False
    if state.secret_updates:
        try:
            update_dotenv_file(state.env_path, state.secret_updates)
            secrets_written = True
        except Exception as exc:
            print_recovery_error(exc, context="file.unwritable", detail=f"Could not write the secrets to '{state.env_path}': {exc}")
            return 1

    print("\n" + colorize("header", "Saved files") + "\n")
    print(f"  Configuration: {state.config_path}")
    if config_backup:
        print(f"  Backup:        {config_backup}")
    if secrets_written:
        print(f"  Secrets:       {state.env_path}")

    doctor_offered = bool(state.target)
    doctor_exit = None
    if doctor_offered:
        print()
    try:
        if doctor_offered and _wizard_ask_yes_no("Run doctor now? It writes no files and offers real delivery tests only with separate approval.", default=True, input_func=input_func):
            print()
            timezone_advice = _wizard_apply_saved_values(state, env_path=state.env_path if secrets_written else None)
            doctor_exit = run_doctor(psn_user_id=state.target, config_path=str(state.config_path), env_path=str(state.env_path) if secrets_written else None, timezone_advice=timezone_advice)
    except (EOFError, KeyboardInterrupt):
        # The files are already written, so an interrupt here only skips the optional check
        print(colorize("warning", "Setup is saved. Use the commands below when ready."))

    env_arguments = ["--env-file", str(state.env_path)] if secrets_written else []
    # A saved target is already in the config file, so the printed commands stay short
    target_arguments = [] if state.persist_target or not state.target else [state.target]
    paths = ["--config-file", str(state.config_path)] + env_arguments
    print("\n" + colorize("header", "Next steps") + "\n")
    print_labelled_command("Check setup again:", render_command(["--doctor", *target_arguments, *paths]))
    start_label = "After Doctor passes, start monitoring:" if doctor_exit not in (None, 0) else "Start monitoring:"
    print_labelled_command(start_label, render_command([*target_arguments, *paths]))
    print(f"Guide: {QUICK_START_GUIDE_URL}\n")

    try:
        # Only a doctor run that passed proves the saved setup can monitor, so the launch offer waits for it
        start_monitoring = bool(state.target and doctor_exit == 0 and _wizard_ask_yes_no("Start monitoring now? Monitoring will continue until Ctrl+C.", default=True, input_func=input_func))
    except (EOFError, KeyboardInterrupt):
        # The files are already written, so an interrupt here only skips the optional launch
        print(colorize("warning", "Setup is saved. Start monitoring with the command above when ready."))
        return 0
    if start_monitoring:
        launch_arguments = _wizard_local_command_args(target=None if state.persist_target else state.target, config_path=state.config_path, env_path=state.env_path if secrets_written else None)
        sys.stdout.flush()
        return _wizard_launch_monitor(launch_arguments)
    return 0

# Renders the --help examples: one heading per task, then a comment and the command it describes
def render_help_examples(groups, guide_url):
    blocks = []
    for title, entries in groups:
        block = [f"{title}:"]
        for comment, command in entries:
            if len(block) > 1:
                block.append("")
            block.extend(f"  # {line}" for line in comment.split("\n"))
            if command:
                block.append(f"  {command}")
        blocks.append("\n".join(block))
    return "Examples:\n\n" + "\n\n".join(blocks) + f"\n\nGuide: {guide_url}\n"


# Returns the --help epilog, listing the commands worth knowing rather than every command there is
def help_examples():
    prefix = render_command(include_paths=False)
    groups = (
        ("Getting started", (
            ("Guided setup, recommended for the first run", f"{prefix} --setup"),
            ("Or save the NPSSO code through a hidden prompt", f"{prefix} --set-npsso"),
            ("Check the setup before relying on it", f"{prefix} --doctor <psn_user_id>"),
            ("Start monitoring", f"{prefix} <psn_user_id>"),
        )),
        ("Notifications", (
            ("Email when the user goes online or offline, and on game changes", f"{prefix} <psn_user_id> -a -g"),
            ("Send one test email", f"{prefix} --send-test-email"),
            ("Send one test webhook", f"{prefix} --send-test-webhook"),
        )),
        ("Information and diagnostics", (
            ("Show detailed profile information and exit", f"{prefix} -i <psn_user_id>"),
            ("Trace what the tool is doing", f"{prefix} <psn_user_id> --debug"),
        )),
    )
    return render_help_examples(groups, QUICK_START_GUIDE_URL)


# Prints the commands a newcomer needs next, instead of an argparse usage error nobody can act on
def print_welcome_screen(input_func=None, interactive=None, config_file=None, env_file=None):
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else bool(interactive)
    prefix = render_command(include_paths=False)
    print(f"For <psn_user_id>, use the {PSN_TARGET_FORMS}.\n")
    print_labelled_command("Quickest start (already configured):", f"{prefix} <psn_user_id>")
    # The suffix names the prompt printed below, so it only appears when that prompt does
    print_labelled_command("Easiest start (guided setup wizard):", f"{prefix} --setup", "   (or just answer Y below)" if terminal_is_interactive else "")
    print_labelled_command("Check setup before monitoring:", f"{prefix} --doctor <psn_user_id>")
    print_labelled_command("Show profile details and exit:", f"{prefix} -i <psn_user_id>")
    print(f"Full options: {colorize('section', prefix + ' --help')}")
    print(f"\nGuide:        {QUICK_START_GUIDE_URL}\n")
    if terminal_is_interactive:
        try:
            start_setup = _wizard_ask_yes_no("Run the guided setup wizard now?", default=True, input_func=input_func)
        except (EOFError, KeyboardInterrupt):
            # This prompt sits outside the wizard, which handles its own interrupts
            print(colorize("warning", "Setup cancelled."))
            return 1
        if start_setup:
            print()
            return run_setup_wizard(config_file=config_file, env_file=env_file, input_func=input_func)
    # Without a terminal there was nothing to answer, so a bare invocation stays the usage error it was
    return 0 if terminal_is_interactive else 1



# Where the NPSSO code is read from, printed before the hidden prompt so nobody has to hunt for it
NPSSO_SOURCE_URL = "https://ca.account.sony.com/api/v1/ssocookie"


# Matches one dotenv assignment, tolerating the export prefix used when the same file is also sourced by a shell
def match_dotenv_assignment(line, key):
    return re.match(rf"^(\s*(?:export\s+)?){re.escape(key)}\s*=", str(line))


# Renders one quoted dotenv assignment, keeping the export prefix of the line it replaces
def render_dotenv_assignment(key, value, prefix=""):
    # A line break inside a value would split the assignment, so it is escaped rather than written through
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    return f'{prefix}{key}="{escaped}"'


# Reports whether one dotenv file already assigns the requested key
def _dotenv_contains_key(path, key):
    target = Path(path).expanduser()
    if not target.is_file():
        return False
    return any(match_dotenv_assignment(line, key) for line in target.read_text(encoding="utf-8").splitlines())


# Replaces dotenv assignments in place in one pass, leaving every other line and every comment untouched
def update_dotenv_file(destination, updates):
    if not hasattr(updates, "items"):
        raise TypeError("Dotenv updates must be a mapping")
    target = Path(destination).expanduser()
    if not target.parent.is_dir():
        raise FileNotFoundError(f"The directory for '{target}' does not exist")
    for key, value in updates.items():
        if key not in SECRET_KEYS:
            raise ValueError(f"Refusing to write an unknown dotenv key: {key}")
        if not isinstance(value, str):
            raise TypeError(f"Dotenv value for {key} must be a string")
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    lines = []
    replaced = set()
    for line in existing.splitlines():
        rewritten = None
        for key in updates:
            match = match_dotenv_assignment(line, key)
            if not match:
                continue
            if key in replaced:
                rewritten = ""
                break
            replaced.add(key)
            # A secret cleared by its owner is removed rather than emptied, so a disabled value cannot linger here
            if not updates[key]:
                rewritten = ""
                break
            # An already exported line is rewritten in place. Appending a second assignment would leave the
            # old credential on disk, with only the load order deciding which one wins
            rewritten = render_dotenv_assignment(key, updates[key], match.group(1))
            break
        if rewritten == "":
            continue
        lines.append(line if rewritten is None else rewritten)
    for key, value in updates.items():
        if key not in replaced and value:
            lines.append(render_dotenv_assignment(key, value))
    # Written through a temporary file, so an interrupted write cannot leave the file without its secrets.
    # No backup is taken here: a copy of the credential being replaced is the one thing not worth keeping
    write_file_atomically(target, "\n".join(lines) + "\n")
    for key, value in updates.items():
        verbose_print(f"{'Saved' if value else 'Removed'} {key} in '{target}'")
    return str(target)




# Returns the dotenv file a one-shot secret command writes to, refusing the disabled setting
def resolve_secret_env_path(env_file, flag):
    selected = env_file if env_file else DOTENV_FILE
    if selected and str(selected).casefold() == "none":
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail=f"{flag} needs a dotenv file to write to, so it cannot be used with 'none'"))
    return Path(os.path.expanduser(str(selected))) if selected else Path.cwd() / ".env"


# Validates one NPSSO code against PlayStation Network, returning the account it signs in as
def validate_npsso_code(npsso):
    candidate = str(npsso or "").strip()
    if not candidate or candidate == "your_psn_npsso_code":
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="No NPSSO code was entered, so the dotenv file was not changed"))
    if "\r" in candidate or "\n" in candidate:
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="The NPSSO code contains a line break, so the dotenv file was not changed"))
    try:
        return psn_client(candidate).me().online_id
    except Exception as exc:
        raise RecoveryError(classify_recovery_error(exc, context="startup"), exc) from None


# The settings a sign-in needs before a password can be checked against the mail server
MAIL_SIGN_IN_SETTINGS = ("SMTP_HOST", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL")


# Returns the mail settings a sign-in needs that are still empty or still hold their shipped placeholder
def mail_sign_in_settings_missing():
    return [name for name in MAIL_SIGN_IN_SETTINGS if not secret_is_set(str(globals().get(name) or ""))]


# Signs in to the configured SMTP server with one candidate password, without sending a message
def smtp_sign_in(password, timeout=15):
    global SMTP_PASSWORD

    candidate = str(password or "")
    if not candidate.strip() or candidate == "your_smtp_password":
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="No SMTP password was entered, so the dotenv file was not changed"))
    previous_password = SMTP_PASSWORD
    SMTP_PASSWORD = candidate
    try:
        settings_advice = validate_smtp_settings()
        if settings_advice is not None:
            raise RecoveryError(settings_advice)
        debug_print("SMTP sign-in check", host=SMTP_HOST, port=SMTP_PORT, starttls=bool(SMTP_SSL), timeout=f"{timeout}s", user=SMTP_USER)
        connection = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=timeout)
        if SMTP_SSL:
            connection.starttls(context=smtp_ssl_context())
        try:
            connection.login(SMTP_USER, candidate)
        finally:
            try:
                connection.quit()
            except Exception as quit_error:
                debug_print("Closing the SMTP connection", outcome="failed", error=f"{type(quit_error).__name__}: {quit_error}")
    except RecoveryError:
        raise
    except Exception as exc:
        raise RecoveryError(classify_recovery_error(exc, context="smtp", detail=f"Signing in to {SMTP_HOST} as {SMTP_USER} failed: {exc}"), exc) from None
    finally:
        SMTP_PASSWORD = previous_password
    return SMTP_USER


# Prints the commands to run next, with the file paths this run was given so they can be pasted as they are
def print_secret_next_steps(env_path, config_path=None, psn_user_id=None, test_step=None):
    paths = []
    if config_path:
        paths.extend(("--config-file", str(config_path)))
    paths.extend(("--env-file", str(env_path)))
    doctor_target, monitor_target = command_targets(psn_user_id, config_file_target(config_path or find_config_file()))
    print()
    if test_step:
        print_labelled_command(test_step[0], render_command([test_step[1], *paths]))
    print_labelled_command("Check setup again:", render_command(["--doctor", *((doctor_target,) if doctor_target else ()), *paths]))
    print_labelled_command("Once the checks pass, start monitoring:", render_command([*((monitor_target,) if monitor_target else ()), *paths]))


# Collects one secret through a hidden prompt, checks it with the given validator and writes it only then
def run_set_secret(key, flag, subject, guide_url, guidance, prompt_text, validator, describe_success, env_file=None, config_path=None, psn_user_id=None, interactive=None, input_func=None, getpass_func=None, normalize=None, test_step=None):
    global DEBUG_MODE

    destination = resolve_secret_env_path(env_file, flag)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else bool(interactive)
    if not terminal_is_interactive:
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail=f"{flag} needs an interactive terminal so the value stays hidden"))

    ask = input if input_func is None else input_func
    if _dotenv_contains_key(destination, key):
        try:
            confirmed = str(read_interactively(ask, f"Replace the saved {subject} in '{destination}'? [y/N]: ")).strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            raise RecoveryError(secret_entry_cancelled_advice(subject, flag, guide_url)) from None
        if not confirmed:
            raise RecoveryError(secret_replacement_declined_advice(subject, flag, guide_url))

    print(guidance)
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    # The entered value must not reach the debug stream, which is the one place it would be printed verbatim
    previous_debug_mode = DEBUG_MODE
    DEBUG_MODE = False
    try:
        entered = read_interactively(hidden_prompt, prompt_text)
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice(subject, flag, guide_url)) from None
    finally:
        DEBUG_MODE = previous_debug_mode

    print(f"* Checking the entered {subject} before changing the dotenv file ...")
    outcome = validator(entered)
    # What is stored can differ from what was typed, so a shorthand the validator accepted is saved in full
    stored = str(entered).strip() if normalize is None else normalize(entered)
    try:
        update_dotenv_file(destination, {key: stored})
    except Exception as exc:
        raise RecoveryError(classify_recovery_error(exc, context="file.unwritable", detail=f"Cannot save {key} to '{destination}': {exc}"), exc) from None

    print(f"* {describe_success(outcome)}")
    print(f"* Updated '{destination}', readable only by you")
    print_secret_next_steps(destination, config_path, psn_user_id, test_step)
    return str(destination)


# Stores one validated NPSSO code in the dotenv file, so it never has to be typed on a command line
def run_set_npsso(env_file=None, config_path=None, psn_user_id=None, interactive=None, input_func=None, getpass_func=None):
    return run_set_secret("PSN_NPSSO", "--set-npsso", "NPSSO code", NPSSO_GUIDE_URL, f"* Sign in at https://my.playstation.com then copy the npsso value from: {NPSSO_SOURCE_URL}", "Enter the NPSSO code (input hidden): ", validate_npsso_code, lambda account: f"PlayStation Network accepted the code, signed in as {account}", env_file, config_path, psn_user_id, interactive, input_func, getpass_func)


# Accepts a complete webhook URL, or a bare ntfy.sh topic name when ntfy is the selected provider
def normalize_webhook_destination(value):
    return normalize_ntfy_topic_url(value) if normalized_webhook_provider() == "ntfy" else str(value or "").strip()


# Checks one entered webhook destination without contacting the service, because the only confirmation a
# webhook service offers is a delivered notification, and setting a URL must not publish one
def validate_webhook_destination(value):
    candidate = normalize_webhook_destination(value)
    if not candidate:
        raise RecoveryError(classify_recovery_error(context="secret.entry", detail="No webhook URL was entered, so the dotenv file was not changed"))
    if not validate_webhook_url(candidate):
        raise RecoveryError(classify_recovery_error(context="webhook", detail="WEBHOOK_URL needs a complete HTTPS link, so the dotenv file was not changed"))
    detected = detect_webhook_provider(candidate)
    configured = normalized_webhook_provider()
    if detected and configured and detected != configured:
        raise RecoveryError(classify_recovery_error(context="webhook", detail=f"WEBHOOK_PROVIDER is set to {webhook_provider_display_name(configured)} but that is a {webhook_provider_display_name(detected)} URL, so the dotenv file was not changed"))
    return webhook_provider_display_name(detected or configured)


# Stores one webhook destination in the dotenv file, so the private URL never has to appear on a command line
def run_set_webhook_url(env_file=None, config_path=None, psn_user_id=None, interactive=None, input_func=None, getpass_func=None):
    return run_set_secret("WEBHOOK_URL", "--set-webhook-url", "webhook URL", WEBHOOK_GUIDE_URL, "* Discord: Edit Channel > Integrations > Webhooks > New Webhook > Copy Webhook URL\n* ntfy: the complete topic URL, or just the topic name when it is hosted on ntfy.sh", "Enter the webhook URL (input hidden): ", validate_webhook_destination, lambda provider: f"The entered value looks like a valid {provider} destination", env_file, config_path, psn_user_id, interactive, input_func, getpass_func, normalize_webhook_destination, ("Send a test webhook:", "--send-test-webhook"))


# Stores one SMTP password in the dotenv file after the mail server has actually accepted it
def run_set_smtp_password(env_file=None, config_path=None, psn_user_id=None, interactive=None, input_func=None, getpass_func=None):
    # Checked before the prompts, so nobody types a password only to be told the mail server was never configured
    missing = mail_sign_in_settings_missing()
    if missing:
        names = join_setting_names(missing, "and")
        raise RecoveryError(make_recovery_advice("smtp.invalid", f"The mail server settings are incomplete, {names} {'is' if len(missing) == 1 else 'are'} not set", recovery_fix_with_guide(f"Set {names} in the config file, or run --setup, then run --set-smtp-password again", SMTP_GUIDE_URL), False))
    return run_set_secret("SMTP_PASSWORD", "--set-smtp-password", "SMTP password", SMTP_GUIDE_URL, f"* The password is checked by signing in to {SMTP_HOST} as {SMTP_USER}. Nothing is sent", "Enter the SMTP password (input hidden): ", smtp_sign_in, lambda user: f"The mail server accepted the password for {user}", env_file, config_path, psn_user_id, interactive, input_func, getpass_func)


def main():
    global CLI_CONFIG_PATH, CONFIG_DISCOVERY_DISABLED, DOTENV_FILE, PSN_STATUS_FILE, LOCAL_TIMEZONE, LOCAL_TIMEZONE_STATE, LIVENESS_REMINDER_SECONDS, PSN_NPSSO, CSV_FILE, DISABLE_LOGGING, PSN_LOGFILE, ACTIVE_INACTIVE_NOTIFICATION, GAME_CHANGE_NOTIFICATION, ERROR_NOTIFICATION, PSN_CHECK_INTERVAL, PSN_ACTIVE_CHECK_INTERVAL, SMTP_PASSWORD, TRUNCATE_CHARS, EXPORTED_SECRET_KEYS, COLORED_OUTPUT, WEBHOOK_ENABLED, stdout_bck, DEBUG_MODE

    if "--generate-config" in sys.argv:
        config_content = CONFIG_BLOCK.strip("\n") + "\n"
        try:
            idx = sys.argv.index("--generate-config")
            if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
                output_file = sys.argv[idx + 1]
                backup_path, written = write_generated_config(output_file, config_content, force="--force" in sys.argv)
                if not written:
                    print("Config was not replaced. The existing file is unchanged")
                    sys.exit(1)
                print(f"Config written to: {output_file}")
                if backup_path:
                    print(f"Previous config backed up to: {backup_path}")
                sys.exit(0)
        except (ValueError, IndexError):
            pass
        except FileExistsError as exc:
            print_recovery_error(context="file.exists", detail=str(exc))
            sys.exit(1)
        except OSError as exc:
            print_recovery_error(exc, context="file.unwritable", detail=f"The config file could not be written: {exc}")
            sys.exit(1)
        sys.stdout.buffer.write(config_content.encode("utf-8"))
        sys.stdout.buffer.flush()
        sys.exit(0)

    if "--version" in sys.argv:
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    stdout_bck = sys.stdout

    # The screen clear and the banner both run before the arguments are parsed, so the two config settings
    # that decide how the terminal looks are read here as well
    apply_early_output_config()

    if "--no-color" in sys.argv:
        COLORED_OUTPUT = False

    init_color_output(stdout_bck)

    # Installed before the banner and before one-shot modes run, so PSN-supplied text printed by --info cannot
    # drive the terminal either. The Logger installed later unwraps this again to keep the single colour pass
    if not isinstance(sys.stdout, TerminalStream):
        sys.stdout = TerminalStream(sys.stdout)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Read straight from sys.argv because argparse has not run yet, and the screen is cleared before it does
    if "--debug" in sys.argv:
        DEBUG_MODE = True
    if CLEAR_SCREEN and DEBUG_MODE:
        debug_print("Terminal screen clear skipped because debug mode is active")
    clear_screen(CLEAR_SCREEN and not keep_terminal_history() and not DEBUG_MODE)

    print_startup_banner()

    parser = argparse.ArgumentParser(
        prog="psn_monitor",
        description=("Monitor a PSN user's playing status and send customizable email or webhook alerts [ https://github.com/misiektoja/psn_monitor/ ]"), formatter_class=argparse.RawTextHelpFormatter,
        epilog=help_examples(),
        **argparse_color_kwargs()
    )

    # Positional
    parser.add_argument(
        "psn_user_id",
        nargs="?",
        metavar="PSN_USER_ID",
        help="User's PSN ID",
        type=str
    )

    # Version, just to list in help, it is handled earlier
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s v{VERSION}"
    )

    # Configuration & dotenv files
    conf = parser.add_argument_group("Configuration & dotenv files")
    conf.add_argument(
        "--config-file",
        dest="config_file",
        metavar="PATH",
        help="Location of the optional config file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--generate-config",
        nargs="?",
        const=True,
        metavar="FILENAME",
        help="Print default config template and exit (on Windows PowerShell, specify a filename to avoid redirect encoding issues)",
    )
    conf.add_argument(
        "--setup",
        dest="setup",
        action="store_true",
        help="Run the guided setup and write a ready-to-run configuration"
    )
    conf.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help="Let --generate-config replace an existing file, after a timestamped backup"
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--set-npsso",
        dest="set_npsso",
        action="store_true",
        help="Enter an NPSSO code privately, check it against PSN and save it to the dotenv file",
    )
    conf.add_argument(
        "--set-smtp-password",
        dest="set_smtp_password",
        action="store_true",
        help="Enter the SMTP password privately, check it against the mail server and save it to the dotenv file",
    )
    conf.add_argument(
        "--set-webhook-url",
        dest="set_webhook_url",
        action="store_true",
        help="Save a Discord or ntfy webhook URL through a hidden prompt",
    )
    conf.add_argument(
        "--doctor",
        dest="doctor",
        action="store_true",
        help="Run read-only preflight checks and report what is ready and what is not",
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

    notify = parser.add_argument_group("Email notifications")
    notify.add_argument(
        "-a", "--notify-active-inactive",
        dest="notify_active_inactive",
        action="store_true",
        default=None,
        help="Email when user goes online/offline"
    )
    notify.add_argument(
        "-g", "--notify-game-change",
        dest="notify_game_change",
        action="store_true",
        default=None,
        help="Email on game start/change/stop"
    )
    notify.add_argument(
        "-e", "--no-error-notify",
        dest="notify_errors",
        action="store_false",
        default=None,
        help="Disable email on errors (e.g. invalid NPSSO)"
    )
    notify.add_argument(
        "--send-test-email",
        dest="send_test_email",
        action="store_true",
        help="Send test email to verify SMTP settings"
    )

    webhook = parser.add_argument_group("Webhook notifications")
    webhook_toggle = webhook.add_mutually_exclusive_group()
    webhook_toggle.add_argument(
        "--webhook",
        dest="webhook_enabled",
        action="store_true",
        default=None,
        help="Enable the configured webhook alerts"
    )
    webhook_toggle.add_argument(
        "--no-webhook",
        dest="webhook_enabled",
        action="store_false",
        default=None,
        help="Disable the configured webhook alerts"
    )
    webhook.add_argument(
        "--webhook-url",
        dest="webhook_url",
        metavar="URL",
        type=str,
        help="Discord webhook or ntfy topic URL for this run (may stay in shell history, prefer --set-webhook-url)"
    )
    webhook.add_argument(
        "--webhook-provider",
        dest="webhook_provider",
        choices=("discord", "ntfy"),
        help="Webhook request format for this run (default: configured provider)"
    )
    webhook.add_argument(
        "--webhook-active-inactive",
        dest="webhook_active_inactive",
        action="store_true",
        default=None,
        help="Send a webhook alert when user goes online/offline"
    )
    webhook.add_argument(
        "--webhook-game-change",
        dest="webhook_game_change",
        action="store_true",
        default=None,
        help="Send a webhook alert on game start/change/stop"
    )
    webhook_error_toggle = webhook.add_mutually_exclusive_group()
    webhook_error_toggle.add_argument(
        "--webhook-errors",
        dest="webhook_errors",
        action="store_true",
        default=None,
        help="Send a webhook alert on errors"
    )
    webhook_error_toggle.add_argument(
        "--no-webhook-error-notify",
        dest="webhook_errors",
        action="store_false",
        default=None,
        help="Disable webhook alerts on errors"
    )
    webhook.add_argument(
        "--send-test-webhook",
        dest="send_test_webhook",
        action="store_true",
        help="Send one test webhook without starting monitoring"
    )
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
        help="Polling interval when user is online"
    )

    # Features & Output
    info = parser.add_argument_group("User information & listing")
    info.add_argument(
        "-i", "--info",
        dest="info_mode",
        action="store_true",
        help="Get detailed user information and display it, then exit"
    )
    info.add_argument(
        "--trophies",
        dest="include_trophies",
        action="store_true",
        help="Show trophy summary and last earned trophies (only works with -i/--info)"
    )
    info.add_argument(
        "--no-recent-games",
        dest="no_recent_games",
        action="store_true",
        help="Don't fetch recently played games list (only works with -i/--info)"
    )

    # Intervals & timers
    opts = parser.add_argument_group("Features & output")
    opts.add_argument(
        "-b", "--csv-file",
        dest="csv_file",
        metavar="CSV_FILENAME",
        type=str,
        help="Write status & game changes to CSV"
    )
    opts.add_argument(
        "--status-file",
        dest="status_file",
        metavar="PATH",
        type=str,
        help="File to save the last seen status to (default: psn_<psn_user_id>_last_status.json)"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        default=None,
        help="Disable logging to psn_monitor_<psn_user_id>.log"
    )
    opts.add_argument(
        "--truncate",
        dest="truncate",
        metavar="N",
        type=int,
        help="Max characters per screen line (not log), use 999 to auto-detect terminal width, ignored if -d is set"
    )
    opts.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        default=None,
        help="Disable coloured output in the terminal"
    )
    opts.add_argument(
        "--verbose",
        dest="verbose_mode",
        action="store_true",
        default=None,
        help="Show rare operational events and the complete startup summary"
    )
    opts.add_argument(
        "--debug",
        dest="debug_mode",
        action="store_true",
        default=None,
        help="Enable debug mode for technical logging"
    )

    args = parser.parse_args()

    # Applied before the config file is read, so a failure while reading it is already diagnosable
    apply_diagnostic_cli_overrides(args)

    # "none" is the documented sentinel that switches discovery off, so it is a selection rather than a missing file
    CONFIG_DISCOVERY_DISABLED = args.config_file is not None and str(args.config_file).casefold() == "none"
    if CONFIG_DISCOVERY_DISABLED:
        CLI_CONFIG_PATH = None
    elif args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = None if CONFIG_DISCOVERY_DISABLED else find_config_file(CLI_CONFIG_PATH)

    # Doctor reports a broken setup instead of exiting on the first thing it finds, so the whole report is usable
    doctor_mode = bool(args.doctor)
    config_advice = None

    if not cfg_path and CLI_CONFIG_PATH:
        config_advice = classify_recovery_error(context="config.missing", detail=f"Config file '{CLI_CONFIG_PATH}' does not exist")
        # Setup is how that file gets created, so a missing --config-file path is its destination, not a failure
        if not doctor_mode and not args.setup:
            print_recovery_advice(config_advice)
            sys.exit(1)

    if cfg_path:
        reported_advice = []
        if not load_config_file(cfg_path, report_errors=not doctor_mode, advice_out=reported_advice):
            if not doctor_mode:
                sys.exit(1)
            config_advice = reported_advice[0]
            cfg_path = None

    # Applied again, so a saved VERBOSE_MODE or DEBUG_MODE cannot switch off a flag the user just typed
    apply_diagnostic_cli_overrides(args)

    apply_tls_verification_setting()

    if args.no_color is True:
        COLORED_OUTPUT = False

    # Re-initialised so a COLORED_OUTPUT or COLOR_THEME from the config file takes effect before the welcome
    # screen, the setup wizard or doctor print anything, with --no-color still winning over both
    init_color_output(stdout_bck)

    # A PSN ID given on the command line always wins over the saved one
    if not args.psn_user_id and PSN_USER_ID:
        args.psn_user_id = PSN_USER_ID
        debug_print("PSN user ID resolved", source="configuration file", value=args.psn_user_id)

    # Evaluated after the config file is read, so a saved PSN ID starts monitoring instead of being welcomed
    if len(sys.argv) == 1 and not args.psn_user_id:
        sys.exit(print_welcome_screen(config_file=args.config_file, env_file=args.env_file))

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    # Which secrets were already exported has to be captured before load_dotenv copies the file's values into
    # os.environ, because afterwards the two sources are indistinguishable
    EXPORTED_SECRET_KEYS = frozenset(secret for secret in SECRET_KEYS if os.getenv(secret) is not None)
    SECRET_SOURCES.clear()
    for secret in SECRET_KEYS:
        if secret_is_set(globals().get(secret)):
            record_secret_source(secret, "configuration file")

    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        try:
            from dotenv import load_dotenv, find_dotenv

            # An exported variable wins over the file at startup, matching python-dotenv's own default, so a
            # one-off secret or one injected by systemd or a container is not silently shadowed by the dotenv.
            # The SIGHUP reload still overrides, because there the edited file is exactly what must take effect.
            if DOTENV_FILE:
                env_path = DOTENV_FILE
                if not os.path.isfile(env_path):
                    # A command that is about to write this file is not warned that it is missing
                    if not command_writes_dotenv(sys.argv[1:]):
                        print(f"* Warning: dotenv file '{env_path}' does not exist\n")
                else:
                    load_dotenv(env_path, override=False)
            else:
                env_path = find_dotenv() or None
                if env_path:
                    load_dotenv(env_path, override=False)
        except ImportError:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            if env_path:
                print_recovery_advice(missing_dependency_advice("python-dotenv", f"The dotenv file '{env_path}' was not loaded"), label="Warning")
                print()

    apply_environment_secrets()

    apply_webhook_cli_overrides(args, parser)

    timezone_advice = resolve_local_timezone()

    if timezone_advice is not None:
        if not doctor_mode:
            print_recovery_advice(timezone_advice)
            sys.exit(1)
        # The report still stamps timestamps, so it falls back rather than stopping before the diagnosis
        LOCAL_TIMEZONE = "UTC"

    # The command-line credential has to be in effect before the report checks it and before the trace reports it
    if args.npsso_key:
        PSN_NPSSO = args.npsso_key
        record_secret_source("PSN_NPSSO", "command line", PSN_NPSSO)

    # Traced here rather than at each layer, so the line reports the value that survived every later override
    resolved_secrets = {secret: SECRET_SOURCES[secret] for secret in SECRET_KEYS if secret in SECRET_SOURCES}
    for secret, source in resolved_secrets.items():
        debug_print("Secret resolution", name=secret, source=source, **secret_fields(globals().get(secret), secret))
    if not resolved_secrets:
        debug_print("No private settings were resolved from config, dotenv, environment or the command line")

    if doctor_mode:
        doctor_exit = run_doctor(args.psn_user_id, cfg_path, env_path, config_advice, timezone_advice)
        # A target the config file already carries is left out, so the command stays as short as the wizard's
        print_doctor_next_steps(args.psn_user_id, PSN_USER_ID, doctor_exit)
        sys.exit(doctor_exit)

    if args.setup:
        sys.exit(run_setup_wizard(initial_target=args.psn_user_id, config_file=args.config_file, env_file=args.env_file))

    if not check_internet():
        sys.exit(1)

    if args.set_npsso:
        try:
            run_set_npsso(env_file=env_path, config_path=cfg_path, psn_user_id=args.psn_user_id)
        except Exception as exc:
            print_recovery_error(exc, context="secret.entry")
            sys.exit(1)
        sys.exit(0)

    if args.set_smtp_password:
        try:
            run_set_smtp_password(env_file=env_path, config_path=cfg_path, psn_user_id=args.psn_user_id)
        except Exception as exc:
            print_recovery_error(exc, context="secret.entry")
            sys.exit(1)
        sys.exit(0)

    if args.set_webhook_url:
        try:
            run_set_webhook_url(env_file=env_path, config_path=cfg_path, psn_user_id=args.psn_user_id)
        except Exception as exc:
            print_recovery_error(exc, context="secret.entry")
            sys.exit(1)
        sys.exit(0)

    if args.send_test_email:
        # Checked before the attempt is announced, so a mail server that was never usable is not reported as a failed send
        settings_advice = validate_smtp_settings()
        if settings_advice is not None:
            print_recovery_advice(settings_advice)
            sys.exit(1)
        print("* Sending test email notification ...\n")
        if send_email("psn_monitor: test email", "This test email was sent by --send-test-email. Your SMTP settings work.", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if args.send_test_webhook:
        if not validate_webhook_url():
            print_recovery_error(context="webhook", detail="WEBHOOK_URL must contain a complete HTTPS link")
            sys.exit(1)
        print(f"* Sending test webhook notification through {webhook_provider_display_name()} to {webhook_destination_host()} ...\n")
        # Forced past the alert settings, because the point of the test is the destination, not the choices
        if send_webhook("psn_monitor: test webhook", "This test notification was sent by --send-test-webhook. Your webhook settings work.", "status", force=True) == 0:
            print("* Webhook sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if not args.psn_user_id:
        print_recovery_error(context="target.missing", detail="PSN_USER_ID needs to be defined")
        sys.exit(1)

    if not PSN_NPSSO or PSN_NPSSO == "your_psn_npsso_code":
        print_recovery_error(context="secret.missing", detail="PSN_NPSSO (-n / --npsso_key) value is empty or incorrect")
        sys.exit(1)

    if args.info_mode:
        include_trophies = args.include_trophies if hasattr(args, 'include_trophies') and args.include_trophies else False
        show_recent_games = not (hasattr(args, 'no_recent_games') and args.no_recent_games)
        get_user_info(args.psn_user_id, include_trophies=include_trophies, show_recent_games=show_recent_games)
        sys.exit(0)

    if args.check_interval:
        PSN_CHECK_INTERVAL = args.check_interval

    # The interval can come from a config file, so the reminder is settled once every layer has been applied
    LIVENESS_REMINDER_SECONDS = LIVENESS_CHECK_INTERVAL if LIVENESS_CHECK_INTERVAL > 0 else 0

    if args.active_interval:
        PSN_ACTIVE_CHECK_INTERVAL = args.active_interval

    if args.status_file:
        PSN_STATUS_FILE = os.path.expanduser(args.status_file)
    elif PSN_STATUS_FILE:
        PSN_STATUS_FILE = os.path.expanduser(PSN_STATUS_FILE)

    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    else:
        if CSV_FILE:
            CSV_FILE = os.path.expanduser(CSV_FILE)

    if CSV_FILE:
        try:
            with open(CSV_FILE, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            print_recovery_error(e, context="file.unwritable", detail=f"CSV file '{CSV_FILE}' cannot be opened for writing: {e}")
            sys.exit(1)

    try:
        ascii_log_separators_enabled()
    except ValueError as e:
        print_recovery_error(context="config.invalid", detail=str(e))
        sys.exit(1)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    TRUNCATE_CHARS = resolve_truncate_chars(args.truncate, TRUNCATE_CHARS, DISABLE_LOGGING)

    if not DISABLE_LOGGING:
        log_path = resolve_log_path(args.psn_user_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        FINAL_LOG_PATH = str(log_path)
        sys.stdout = Logger(FINAL_LOG_PATH)
        debug_print("Logging output", path=FINAL_LOG_PATH)
    else:
        FINAL_LOG_PATH = None

    if args.notify_active_inactive is True:
        ACTIVE_INACTIVE_NOTIFICATION = True

    if args.notify_game_change is True:
        GAME_CHANGE_NOTIFICATION = True

    if args.notify_errors is False:
        ERROR_NOTIFICATION = False

    if SMTP_HOST.startswith("your_smtp_server_"):
        verbose_print("Email notifications are off because SMTP_HOST is still the shipped placeholder")
        ACTIVE_INACTIVE_NOTIFICATION = False
        GAME_CHANGE_NOTIFICATION = False
        ERROR_NOTIFICATION = False

    if WEBHOOK_ENABLED and not validate_webhook_url():
        verbose_print("Webhook notifications are off because WEBHOOK_URL is not a complete HTTPS link")
        WEBHOOK_ENABLED = False

    emit_startup_summary(build_startup_summary(args.psn_user_id, cfg_path, env_path, FINAL_LOG_PATH), full_startup_summary_enabled())

    # The summary block already ended with one blank line, so this heading starts at the cursor
    out = f"Monitoring user with PSN ID {args.psn_user_id}"
    print(out)
    print("─" * len(out))

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_game_change_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)
        signal.signal(signal.SIGHUP, reload_secrets_signal_handler)

    psn_monitor_user(args.psn_user_id, CSV_FILE)

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()
