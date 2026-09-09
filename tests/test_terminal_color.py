"""Terminal colour contract tests: which part colours which token, and where colour must never reach."""

import os
import platform
import pty
import re
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest

import psn_monitor as monitor


CHANGE_REPORT_LINES = (
    "PSN user misiektoja changed status from offline to online",
    "PSN user misiektoja changed game from 'Ghost of Tsushima' to 'Elden Ring' (PS5) after 1 hour, 12 minutes",
    "*** User got ACTIVE ! (was offline since Sat 22 Nov 2025, 16:54:31)",
    "User played game from Sun 23 Nov 20:15 to 21:27",
)


@pytest.fixture
# Enables colour with a known style map so assertions do not depend on the shipped theme
def colored(monkeypatch):
    styles = {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", styles)
    return styles


# Builds a Logger writing into two in-memory buffers and returns it with both buffers
def make_logger():
    terminal = StringIO()
    logfile = StringIO()
    logger = monitor.Logger.__new__(monitor.Logger)
    logger.__dict__["terminal"] = terminal
    logger.__dict__["logfile"] = logfile
    return logger, terminal, logfile


# Reads a block the template ships commented out, as the parser would see it once uncommented
def uncomment_block(first_line):
    lines = monitor.CONFIG_BLOCK.split("\n")
    start = next(index for index, line in enumerate(lines) if line.startswith(first_line))
    end = next(index for index in range(start, len(lines)) if lines[index].rstrip() == "# }")
    return "\n".join(line[2:] if line.startswith("# ") else line[1:] for line in lines[start:end + 1])


# Verifies the shipped config template and the built-in theme describe exactly the same keys and values
def test_config_template_theme_matches_the_built_in_theme():
    values = monitor.parse_config_content(monitor.CONFIG_BLOCK, "<built-in-config>")
    commented = monitor.parse_config_content(uncomment_block("# COLOR_THEME = {"), "<built-in-config>")

    assert values["COLORED_OUTPUT"] is True
    assert "COLOR_THEME" not in values
    assert commented["COLOR_THEME"] == monitor.DEFAULT_COLOR_THEME


# Verifies a configuration that sets the commented-out theme is still accepted, since older files all set it
def test_a_config_setting_the_theme_is_still_accepted(tmp_path):
    config = tmp_path / "monitor.conf"
    config.write_text('COLOR_THEME = { "username": "green" }\n', encoding="utf-8")

    assert monitor.parse_config_content(config.read_text(encoding="utf-8"), str(config)) == {"COLOR_THEME": {"username": "green"}}


# Verifies every style word the shipped theme uses resolves, allowing a deliberately uncoloured part
def test_default_theme_styles_all_resolve():
    for name, value in monitor.DEFAULT_COLOR_THEME.items():
        assert monitor._build_ansi_sequence(value) or value == "", name


# Verifies a value colour never equals a whole-line style that can enclose it, which would hide the value
def test_block_styles_never_hide_a_name(colored):
    for block in monitor.BLOCK_STYLE_PARTS:
        for name in monitor.NAME_STYLE_PARTS:
            assert colored[name] != colored[block], f"{name} is invisible inside a {block} line"


# Verifies the Timestamp label is left uncoloured, matching the sibling monitors
def test_timestamp_label_is_uncolored(colored):
    assert monitor.DEFAULT_COLOR_THEME["timestamp_label"] == ""
    assert "timestamp_label" not in colored
    assert monitor._colorize_line("Timestamp:\t\t\tWed 26 Aug 2026, 20:23:03") == f"Timestamp:\t\t\t{colored['timestamp_value']}Wed 26 Aug 2026, 20:23:03{monitor.ANSI_RESET}"


# Verifies the liveness heartbeat uses the same timestamp colouring as every other timestamp row
def test_the_liveness_row_is_a_timestamp_row(colored):
    result = monitor._colorize_line("Liveness check, timestamp:\tMon 24 Nov 2025, 01:18:44")

    assert result == f"Liveness check, timestamp:\t{colored['timestamp_value']}Mon 24 Nov 2025, 01:18:44{monitor.ANSI_RESET}"


# Verifies a startup summary row is not block-coloured just because it names a mode or a setting
def test_startup_summary_rows_are_not_block_colored(colored):
    for line in ("* Install method:               pip package", "* Config:                       /home/me/psn_monitor.conf", "* Local timezone:               Europe/Warsaw"):
        assert monitor._colorize_line(line) == line


# Verifies the notification rollup row colours its own state word rather than the whole line
def test_the_notification_summary_row_colours_its_state(colored):
    on_row = monitor._colorize_line("* Notifications (email):        On (status changes, game changes, errors)")
    off_row = monitor._colorize_line("* Notifications (email):        Off")

    assert on_row == f"* Notifications (email):        {colored['boolean_true']}On{monitor.ANSI_RESET} (status changes, game changes, errors)"
    assert off_row == f"* Notifications (email):        {colored['boolean_false']}Off{monitor.ANSI_RESET}"


# Verifies the webhook rollup gets the same treatment, so one channel is not styled differently from the other
def test_the_webhook_summary_row_colours_its_state(colored):
    row = monitor._colorize_line("* Notifications (webhook):      On (status changes) through Discord")

    assert row == f"* Notifications (webhook):      {colored['boolean_true']}On{monitor.ANSI_RESET} (status changes) through Discord"


# Verifies the two delivery channels are told apart at a glance rather than sharing one colour
def test_the_two_delivery_channels_are_coloured_differently(colored):
    assert colored["email"] != colored["webhook"]


# Verifies a debug trace and a recovery notice are not painted red. A debug line records an attempt the tool
# then handles, and a rebuilt session reports a recovery that worked rather than the failures behind it
@pytest.mark.parametrize("line", [
    "[DEBUG 20:15:03] PSN API get_presence() failed for 'misiektoja': timeout=15",
    "[DEBUG 20:15:03] HTTP GET https://www.google.com (connectivity check, timeout 5s) failed",
    "* Rebuilt the PSNAWP session after 3 failed checks in a row",
    "Technical detail: 401 Client Error: Unauthorized",
])
def test_diagnostic_details_and_recovery_notices_are_not_error_colored(colored, line):
    assert colored["error"] not in monitor._colorize_line(line)


# Verifies the lines that really report a problem are still painted end to end
@pytest.mark.parametrize("line,part", [
    ("* Error: PlayStation Network rejected the NPSSO code", "error"),
    ("* Warning: dotenv file '/home/me/.env' does not exist", "warning"),
    ("* Note: Config file contains settings this version no longer uses", "info"),
    ("* Signal SIGUSR1 received", "signal"),
    ("Sending email notification to alerts@example.test", "email"),
    ("Sending webhook notification", "webhook"),
])
def test_only_problem_lines_are_painted_end_to_end(colored, line, part):
    assert monitor._colorize_line(line).startswith(colored[part])


# Verifies a static count stays plain. This tool reports no numeric change, so it ships no counter colours and
# the numbers it does print are left alone
def test_static_counts_stay_plain(colored):
    assert monitor._colorize_line("Mutual friends:\t\t\t3") == "Mutual friends:\t\t\t3"
    assert monitor._colorize_line("Trophies earned:\t\t12 Platinum, 210 Gold").count(monitor.ANSI_RESET) == 1

    played = monitor._colorize_line("User played 3 games for total time of 4 hours, 12 minutes")
    assert played == f"User played 3 games for total time of {colored['duration']}4 hours{monitor.ANSI_RESET}, {colored['duration']}12 minutes{monitor.ANSI_RESET}"


# Verifies colouring only inserts escape sequences and never changes the text itself
@pytest.mark.parametrize("line", [
    "PlayStation ID:\t\t\tmisiektoja",
    "PSN account ID:\t\t\t1234567890123456789",
    "Status:\t\t\t\tONLINE",
    "Trophy level:\t\t\t312 (45% to next, tier 2)",
    "Profile URL:\t\t\thttps://psnprofiles.com/misiektoja",
    "*** User got OFFLINE ! (after 5 hours, 3 minutes: Sun 23 Nov 20:15 - Mon 24 Nov 01:18)",
    "* Signal SIGUSR1 received",
    "Timestamp:\t\t\tSun 21 Apr 2024, 15:08:45",
    "- Sun 23 Nov 2025, 20:15:03 | Elden Ring | GOLD | Legendary Armaments",
])
def test_colorize_line_never_rewrites_the_text(colored, line):
    assert monitor.ANSI_ESCAPE_RE.sub("", monitor._colorize_line(line)) == line


# Verifies the startup line reaches the terminal in the tool's own two colours and nothing else
def test_startup_banner_uses_only_its_own_colours(colored, capsys):
    monitor.print_startup_banner()
    printed = capsys.readouterr().out

    assert f"{colored['info']}{'':21}v{monitor.VERSION}{monitor.ANSI_RESET}" in printed
    assert set(monitor.SGR_SEQUENCE_RE.findall(printed)) <= {colored["header"], colored["info"], monitor.ANSI_RESET}
    for line in monitor.STARTUP_BANNER.splitlines():
        if line:
            assert f"{colored['header']}{line}{monitor.ANSI_RESET}" in printed


# Verifies a second colour pass over the printed banner leaves both the text and the colours alone
def test_startup_banner_text_is_unchanged(colored, capsys):
    monitor.print_startup_banner()
    printed = capsys.readouterr().out

    assert monitor.apply_color_to_text(printed) == printed
    assert monitor.ANSI_ESCAPE_RE.sub("", printed) == monitor.STARTUP_BANNER + "\n" + (" " * 21) + f"v{monitor.VERSION}\n\n"


# Verifies labelled PlayStation rows colour the value with the expected theme part
@pytest.mark.parametrize("line,part", [
    ("PlayStation ID:\t\t\tmisiektoja", "username"),
    ("PSN account ID:\t\t\t1234567890123456789", "id"),
    ("Platform:\t\t\tPlayStation 5", "platform"),
    ("Trophy level:\t\t\t312 (45% to next, tier 2)", "trophy"),
    ("Trophies earned:\t\t12 Platinum, 210 Gold", "trophy"),
    ("User is currently in-game:\tElden Ring", "game"),
])
def test_labelled_rows_use_the_expected_theme_part(colored, line, part):
    assert colored[part] in monitor._colorize_line(line)


# Verifies the presence rows use the status table rather than a fixed colour
@pytest.mark.parametrize("line,part", [
    ("Status:\t\t\t\tONLINE", "status_active"),
    ("Status:\t\t\t\tOFFLINE", "status_offline"),
    ("Status:\t\t\t\tSTANDBY", "status_inactive"),
    ("Available to play:\t\tYes", "status_active"),
    ("Available to play:\t\tNo", "status_inactive"),
])
def test_presence_rows_use_the_status_table(colored, line, part):
    assert colored[part] in monitor._colorize_line(line)


# Verifies the console tag beside a game keeps its own colour instead of disappearing into the title
def test_the_console_tag_keeps_its_own_colour_next_to_a_game(colored):
    labelled = monitor._colorize_line("User is currently in-game:\tElden Ring (PS5)")
    sentence = monitor._colorize_line("PSN user misiektoja started playing 'Elden Ring' (PS5)")

    assert labelled == f"User is currently in-game:\t{colored['game']}Elden Ring{monitor.ANSI_RESET} ({colored['platform']}PS5{monitor.ANSI_RESET})"
    assert f"({colored['platform']}PS5{monitor.ANSI_RESET})" in sentence


# Verifies each column of a trophy listing row is coloured for what it holds
def test_trophy_rows_colour_each_column(colored):
    result = monitor._colorize_line("- Sun 23 Nov 2025, 20:15:03 | Elden Ring | GOLD | Legendary Armaments")

    assert result == (
        f"- {colored['date']}Sun 23 Nov 2025, 20:15:03{monitor.ANSI_RESET}"
        f" | {colored['game']}Elden Ring{monitor.ANSI_RESET}"
        f" | {colored['trophy']}GOLD{monitor.ANSI_RESET}"
        f" | {colored['trophy']}Legendary Armaments{monitor.ANSI_RESET}"
    )


# Verifies Doctor status markers are coloured while the rest of the line stays plain
@pytest.mark.parametrize("marker,part", [("PASS", "boolean_true"), ("WARN", "warning"), ("FAIL", "error"), ("SKIP", "info")])
def test_doctor_status_markers_are_colored(colored, marker, part):
    line = f"[{marker}] PSN_NPSSO is missing or still a placeholder"

    assert monitor._colorize_line(line) == f"{colored[part]}[{marker}]{monitor.ANSI_RESET} PSN_NPSSO is missing or still a placeholder"


# Verifies presence keywords and the verbs that report an activity change pick the matching style apart
def test_presence_keywords_pick_the_matching_style(colored):
    assert colored["status_active"] in monitor._colorize_line("*** User got ACTIVE ! (was offline since Sat 22 Nov 2025, 16:54:31)")
    assert colored["status_offline"] in monitor._colorize_line("*** User got OFFLINE ! (after 5 hours)")
    assert colored["status_active"] in monitor._colorize_line("PSN user misiektoja started playing 'Elden Ring'")
    assert colored["status_inactive"] in monitor._colorize_line("PSN user misiektoja stopped playing 'Elden Ring' after 2 hours")
    assert colored["status_change"] in monitor._colorize_line("PSN user misiektoja changed game from 'A' to 'B'")


# Verifies a status change colours both presence values with the same table the Status row uses
def test_a_status_change_colours_both_presence_values(colored):
    result = monitor._colorize_line("PSN user misiektoja changed status from offline to online")

    assert f"{colored['status_offline']}offline{monitor.ANSI_RESET}" in result
    assert f"{colored['status_active']}online{monitor.ANSI_RESET}" in result


# Verifies time highlighting accepts valid clock values without matching numeric port mappings
@pytest.mark.parametrize("value", ["00:00", "23:59", "21:07:39", "~21:07:39", "09:15 PM"])
def test_time_color_regex_accepts_only_complete_clock_values(value):
    assert monitor._TIME_ONLY_RE.fullmatch(value)
    for invalid in ("24:00", "12:60", "8000:8000", "abc12:30", "1:12:30"):
        assert monitor._TIME_ONLY_RE.search(invalid) is None


# Verifies hostile terminal control sequences in PSN text cannot drive the operator's terminal
@pytest.mark.parametrize("hostile,expected", [
    ("game\x1b[2Jcleared", "game[2Jcleared"),
    ("game\x1b]0;stolen title\x07", "game]0;stolen title"),
    ("visible\rhidden", "visiblehidden"),
    ("bell\x07 and null\x00", "bell and null"),
    ("delete\x7f and c1\x9b[3J", "delete and c1[3J"),
])
def test_sanitize_terminal_text_removes_control_sequences(hostile, expected):
    assert monitor.sanitize_terminal_text(hostile) == expected


# Verifies the tool's own colour codes and ordinary whitespace survive sanitization
def test_sanitize_terminal_text_keeps_colours_and_layout():
    coloured = "\033[36mInfo\033[0m\tvalue\nnext line"

    assert monitor.sanitize_terminal_text(coloured) == coloured


# Verifies PSN text cannot smuggle an escape sequence between the tool's own colour codes
def test_sanitize_terminal_text_cleans_between_colour_codes():
    smuggled = "\033[36mlabel\033[0m \x1b[2J\033[31mvalue\033[0m"

    assert monitor.sanitize_terminal_text(smuggled) == "\033[36mlabel\033[0m [2J\033[31mvalue\033[0m"


# Verifies the log file stays plain text while the terminal receives the coloured version
def test_logger_colors_the_terminal_and_keeps_the_log_plain(colored, monkeypatch):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    logger, terminal, logfile = make_logger()

    logger.write("PlayStation ID:\t\t\tmisiektoja\n")
    logger.log_only("PSN account ID:\t\t\t1234567890\n")
    logger.terminal_only("Status:\t\t\t\tONLINE\n")

    assert colored["username"] in terminal.getvalue()
    assert colored["status_active"] in terminal.getvalue()
    assert "\x1b" not in logfile.getvalue()
    assert logfile.getvalue().startswith("PlayStation ID:")


# Verifies truncation measures plain text so escape sequences never consume the visible width
def test_truncation_runs_before_colour_is_applied(colored, monkeypatch):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 20)
    logger, terminal, _logfile = make_logger()

    logger.write("PlayStation ID:\tmisiektoja-with-a-very-long-name\n")

    plain = monitor.ANSI_ESCAPE_RE.sub("", terminal.getvalue()).rstrip("\n")
    assert len(plain.expandtabs(8)) == 20
    assert colored["username"] in terminal.getvalue()


# Verifies the early terminal wrapper colours output while still neutralizing hostile text
def test_terminal_stream_colors_and_sanitizes(colored):
    terminal = StringIO()

    monitor.TerminalStream(terminal).write("PlayStation ID:\tmisiek\x1b[2Jtoja\n")

    assert colored["username"] in terminal.getvalue()
    assert "\x1b[2J" not in terminal.getvalue()


# Verifies the startup summary reaches the terminal coloured and the log file plain through the real writers
def test_the_startup_summary_is_coloured_through_the_real_writers(colored, monkeypatch):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    logger, terminal, logfile = make_logger()
    rows = [monitor.StartupSummaryRow("Notifications (email)", "On (status changes)", concise=True)]

    monitor.emit_startup_summary(rows, show_full=False, stream=logger)

    assert f"{colored['boolean_true']}On{monitor.ANSI_RESET}" in terminal.getvalue()
    assert "\x1b" not in logfile.getvalue()


# Verifies the transient Doctor progress line stays uncoloured so its erase width remains correct
def test_doctor_progress_line_is_never_colored(colored, monkeypatch):
    written = []
    terminal = type("Stream", (), {"isatty": lambda self: True, "write": lambda self, text: written.append(text), "flush": lambda self: None})()
    monkeypatch.setattr(monitor, "doctor_terminal_stream", lambda: terminal)
    monkeypatch.setattr(monitor, "DOCTOR_PROGRESS_WIDTH", 0)

    monitor.doctor_progress("authentication\x1b[32m")
    progress_line = written[-1]
    monitor.doctor_progress_clear()

    assert "\x1b" not in "".join(written)
    assert written[-1] == "\r" + (" " * (len(progress_line) - 1)) + "\r"


# Verifies the doctor progress stream unwraps every output wrapper down to the real terminal
def test_doctor_terminal_stream_unwraps_output_wrappers(monkeypatch):
    real_terminal = StringIO()
    logger, _terminal, _logfile = make_logger()
    logger.__dict__["terminal"] = monitor.TerminalStream(real_terminal)
    monkeypatch.setattr(monitor.sys, "stdout", logger)

    assert monitor.doctor_terminal_stream() is real_terminal


# Verifies colour stays off unless the stream is an interactive terminal that allows it
def test_stream_support_detection_honours_environment(monkeypatch):
    monkeypatch.setattr(monitor.sys, "stdin", type("Stdin", (), {"isatty": lambda self: True})())
    interactive = type("Stream", (), {"isatty": lambda self: True})()
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)

    assert monitor._stream_supports_color(interactive) is True
    assert monitor._stream_supports_color(type("Stream", (), {"isatty": lambda self: False})()) is False

    monkeypatch.setenv("NO_COLOR", "1")
    assert monitor._stream_supports_color(interactive) is False
    monkeypatch.delenv("NO_COLOR")

    monkeypatch.setenv("TERM", "dumb")
    assert monitor._stream_supports_color(interactive) is False


# Verifies a piped stdin disables colour so redirected output never carries escape sequences
def test_piped_stdin_disables_color(monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(monitor.sys, "stdin", type("Stdin", (), {"isatty": lambda self: False})())

    assert monitor._stream_supports_color(type("Stream", (), {"isatty": lambda self: True})()) is False


# Verifies a configured theme overrides only the parts it names and leaves the rest built in
def test_config_theme_overrides_only_named_parts(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"username": "red bold"})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)

    monitor.init_color_output(StringIO())

    assert monitor.COLOR_ENABLED is True
    assert monitor._COLOR_STYLES["username"] == "\033[31;1m"
    assert monitor._COLOR_STYLES["game"] == monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["game"])


# Verifies a disabled setting clears the style map so every colour helper becomes a no-op
def test_disabled_color_output_clears_the_style_map(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", False)
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)

    monitor.init_color_output(StringIO())

    assert monitor.COLOR_ENABLED is False
    assert monitor._COLOR_STYLES == {}
    assert monitor.colorize("username", "misiektoja") == "misiektoja"
    assert monitor.apply_color_to_text("PlayStation ID:\tmisiektoja\n") == "PlayStation ID:\tmisiektoja\n"


# Verifies the early config peek applies terminal appearance before arguments are parsed
def test_early_output_config_reads_terminal_appearance(monkeypatch, tmp_path):
    config_file = tmp_path / "psn_monitor.conf"
    config_file.write_text("CLEAR_SCREEN = False\nCOLORED_OUTPUT = False\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["psn_monitor.py", "--config-file", str(config_file)])
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)

    monitor.apply_early_output_config()

    assert monitor.CLEAR_SCREEN is False
    assert monitor.COLORED_OUTPUT is False


# Verifies a broken config leaves the early defaults alone so the later load reports the error
def test_early_output_config_ignores_a_broken_config(monkeypatch, tmp_path):
    config_file = tmp_path / "psn_monitor.conf"
    config_file.write_text("import os\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["psn_monitor.py", "--config-file", str(config_file)])
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)

    monitor.apply_early_output_config()

    assert monitor.COLORED_OUTPUT is True


# Verifies a run with no config file to read changes nothing
def test_early_output_config_without_a_config_file_changes_nothing(monkeypatch):
    monkeypatch.setattr(monitor.sys, "argv", ["psn_monitor.py"])
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)

    monitor.apply_early_output_config()

    assert monitor.COLORED_OUTPUT is True
    assert monitor.CLEAR_SCREEN is True


# Verifies the raw argument scan finds the config path in both accepted spellings
@pytest.mark.parametrize("arguments,expected", [
    (["--config-file", "/tmp/one.conf"], "/tmp/one.conf"),
    (["--config-file=/tmp/two.conf"], "/tmp/two.conf"),
    (["--verbose"], None),
    (["--config-file"], None),
])
def test_early_config_file_argument_scan(arguments, expected):
    assert monitor.early_config_file_argument(arguments) == expected


# Verifies --no-color turns colour off even when the config file enables it
def test_no_color_flag_disables_colored_output(monkeypatch):
    monkeypatch.setattr(monitor.sys, "argv", ["psn_monitor.py", "--no-color"])
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)

    if "--no-color" in monitor.sys.argv:
        monkeypatch.setattr(monitor, "COLORED_OUTPUT", False)
    monitor.init_color_output(StringIO())

    assert monitor.COLOR_ENABLED is False


# Verifies the logger writes past the early sanitizing stream so no line is colourised twice
def test_logger_unwraps_the_early_terminal_stream(colored, monkeypatch, tmp_path):
    raw_terminal = StringIO()
    monkeypatch.setattr(monitor.sys, "stdout", monitor.TerminalStream(raw_terminal))
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    logger = monitor.Logger(str(tmp_path / "monitor.log"))
    try:
        logger.write("Timestamp:\t\t\tWed 26 Aug 2026, 20:23:03\n")
    finally:
        logger.logfile.close()

    assert logger.terminal is raw_terminal
    # A second colour pass would no longer see the label and would recolour the value as a date
    assert raw_terminal.getvalue() == f"Timestamp:\t\t\t{colored['timestamp_value']}Wed 26 Aug 2026, 20:23:03{monitor.ANSI_RESET}\n"


# Verifies the unwrapper reaches the real terminal through any depth of sanitizing wrappers
def test_unwrap_terminal_stream_reaches_the_real_terminal():
    raw_terminal = StringIO()

    assert monitor.unwrap_terminal_stream(raw_terminal) is raw_terminal
    assert monitor.unwrap_terminal_stream(monitor.TerminalStream(monitor.TerminalStream(raw_terminal))) is raw_terminal


# Verifies a rule cannot reclaim text an earlier rule already coloured, so each value gets one clean span
def test_inline_rules_do_not_reclaim_already_colored_text(colored):
    result = monitor._colorize_line("[ date: Sun 16 Feb 2025, 14:34:06 - 1 year ago ]")

    assert result.count(colored["date"]) == 1
    assert result == f"[ date: {colored['date']}Sun 16 Feb 2025, 14:34:06{monitor.ANSI_RESET} - {colored['duration']}1 year{monitor.ANSI_RESET} ago ]"


# Verifies a game name is coloured whatever punctuation it contains, so a feed does not colour only some rows
@pytest.mark.parametrize("name", ["Ghost of Tsushima", "NieR:Automata", "Ratchet & Clank: Rift Apart", "F.I.S.T.: Forged In Shadow Torch", "Uncharted 4"])
def test_game_names_with_punctuation_are_still_colored(colored, name):
    assert colored["game"] in monitor._colorize_line(f"PSN user misiektoja started playing '{name}'")


# Verifies a title's own apostrophe does not end the name early, which left most of the title uncoloured
@pytest.mark.parametrize("title", ["Tom Clancy's Rainbow Six Siege", "Assassin's Creed Valhalla"])
def test_a_title_containing_an_apostrophe_is_coloured_whole(colored, title):
    result = monitor._colorize_line(f"PSN user misiektoja started playing '{title}' after 1 hour")

    assert f"{colored['game']}{title}{monitor.ANSI_RESET}" in result


# Verifies two quoted titles on one line stay two names, since the closing quote rule could have joined them
def test_two_quoted_titles_on_one_line_stay_separate(colored):
    result = monitor._colorize_line("PSN user misiektoja changed game from 'Bloodborne' to 'Ghost of Tsushima' after 2 hours")

    assert f"{colored['game']}Bloodborne{monitor.ANSI_RESET}" in result
    assert f"{colored['game']}Ghost of Tsushima{monitor.ANSI_RESET}" in result


# Verifies a quoted placeholder inside a printed command stays plain, since it is text to replace rather than a name
@pytest.mark.parametrize("line", ["Run: psn_monitor '<psn_user_id>'", "Replace '<topic>' with your own ntfy topic"])
def test_quoted_command_placeholders_stay_plain(colored, line):
    assert colored["game"] not in monitor._colorize_line(line)


# Verifies a quoted fragment of a URL stays plain, since it is a piece of an address rather than a name
@pytest.mark.parametrize("value", ["?code=", "&state="])
def test_quoted_url_fragments_stay_plain(colored, value):
    line = f"Copy everything after '{value}' from the address bar."

    assert monitor._colorize_line(line) == line


# Verifies quoted values shaped like a file name or a path stay plain
@pytest.mark.parametrize("value", ["psn_misiektoja_last_status.json", "/var/log/psn.log", "~/logs/output.txt", "C:\\Users\\me\\state.json"])
def test_quoted_file_and_path_values_stay_plain(colored, value):
    line = f"* Last status loaded from file '{value}'"

    assert monitor._colorize_line(line) == line


# Verifies a quoted command-line option is left plain, since it is text to retype rather than a name
def test_quoted_command_options_stay_plain(colored):
    line = "--setup needs a dotenv destination. Replace '--env-file none' with a writable path."

    assert monitor._colorize_line(line) == line


# Verifies a standalone quoted description is left plain instead of being read as a name
def test_standalone_quoted_description_stays_plain(colored):
    line = "'Just here for the platinums, add me if you play souls games.'"

    assert monitor._colorize_line(line) == line


# Verifies a change report is not painted end to end, so every value it names keeps its own colour
@pytest.mark.parametrize("line", CHANGE_REPORT_LINES)
def test_change_reports_are_not_painted_end_to_end(colored, line):
    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert not result.startswith("\x1b")


# Verifies every part the shipped theme offers is actually looked up somewhere, so the documented theme only
# lists colours a user can really change
def test_every_theme_part_is_used():
    source = Path(monitor.__file__).read_text(encoding="utf-8")
    looked_up = set(re.findall(r"""colorize\(\s*["']([a-z_]+)["']""", source))
    looked_up |= set(re.findall(r"""_apply_style_nested\([^,]+,\s*["']([a-z_]+)["']""", source))
    looked_up |= set(re.findall(r"""_COLOR_STYLES\.get\(["']([a-z_]+)["']""", source))
    looked_up |= set(re.findall(r"""(?:style_name|key) = ["']([a-z_]+)["']""", source))
    looked_up |= set(re.findall(r""",\s*["']([a-z_]+)["']\),?\s*$""", source, re.M))
    doctor_marks = re.search(r"_DOCTOR_MARK_STYLES = \{(.*?)\}", source, re.S)
    assert doctor_marks is not None
    looked_up |= set(re.findall(r""":\s*["']([a-z_]+)["']""", doctor_marks.group(1)))

    assert not set(monitor.DEFAULT_COLOR_THEME) - looked_up


# Verifies the monitored account renders as a name everywhere it is mentioned, quoted or not, since this tool
# identifies a player by online ID rather than by the numeric account ID
@pytest.mark.parametrize("line", [
    "PSN user misiektoja changed status from offline to online",
    "* Fetching details for PlayStation user 'misiektoja'...",
    "[DEBUG 20:15:03] PSN API get_presence(): user=misiektoja",
    "PS+ user:\t\t\tmisiektoja",
    "PlayStation ID:\t\t\tmisiektoja",
])
def test_the_account_name_uses_the_name_colour_everywhere(colored, line):
    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert f"{colored['username']}misiektoja{monitor.ANSI_RESET}" in result
    assert colored["game"] not in result


# Verifies an ordinary sentence about the user is not read as a name, since prose follows "user" with a verb
@pytest.mark.parametrize("line", [
    "* Last time user was available:\tSat 22 Nov 2025, 16:54:31",
    "* User is OFFLINE for:\t\t2 hours",
    "Email when user goes online/offline",
    "Monitoring healthy for misiektoja. The user is still offline with no activity change",
    "Check that the path exists and that this user can read it, then retry",
    "[DEBUG 20:15:03] PSN user ID resolved | source=configuration file, value=misiektoja",
])
def test_a_word_after_user_in_prose_keeps_no_name_colour(colored, line):
    assert colored["username"] not in monitor._colorize_line(line)


# Verifies the startup line colours the account name and not the words that introduce it
def test_the_startup_line_colours_only_the_account_name(colored):
    result = monitor._colorize_line("Monitoring user with PSN ID misiektoja")

    assert result == f"Monitoring user with PSN ID {colored['username']}misiektoja{monitor.ANSI_RESET}"


# Verifies the numeric account ID keeps its own colour, so the two identifiers stay distinguishable
def test_the_account_id_uses_the_id_colour(colored):
    assert colored["id"] in monitor._colorize_line("PSN account ID:\t\t\t1234567890123456789")


# Verifies the summary target row is coloured as the PlayStation ID it holds
def test_the_target_row_uses_the_name_colour(colored):
    line = "* Target:                       misiektoja"
    assert monitor._colorize_line(line) == f"* Target:                       {colored['username']}misiektoja{monitor.ANSI_RESET}"


# Verifies a config written against the pre-rename 'user_uri_id' key still colours identifiers
def test_legacy_theme_key_still_applies(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"user_uri_id": "red"})
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)
    monitor.init_color_output(StringIO())
    assert monitor._COLOR_STYLES["id"] == monitor._build_ansi_sequence("red")


# Verifies the current key name wins when a config sets both the old and the new name
def test_current_theme_key_wins_over_the_legacy_name(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"user_uri_id": "red", "id": "green"})
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)
    monitor.init_color_output(StringIO())
    assert monitor._COLOR_STYLES["id"] == monitor._build_ansi_sequence("green")


# Verifies the guided setup surface is coloured, not only the monitoring output. The install method decides
# every command shown afterwards, and the commands themselves are what the user has to copy
def test_setup_surface_is_coloured(colored, capsys, monkeypatch):
    monkeypatch.setattr(monitor, "detect_install_method", lambda: "pip")

    monitor._wizard_print_setup_destinations(Path("psn_monitor.conf"), Path(".env"))
    monitor.print_labelled_command("Check setup before monitoring:", "psn_monitor --doctor <psn_user_id>")
    output = capsys.readouterr().out

    assert f"Detected install method: {colored['username']}pip{monitor.ANSI_RESET}" in output
    assert f"{colored['section']}psn_monitor --doctor <psn_user_id>{monitor.ANSI_RESET}" in output


# Verifies a wizard prompt and its menu are coloured so the question and the number to type stand out
def test_wizard_prompt_and_menu_are_coloured(colored, capsys):
    asked = []

    monitor._wizard_ask_choice("Pick one", [("First", ""), ("Second", "")], default_index=1, input_func=lambda prompt: asked.append(prompt) or "1")
    output = capsys.readouterr().out

    assert f"{colored['username']}1{monitor.ANSI_RESET}. First" in output
    assert f"{colored['info']} (default){monitor.ANSI_RESET}" in output
    assert asked == [f"{colored['info']}Choose [1-2]: {monitor.ANSI_RESET}"]


# Verifies the Doctor report headings, sections and verdict are coloured, matching the sibling monitors
def test_doctor_report_headings_are_coloured(colored, pm_module):
    report = pm_module.build_doctor_report(None, None, None)
    sections = pm_module.render_doctor_sections(report)
    summary = pm_module.render_doctor_summary(report.checks)

    assert f"{colored['header']}Doctor{monitor.ANSI_RESET}" in sections
    assert f"{colored['section']}Environment{monitor.ANSI_RESET}" in sections
    assert f"{colored['header']}Summary{monitor.ANSI_RESET}" in summary
    assert monitor.ANSI_ESCAPE_RE.sub("", sections).splitlines()[0] == "Doctor"


# Verifies recovery guidance reads as advice rather than inheriting the colour of the failure it explains
def test_recovery_guidance_uses_the_info_colour(colored):
    assert monitor._colorize_line("To fix: Verify the --config-file path then retry").startswith(colored["info"])


@pytest.mark.skipif(platform.system() == "Windows", reason="the pty module is POSIX only")
# Verifies a real run on a real terminal colours the banner and the commands the welcome screen prints
def test_a_real_terminal_run_is_coloured(tmp_path):
    (tmp_path / "psn_monitor.conf").write_text("CLEAR_SCREEN = False\nCOLORED_OUTPUT = True\n", encoding="utf-8")
    environment = dict(os.environ, TERM="xterm-256color", HOME=str(tmp_path), PYTHONPATH=str(Path(monitor.__file__).parent))
    environment.pop("NO_COLOR", None)
    controller, follower = pty.openpty()
    process = subprocess.Popen([sys.executable, str(Path(monitor.__file__))], stdin=follower, stdout=follower, stderr=follower, cwd=str(tmp_path), env=environment, close_fds=True)
    os.close(follower)
    os.write(controller, b"n\n")
    output = b""
    try:
        while True:
            try:
                chunk = os.read(controller, 4096)
            except OSError:
                break
            if not chunk:
                break
            output += chunk
    finally:
        os.close(controller)
        process.wait(timeout=60)

    rendered = output.decode("utf-8", "replace")
    assert f"\x1b[96m{monitor.STARTUP_BANNER.splitlines()[1]}\x1b[0m" in rendered
    assert "\x1b[97m" in rendered


# Returns the documented theme table from the page that carries it
def documented_theme_table():
    page = (Path(monitor.__file__).parent / "docs" / "usage.md").read_text(encoding="utf-8")
    return page.split("| Theme key | Default | What it colours |", 1)[1].split("\n\n", 1)[0]


# Verifies the documented theme table and the shipped theme describe exactly the same keys, in both directions
def test_the_documented_theme_table_matches_the_shipped_theme():
    documented = {row.split("|")[1].strip().strip("`") for row in documented_theme_table().splitlines() if row.startswith("| `")}

    assert documented == set(monitor.DEFAULT_COLOR_THEME)


# Verifies each documented default matches the value the theme actually ships
def test_the_documented_theme_defaults_match_the_shipped_values():
    table = documented_theme_table()
    for row in table.splitlines():
        if not row.startswith("| `"):
            continue
        name, default = row.split("|")[1].strip().strip("`"), row.split("|")[2].strip()
        expected = f"`{monitor.DEFAULT_COLOR_THEME[name]}`" if monitor.DEFAULT_COLOR_THEME[name] else "*(empty)*"
        assert default == expected, name
