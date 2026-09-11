"""Tests for backups, atomic replacement and the guard on writing a generated config."""

import re
import ast
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

import psn_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Returns the CONFIG_BLOCK template one release tag shipped, or None when that tag predates the template or this interpreter cannot parse its source
def template_from_tag(tag):
    source = subprocess.run(["git", "show", f"{tag}:psn_monitor.py"], cwd=PROJECT_ROOT, check=False, capture_output=True, text=True)
    if source.returncode != 0 or not source.stdout:
        return None
    try:
        # v1.2 and v1.3 nest same-type quotes inside f-strings, which needs Python 3.12 or newer to parse. Both predate CONFIG_BLOCK, so skipping them loses no coverage
        released = ast.parse(source.stdout)
    except SyntaxError:
        return None
    for statement in released.body:
        if isinstance(statement, ast.Assign) and getattr(statement.targets[0], "id", "") == "CONFIG_BLOCK" and isinstance(statement.value, ast.Constant):
            template = statement.value.value
            return template if isinstance(template, str) else None
    return None


# Returns every stable release tag in this checkout, newest first
def stable_release_tags():
    listing = subprocess.run(["git", "tag", "--sort=-version:refname"], cwd=PROJECT_ROOT, check=False, capture_output=True, text=True)
    if listing.returncode != 0:
        return []
    return [tag for tag in listing.stdout.split() if not any(marker in tag for marker in ("rc", "a", "b", "dev"))]


# Verifies a backup keeps the previous bytes, is private to the owner and is named for the file it copies
def test_a_backup_keeps_the_previous_content_privately(tmp_path):
    target = tmp_path / "psn_monitor.conf"
    target.write_text("PSN_CHECK_INTERVAL = 180\n", encoding="utf-8")

    backup_path = monitor.create_timestamped_backup(target)
    assert backup_path is not None

    assert backup_path is not None
    backup = Path(backup_path)
    assert backup.read_text(encoding="utf-8") == "PSN_CHECK_INTERVAL = 180\n"
    assert backup.name.startswith("psn_monitor.conf.") and backup.name.endswith(".bak")
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600


# Verifies a second backup in the same second gets its own name instead of overwriting the first
def test_backups_never_overwrite_each_other(tmp_path):
    target = tmp_path / "psn_monitor.conf"
    target.write_text("first\n", encoding="utf-8")
    first = monitor.create_timestamped_backup(target)
    assert first is not None
    target.write_text("second\n", encoding="utf-8")

    second = monitor.create_timestamped_backup(target)
    assert second is not None

    assert first is not None and second is not None
    assert first != second
    assert Path(first).read_text(encoding="utf-8") == "first\n"
    assert Path(second).read_text(encoding="utf-8") == "second\n"


# Verifies nothing is backed up when there is nothing to lose
def test_a_missing_file_produces_no_backup(tmp_path):
    assert monitor.create_timestamped_backup(tmp_path / "absent.conf") is None
    assert list(tmp_path.iterdir()) == []


# Verifies a write leaves either the old file or the new one, never a temporary file beside them
def test_an_atomic_write_leaves_no_temporary_file(tmp_path):
    target = tmp_path / "state.json"
    target.write_text("old\n", encoding="utf-8")

    monitor.write_file_atomically(target, "new\n")

    assert target.read_text(encoding="utf-8") == "new\n"
    assert [entry.name for entry in tmp_path.iterdir()] == ["state.json"]


# Verifies a failed write is cleaned up rather than left behind as a half-written temporary file
def test_a_failed_atomic_write_cleans_up_after_itself(tmp_path, monkeypatch):
    target = tmp_path / "state.json"
    target.write_text("old\n", encoding="utf-8")
    monkeypatch.setattr(monitor.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("replace refused")))

    with pytest.raises(OSError):
        monitor.write_file_atomically(target, "new\n")

    assert target.read_text(encoding="utf-8") == "old\n"
    assert [entry.name for entry in tmp_path.iterdir()] == ["state.json"]


# Verifies the last status file is written atomically and reads back as the pair the monitor saved
def test_the_saved_status_is_written_atomically(tmp_path):
    status_file = tmp_path / "psn_someone_last_status.json"

    monitor.save_last_status(status_file, 1767222000, "online")

    assert json.loads(status_file.read_text(encoding="utf-8")) == [1767222000, "online"]
    assert [entry.name for entry in tmp_path.iterdir()] == ["psn_someone_last_status.json"]


# Verifies writing a config where nothing exists yet asks nobody anything
def test_writing_a_new_config_needs_no_confirmation(tmp_path):
    destination = tmp_path / "psn_monitor.conf"

    def refuse_to_ask(prompt):
        raise AssertionError(f"should not have prompted: {prompt}")

    backup_path, written = monitor.write_generated_config(destination, "PSN_CHECK_INTERVAL = 180\n", input_func=refuse_to_ask, interactive=True)

    assert (backup_path, written) == (None, True)
    assert destination.read_text(encoding="utf-8") == "PSN_CHECK_INTERVAL = 180\n"


# Verifies replacing an existing config outside a terminal refuses and names the flag that allows it
def test_replacing_a_config_outside_a_terminal_refuses(tmp_path):
    destination = tmp_path / "psn_monitor.conf"
    destination.write_text("PSN_CHECK_INTERVAL = 999\n", encoding="utf-8")

    with pytest.raises(FileExistsError) as raised:
        monitor.write_generated_config(destination, "template\n", interactive=False)

    assert "already exists" in str(raised.value)
    assert destination.read_text(encoding="utf-8") == "PSN_CHECK_INTERVAL = 999\n"


# Verifies a declined prompt leaves the existing config exactly as it was
def test_a_declined_replacement_changes_nothing(tmp_path):
    destination = tmp_path / "psn_monitor.conf"
    destination.write_text("PSN_CHECK_INTERVAL = 999\n", encoding="utf-8")

    backup_path, written = monitor.write_generated_config(destination, "template\n", interactive=True, input_func=lambda prompt: "n")

    assert (backup_path, written) == (None, False)
    assert destination.read_text(encoding="utf-8") == "PSN_CHECK_INTERVAL = 999\n"
    assert [entry.name for entry in tmp_path.iterdir()] == ["psn_monitor.conf"]


@pytest.mark.parametrize("answer", ["y", "yes", "YES"])
# Verifies an accepted prompt replaces the config and keeps the previous one as a backup
def test_an_accepted_replacement_backs_up_first(tmp_path, answer):
    destination = tmp_path / "psn_monitor.conf"
    destination.write_text("PSN_CHECK_INTERVAL = 999\n", encoding="utf-8")

    backup_path, written = monitor.write_generated_config(destination, "template\n", interactive=True, input_func=lambda prompt: answer)

    assert written is True
    assert backup_path is not None
    assert destination.read_text(encoding="utf-8") == "template\n"
    assert Path(backup_path).read_text(encoding="utf-8") == "PSN_CHECK_INTERVAL = 999\n"


# Verifies --force replaces an existing config without asking, still keeping a backup
def test_force_replaces_without_asking(tmp_path):
    destination = tmp_path / "psn_monitor.conf"
    destination.write_text("PSN_CHECK_INTERVAL = 999\n", encoding="utf-8")

    def refuse_to_ask(prompt):
        raise AssertionError(f"should not have prompted: {prompt}")

    backup_path, written = monitor.write_generated_config(destination, "template\n", force=True, interactive=False, input_func=refuse_to_ask)

    assert written is True
    assert backup_path is not None
    assert destination.read_text(encoding="utf-8") == "template\n"
    assert Path(backup_path).read_text(encoding="utf-8") == "PSN_CHECK_INTERVAL = 999\n"


# Verifies the advice for a config that could not be replaced names the flag that allows it
def test_the_refusal_advice_names_the_force_flag():
    advice = monitor.classify_recovery_error(context="file.exists", detail="Config file 'psn_monitor.conf' already exists")

    assert advice.code == "file.exists"
    assert "--force" in advice.fix


# Verifies the advice for a broken config never sends the reader at the file that just failed
def test_the_broken_config_advice_does_not_name_the_default_config_file():
    advice = monitor.classify_recovery_error(context="config.invalid", detail="Line 2: only NAME = value assignments are allowed")

    assert "--generate-config" in advice.fix
    assert "psn_monitor.conf" not in advice.fix


# Verifies every config template a released version shipped still loads through the current parser
def test_templates_from_every_release_still_load():
    tags = stable_release_tags()
    if not tags:
        pytest.skip("no release tags in this checkout")

    replayed = []
    for tag in tags:
        template = template_from_tag(tag)
        if template is None:
            continue
        replayed.append(tag)
        retired = []
        try:
            values = monitor.parse_config_content(template, f"<{tag}>", retired_out=retired)
        except ValueError as exc:
            pytest.fail(f"the {tag} config template no longer loads: {exc}")
        assert values, f"the {tag} config template parsed to nothing"

    assert replayed, "no release tag shipped a config template, so nothing was replayed"


# Verifies a setting a released template defined is still accepted today or explicitly retired
def test_no_released_setting_was_dropped_silently():
    tags = stable_release_tags()
    if not tags:
        pytest.skip("no release tags in this checkout")

    allowed = monitor._config_allowed_names()
    for tag in tags:
        template = template_from_tag(tag)
        if template is None:
            continue
        for statement in ast.parse(template).body:
            if isinstance(statement, ast.Assign) and isinstance(statement.targets[0], ast.Name):
                name = statement.targets[0].id
                assert name in allowed or name in monitor.RETIRED_CONFIG_SETTINGS, f"{tag} shipped {name}, which this version neither accepts nor retires"


# Verifies the generated template is written where it was asked for, with the file mode the platform gives it
def test_the_generated_template_is_written_to_the_named_path(tmp_path):
    destination = tmp_path / "nested" / "psn_monitor.conf"

    monitor.write_generated_config(destination, monitor.CONFIG_BLOCK.strip("\n") + "\n", interactive=True, input_func=lambda prompt: "y")

    assert destination.is_file()
    assert monitor.parse_config_content(destination.read_text(encoding="utf-8"), str(destination))
    assert os.path.isdir(destination.parent)


# Verifies the backup name every tool in this family writes, so one documented shape covers them all
def test_the_backup_carries_the_family_name_and_mode(tmp_path):
    destination = tmp_path / "monitor.conf"
    destination.write_text("SETTING = 1\n", encoding="utf-8")

    backup_path = monitor.create_timestamped_backup(destination)
    assert backup_path is not None

    assert re.fullmatch(r"monitor\.conf\.\d{14}\.bak", Path(backup_path).name)
    assert Path(backup_path).read_text(encoding="utf-8") == "SETTING = 1\n"
    assert stat.S_IMODE(Path(backup_path).stat().st_mode) == 0o600


# Verifies a second backup in the same second takes its own name rather than overwriting the first
def test_a_second_backup_in_the_same_second_keeps_the_first(tmp_path):
    destination = tmp_path / "monitor.conf"
    destination.write_text("first\n", encoding="utf-8")
    first = monitor.create_timestamped_backup(destination)
    assert first is not None
    destination.write_text("second\n", encoding="utf-8")

    second = monitor.create_timestamped_backup(destination)
    assert second is not None

    assert first != second
    assert Path(first).read_text(encoding="utf-8") == "first\n"
    assert Path(second).read_text(encoding="utf-8") == "second\n"


# Verifies a destination that is not there yet earns no backup, since there is nothing to copy
def test_a_missing_destination_earns_no_backup(tmp_path):
    assert monitor.create_timestamped_backup(tmp_path / "absent.conf") is None


# A parent path that is a file is a write failure, not an existing config, so the advice must not say --force
def test_a_file_in_the_way_of_the_parent_directory_is_not_an_existing_config(tmp_path):
    blocker = tmp_path / "configs"
    blocker.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(OSError) as raised:
        monitor.write_generated_config(blocker / "psn_monitor.conf", "SMTP_PORT = 587\n", interactive=False)

    assert not isinstance(raised.value, monitor.ConfigExistsError)
    assert blocker.read_text(encoding="utf-8") == "not a directory\n"


# Refusing to replace a config without a terminal is its own error, so the generate-config path can tell it apart
def test_refusing_to_replace_a_config_without_a_terminal_raises_its_own_error(tmp_path):
    destination = tmp_path / "psn_monitor.conf"
    destination.write_text("SMTP_PORT = 587\n", encoding="utf-8")

    with pytest.raises(monitor.ConfigExistsError):
        monitor.write_generated_config(destination, "SMTP_PORT = 465\n", interactive=False)

    assert destination.read_text(encoding="utf-8") == "SMTP_PORT = 587\n"
