"""Tests for secret redaction, terminal safety and the single output layer.

These cover the plumbing every other user-facing surface prints through: what reaches
the screen, what reaches the log file and what is removed from either on the way.
"""

import io
import os
import re

import pytest


MODULE_SOURCE = io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "psn_monitor.py"), encoding="utf-8").read()


# Builds a Logger whose terminal side is a buffer the test can read back
def logger_with_buffer(pm_module, monkeypatch, tmp_path):
    buffer = io.StringIO()
    monkeypatch.setattr(pm_module.sys, "stdout", buffer)
    return pm_module.Logger(str(tmp_path / "psn_monitor_test.log")), buffer


# Verifies a real credential is removed wherever it appears, not only in a known message shape
def test_a_full_length_secret_is_redacted_wherever_it_appears(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "aVeryLongNpssoValue1234567890")

    redacted = pm_module.sanitize_error_text("PSN refused the request for aVeryLongNpssoValue1234567890 twice")

    assert "aVeryLongNpssoValue1234567890" not in redacted
    assert redacted.count("<redacted>") == 1


# Verifies a short configured password is not replaced in ordinary text, where it is also an ordinary word
def test_a_short_secret_is_left_alone_in_ordinary_text(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "ghost")

    assert pm_module.sanitize_error_text("Cannot read title 'Ghost of ghost island'") == "Cannot read title 'Ghost of ghost island'"


# Verifies the length floor does not stop a short secret being redacted where an error really exposes one
@pytest.mark.parametrize("text", [
    "SMTP_PASSWORD = ghost",
    "Cookie: npsso=ghost; other=1",
    "Authorization: Bearer ghost",
    '{"refresh_token": "ghost"}',
])
def test_a_short_secret_is_still_redacted_where_it_is_exposed(pm_module, monkeypatch, text):
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "ghost")

    redacted = pm_module.sanitize_error_text(text)

    assert "ghost" not in redacted
    assert "<redacted>" in redacted


# Verifies a secret that contains another one is redacted whole, since replacing the shorter value first
# would leave the rest of the longer one on screen
def test_a_secret_containing_another_secret_is_redacted_whole(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "npssoValue1234567890")
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "aVeryLongnpssoValue1234567890tail")

    redacted = pm_module.sanitize_error_text("PSN refused aVeryLongnpssoValue1234567890tail")

    assert redacted == "PSN refused <redacted>"


# Verifies a placeholder that was never filled in is not treated as a secret worth redacting
def test_placeholder_values_are_not_treated_as_secrets(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "your_psn_npsso_code")
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "your_smtp_password")

    assert pm_module.known_secret_values() == []


# The printers that redact on the caller's behalf, so a call site does not have to name the redactor itself
SANITIZING_PRINTERS = ("sanitize_error_text", "debug_print(", "verbose_print(")


# Guards the rule that no printed exception may reach a user without passing through the redactor
def test_every_printed_exception_goes_through_the_redactor():
    unguarded = [line.strip() for line in MODULE_SOURCE.split("\n") if "print(" in line and "{e}" in line and not any(printer in line for printer in SANITIZING_PRINTERS)]

    assert unguarded == []


# Guards the exemption above, which is only sound while both diagnostic printers redact what they are given
@pytest.mark.parametrize("printer", ["debug_print", "verbose_print"])
def test_the_diagnostic_printers_redact_what_they_print(pm_module, monkeypatch, capsys, printer):
    monkeypatch.setattr(pm_module, "DEBUG_MODE", True)
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", True)
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "aVeryLongNpssoValue1234567890")

    getattr(pm_module, printer)("token aVeryLongNpssoValue1234567890 refused")

    printed = capsys.readouterr().out
    assert "aVeryLongNpssoValue1234567890" not in printed
    assert "<redacted>" in printed


# Verifies PSN-supplied text cannot move the cursor, clear the screen or retitle the terminal window
@pytest.mark.parametrize("hostile", [
    "\x1b[2J",
    "\x1b[10A",
    "\x1b]0;owned\x07",
    "done\rowned",
    "bell\x07",
])
def test_hostile_remote_text_cannot_drive_the_terminal(pm_module, hostile):
    cleaned = pm_module.sanitize_terminal_text(f"Now playing '{hostile}'")

    assert "\x1b" not in cleaned
    assert "\r" not in cleaned
    assert "\x07" not in cleaned


# Verifies the tool's own colour sequences survive a pass through its writers, which a strict sanitizer would eat
def test_colour_sequences_survive_the_terminal_sanitizer(pm_module):
    assert pm_module.sanitize_terminal_text("\x1b[31mred\x1b[0m") == "\x1b[31mred\x1b[0m"


# Verifies a hostile sequence next to a colour sequence is still removed, so one cannot smuggle the other through
def test_hostile_text_beside_a_colour_sequence_is_still_removed(pm_module):
    assert pm_module.sanitize_terminal_text("\x1b[31mred\x1b[0m\x1b[2Jgone") == "\x1b[31mred\x1b[0m[2Jgone"


# Verifies tabs and newlines are kept, since the output relies on both for its column layout
def test_layout_whitespace_is_kept(pm_module):
    assert pm_module.sanitize_terminal_text("a\tb\nc") == "a\tb\nc"


# Verifies text bound for a file or an email loses colour as well as control characters
def test_plain_text_strips_colour_and_control_characters(pm_module):
    assert pm_module.plain_text("\x1b[31mGhost\x1b[0m\x07 of\rTsushima") == "Ghost ofTsushima"


# Verifies truncation measures what is displayed, so colour codes do not eat into the visible width
def test_truncation_measures_display_width_not_escape_sequences(pm_module):
    pytest.importorskip("wcwidth")

    truncated = pm_module.truncate_string_per_line("\x1b[31m0123456789ABCDEF\x1b[0m", 10)

    assert re.sub(r"\x1b\[[0-9;]*m", "", truncated) == "0123456789"


# Verifies a double-width character costs two columns, so a CJK title does not wrap past the limit
def test_truncation_counts_double_width_characters(pm_module):
    pytest.importorskip("wcwidth")

    assert pm_module.truncate_string_per_line("原神原神原神", 4) == "原神"


# Verifies each line is measured on its own rather than the whole message being cut at one offset
def test_truncation_applies_to_every_line(pm_module):
    pytest.importorskip("wcwidth")

    assert pm_module.truncate_string_per_line("abcdef\nabcdef", 3) == "abc\nabc"


# Verifies the command line width wins over the configured one
def test_truncation_width_prefers_the_command_line(pm_module):
    assert pm_module.resolve_truncate_chars(80, 120, False) == 80
    assert pm_module.resolve_truncate_chars(None, 120, False) == 120


# Verifies truncation is off without a log file, where the trimmed text would be lost for good
def test_truncation_is_disabled_when_logging_is_disabled(pm_module):
    assert pm_module.resolve_truncate_chars(120, 120, True) == 0


# Verifies the sentinel expands to the detected terminal width and says what it detected
def test_truncation_sentinel_expands_to_the_terminal_width(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module.shutil, "get_terminal_size", lambda: os.terminal_size((132, 40)))

    assert pm_module.resolve_truncate_chars(999, 0, False) == 132
    assert "132 characters" in capsys.readouterr().out


# Verifies the logger writes straight to the real terminal, so sanitizing and colouring happen exactly once
def test_logger_unwraps_the_early_terminal_stream(pm_module, monkeypatch, tmp_path):
    real_terminal = io.StringIO()
    monkeypatch.setattr(pm_module.sys, "stdout", pm_module.TerminalStream(pm_module.TerminalStream(real_terminal)))

    logger = pm_module.Logger(str(tmp_path / "psn_monitor_test.log"))

    assert logger.terminal is real_terminal


# Verifies the log file stays plain text, so a viewer or a grep never meets an escape sequence
def test_log_file_contains_no_escape_sequences(pm_module, monkeypatch, tmp_path):
    monkeypatch.setattr(pm_module, "TRUNCATE_CHARS", 0)
    logger, _ = logger_with_buffer(pm_module, monkeypatch, tmp_path)

    logger.write("\x1b[31mUser misiektoja started playing\x1b[0m\n")
    logger.logfile.flush()

    assert "\x1b" not in io.open(logger.logfile.name, encoding="utf-8").read()


# Verifies the screen copy is shortened while the log file keeps the whole line
def test_truncation_shortens_the_screen_copy_only(pm_module, monkeypatch, tmp_path):
    pytest.importorskip("wcwidth")
    monkeypatch.setattr(pm_module, "TRUNCATE_CHARS", 10)
    logger, buffer = logger_with_buffer(pm_module, monkeypatch, tmp_path)

    logger.write("0123456789ABCDEF\n")
    logger.logfile.flush()

    assert buffer.getvalue() == "0123456789\n"
    assert "0123456789ABCDEF" in io.open(logger.logfile.name, encoding="utf-8").read()


# Verifies the logger removes control sequences from what it prints as well as from what it logs
def test_logger_sanitizes_both_copies(pm_module, monkeypatch, tmp_path):
    monkeypatch.setattr(pm_module, "TRUNCATE_CHARS", 0)
    logger, buffer = logger_with_buffer(pm_module, monkeypatch, tmp_path)

    logger.write("Now playing 'done\x1b[2Jowned'\n")
    logger.logfile.flush()

    assert "\x1b" not in buffer.getvalue()
    assert "\x1b" not in io.open(logger.logfile.name, encoding="utf-8").read()


# Verifies output printed before the logging policy is known is sanitized too, such as the --info report
def test_early_terminal_stream_sanitizes_output(pm_module):
    real_terminal = io.StringIO()

    pm_module.TerminalStream(real_terminal).write("About me: \x1b]0;owned\x07\n")

    assert real_terminal.getvalue() == "About me: ]0;owned\n"


# Verifies the early stream still behaves like the stream it replaced
def test_early_terminal_stream_forwards_stream_attributes(pm_module):
    real_terminal = io.StringIO()

    assert pm_module.TerminalStream(real_terminal).writable() is True


# Verifies a game name from PSN cannot carry control sequences into the CSV history file
def test_csv_game_name_loses_control_sequences(pm_module, tmp_path):
    csv_path = tmp_path / "history.csv"
    pm_module.init_csv_file(str(csv_path))

    pm_module.write_csv_entry(str(csv_path), "2026-08-31 10:00:00", "online", "Ghost\x1b[2J of\r Tsushima")

    written = csv_path.read_text(encoding="utf-8")
    assert "\x1b" not in written
    assert "Ghost of Tsushima" in written


# Verifies a cut line closes the colour it opened, so the truncated tail does not paint every line printed after it
def test_a_truncated_line_closes_its_open_colour(pm_module):
    pytest.importorskip("wcwidth")

    assert pm_module.truncate_string_per_line("\x1b[31m0123456789ABCDEF\x1b[0m", 10) == "\x1b[31m0123456789" + pm_module.ANSI_RESET


# Verifies no extra reset is added when the colour closed before the cut or the line was never cut
def test_a_closed_or_uncut_colour_gains_no_extra_reset(pm_module):
    pytest.importorskip("wcwidth")

    assert pm_module.truncate_string_per_line("\x1b[31m0123\x1b[0m456789ABCDEF", 10) == "\x1b[31m0123\x1b[0m456789"
    assert pm_module.truncate_string_per_line("\x1b[31m0123\x1b[0m", 10) == "\x1b[31m0123\x1b[0m"
    assert pm_module.truncate_string_per_line("0123456789ABCDEF", 10) == "0123456789"
