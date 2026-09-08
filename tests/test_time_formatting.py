"""Tests for the duration, timestamp and timezone helpers used across the output."""

from datetime import datetime, timezone

import pytest


@pytest.fixture(autouse=True)
# Pins the timezone so the rendered timestamps do not depend on the machine running the suite
def utc_timezone(monkeypatch, pm_module):
    monkeypatch.setattr(pm_module, "LOCAL_TIMEZONE", "UTC")


@pytest.mark.parametrize("seconds,expected", [
    (0, "0 seconds"),
    (-5, "0 seconds"),
    (1, "1 second"),
    (59, "59 seconds"),
    (60, "1 minute"),
    (90, "1 minute, 30 seconds"),
    (3600, "1 hour"),
    (3661, "1 hour, 1 minute"),
    (86400, "1 day"),
    (604800, "1 week"),
])
# Verifies polling intervals and session lengths are rendered in the units a reader expects
def test_durations_are_rendered_in_readable_units(pm_module, seconds, expected):
    assert pm_module.display_time(seconds) == expected


# Verifies granularity limits how many units are printed, which keeps subject lines short
def test_duration_granularity_limits_the_units_shown(pm_module):
    assert pm_module.display_time(90061, granularity=1) == "1 day"
    assert pm_module.display_time(90061, granularity=3) == "1 day, 1 hour, 1 minute"


# Verifies a span between two epoch timestamps is described from the larger unit down
def test_timespan_between_epoch_timestamps(pm_module):
    start = 1767226800
    assert pm_module.calculate_timespan(start + 3661, start) == "1 hour, 1 minute, 1 second"


# Verifies the span is the same regardless of which timestamp is passed first
def test_timespan_is_order_independent(pm_module):
    start = 1767226800
    assert pm_module.calculate_timespan(start, start + 7200) == pm_module.calculate_timespan(start + 7200, start)


# Verifies datetime objects, floats and ISO strings are all accepted, since each reaches this helper somewhere
def test_timespan_accepts_every_supported_input_type(pm_module):
    earlier = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    later = datetime(2026, 1, 1, 14, 30, 0, tzinfo=timezone.utc)

    assert pm_module.calculate_timespan(later, earlier) == "2 hours, 30 minutes"
    assert pm_module.calculate_timespan(later.timestamp(), earlier.timestamp()) == "2 hours, 30 minutes"
    assert pm_module.calculate_timespan("2026-01-01T14:30:00Z", "2026-01-01T12:00:00Z") == "2 hours, 30 minutes"


# Verifies a naive datetime is read as UTC rather than silently shifting the result
def test_timespan_treats_naive_datetimes_as_utc(pm_module):
    naive = datetime(2026, 1, 1, 12, 0, 0)
    aware = datetime(2026, 1, 1, 15, 0, 0, tzinfo=timezone.utc)

    assert pm_module.calculate_timespan(aware, naive) == "3 hours"


# Verifies weeks can be folded into days, which the shorter notification lines rely on
def test_timespan_can_hide_weeks(pm_module):
    start = 1767226800
    ten_days = start + 10 * 86400

    assert pm_module.calculate_timespan(ten_days, start) == "1 week, 3 days"
    assert pm_module.calculate_timespan(ten_days, start, show_weeks=False) == "10 days"


# Verifies seconds are still shown for a sub-minute span even when the caller suppressed them
def test_short_spans_keep_seconds_even_when_suppressed(pm_module):
    start = 1767226800

    assert pm_module.calculate_timespan(start + 30, start, show_seconds=False) == "30 seconds"


# Verifies an identical pair of timestamps reports no elapsed time
def test_identical_timestamps_report_zero(pm_module):
    assert pm_module.calculate_timespan(1767226800, 1767226800) == "0 seconds"


@pytest.mark.parametrize("value", [None, object(), "not a timestamp"])
# Verifies an unusable value produces an empty string instead of raising inside the monitoring loop
def test_unusable_timespan_inputs_return_empty(pm_module, value):
    assert pm_module.calculate_timespan(value, 1767226800) == ""
    assert pm_module.calculate_timespan(1767226800, value) == ""


# Verifies the long timestamp format carries weekday, date and full time
def test_long_timestamp_format(pm_module):
    assert pm_module.get_date_from_ts(1767226800) == "Thu 01 Jan 2026, 00:20:00"


# Verifies epoch integers, floats, datetimes and ISO strings all render identically
def test_long_timestamp_accepts_every_supported_input_type(pm_module):
    expected = "Thu 01 Jan 2026, 00:20:00"

    assert pm_module.get_date_from_ts(1767226800.4) == expected
    assert pm_module.get_date_from_ts(datetime(2026, 1, 1, 0, 20, 0, tzinfo=timezone.utc)) == expected
    assert pm_module.get_date_from_ts("2026-01-01T00:20:00Z") == expected


# Verifies an unusable timestamp renders as empty rather than breaking a notification body
def test_long_timestamp_of_an_unusable_value_is_empty(pm_module):
    assert pm_module.get_date_from_ts(None) == ""
    assert pm_module.get_date_from_ts("yesterday") == ""


# Verifies each short-format switch changes exactly the part of the string it names
def test_short_timestamp_switches(pm_module):
    ts = 1767226800

    assert pm_module.get_short_date_from_ts(ts) == "Thu 01 Jan 00:20"
    assert pm_module.get_short_date_from_ts(ts, show_hour=False) == "Thu 01 Jan"
    assert pm_module.get_short_date_from_ts(ts, show_weekday=False) == "01 Jan 00:20"
    assert pm_module.get_short_date_from_ts(ts, show_seconds=True) == "Thu 01 Jan 00:20:00"
    assert pm_module.get_short_date_from_ts(ts, always_show_year=True) == "Thu 01 Jan 26, 00:20"


# Verifies the year appears only when the timestamp is not from the current year
def test_short_timestamp_adds_the_year_only_when_it_differs(pm_module):
    now = datetime.now(timezone.utc)
    same_year = now.replace(month=6, day=15, hour=12, minute=0, second=0, microsecond=0)
    other_year = same_year.replace(year=now.year - 3)

    assert pm_module.get_short_date_from_ts(same_year, show_year=True) == pm_module.get_short_date_from_ts(same_year)
    assert str(other_year.year)[2:] in pm_module.get_short_date_from_ts(other_year, show_year=True)


# Verifies the time-only format honors the seconds switch
def test_hour_and_minute_format(pm_module):
    assert pm_module.get_hour_min_from_ts(1767226800) == "00:20"
    assert pm_module.get_hour_min_from_ts(1767226800, show_seconds=True) == "00:20:00"


# Verifies a range inside one day prints the date once and then only the end time
def test_range_within_one_day_prints_the_date_once(pm_module):
    start = 1767226800

    assert pm_module.get_range_of_dates_from_tss(start, start + 3600) == "Thu 01 Jan 2026, 00:20:00 - 01:20:00"
    assert pm_module.get_range_of_dates_from_tss(start, start + 3600, short=True) == "Thu 01 Jan 00:20 - 01:20"


# Verifies a range spanning midnight prints both dates in full
def test_range_across_days_prints_both_dates(pm_module):
    start = 1767226800

    assert pm_module.get_range_of_dates_from_tss(start, start + 86400, short=True) == "Thu 01 Jan 00:20 - Fri 02 Jan 00:20"


# Verifies the separator between the two ends of a range is configurable
def test_range_separator_is_configurable(pm_module):
    start = 1767226800

    assert " to " in pm_module.get_range_of_dates_from_tss(start, start + 3600, between_sep=" to ")


# Verifies an unusable end of a range collapses to an empty string
def test_range_with_an_unusable_end_is_empty(pm_module):
    assert pm_module.get_range_of_dates_from_tss(None, 1767226800) == ""
    assert pm_module.get_range_of_dates_from_tss(1767226800, None) == ""


# Verifies PSN timestamps are converted into the configured local timezone
def test_iso_timestamps_are_converted_to_the_configured_timezone(pm_module, monkeypatch):
    monkeypatch.setattr(pm_module, "LOCAL_TIMEZONE", "Europe/Warsaw")

    converted = pm_module.convert_iso_str_to_datetime("2026-01-01T00:20:00Z")

    assert converted.hour == 1
    assert converted.tzinfo is not None


# Verifies an empty or unparsable PSN timestamp yields no datetime instead of raising
def test_unparsable_iso_timestamps_yield_nothing(pm_module):
    assert pm_module.convert_iso_str_to_datetime("") is None
    assert pm_module.convert_iso_str_to_datetime(None) is None
    assert pm_module.convert_iso_str_to_datetime("not-a-date") is None


# Verifies the timezone check accepts real zone names and rejects anything else
def test_timezone_validation(pm_module):
    assert pm_module.is_valid_timezone("Europe/Warsaw") is True
    assert pm_module.is_valid_timezone("UTC") is True
    assert pm_module.is_valid_timezone("Mars/Olympus_Mons") is False
