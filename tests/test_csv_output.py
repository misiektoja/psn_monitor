"""Tests for the CSV history file the tool writes alongside the log."""

import csv
from datetime import datetime

import pytest


# Verifies a new file gets the documented header row
def test_new_file_starts_with_the_header(pm_module, tmp_path):
    target = tmp_path / "history.csv"

    pm_module.init_csv_file(str(target))

    assert target.read_text(encoding="utf-8").splitlines()[0] == '"Date","Status","Game name"'
    assert list(csv.reader(target.open(encoding="utf-8")))[0] == pm_module.csvfieldnames


# Verifies an existing history keeps its rows instead of being re-headered on restart
def test_existing_history_is_not_rewritten(pm_module, tmp_path):
    target = tmp_path / "history.csv"
    pm_module.init_csv_file(str(target))
    pm_module.write_csv_entry(str(target), datetime(2026, 1, 1, 12, 0, 0), "online", "Bloodborne")

    pm_module.init_csv_file(str(target))

    rows = list(csv.DictReader(target.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["Status"] == "online"


# Verifies an empty leftover file is given a header rather than left unusable
def test_empty_file_is_given_a_header(pm_module, tmp_path):
    target = tmp_path / "history.csv"
    target.write_text("", encoding="utf-8")

    pm_module.init_csv_file(str(target))

    assert target.read_text(encoding="utf-8").strip() == '"Date","Status","Game name"'


# Verifies each status change is appended as its own row in the documented column order
def test_status_changes_are_appended_in_order(pm_module, tmp_path):
    target = tmp_path / "history.csv"
    pm_module.init_csv_file(str(target))

    pm_module.write_csv_entry(str(target), datetime(2026, 1, 1, 12, 0, 0), "online", "")
    pm_module.write_csv_entry(str(target), datetime(2026, 1, 1, 12, 5, 0), "online", "Bloodborne")
    pm_module.write_csv_entry(str(target), datetime(2026, 1, 1, 13, 0, 0), "offline", "")

    rows = list(csv.DictReader(target.open(encoding="utf-8")))
    assert [row["Status"] for row in rows] == ["online", "online", "offline"]
    assert [row["Game name"] for row in rows] == ["", "Bloodborne", ""]
    assert rows[1]["Date"] == "2026-01-01 12:05:00"


# Verifies a title containing a comma or a quote is quoted so the file stays parsable
def test_titles_with_separators_stay_parsable(pm_module, tmp_path):
    target = tmp_path / "history.csv"
    pm_module.init_csv_file(str(target))

    pm_module.write_csv_entry(str(target), datetime(2026, 1, 1, 12, 0, 0), "online", 'Bloodborne, "Old Hunters"')

    rows = list(csv.DictReader(target.open(encoding="utf-8")))
    assert rows[0]["Game name"] == 'Bloodborne, "Old Hunters"'


# Verifies a title with non-ASCII-safe punctuation survives the round trip through the file
def test_unicode_titles_round_trip(pm_module, tmp_path):
    target = tmp_path / "history.csv"
    pm_module.init_csv_file(str(target))

    pm_module.write_csv_entry(str(target), datetime(2026, 1, 1, 12, 0, 0), "online", "Ni no Kuni II: Revenant Kingdom")

    rows = list(csv.DictReader(target.open(encoding="utf-8")))
    assert rows[0]["Game name"] == "Ni no Kuni II: Revenant Kingdom"


# Verifies an unwritable path is reported with the file name instead of surfacing a bare OS error
def test_unwritable_path_is_reported_with_the_file_name(pm_module, tmp_path):
    unreachable = tmp_path / "missing-directory" / "history.csv"

    with pytest.raises(RuntimeError, match="Could not initialize CSV file"):
        pm_module.init_csv_file(str(unreachable))

    with pytest.raises(RuntimeError, match="Failed to write to CSV file"):
        pm_module.write_csv_entry(str(unreachable), datetime(2026, 1, 1, 12, 0, 0), "online", "")
