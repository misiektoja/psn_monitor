"""Tests for the startup summary rows, where each one is shown and the welcome screen."""

import pytest


# Collects what the terminal and the log file were each given, the way the real Logger splits them
class RoutedStream:
    def __init__(self):
        self.terminal = []
        self.log = []

    # Records text meant only for the reader at the terminal
    def terminal_only(self, message):
        self.terminal.append(message)

    # Records text meant only for the log file
    def log_only(self, message):
        self.log.append(message)

    # Present because every stream the tool writes to has one
    def flush(self):
        pass

    # Returns what the terminal was shown
    def terminal_text(self):
        return "".join(self.terminal)

    # Returns what the log file kept
    def log_text(self):
        return "".join(self.log)


@pytest.fixture
# Builds the summary rows with settings that make every optional feature visible and predictable
def summary_rows(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "PSN_CHECK_INTERVAL", 600)
    monkeypatch.setattr(pm_module, "PSN_ACTIVE_CHECK_INTERVAL", 30)
    monkeypatch.setattr(pm_module, "LIVENESS_CHECK_INTERVAL", 43200)
    monkeypatch.setattr(pm_module, "CSV_FILE", "history.csv")
    monkeypatch.setattr(pm_module, "TRUNCATE_CHARS", 100)
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", False)
    monkeypatch.setattr(pm_module, "DEBUG_MODE", False)
    return pm_module.build_startup_summary("misiektoja", "psn_monitor.conf", ".env", "psn_monitor_misiektoja.log")


# Returns the row with the given label, failing the test when the summary has no such row
def row_named(rows, label):
    matched = [row for row in rows if row.label == label]
    assert len(matched) == 1, f"expected exactly one {label!r} row, found {len(matched)}"
    return matched[0]


# Verifies a row is part of the full view and the log file unless it opts out, and stays out of the concise view
def test_a_row_is_full_view_only_until_it_opts_in(pm_module):
    row = pm_module.StartupSummaryRow("Some setting", "some value")

    assert row.concise is False
    assert row.full is True
    assert row.log is True


# Verifies the concise view stays short and the full view is a superset of the settings it reports
def test_the_full_view_reports_more_settings_than_the_concise_one(summary_rows):
    concise = {row.label for row in summary_rows if row.concise}
    full = {row.label for row in summary_rows if row.full}

    assert len(concise) < len(full)
    # The two rows the concise view uses to orient a new reader have a better place in the full view
    assert concise - full == {"Output", "More details"}


# Verifies the pointer at the two flags is dropped once the reader has used one of them
def test_the_flag_pointer_is_concise_view_only(summary_rows):
    pointer = row_named(summary_rows, "More details")

    assert pointer.concise is True
    assert pointer.full is False
    assert pointer.log is False


# Verifies every file the tool can be configured to write is named in the full view with its effective path
def test_the_full_view_names_every_generated_file(summary_rows):
    for label, expected in (("Output logging", "psn_monitor_misiektoja.log"), ("Status file", "psn_misiektoja_last_status.json"), ("CSV output", "history.csv")):
        row = row_named(summary_rows, label)
        assert row.full is True
        assert expected in str(row.value)


# Verifies the log file keeps the complete summary even when the terminal was shown the concise view
def test_the_log_file_keeps_the_full_summary_whatever_the_terminal_showed(pm_module, summary_rows):
    stream = RoutedStream()

    pm_module.emit_startup_summary(summary_rows, show_full=False, stream=stream)

    terminal = stream.terminal_text()
    log = stream.log_text()
    assert "Install method:" not in terminal
    assert "Install method:" in log
    assert "Local timezone:" not in terminal
    assert "Local timezone:" in log


# Verifies the two orientation rows never reach the log file, which already records the same facts
def test_terminal_only_rows_are_kept_out_of_the_log(pm_module, summary_rows):
    stream = RoutedStream()

    pm_module.emit_startup_summary(summary_rows, show_full=True, stream=stream)

    log = stream.log_text()
    assert "* Output:" not in log
    assert "More details:" not in log
    assert "Output logging:" in log


# Verifies a plain stream that cannot route rows still gets one complete view rather than nothing
def test_an_unrouted_stream_receives_the_requested_view(pm_module, summary_rows):
    class PlainStream:
        def __init__(self):
            self.text = ""

        def write(self, message):
            self.text += message

        def flush(self):
            pass

    concise, full = PlainStream(), PlainStream()

    pm_module.emit_startup_summary(summary_rows, show_full=False, stream=concise)
    pm_module.emit_startup_summary(summary_rows, show_full=True, stream=full)

    assert "More details:" in concise.text
    assert "Install method:" not in concise.text
    assert "Install method:" in full.text
    assert "More details:" not in full.text


# Verifies the summary ends with one blank line, so the next heading starts at the cursor
def test_the_summary_ends_with_a_single_blank_line(pm_module, summary_rows):
    stream = RoutedStream()

    pm_module.emit_startup_summary(summary_rows, show_full=False, stream=stream)

    assert stream.terminal_text().endswith("\n\n")
    assert not stream.terminal_text().endswith("\n\n\n")


# Verifies every value starts in the same column, so the summary reads as a table
def test_values_line_up_in_one_column(pm_module, summary_rows):
    rendered = [pm_module.format_startup_summary_row(row) for row in summary_rows]

    columns = {line.index(str(row.value).split(" ")[0]) for row, line in zip(summary_rows, rendered, strict=True) if row.value}
    assert len(columns) == 1


# Verifies the email rollup names what is switched on instead of printing three separate booleans
def test_the_notification_row_names_what_is_enabled(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "ACTIVE_INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "GAME_CHANGE_NOTIFICATION", False)
    monkeypatch.setattr(pm_module, "ERROR_NOTIFICATION", True)

    assert pm_module.startup_notification_state() == "On (status changes, errors)"


# Verifies the rollup says so plainly when no email alert can fire
def test_the_notification_row_reports_when_everything_is_off(pm_module, monkeypatch):
    for name in ("ACTIVE_INACTIVE_NOTIFICATION", "GAME_CHANGE_NOTIFICATION", "ERROR_NOTIFICATION"):
        monkeypatch.setattr(pm_module, name, False)

    assert pm_module.startup_notification_state() == "Off"


# Verifies the webhook rollup names what is switched on and which service would receive it
def test_the_webhook_row_names_the_alerts_and_the_service(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(pm_module, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(pm_module, "WEBHOOK_ERROR_NOTIFICATION", True)

    assert pm_module.startup_webhook_notification_state() == "On (status changes, errors) through ntfy"


# Verifies the rollup reports the resolved state, so selected alerts with the channel off still read Off
def test_the_webhook_row_reports_the_channel_being_off(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(pm_module, "WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION", True)

    assert pm_module.startup_webhook_notification_state() == "Off"


# Verifies both channels get their own concise row, so neither is mistaken for the other
def test_each_channel_has_its_own_row(summary_rows):
    for label in ("Notifications (email)", "Notifications (webhook)"):
        assert row_named(summary_rows, label).concise is True


# Verifies a long webhook rollup wraps under its own label instead of running past the column
def test_a_long_webhook_rollup_wraps_under_its_label(pm_module):
    row = pm_module.StartupSummaryRow("Notifications (webhook)", "On (" + ", ".join(["a long alert name"] * 8) + ") through Discord", concise=True)

    lines = pm_module.format_startup_summary_row(row).splitlines()

    assert len(lines) > 1
    assert all(len(line) <= 100 for line in lines)
    assert lines[1].startswith(" " * 32)


# Verifies disabled logging is reported as such rather than leaving the reader guessing where output went
def test_disabled_logging_is_named_in_both_views(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "CSV_FILE", None)
    rows = pm_module.build_startup_summary("misiektoja", None, None, None)

    assert row_named(rows, "Output").value == "Terminal only (logging disabled)"
    assert row_named(rows, "Output logging").value == "Disabled"
    assert row_named(rows, "CSV output").value == "Disabled"


# Verifies either diagnostic flag asks for the full view, since both of them report settings
@pytest.mark.parametrize("verbose,debug,expected", [(False, False, False), (True, False, True), (False, True, True), (True, True, True)])
def test_either_flag_asks_for_the_full_view(pm_module, monkeypatch, verbose, debug, expected):
    monkeypatch.setattr(pm_module, "VERBOSE_MODE", verbose)
    monkeypatch.setattr(pm_module, "DEBUG_MODE", debug)

    assert pm_module.full_startup_summary_enabled() is expected


# Verifies the welcome screen renders its commands the way this copy of the tool is actually started
@pytest.mark.parametrize("method,prefix", [("pip", "psn_monitor"), ("manual", "psn_monitor.py")])
def test_the_welcome_screen_uses_the_detected_install_method(pm_module, monkeypatch, capsys, method, prefix):
    monkeypatch.setattr(pm_module, "detect_install_method", lambda: method)

    assert pm_module.print_welcome_screen() == 1

    output = capsys.readouterr().out
    assert f"{prefix} <psn_user_id>" in output
    assert f"{prefix} --doctor <psn_user_id>" in output
    assert f"{prefix} -i <psn_user_id>" in output
    assert f"{prefix} --help" in output


# Verifies the welcome screen says what a PSN ID is, since the wrong value is the common first mistake
def test_the_welcome_screen_explains_the_target(pm_module, capsys):
    pm_module.print_welcome_screen()

    output = capsys.readouterr().out
    assert pm_module.PSN_TARGET_FORMS in output
    assert output.endswith("\n")


# Verifies the welcome screen never prints a secret it happens to have loaded
def test_the_welcome_screen_prints_no_secrets(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "PSN_NPSSO", "npsso-secret-value")

    pm_module.print_welcome_screen()

    assert "npsso-secret-value" not in capsys.readouterr().out


# Verifies the real logger writes the full summary to the file while the terminal keeps the concise view
def test_the_real_logger_splits_the_summary(pm_module, monkeypatch, tmp_path, summary_rows, capsys):
    log_file = tmp_path / "psn_monitor.log"
    logger = pm_module.Logger(str(log_file))

    pm_module.emit_startup_summary(summary_rows, show_full=False, stream=logger)
    logger.flush()

    saved = log_file.read_text(encoding="utf-8")
    shown = capsys.readouterr().out
    assert "Install method:" in saved
    assert "Install method:" not in shown
    assert "Polling intervals:" in saved
    assert "Polling intervals:" in shown
    # The log file stays plain text, whichever writer put the line there
    assert "\x1b" not in saved
    assert "\t" not in saved


# The rows shared with the sibling monitors, in the order every one of them prints
SHARED_ROW_ORDER = ("Target", "Polling intervals", "Notifications (email)", "Notifications (webhook)", "Output", "Output logging", "Config", "Dotenv", "Liveness output", "CSV output", "Terminal truncation", "Local timezone", "Install method", "Secrets from dotenv", "Secrets from environment", "Secrets from config file", "TLS verification", "ASCII log separators", "Coloured output", "Verbose mode", "Debug mode", "More details")


# Verifies the shared rows keep the order and the label column width every sibling monitor prints
def test_the_shared_summary_rows_match_the_sibling_tools(summary_rows):
    assert [row.label for row in summary_rows if row.label in SHARED_ROW_ORDER] == list(SHARED_ROW_ORDER)
    # The renderer pads "<label>:" into a 30-character column, so a longer label swallows the separating space
    assert max(len(row.label) for row in summary_rows) <= 28


# Verifies the selected PlayStation banner remains exact and version independent
def test_selected_banner_exact_content(pm_module):
    assert pm_module.STARTUP_BANNER == r"""
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


# Verifies the art is portable, bounded and free of trailing whitespace
def test_banner_ascii_width_and_whitespace(pm_module):
    pm_module.STARTUP_BANNER.encode("ascii")
    lines = pm_module.STARTUP_BANNER.splitlines()
    assert max(map(len, lines)) <= 90
    assert all(line == line.rstrip() for line in lines)


# Verifies the PSN wordmark matches the standard FIGlet rows at the shared body column
def test_banner_psn_wordmark_rows(pm_module):
    assert [line[21:] for line in pm_module.STARTUP_BANNER.splitlines()[1:6]] == [
        " ____  ____  _   _",
        "|  _ \\/ ___|| \\ | |",
        "| |_) \\___ \\|  \\| |",
        "|  __/ ___) | |\\  |",
        "|_|   |____/|_| \\_|",
    ]


# Verifies the Monitor wordmark matches the standard FIGlet rows at the shared body column
def test_banner_monitor_wordmark_rows(pm_module):
    assert [line[21:] for line in pm_module.STARTUP_BANNER.splitlines()[7:12]] == [
        " __  __             _ _",
        "|  \\/  | ___  _ __ (_) |_ ___  _ __",
        "| |\\/| |/ _ \\| '_ \\| | __/ _ \\| '__|",
        "| |  | | (_) | | | | | || (_) | |",
        "|_|  |_|\\___/|_| |_|_|\\__\\___/|_|",
    ]


# Verifies PSN, Monitor and the version share the same body column
def test_banner_version_alignment(pm_module):
    banner_lines = pm_module.STARTUP_BANNER.splitlines()
    psn_body_column = banner_lines[2].index("|  _ \\")
    monitor_body_indent = len(banner_lines[8]) - len(banner_lines[8].lstrip())
    assert psn_body_column == monitor_body_indent == 21


# Verifies the printed version stays dynamic and followed by one blank line
def test_banner_dynamic_version_line(pm_module, monkeypatch, capsys):
    monkeypatch.setattr(pm_module, "VERSION", "9.9-test")
    monkeypatch.setattr(pm_module, "COLOR_ENABLED", False)

    pm_module.print_startup_banner()

    assert capsys.readouterr().out == pm_module.STARTUP_BANNER + "\n" + (" " * 21) + "v9.9-test\n\n"


# Verifies an unedited placeholder is never reported as a loaded secret, whichever layer recorded it
def test_placeholder_secrets_are_not_reported_as_loaded(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "SECRET_SOURCES", {"WEBHOOK_URL": "dotenv file", "SMTP_PASSWORD": "configuration file"})
    monkeypatch.setattr(pm_module, "WEBHOOK_URL", "your_webhook_url")
    monkeypatch.setattr(pm_module, "SMTP_PASSWORD", "your_smtp_password")

    reported = [name for names in pm_module.doctor_secret_sources().values() for name in names]

    assert "WEBHOOK_URL" not in reported
    assert "SMTP_PASSWORD" not in reported
