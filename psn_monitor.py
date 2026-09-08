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
"""

VERSION = "1.9"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
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
LIVENESS_CHECK_INTERVAL = 43200  # 12 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://ca.account.sony.com/'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# CSV file to write all status & game changes
# Can also be set using the -b flag
CSV_FILE = ""

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

# Value used by signal handlers increasing/decreasing the check for player activity
# when user is online (PSN_ACTIVE_CHECK_INTERVAL); in seconds
PSN_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds
"""

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Default dummy values so linters shut up
# Do not change values below - modify them in the configuration section or config file instead
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
PSN_CHECK_INTERVAL = 0
PSN_ACTIVE_CHECK_INTERVAL = 0
LOCAL_TIMEZONE = ""
OFFLINE_INTERRUPT = 0
LIVENESS_CHECK_INTERVAL = 0
CHECK_INTERNET_URL = ""
CHECK_INTERNET_TIMEOUT = 0
CSV_FILE = ""
DOTENV_FILE = ""
PSN_LOGFILE = ""
DISABLE_LOGGING = False
ASCII_LOG_SEPARATORS = "Auto"
VERBOSE_MODE = False
DEBUG_MODE = False
TRUNCATE_CHARS = 0
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
PSN_ACTIVE_CHECK_SIGNAL_VALUE = 0

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "psn_monitor.conf"

# List of secret keys to load from env/config
SECRET_KEYS = ("PSN_NPSSO", "SMTP_PASSWORD")

# Records where each secret was finally resolved from, filled in as the documented precedence is applied.
# The winning source cannot be reconstructed afterwards, because the same key may sit in several places
SECRET_SOURCES = {}

# Secret keys that were already exported when the tool started, so a dotenv file cannot be credited for them
EXPORTED_SECRET_KEYS = frozenset()

# Default value for timeouts in alarm signal handler; in seconds
FUNCTION_TIMEOUT = 15

LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / PSN_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name']

CLI_CONFIG_PATH = None

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
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
try:
    from psnawp_api import PSNAWP
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the PSNAWP library !\n\nTo install it, run:\n    pip3 install PSNAWP\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://github.com/isFakeAccount/psnawp")
import importlib.util
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


# Probes the PSN OAuth endpoint with the given npsso and returns a specific error hint if the redirect carries a recognizable error such as ToSUA re-acceptance, otherwise None
def probe_npsso_auth_error(npsso):
    try:
        import uuid
        from urllib.parse import urlparse, parse_qs
        from psnawp_api.core.authenticator import Authenticator
        from psnawp_api.utils.endpoints import BASE_PATH, API_PATH
    except Exception as diag_exc:
        debug_print(f"Auth probe unavailable, PSNAWP internals could not be imported: {type(diag_exc).__name__}: {diag_exc}")
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
        debug_print(f"HTTP GET {BASE_PATH['base_uri']}{API_PATH['oauth_code']} (auth probe, timeout 15s)")
        resp = req.get(f"{BASE_PATH['base_uri']}{API_PATH['oauth_code']}", headers=headers, params=params, allow_redirects=False, timeout=15)
        debug_print(f"Auth probe returned HTTP {resp.status_code}")
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
        debug_print(f"Auth probe against the PSN OAuth endpoint failed: {type(diag_exc).__name__}: {diag_exc}")
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
GUIDE_BASE_URL = "https://github.com/misiektoja/psn_monitor/blob/main/README.md"
INSTALLATION_GUIDE_URL = f"{GUIDE_BASE_URL}#installation"
QUICK_START_GUIDE_URL = f"{GUIDE_BASE_URL}#quick-start"
CONFIG_GUIDE_URL = f"{GUIDE_BASE_URL}#configuration-file"
NPSSO_GUIDE_URL = f"{GUIDE_BASE_URL}#psn-npsso-code"
SECRETS_GUIDE_URL = f"{GUIDE_BASE_URL}#storing-secrets"
PRIVACY_GUIDE_URL = f"{GUIDE_BASE_URL}#user-privacy-settings"
TIMEZONE_GUIDE_URL = f"{GUIDE_BASE_URL}#time-zone"
SMTP_GUIDE_URL = f"{GUIDE_BASE_URL}#smtp-settings"
INTERVALS_GUIDE_URL = f"{GUIDE_BASE_URL}#check-intervals"
DIAGNOSTICS_GUIDE_URL = f"{GUIDE_BASE_URL}#verbose-and-debug-output"

# Installs this tool can be running from. There is no container image, so no container method is detected
INSTALL_METHODS = ("pip", "manual")


# Returns whether this process was started from the packaged entry point or from a downloaded script
def detect_install_method():
    return "manual" if os.path.basename(sys.argv[0] or "").endswith(".py") else "pip"


# Returns a readable name for one install method
def install_method_display_name(method=None):
    return {"pip": "PyPI install", "manual": "downloaded script"}.get(method or detect_install_method(), "unknown install")


# Renders command arguments quoted for the shell of the host operating system
def render_command(arguments):
    values = [str(argument) for argument in arguments]
    return subprocess.list2cmdline(values) if platform.system() == "Windows" else shlex.join(values)


# Returns the bare command that starts this tool on the detected install, without arguments
def tool_command_prefix(method=None):
    if (method or detect_install_method()) == "manual":
        return render_command([("python" if platform.system() == "Windows" else "python3"), Path(__file__).name])
    return "psn_monitor"


# Returns a complete, copy-pasteable command line for this tool with every argument quoted for the host shell
def tool_command(*arguments, method=None):
    return " ".join([tool_command_prefix(method), *[render_command([argument]) for argument in arguments]])


# Stable recovery categories. Every code here is produced somewhere in this file, and nothing else is accepted
RECOVERY_CODES = frozenset({
    "config.missing", "config.invalid", "dependency.missing", "secret.missing",
    "auth.npsso_invalid", "auth.npsso_expired", "auth.tos_required",
    "network.unavailable", "network.timeout",
    "psn.malformed_response", "psn.rate_limited", "resource.exhausted",
    "target.missing", "target.not_found", "target.not_visible",
    "smtp.invalid", "smtp.authentication", "smtp.connection",
    "file.unreadable", "file.unwritable", "unknown",
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


# Returns the command that installs one optional library into the interpreter running this tool
def pip_install_command(requirement):
    return render_command([sys.executable or "python3", "-m", "pip", "install", requirement])


# Returns advice for an optional library that is missing, naming the exact install command for this interpreter
def missing_dependency_advice(package, effect, alternative=""):
    fix = f"Install it with: {pip_install_command(package)}"
    if alternative:
        fix = f"{fix}. {alternative}"
    return make_recovery_advice("dependency.missing", f"{effect} because the optional '{package}' library is missing", recovery_fix_with_guide(fix, INSTALLATION_GUIDE_URL), False)


# Returns install-aware guidance for replacing the NPSSO code, which differs once monitoring has started
def npsso_recovery_fix(monitoring=False):
    command = f"{tool_command_prefix()} <psn_user_id> -n <npsso_code>"
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
        debug_print(f"requests exception types unavailable, transient error detection is reduced: {type(diag_exc).__name__}: {diag_exc}")
    try:
        from psnawp_api.core.psnawp_exceptions import PSNAWPAuthenticationError, PSNAWPForbiddenError, PSNAWPInvalidTokenError, PSNAWPNotFoundError, PSNAWPTooManyRequestsError, PSNAWPUnauthorizedError
        types["auth"].extend((PSNAWPAuthenticationError, PSNAWPUnauthorizedError, PSNAWPInvalidTokenError))
        types["not_found"].append(PSNAWPNotFoundError)
        types["forbidden"].append(PSNAWPForbiddenError)
        types["rate_limited"].append(PSNAWPTooManyRequestsError)
    except Exception as diag_exc:
        debug_print(f"PSNAWP exception types unavailable, PSN errors fall back to text matching: {type(diag_exc).__name__}: {diag_exc}")
    return {name: tuple(values) for name, values in types.items()}


# Classifies a failure by exception type, then by message, without contacting PSN
def classify_recovery_error_offline(error=None, context="runtime", detail=""):
    safe_detail = sanitize_error_text(detail or error or "")
    message = str(detail or error or "").lower()
    monitoring = context == "monitor"

    if error is not None and is_too_many_open_files(error):
        # Repeated auth refreshes against an expired NPSSO are a common way to reach the limit, so say so
        npsso_note = " This can also be a side effect of repeated PSN auth refreshes, so check your NPSSO code once the limit is raised." if ("oauth/token" in message or "authz" in message or "npsso" in message) else ""
        return make_recovery_advice("resource.exhausted", "This process ran out of file descriptors, which is a local limit and not a PlayStation Network problem", recovery_fix_with_guide(f"Raise the file descriptor limit, for example with 'ulimit -n 4096', or set LimitNOFILE= if you run under systemd, then restart the tool.{npsso_note}", DIAGNOSTICS_GUIDE_URL), False, safe_detail)

    if context == "config.missing":
        return make_recovery_advice("config.missing", safe_detail or "The configuration file was not found", recovery_fix_with_guide(f"Check the --config-file path, or create one with: {tool_command('--generate-config', 'psn_monitor.conf')}", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "config.invalid":
        return make_recovery_advice("config.invalid", safe_detail or "The configuration file could not be loaded", recovery_fix_with_guide(f"Config files are read as data. Only documented SETTING = value lines with plain literal values are accepted. Correct the reported line, or generate a fresh file with: {tool_command('--generate-config', 'psn_monitor.conf')}", CONFIG_GUIDE_URL), False, safe_detail)

    if context == "secret.missing":
        return make_recovery_advice("secret.missing", safe_detail or "A required credential is missing", recovery_fix_with_guide(npsso_recovery_fix(), SECRETS_GUIDE_URL), False, safe_detail)

    if context == "target.missing":
        return make_recovery_advice("target.missing", safe_detail or "No PlayStation ID was given", recovery_fix_with_guide(f"Pass the PlayStation ID of the account to watch: {tool_command_prefix()} <psn_user_id>", QUICK_START_GUIDE_URL), False, safe_detail)

    if context == "smtp.settings":
        return make_recovery_advice("smtp.invalid", f"The SMTP settings are incorrect: {safe_detail}" if safe_detail else "The SMTP settings are incorrect", recovery_fix_with_guide(f"Check SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL and RECEIVER_EMAIL then run: {tool_command('--send-test-email')}", SMTP_GUIDE_URL), False, safe_detail)

    if context == "file.unreadable":
        return make_recovery_advice("file.unreadable", safe_detail or "A file the tool needs could not be read", recovery_fix_with_guide("Check that the path exists and that this user can read it, then retry", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    if context == "file.unwritable":
        return make_recovery_advice("file.unwritable", safe_detail or "A file the tool needs could not be written", recovery_fix_with_guide("Check that the directory exists, that this user can write to it and that there is free space, then retry", DIAGNOSTICS_GUIDE_URL), True, safe_detail)

    types = recovery_exception_types()

    if context.startswith("smtp"):
        for current in iter_exc_chain(error):
            if isinstance(current, smtplib.SMTPAuthenticationError):
                return make_recovery_advice("smtp.authentication", "The SMTP server rejected the login", recovery_fix_with_guide(f"Check SMTP_USER and SMTP_PASSWORD. Providers such as Gmail need an app password rather than the account password. Then run: {tool_command('--send-test-email')}", SMTP_GUIDE_URL), False, safe_detail)
            if isinstance(current, smtplib.SMTPException) or isinstance(current, types["timeout"]) or isinstance(current, types["unavailable"]) or isinstance(current, (ssl.SSLError, OSError)):
                return make_recovery_advice("smtp.connection", "The SMTP server could not be reached", recovery_fix_with_guide(f"Check SMTP_HOST, SMTP_PORT and SMTP_SSL, and that the port is not blocked. Then run: {tool_command('--send-test-email')}", SMTP_GUIDE_URL), True, safe_detail)

    for current in iter_exc_chain(error):
        if isinstance(current, PsnMalformedResponse):
            return make_recovery_advice("psn.malformed_response", "PlayStation Network returned a presence response in an unexpected shape", recovery_fix_with_guide("Nothing to do in most cases, the tool rebuilds its session and retries. If it continues, upgrade PSNAWP and rerun with --debug", DIAGNOSTICS_GUIDE_URL), True, safe_detail)
        if types["rate_limited"] and isinstance(current, types["rate_limited"]):
            return make_recovery_advice("psn.rate_limited", "PlayStation Network is rate limiting this account", recovery_fix_with_guide("Raise PSN_CHECK_INTERVAL and PSN_ACTIVE_CHECK_INTERVAL, or run fewer instances against the same account, then restart", INTERVALS_GUIDE_URL), True, safe_detail)
        if types["not_found"] and isinstance(current, types["not_found"]):
            return make_recovery_advice("target.not_found", "PlayStation Network does not know that PlayStation ID", recovery_fix_with_guide("Check the spelling of the PlayStation ID. It is the online ID, not the account e-mail or the real name", QUICK_START_GUIDE_URL), False, safe_detail)
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

    return make_recovery_advice("unknown", "Something unexpected went wrong", recovery_fix_with_guide("Rerun with --debug and check the technical detail it prints. If the problem continues, open an issue with that output", DIAGNOSTICS_GUIDE_URL), True, safe_detail)


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
        if (DEBUG_MODE if debug is None else debug) and advice.detail:
            lines.append(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return "\n".join(lines)


# Prints advice in full the first time its category appears and as one line while the same category persists
def print_recovery_advice(advice, tracker=None, retry_note="", debug=None, label="Error"):
    print(render_recovery_advice(advice, debug, retry_note, tracker is None or tracker.should_render(advice), label))


# Classifies a failure, prints the advice and returns it so the caller can reuse the same wording
def report_recovery_error(error=None, context="runtime", detail="", probe_auth=False, tracker=None, retry_note="", debug=None, label="Error"):
    advice = classify_recovery_error(error, context, detail, probe_auth)
    print_recovery_advice(advice, tracker, retry_note, debug, label)
    return advice


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


# Returns every redactable secret value currently known to the process, longest first so overlaps redact fully
def known_secret_values():
    values = [value for key in SECRET_KEYS for value in (globals().get(key),) if secret_is_set(value) and len(value) >= MIN_REDACTABLE_SECRET_LENGTH]
    return sorted(set(values), key=len, reverse=True)


# Redacts credentials and secret-bearing assignments from arbitrary text before it is shown, logged or emailed
def sanitize_error_text(value):
    text = str(value or "")
    for secret in known_secret_values():
        text = text.replace(secret, "<redacted>")
    patterns = (
        (r"(?m)(\b(?:PSN_NPSSO|SMTP_PASSWORD)\b\s*=\s*).*$", r"\1<redacted>"),
        (r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?bearer\s+)[^\s,;'\"}]+", r"\1<redacted>"),
        (r"(?i)(['\"]?(?:npsso|access_token|refresh_token|smtp_password)['\"]?\s*[:=]\s*['\"]?)[^\s,;'\"}]+", r"\1<redacted>"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


# Describes a secret in diagnostic output without revealing any part of it
def secret_fingerprint(value):
    return f"set, {len(value)} chars" if secret_is_set(value) else "not set"


# Prints a technical diagnostic line, shown only when debug mode is on
def debug_print(message):
    if DEBUG_MODE:
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] {sanitize_error_text(message)}")


# Prints a rare operational event, shown only when verbose mode is on
def verbose_print(message):
    if VERBOSE_MODE:
        print(f"* {sanitize_error_text(message)}")


# Applies the diagnostic flags that were actually typed, leaving the rest to the config file
def apply_diagnostic_cli_overrides(args):
    global VERBOSE_MODE, DEBUG_MODE
    if args.verbose_mode is not None:
        VERBOSE_MODE = args.verbose_mode
    if args.debug_mode is not None:
        DEBUG_MODE = args.debug_mode


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


# Sanitizing stdout wrapper installed before the logging policy is known, so early output is covered too
class TerminalStream(object):
    # Stores the wrapped terminal stream
    def __init__(self, stream):
        self.terminal = stream

    # Writes one sanitized message to the wrapped terminal
    def write(self, message):
        self.terminal.write(sanitize_terminal_text(message))
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
        # The early sanitizing stream is unwrapped so sanitizing happens exactly once. Writing through it would
        # sanitize every line twice, and it would leave two layers to keep in step once colouring is added
        self.terminal = unwrap_terminal_stream(sys.stdout)
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        message = sanitize_terminal_text(message)
        # The log file stays plain text, so colour codes are stripped and tabs expanded before it is written
        self.logfile.write(normalize_log_separators(ANSI_ESCAPE_RE.sub("", message).expandtabs(8)))
        # Truncation runs on the text as displayed, so escape sequences never count toward the visible width
        if TRUNCATE_CHARS:
            message = truncate_string_per_line(message, TRUNCATE_CHARS)
        self.terminal.write(message)
        self.terminal.flush()
        self.logfile.flush()

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


# Checks internet connectivity
def check_internet(url=CHECK_INTERNET_URL, timeout=CHECK_INTERNET_TIMEOUT):
    debug_print(f"HTTP GET {url} (connectivity check, timeout {timeout}s)")
    try:
        _ = req.get(url, timeout=timeout)
        debug_print(f"HTTP GET {url} succeeded")
        return True
    except req.RequestException as e:
        debug_print(f"HTTP GET {url} failed: {type(e).__name__}: {e}")
        report_recovery_error(e, context="startup", detail=f"The connectivity check to {url} failed: {e}")
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
    except Exception as e:
        debug_print(f"Clearing the screen failed: {type(e).__name__}: {e}")
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
        except Exception as diag_exc:
            debug_print(f"Cannot parse the first timestamp as a date, timespan reported as empty: {type(diag_exc).__name__}: {diag_exc}")
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
            debug_print(f"Cannot parse the second timestamp as a date, timespan reported as empty: {type(diag_exc).__name__}: {diag_exc}")
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


# Returns advice for the first unusable SMTP server setting, or None when they are all present and valid
def validate_smtp_settings():
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')
    reason = ""

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            reason = "SMTP_HOST is not a valid IP address or hostname"

    if not reason:
        try:
            port = int(SMTP_PORT)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            reason = "SMTP_PORT is not a port number between 1 and 65535"

    if not reason and (not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL))):
        reason = "SENDER_EMAIL or RECEIVER_EMAIL is not an email address"

    if not reason and (not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password"):
        reason = "SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder"

    return classify_recovery_error(context="smtp.settings", detail=reason) if reason else None


# Sends email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    settings_advice = validate_smtp_settings()
    if settings_advice is not None:
        print_recovery_advice(settings_advice)
        return 1

    if not subject or not isinstance(subject, str):
        report_recovery_error(context="smtp.settings", detail="the message subject is empty")
        return 1

    if not body and not body_html:
        report_recovery_error(context="smtp.settings", detail="the message body is empty")
        return 1

    # Game and profile names taken from PSN reach the message, so control sequences are removed before a mail
    # client renders them. A terminal is not the only thing that acts on them
    subject = plain_text(subject)
    body = plain_text(body)

    debug_print(f"SMTP connect {SMTP_HOST}:{SMTP_PORT} (starttls={bool(use_ssl)}, timeout {smtp_timeout}s, user {SMTP_USER})")
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
        report_recovery_error(e, context="smtp", detail=f"Sending the notification to {RECEIVER_EMAIL} failed: {e}")
        return 1
    # Reported separately from the "Sending email notification" line, which only records the attempt
    verbose_print(f"Email delivered to {RECEIVER_EMAIL}: {subject}")
    debug_print(f"SMTP delivery finished for {RECEIVER_EMAIL}")
    return 0


# Initializes the CSV file
def init_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
    except Exception as e:
        debug_print(f"CSV file '{csv_file_name}' could not be initialized: {type(e).__name__}: {e}")
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")
    debug_print(f"CSV file '{csv_file_name}' is ready for writing")


# Writes CSV entry
def write_csv_entry(csv_file_name, timestamp, status, game_name):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Date': timestamp, 'Status': status, 'Game name': plain_text(game_name)})

    except Exception as e:
        debug_print(f"CSV write to '{csv_file_name}' failed: {type(e).__name__}: {e}")
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")
    debug_print(f"CSV entry written to '{csv_file_name}': {status} | {game_name or 'no game'}")


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
        debug_print(f"Cannot parse ISO timestamp '{dt_str}': {type(diag_exc).__name__}: {diag_exc}")
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
            debug_print(f"Cannot parse timestamp '{ts}' for the full date format: {type(diag_exc).__name__}: {diag_exc}")
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
            debug_print(f"Cannot parse timestamp '{ts}' for the short date format: {type(diag_exc).__name__}: {diag_exc}")
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
            debug_print(f"Cannot parse timestamp '{ts}' for the time format: {type(diag_exc).__name__}: {diag_exc}")
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

    if env_path:
        for secret in SECRET_KEYS:
            old_val = globals().get(secret)
            val = os.getenv(secret)
            if val is not None and val != old_val:
                globals()[secret] = val
                SECRET_SOURCES[secret] = "dotenv file"
                debug_print(f"{secret} reloaded from '{env_path}' ({secret_fingerprint(val)})")
                print(f"* Reloaded {secret} from {env_path}")

    print_cur_ts("Timestamp:\t\t\t")


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
        debug_print(f"Looking for a config file at '{p}'")
        if p.is_file():
            return str(p)
    return None


# Settings an older version wrote that this version no longer defines, ignored instead of rejected
RETIRED_CONFIG_SETTINGS = frozenset(())


# Collects the setting names the built-in configuration template defines
def _config_allowed_names():
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    return frozenset(statement.targets[0].id for statement in template_tree.body if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name))


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
        debug_print(f"Config file '{config_path}' applied {len(parsed_values)} settings: {', '.join(sorted(parsed_values)) or 'none'}")
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
    debug_print(f"Config file '{config_path}' rejected: {detail}")
    advice = classify_recovery_error(context="config.invalid", detail=detail)
    if advice_out is not None:
        advice_out.append(advice)
    if report_errors:
        print_recovery_advice(advice)
    return False


# Resolves an executable path by checking if it's a valid file or searching in $PATH
def resolve_executable(path):
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path

    found = shutil.which(path)
    if found:
        return found

    raise FileNotFoundError(f"Could not find executable '{path}'")


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
        debug_print(f"PSNAWP PlatformType is unavailable, falling back to string platform names: {type(diag_exc).__name__}: {diag_exc}")
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
                        debug_print(f"Cannot read attribute '{attr}' while looking for a title name: {type(diag_exc).__name__}: {diag_exc}")
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
            debug_print(f"PSN API trophy_groups() failed for {npcomm}: {type(diag_exc).__name__}: {diag_exc}")

        # B) per-title summary
        if not name:
            try:
                summ = psn_user.trophy_summary(np_communication_id=npcomm, platform=platform)
                name = _first_name_like(summ)
            except Exception as diag_exc:
                debug_print(f"PSN API trophy_summary() failed for {npcomm}: {type(diag_exc).__name__}: {diag_exc}")

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
                debug_print(f"PSN API trophy_titles() failed while resolving the name of {npcomm}: {type(diag_exc).__name__}: {diag_exc}")

        if not name:
            name = npcomm  # last resort

        _title_name_cache[key] = name
        return name
    # -------------------------------------

    items = []

    # 1) list titles (no special args for cross-version compat)
    debug_print(f"PSN API trophy_titles(limit={title_limit})")
    try:
        titles_iter = psn_user.trophy_titles(limit=title_limit)
    except Exception as diag_exc:
        debug_print(f"PSN API trophy_titles() failed, no trophy titles to scan: {type(diag_exc).__name__}: {diag_exc}")
        titles_iter = []

    for tt in titles_iter:
        npcomm = _get(tt, "np_communication_id", "npCommunicationId", default=None)
        if not npcomm:
            continue

        for plat in _platforms_to_try(tt):
            debug_print(f"PSN API trophies() for {npcomm} on platform {plat}")
            try:
                it = psn_user.trophies(
                    np_communication_id=npcomm,
                    platform=plat,
                    include_progress=True,
                    trophy_group_id="all",
                )
            except Exception as diag_exc:
                debug_print(f"PSN API trophies() failed for {npcomm} on platform {plat}: {type(diag_exc).__name__}: {diag_exc}")
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
        debug_print(f"Trophy list could not be sorted by earn date, falling back to a tolerant sort: {type(diag_exc).__name__}: {diag_exc}")
        def _ts(dt):
            try:
                return int(dt.timestamp())
            except Exception as diag_exc:
                debug_print(f"Cannot read the earn timestamp of a trophy, sorting it last: {type(diag_exc).__name__}: {diag_exc}")
                return -1
        items.sort(key=lambda x: _ts(x[0]), reverse=True)

    for dt, game, ttype, tname in items[:max_items]:
        try:
            ts = int(dt.timestamp())
            dt_fmt = get_date_from_ts(ts)
        except Exception as diag_exc:
            debug_print(f"Cannot format the earn date of a trophy: {type(diag_exc).__name__}: {diag_exc}")
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

    debug_print(f"PSNAWP session init for PSN user '{psn_user_id}' with PSN_NPSSO {secret_fingerprint(PSN_NPSSO)}")
    print_step("Authenticating with PSN...")
    try:
        psnawp = PSNAWP(PSN_NPSSO)
        psn_user = psnawp.user(online_id=psn_user_id)
    except Exception as e:
        print()
        report_recovery_error(e, context="startup", probe_auth=True)
        sys.exit(1)
    print_ok()

    debug_print(f"PSN API profile(), friendship() and get_shareable_profile_link() for '{psn_user_id}'")
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
        report_recovery_error(e, context="startup", detail=f"Reading the PSN profile of '{psn_user_id}' failed: {e}", probe_auth=True)
        sys.exit(1)
    print_ok()

    debug_print(f"PSN API get_presence() for '{psn_user_id}'")
    print_step("Fetching presence info...")
    try:
        psn_user_presence = psn_user.get_presence()
        parse_presence(psn_user_presence)
    except Exception as e:
        print()
        report_recovery_error(e, context="startup", detail=f"Cannot get presence for user '{psn_user_id}': {e}", probe_auth=True)
        sys.exit(1)
    print_ok()

    print_step("Fetching game title info...")
    try:
        status = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("onlineStatus")

        if not status:
            print()
            report_recovery_error(PsnMalformedResponse(f"Cannot get status for user '{psn_user_id}': the presence payload carries no onlineStatus"), context="startup")
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
        report_recovery_error(e, context="startup", detail=f"Reading the game title info of '{psn_user_id}' failed: {e}")
        sys.exit(1)
    print_ok()
    print()

    psn_last_status_file = f"psn_{psn_user_id}_last_status.json"
    status_ts_old = int(time.time())

    if os.path.isfile(psn_last_status_file):
        try:
            with open(psn_last_status_file, 'r', encoding="utf-8") as f:
                last_status_read = json.load(f)
            debug_print(f"Saved status read from '{psn_last_status_file}'")
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
            debug_print(f"Cannot reconcile the saved status with the PSN profile, falling back to the last online timestamp: {type(diag_exc).__name__}: {diag_exc}")
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
        debug_print(f"Cannot read the friendship relation from the PSN profile: {type(diag_exc).__name__}: {diag_exc}")

    try:
        print(f"\nProfile URL:\t\t\t{share.get('shareUrl')}")
        # print(f"Profile QR image:\t\t{share.get('shareImageUrl')}")
    except Exception as diag_exc:
        debug_print(f"Cannot read the shareable profile link from the PSN profile: {type(diag_exc).__name__}: {diag_exc}")

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
                debug_print(f"Cannot read the saved status file '{psn_last_status_file}': {type(diag_exc).__name__}: {diag_exc}")

    # Show trophy summary and last earned trophies only if requested
    if include_trophies:
        try:
            print(f"\n* Getting trophy summary ...")
            debug_print(f"PSN API trophy_summary() for '{psn_user_id}'")
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
            debug_print(f"PSN API trophy_summary() failed, trophy level is not shown: {type(diag_exc).__name__}: {diag_exc}")

        num_trophies = 5
        try:
            print(f"\n* Getting list of last {num_trophies} earned trophies ...\n")
            print_last_earned_trophies(psn_user, max_items=num_trophies, title_limit=15)
        except Exception as diag_exc:
            debug_print(f"Cannot list the last earned trophies: {type(diag_exc).__name__}: {diag_exc}")

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
                        debug_print(f"Cannot compact the duration '{s}', keeping the original text: {type(diag_exc).__name__}: {diag_exc}")
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
            debug_print(f"PSN API title_stats(limit=10, page_size=50) for '{psn_user_id}'")
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
                debug_print(f"Cannot detect the terminal width, falling back to 100 columns: {type(diag_exc).__name__}: {diag_exc}")
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
                print(hdr)
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
                    row = (
                        f"{str(i).ljust(w_num)}  "
                        f"{name_fmt.ljust(w_title)}  "
                        f"{cat.ljust(w_platform)}  "
                        f"{last_played.ljust(w_last)}  "
                        f"{total.ljust(w_total)}"
                    )
                    print(row)
        except Exception as diag_exc:
            debug_print(f"Cannot render the recently played games table: {type(diag_exc).__name__}: {diag_exc}")

    if game_name:
        launchplatform_str = ""
        if launchplatform:
            launchplatform_str = f" ({launchplatform})"
        print(f"\nUser is currently in-game:\t{game_name}{launchplatform_str}")


# Main function that monitors gaming activity of the specified PSN user
def psn_monitor_user(psn_user_id, csv_file_name):

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
        report_recovery_error(e, context="file.unwritable", detail=f"Cannot prepare the CSV file '{csv_file_name}': {e}")

    print("Sneaking into PlayStation like a ninja ...\n")

    # Helper to print step message
    def print_step(msg):
        sys.stdout.write(f"- {msg}".ljust(32))
        sys.stdout.flush()

    # Helper to print OK
    def print_ok():
        print("OK")

    debug_print(f"PSNAWP session init for PSN user '{psn_user_id}' with PSN_NPSSO {secret_fingerprint(PSN_NPSSO)}")
    print_step("Authenticating with PSN...")
    try:
        psnawp = PSNAWP(PSN_NPSSO)
        psn_user = psnawp.user(online_id=psn_user_id)
    except Exception as e:
        print()
        report_recovery_error(e, context="startup", probe_auth=True)
        sys.exit(1)
    print_ok()

    debug_print(f"PSN API profile(), friendship() and get_shareable_profile_link() for '{psn_user_id}'")
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
        report_recovery_error(e, context="startup", detail=f"Reading the PSN profile of '{psn_user_id}' failed: {e}", probe_auth=True)
        sys.exit(1)
    print_ok()

    debug_print(f"PSN API get_presence() for '{psn_user_id}'")
    print_step("Fetching presence info...")
    try:
        psn_user_presence = psn_user.get_presence()
        parse_presence(psn_user_presence)
    except Exception as e:
        print()
        report_recovery_error(e, context="startup", detail=f"Cannot get presence for user '{psn_user_id}': {e}", probe_auth=True)
        sys.exit(1)
    print_ok()

    print_step("Fetching game title info...")
    try:
        status = psn_user_presence["basicPresence"]["primaryPlatformInfo"].get("onlineStatus")

        if not status:
            print()
            report_recovery_error(PsnMalformedResponse(f"Cannot get status for user '{psn_user_id}': the presence payload carries no onlineStatus"), context="startup")
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
        report_recovery_error(e, context="startup", detail=f"Reading the game title info of '{psn_user_id}' failed: {e}")
        sys.exit(1)
    print_ok()

    print()

    status_ts_old = int(time.time())
    status_ts_old_bck = status_ts_old

    if status and status != "offline":
        status_online_start_ts = status_ts_old
        status_online_start_ts_old = status_online_start_ts

    psn_last_status_file = f"psn_{psn_user_id}_last_status.json"
    last_status_read = []
    last_status_ts = 0
    last_status = ""

    if os.path.isfile(psn_last_status_file):
        try:
            with open(psn_last_status_file, 'r', encoding="utf-8") as f:
                last_status_read = json.load(f)
            debug_print(f"Saved status read from '{psn_last_status_file}'")
        except Exception as e:
            report_recovery_error(e, context="file.unreadable", detail=f"Cannot load the last saved status from '{psn_last_status_file}': {e}")
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
            debug_print(f"Saved status written to '{psn_last_status_file}': {last_status_to_save[1]}")
        except Exception as e:
            report_recovery_error(e, context="file.unwritable", detail=f"Cannot save the last status to '{psn_last_status_file}': {e}")

    try:
        if csv_file_name and (status != last_status):
            write_csv_entry(csv_file_name, now_local_naive(), status, game_name)
    except Exception as e:
        report_recovery_error(e, context="file.unwritable", detail=f"Cannot write to the CSV file '{csv_file_name}': {e}")

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
        debug_print(f"Cannot read the friendship relation from the PSN profile: {type(diag_exc).__name__}: {diag_exc}")

    try:
        print(f"\nProfile URL:\t\t\t{share.get('shareUrl')}")
        # print(f"Profile QR image:\t\t{share.get('shareImageUrl')}")
    except Exception as diag_exc:
        debug_print(f"Cannot read the shareable profile link from the PSN profile: {type(diag_exc).__name__}: {diag_exc}")

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
            debug_print(f"Saved status written to '{psn_last_status_file}': {last_status_to_save[1]}")
        except Exception as e:
            report_recovery_error(e, context="file.unwritable", detail=f"Cannot save the last status to '{psn_last_status_file}': {e}")

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
    error_streak = 0
    last_recreate_ts = 0
    recreate_cooldown = 300  # avoid recreating PSNAWP session too frequently
    last_npsso_seen = PSN_NPSSO

    def _close_psnawp_sessions(obj):
        try:
            if obj and hasattr(obj, "close"):
                try:
                    obj.close()
                except Exception as diag_exc:
                    debug_print(f"Closing a PSNAWP object failed: {type(diag_exc).__name__}: {diag_exc}")
            for attr in ("session", "_session", "http", "_http", "client", "_client"):
                s = getattr(obj, attr, None)
                if s and hasattr(s, "close"):
                    try:
                        s.close()
                    except Exception as diag_exc:
                        debug_print(f"Closing the PSNAWP '{attr}' session failed: {type(diag_exc).__name__}: {diag_exc}")
        except Exception as diag_exc:
            debug_print(f"Closing PSNAWP sessions failed: {type(diag_exc).__name__}: {diag_exc}")

    def get_sleep_interval():
        return PSN_ACTIVE_CHECK_INTERVAL if status and status != "offline" else PSN_CHECK_INTERVAL

    def _recreate_session_rate_limited():
        nonlocal psnawp, psn_user, last_recreate_ts
        now = int(time.time())
        if (now - last_recreate_ts) < recreate_cooldown:
            debug_print(f"PSNAWP session recreation skipped, {display_time(recreate_cooldown - (now - last_recreate_ts))} left of the {display_time(recreate_cooldown)} cooldown")
            return False
        try:
            _close_psnawp_sessions(psnawp)
        except Exception as diag_exc:
            debug_print(f"Closing the old PSNAWP session before recreating it failed: {type(diag_exc).__name__}: {diag_exc}")
        try:
            psnawp = PSNAWP(PSN_NPSSO)
            psn_user = psnawp.user(online_id=psn_user_id)
            last_recreate_ts = now
            verbose_print("Recreated the PSNAWP session")
            return True
        except Exception as diag_exc:
            debug_print(f"Recreating the PSNAWP session failed: {type(diag_exc).__name__}: {diag_exc}")
            return False

    sleep_interval = get_sleep_interval()

    debug_print(f"Sleeping {display_time(sleep_interval)} before the first check (status: {status or 'unknown'})")
    time.sleep(sleep_interval)

    check_number = 0
    recovery_hints = RecoveryHintTracker()

    # Main loop
    while True:
        check_number += 1
        # If PSN_NPSSO changed (e.g. .env updated + SIGHUP), recreate the PSNAWP session immediately.
        if PSN_NPSSO != last_npsso_seen:
            verbose_print(f"PSN_NPSSO changed ({secret_fingerprint(PSN_NPSSO)}), recreating the PSNAWP session")
            try:
                _close_psnawp_sessions(psnawp)
            except Exception as diag_exc:
                debug_print(f"Closing the old PSNAWP session after the NPSSO change failed: {type(diag_exc).__name__}: {diag_exc}")
            try:
                psnawp = PSNAWP(PSN_NPSSO)
                psn_user = psnawp.user(online_id=psn_user_id)
                last_recreate_ts = int(time.time())
                print("* PSN_NPSSO updated - recreated PSNAWP session")
                print_cur_ts("Timestamp:\t\t\t")
            except Exception as e:
                advice = report_recovery_error(e, context="monitor", detail=f"Rebuilding the PSNAWP session after the PSN_NPSSO change failed: {e}", probe_auth=True)
                if ERROR_NOTIFICATION and not email_sent:
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(recovery_email_subject(advice, psn_user_id), recovery_email_body(advice), "", SMTP_SSL)
                    email_sent = True
                print_cur_ts("Timestamp:\t\t\t")
            last_npsso_seen = PSN_NPSSO
            # allow notifications again after token rotation
            email_sent = False
            error_streak = 0

        # Sometimes PSN network functions halt, so we use alarm signal functionality to kill it inevitably, not available on Windows
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT)
        debug_print(f"Starting check #{check_number} for '{psn_user_id}', PSN API get_presence() with a {FUNCTION_TIMEOUT}s alarm timeout")
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
            report_recovery_error(e, context="monitor", detail=f"psn_user.get_presence() did not answer within {display_time(FUNCTION_TIMEOUT)}", tracker=recovery_hints, retry_note=f"retrying in {display_time(FUNCTION_TIMEOUT)}")
            print_cur_ts("Timestamp:\t\t\t")
            debug_print(f"Sleeping {display_time(FUNCTION_TIMEOUT)} after check #{check_number} timed out")
            time.sleep(FUNCTION_TIMEOUT)
            continue

        except Exception as e:
            if platform.system() != 'Windows':
                signal.alarm(0)

            advice = classify_recovery_error(e, context="monitor", probe_auth=True)
            kind = recovery_poll_kind(advice)
            debug_print(f"Check #{check_number} failed, classified as '{advice.code}' under the {kind} retry policy: {type(e).__name__}: {e}")

            # Local file descriptor exhaustion cannot be recovered inside this process
            if kind == "exhausted":
                print_recovery_advice(advice)
                if ERROR_NOTIFICATION and not email_sent:
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(recovery_email_subject(advice, psn_user_id), recovery_email_body(advice), "", SMTP_SSL)
                    email_sent = True
                print_cur_ts("Timestamp:\t\t\t")
                sys.exit(2)

            error_streak += 1
            policy = RECOVERY_POLL_POLICY[kind]
            sleep_interval = FUNCTION_TIMEOUT if kind == "transient" else (get_sleep_interval() if kind == "unknown" else max(60, get_sleep_interval()))
            # A failure nothing here can retry away is worth reporting at once rather than after a streak
            alert_after = policy["alert_after"] if advice.retryable else 1

            if error_streak >= policy["report_after"]:
                print_recovery_advice(advice, recovery_hints, f"retrying in {display_time(sleep_interval)}")

            if error_streak >= policy["recreate_after"] and _recreate_session_rate_limited():
                print(f"* Rebuilt the PSNAWP session after {error_streak} failed {'check' if error_streak == 1 else 'checks'} in a row")

            if ERROR_NOTIFICATION and not email_sent and error_streak >= alert_after:
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(recovery_email_subject(advice, psn_user_id), recovery_email_body(advice, error_streak), "", SMTP_SSL)
                email_sent = True

            if error_streak >= policy["report_after"]:
                print_cur_ts("Timestamp:\t\t\t")
            debug_print(f"Sleeping {display_time(sleep_interval)} after a {kind} failure (streak: {error_streak})")
            time.sleep(sleep_interval)
            continue

        else:
            if error_streak:
                verbose_print(f"Recovered after {error_streak} failed checks in a row")
            recovery_hints.reset()
            email_sent = False
            error_streak = 0

        finally:
            if platform.system() != 'Windows':
                signal.alarm(0)

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
                debug_print(f"Saved status written to '{psn_last_status_file}': {last_status_to_save[1]}")
            except Exception as e:
                report_recovery_error(e, context="file.unwritable", detail=f"Cannot save the last status to '{psn_last_status_file}': {e}")

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
            if ACTIVE_INACTIVE_NOTIFICATION and act_inact_flag:
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

            if GAME_CHANGE_NOTIFICATION and m_subject and m_body:
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
                report_recovery_error(e, context="file.unwritable", detail=f"Cannot write to the CSV file '{csv_file_name}': {e}")
                print_cur_ts("Timestamp:\t\t\t")

        status_old = status
        game_name_old = game_name
        alive_counter += 1

        if LIVENESS_CHECK_COUNTER and alive_counter >= LIVENESS_CHECK_COUNTER and (status == "offline" or not status):
            print_cur_ts("Liveness check, timestamp:\t")
            alive_counter = 0

        sleep_interval = get_sleep_interval()
        debug_print(f"Check #{check_number} done for '{psn_user_id}', status: {status or 'unknown'}, game: {game_name or 'none'}, next check in {display_time(sleep_interval)}")
        time.sleep(sleep_interval)


# Preflight diagnostics. Every section, marker and summary sentence is shared with the sibling monitors,
# so a user who runs two of them reads one report format rather than two
DOCTOR_GUIDE_URL = f"{GUIDE_BASE_URL}#doctor-preflight"

DOCTOR_SECTIONS = ("Environment", "Configuration", "Authentication", "Target", "Notifications")

DOCTOR_STATUSES = ("PASS", "WARN", "FAIL", "SKIP")

# Imported without a guard, so the tool cannot start when one of these is missing
DOCTOR_REQUIRED_DEPENDENCIES = (("psnawp_api", "PSNAWP"), ("requests", "requests"), ("dateutil", "python-dateutil"), ("pytz", "pytz"))

# Guarded imports the tool degrades around, with what stops working and what to do instead
DOCTOR_OPTIONAL_DEPENDENCIES = (
    ("tzlocal", "tzlocal", "Used only to auto-detect the local time zone", "Automatic time zone detection is unavailable", "Or set LOCAL_TIMEZONE to a pytz timezone name in the config file"),
    ("dotenv", "python-dotenv", "Used only to read secrets from a dotenv file", "Secrets cannot be read from a dotenv file", "Or export them as environment variables"),
    ("wcwidth", "wcwidth", "Used only to measure display width for screen truncation", "Screen truncation is disabled", ""),
)

# An active check interval below this invites the PSN rate limiter, which stops the tool seeing anything
DOCTOR_MIN_SAFE_ACTIVE_INTERVAL = 30


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


# Creates one doctor result, refusing a marker outside the shared four and redacting every field it shows
def make_doctor_check(section, status, label, detail="", advice=None):
    if status not in DOCTOR_STATUSES:
        raise ValueError(f"Unsupported doctor status: {status}")
    return DoctorCheck(section, status, sanitize_error_text(label), sanitize_error_text(detail), advice)


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
    if selected[:2] >= MINIMUM_PYTHON_VERSION:
        checks.append(make_doctor_check("Environment", "PASS", f"Python {version_text} is supported"))
    else:
        advice = make_recovery_advice("dependency.missing", f"Python {version_text} is unsupported", recovery_fix_with_guide(f"Install Python {MINIMUM_PYTHON_VERSION_TEXT} or newer then retry", INSTALLATION_GUIDE_URL), False)
        checks.append(make_doctor_check("Environment", "FAIL", advice.summary, advice=advice))

    for module_name, package_name in DOCTOR_REQUIRED_DEPENDENCIES:
        if dependency_is_installed(module_name, spec_finder):
            checks.append(make_doctor_check("Environment", "PASS", f"Required dependency {package_name} is installed"))
        else:
            advice = make_recovery_advice("dependency.missing", f"Required dependency {package_name} is missing", recovery_fix_with_guide(f"Install it with: {pip_install_command(package_name)}", INSTALLATION_GUIDE_URL), False)
            checks.append(make_doctor_check("Environment", "FAIL", advice.summary, advice=advice))

    for module_name, package_name, purpose, effect, alternative in DOCTOR_OPTIONAL_DEPENDENCIES:
        if dependency_is_installed(module_name, spec_finder):
            checks.append(make_doctor_check("Environment", "PASS", f"Optional dependency {package_name} is installed", purpose))
        else:
            advice = missing_dependency_advice(package_name, effect, alternative)
            checks.append(make_doctor_check("Environment", "WARN", f"Optional dependency {package_name} is not installed", f"{effect}. Monitoring is unaffected", advice))

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


# Reports the effective settings and the files the tool would write, without writing any of them
def doctor_check_configuration(config_path=None, env_path=None, config_advice=None, timezone_advice=None, psn_user_id=None):
    checks = []
    if config_advice is not None:
        checks.append(make_doctor_check("Configuration", "FAIL", config_advice.summary, advice=config_advice))
    elif config_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Configuration file loaded", f"Path: {config_path}"))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No configuration file selected", "Using built-in defaults and command-line overrides"))

    if env_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Dotenv file loaded", f"Path: {env_path}"))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No dotenv file selected", "Using environment variables and other configured sources"))

    checks.extend(doctor_secret_checks())

    if timezone_advice is not None:
        checks.append(make_doctor_check("Configuration", "FAIL", timezone_advice.summary, advice=timezone_advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", f"Time zone is {LOCAL_TIMEZONE}"))

    intervals = f"{display_time(PSN_CHECK_INTERVAL)} while offline, {display_time(PSN_ACTIVE_CHECK_INTERVAL)} while online"
    if PSN_ACTIVE_CHECK_INTERVAL < DOCTOR_MIN_SAFE_ACTIVE_INTERVAL:
        advice = make_recovery_advice("psn.rate_limited", "Check intervals are short enough to be rate limited", recovery_fix_with_guide(f"Raise PSN_ACTIVE_CHECK_INTERVAL to at least {DOCTOR_MIN_SAFE_ACTIVE_INTERVAL} seconds", INTERVALS_GUIDE_URL), True)
        checks.append(make_doctor_check("Configuration", "WARN", "Check intervals are short", intervals, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "Check intervals are set", intervals))

    try:
        checks.append(make_doctor_check("Configuration", "PASS", f"ASCII log separators are {'on' if ascii_log_separators_enabled() else 'off'}", f"Mode: {ASCII_LOG_SEPARATORS}"))
    except ValueError as exc:
        advice = classify_recovery_error(context="config.invalid", detail=str(exc))
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))

    if CSV_FILE:
        csv_path = os.path.expanduser(CSV_FILE)
        if path_is_writable(csv_path):
            checks.append(make_doctor_check("Configuration", "PASS", "CSV history file is writable", f"Path: {csv_path}"))
        else:
            advice = classify_recovery_error(context="file.unwritable", detail=f"CSV file '{csv_path}' cannot be written")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "CSV history is disabled", "Set CSV_FILE or use -b to record every reported change"))

    if DISABLE_LOGGING:
        checks.append(make_doctor_check("Configuration", "PASS", "Output logging is disabled", "Nothing is written to a log file"))
    else:
        log_path = resolve_log_path(psn_user_id or "<psn_user_id>")
        if path_is_writable(log_path):
            checks.append(make_doctor_check("Configuration", "PASS", "Log file is writable", f"Path: {log_path}"))
        else:
            advice = classify_recovery_error(context="file.unwritable", detail=f"Log file '{log_path}' cannot be written")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice=advice))
    return checks


# Authenticates once and keeps the session, so the target checks do not sign in a second time
def doctor_check_authentication(report):
    if not secret_is_set(PSN_NPSSO):
        advice = classify_recovery_error(context="secret.missing", detail="PSN_NPSSO is not set")
        return [make_doctor_check("Authentication", "FAIL", advice.summary, advice=advice)]
    try:
        psnawp = PSNAWP(PSN_NPSSO)
        signed_in = psnawp.me().online_id
    except Exception as exc:
        advice = classify_recovery_error(exc, context="startup", probe_auth=True)
        return [make_doctor_check("Authentication", "FAIL", advice.summary, advice=advice)]
    report.psnawp = psnawp
    return [make_doctor_check("Authentication", "PASS", "PlayStation Network accepted the NPSSO code", f"Signed in as {signed_in}")]


# Checks the monitored profile can be found and that it shares the activity the tool reads
def doctor_check_target(report, psn_user_id=None):
    if not psn_user_id:
        advice = classify_recovery_error(context="target.missing", detail="No PlayStation ID was given")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice=advice)]
    if report.psnawp is None:
        # Authentication already failed and reported why. A second row would repeat one problem as two
        return []
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


# Reports whether email alerts can fire at all, then whether the settings they would use are usable
def doctor_check_notifications(report):
    settings_advice = validate_smtp_settings()
    # An error alert is on by default, so on its own it cannot make a fresh install look configured
    deliberate = ACTIVE_INACTIVE_NOTIFICATION or GAME_CHANGE_NOTIFICATION
    if not deliberate and not (ERROR_NOTIFICATION and settings_advice is None):
        return [make_doctor_check("Notifications", "PASS", "Email alerts are disabled", "Use -a, -g or SMTP settings with ERROR_NOTIFICATION to turn them on")]
    if settings_advice is not None:
        return [make_doctor_check("Notifications", "WARN", "Email alerts are on but cannot be delivered", settings_advice.summary, settings_advice)]
    alerts = ", ".join(name for name, enabled in (("status changes", ACTIVE_INACTIVE_NOTIFICATION), ("game changes", GAME_CHANGE_NOTIFICATION), ("errors", ERROR_NOTIFICATION)) if enabled)
    report.email_ready = True
    return [make_doctor_check("Notifications", "PASS", "SMTP settings and alert choices look valid", f"{SMTP_HOST}:{SMTP_PORT} to {RECEIVER_EMAIL}, alerts: {alerts}")]


# Returns the raw terminal stream, so the transient progress line is not captured by the log writer
def doctor_terminal_stream():
    stream = sys.stdout
    while isinstance(stream, (Logger, TerminalStream)):
        stream = stream.terminal
    return stream


# Width of the progress line currently on screen, which is what erasing it needs to know
DOCTOR_PROGRESS_WIDTH = 0


# Shows one transient step only on an interactive terminal, erased by overwriting its own width
def doctor_progress(label):
    global DOCTOR_PROGRESS_WIDTH
    terminal = doctor_terminal_stream()
    if terminal.isatty():
        doctor_progress_clear()
        line = f"* Checking {sanitize_terminal_text(label)} ..."
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
        ("authentication", lambda: doctor_check_authentication(report)),
        ("target", lambda: doctor_check_target(report, psn_user_id)),
        ("notifications", lambda: doctor_check_notifications(report)),
    )
    for label, run_step in steps:
        if progress is not None:
            progress(label)
        report.checks.extend(run_step())
    return report


# Prints the notice that has to be true before anything runs
def render_doctor_notice():
    print("Running preflight checks. No files will be written. Interactive email tests run only after separate approval.\n")


# Renders the whole report, with a fix line on the rows that are not a pass
def render_doctor_report(report):
    # The install method is context rather than a check: it cannot fail, so it is stated once here
    # instead of occupying a result row that no marker describes. The raw key is what support reports use
    lines = ["Doctor", f"Detected install method: {detect_install_method()}"]
    for section in DOCTOR_SECTIONS:
        section_checks = [check for check in report.checks if check.section == section]
        if not section_checks:
            continue
        lines.extend(("", section))
        for check in section_checks:
            lines.append(f"[{check.status}] {check.label}")
            if check.detail:
                lines.append(f"  {check.detail}")
            if check.advice is not None and check.status in ("FAIL", "WARN"):
                lines.append(f"To fix: {check.advice.fix}")
    return sanitize_error_text("\n".join(lines) + render_doctor_summary(report.checks))


# Renders the one sentence that says whether the setup is usable, and where to read more
def render_doctor_summary(checks):
    failures = sum(check.status == "FAIL" for check in checks)
    warnings = sum(check.status == "WARN" for check in checks)
    if failures:
        sentence = f"  {failures} check(s) failed, {warnings} warning(s). Fix the failures above before relying on the tool."
    elif warnings:
        sentence = f"  All critical checks passed with {warnings} warning(s). Review the warnings above."
    else:
        sentence = "  All checks passed. You are good to go!"
    return "\n".join(("", "", "Summary", sentence, "", f"Guide: {DOCTOR_GUIDE_URL}"))


# Asks one yes or no question, treating a closed or interrupted input as no
def ask_yes_no(question, default=False):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = input(f"{question} {hint}: ").strip().casefold()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Offers the one delivery test this tool has, and only for a channel that already passed
def offer_doctor_delivery_tests(report):
    if not report.email_ready or not sys.stdin.isatty() or not sys.stdout.isatty():
        return []
    print("\nOptional delivery tests\n")
    print("Doctor will not write files. Each approved test sends one real message.\n")
    if not ask_yes_no("Send one test email now? This will deliver a real message"):
        print("[SKIP] Test email was not sent")
        return [make_doctor_check("Notifications", "SKIP", "Test email was not sent")]
    delivered = send_email("psn_monitor: doctor test email", "This test email was sent after approval in --doctor. Your SMTP delivery settings work.", "", SMTP_SSL, smtp_timeout=5) == 0
    check = make_doctor_check("Notifications", "PASS" if delivered else "FAIL", "Doctor test email delivered" if delivered else "Doctor test email delivery failed", "One real test email was sent after confirmation" if delivered else "The approved test email could not be delivered")
    print(f"[{check.status}] {check.label}")
    return [check]


# Runs the preflight report plus any approved delivery test and returns the process exit code
def run_doctor(psn_user_id=None, config_path=None, env_path=None, config_advice=None, timezone_advice=None):
    render_doctor_notice()
    progress = doctor_progress if doctor_terminal_stream().isatty() else None
    try:
        report = build_doctor_report(psn_user_id, config_path, env_path, config_advice, timezone_advice, progress)
    finally:
        doctor_progress_clear()
    print(render_doctor_report(report))
    delivery_checks = offer_doctor_delivery_tests(report)
    return 1 if any(check.status == "FAIL" for check in (*report.checks, *delivery_checks)) else 0


def main():
    global CLI_CONFIG_PATH, DOTENV_FILE, LOCAL_TIMEZONE, LIVENESS_CHECK_COUNTER, PSN_NPSSO, CSV_FILE, DISABLE_LOGGING, PSN_LOGFILE, ACTIVE_INACTIVE_NOTIFICATION, GAME_CHANGE_NOTIFICATION, ERROR_NOTIFICATION, PSN_CHECK_INTERVAL, PSN_ACTIVE_CHECK_INTERVAL, SMTP_PASSWORD, TRUNCATE_CHARS, EXPORTED_SECRET_KEYS, stdout_bck

    if "--generate-config" in sys.argv:
        config_content = CONFIG_BLOCK.strip("\n") + "\n"
        try:
            idx = sys.argv.index("--generate-config")
            if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
                output_file = sys.argv[idx + 1]
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(config_content)
                print(f"Config written to: {output_file}")
                sys.exit(0)
        except (ValueError, IndexError):
            pass
        sys.stdout.buffer.write(config_content.encode("utf-8"))
        sys.stdout.buffer.flush()
        sys.exit(0)

    if "--version" in sys.argv:
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    stdout_bck = sys.stdout

    # Installed before the banner and before one-shot modes run, so PSN-supplied text printed by --info cannot
    # drive the terminal either. The Logger installed later unwraps this again to keep sanitizing single-pass
    if not isinstance(sys.stdout, TerminalStream):
        sys.stdout = TerminalStream(sys.stdout)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    clear_screen(CLEAR_SCREEN)

    print(f"PSN Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser(
        prog="psn_monitor",
        description=("Monitor a PSN user's playing status and send customizable email alerts [ https://github.com/misiektoja/psn_monitor/ ]"), formatter_class=argparse.RawTextHelpFormatter
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
        help="Location of the optional config file",
    )
    conf.add_argument(
        "--generate-config",
        nargs="?",
        const=True,
        metavar="FILENAME",
        help="Print default config template and exit (on Windows PowerShell, specify a filename to avoid redirect encoding issues)",
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
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

    # User information
    info = parser.add_argument_group("User information")
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
        "--doctor",
        dest="doctor",
        action="store_true",
        help="Run preflight checks on this setup and exit"
    )
    opts.add_argument(
        "--verbose",
        dest="verbose_mode",
        action="store_true",
        default=None,
        help="Show rare operational events and the settings the tool resolved"
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

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = find_config_file(CLI_CONFIG_PATH)

    # Doctor reports a broken setup instead of exiting on the first thing it finds, so the whole report is usable
    doctor_mode = bool(args.doctor)
    config_advice = None
    timezone_advice = None

    if not cfg_path and CLI_CONFIG_PATH:
        config_advice = classify_recovery_error(context="config.missing", detail=f"Config file '{CLI_CONFIG_PATH}' does not exist")
        if not doctor_mode:
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
            SECRET_SOURCES[secret] = "configuration file"

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

    # Environment variables are a documented alternative to a dotenv file, so they apply even when no file was loaded
    for secret in SECRET_KEYS:
        val = os.getenv(secret)
        if val is not None:
            globals()[secret] = val
            SECRET_SOURCES[secret] = "environment" if secret in EXPORTED_SECRET_KEYS else "dotenv file"

    verbose_print(f"Configuration file in use is {cfg_path or 'none'}")
    verbose_print(f"Dotenv file in use is {env_path or 'none'}")
    for secret in SECRET_KEYS:
        debug_print(f"Secret {secret} is {secret_fingerprint(globals().get(secret))}, resolved from {SECRET_SOURCES.get(secret, 'nowhere')}")

    local_tz = None
    if LOCAL_TIMEZONE == "Auto":
        if get_localzone is not None:
            try:
                local_tz = get_localzone()
            except Exception as diag_exc:
                debug_print(f"Local timezone auto-detection failed: {type(diag_exc).__name__}: {diag_exc}")
        if local_tz:
            LOCAL_TIMEZONE = str(local_tz)
        else:
            timezone_advice = missing_dependency_advice("tzlocal", "The local timezone could not be detected", f"Or set LOCAL_TIMEZONE to a pytz timezone name such as 'Europe/Warsaw'. See {TIMEZONE_GUIDE_URL}")
    elif not is_valid_timezone(LOCAL_TIMEZONE):
        timezone_advice = classify_recovery_error(context="config.invalid", detail=f"Configured LOCAL_TIMEZONE '{LOCAL_TIMEZONE}' is not valid")

    if timezone_advice is not None:
        if not doctor_mode:
            print_recovery_advice(timezone_advice)
            sys.exit(1)
        # The report still stamps timestamps, so it falls back rather than stopping before the diagnosis
        LOCAL_TIMEZONE = "UTC"

    verbose_print(f"Local timezone resolved to {LOCAL_TIMEZONE}")

    if doctor_mode:
        sys.exit(run_doctor(args.psn_user_id, cfg_path, env_path, config_advice, timezone_advice))

    if not check_internet():
        sys.exit(1)

    if args.send_test_email:
        print("* Sending test email notification ...\n")
        if send_email("psn_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if not args.psn_user_id:
        report_recovery_error(context="target.missing", detail="PSN_USER_ID needs to be defined")
        sys.exit(1)

    if args.npsso_key:
        PSN_NPSSO = args.npsso_key
        SECRET_SOURCES["PSN_NPSSO"] = "command line"
        debug_print(f"PSN_NPSSO taken from the command line ({secret_fingerprint(PSN_NPSSO)})")

    if not PSN_NPSSO or PSN_NPSSO == "your_psn_npsso_code":
        report_recovery_error(context="secret.missing", detail="PSN_NPSSO (-n / --npsso_key) value is empty or incorrect")
        sys.exit(1)

    if args.info_mode:
        include_trophies = args.include_trophies if hasattr(args, 'include_trophies') and args.include_trophies else False
        show_recent_games = not (hasattr(args, 'no_recent_games') and args.no_recent_games)
        get_user_info(args.psn_user_id, include_trophies=include_trophies, show_recent_games=show_recent_games)
        sys.exit(0)

    if args.check_interval:
        PSN_CHECK_INTERVAL = args.check_interval
        LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / PSN_CHECK_INTERVAL

    if args.active_interval:
        PSN_ACTIVE_CHECK_INTERVAL = args.active_interval

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
            report_recovery_error(e, context="file.unwritable", detail=f"CSV file '{CSV_FILE}' cannot be opened for writing: {e}")
            sys.exit(1)

    try:
        ascii_log_separators_enabled()
    except ValueError as e:
        report_recovery_error(context="config.invalid", detail=str(e))
        sys.exit(1)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    TRUNCATE_CHARS = resolve_truncate_chars(args.truncate, TRUNCATE_CHARS, DISABLE_LOGGING)

    if not DISABLE_LOGGING:
        log_path = resolve_log_path(args.psn_user_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        FINAL_LOG_PATH = str(log_path)
        sys.stdout = Logger(FINAL_LOG_PATH)
        debug_print(f"Logging output to '{FINAL_LOG_PATH}'")
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

    print(f"* PSN polling intervals:\t[offline: {display_time(PSN_CHECK_INTERVAL)}] [online: {display_time(PSN_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[online/offline status changes = {ACTIVE_INACTIVE_NOTIFICATION}] [game changes = {GAME_CHANGE_NOTIFICATION}]\n*\t\t\t\t[errors = {ERROR_NOTIFICATION}]")
    print(f"* Liveness check:\t\t{bool(LIVENESS_CHECK_INTERVAL)}" + (f" ({display_time(LIVENESS_CHECK_INTERVAL)})" if LIVENESS_CHECK_INTERVAL else ""))
    print(f"* CSV logging enabled:\t\t{bool(CSV_FILE)}" + (f" ({CSV_FILE})" if CSV_FILE else ""))
    print(f"* Output logging enabled:\t{not DISABLE_LOGGING}" + (f" ({FINAL_LOG_PATH})" if not DISABLE_LOGGING else ""))
    print(f"* ASCII log separators:\t\t{ascii_log_separators_enabled()} (mode: {ASCII_LOG_SEPARATORS})")
    print(f"* Terminal truncation:\t\t{bool(TRUNCATE_CHARS)}" + (f" ({TRUNCATE_CHARS} chars)" if TRUNCATE_CHARS else ""))
    print(f"* Configuration file:\t\t{cfg_path}")
    print(f"* Dotenv file:\t\t\t{env_path or 'None'}")
    print(f"* Local timezone:\t\t{LOCAL_TIMEZONE}")
    if VERBOSE_MODE or DEBUG_MODE:
        print(f"* Verbose mode:\t\t\t{VERBOSE_MODE}")
        print(f"* Debug mode:\t\t\t{DEBUG_MODE}")
    else:
        print("* More details:\t\t\tuse --verbose or --debug")

    out = f"\nMonitoring user with PSN ID {args.psn_user_id}"
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
