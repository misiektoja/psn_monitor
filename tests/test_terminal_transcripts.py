"""Transcript tests: what the tool actually prints on a real terminal, which captured output cannot show."""

import os
import re
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest

import psn_monitor as monitor


pty = pytest.importorskip("pty")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL = PROJECT_ROOT / "psn_monitor.py"
CONTROL_SEQUENCE_RE = re.compile(r"\x1B\[[0-9;]*[A-Za-z]")
# An unroutable endpoint keeps every run offline and deterministic without changing the output shape
OFFLINE_CONFIG = 'CLEAR_SCREEN = False\nDISABLE_LOGGING = True\nCHECK_INTERNET_URL = "https://localhost:1/"\nCHECK_INTERNET_TIMEOUT = 1\n'

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the pty module is POSIX only")


# Returns a transcript with the terminal control sequences removed, leaving what the reader sees
def visible(transcript):
    return CONTROL_SEQUENCE_RE.sub("", transcript)


# Collapses a raw transcript the way a terminal would, so transient progress is not read as content
def displayed_lines(transcript):
    lines = []
    for line in visible(transcript).split("\n"):
        if line.endswith("\r"):
            line = line[:-1]
        lines.append(line.split("\r")[-1])
    return lines


# Returns the environment a transcript run uses, isolated from the developer's own configuration
def transcript_environment(workdir):
    environment = {**os.environ, "TERM": "xterm", "HOME": str(workdir), "PSN_NPSSO": ""}
    environment.pop("NO_COLOR", None)
    return environment


# Runs the tool on a real pseudo-terminal, answering each prompt only once it has actually been asked
def drive_pty(arguments, workdir, script=(), timeout=60):
    controller, worker = pty.openpty()
    process = subprocess.Popen([sys.executable, str(TOOL), *arguments], stdin=worker, stdout=worker, stderr=worker, cwd=str(workdir), env=transcript_environment(workdir))
    os.close(worker)
    transcript = ""

    # Reads until the given text appears, or until the deadline, whichever comes first
    def read_until(expected):
        nonlocal transcript
        deadline = time.monotonic() + timeout
        while expected is None or expected not in visible(transcript):
            if time.monotonic() > deadline:
                if expected is None:
                    return
                raise AssertionError(f"the tool never asked {expected!r}. Transcript so far:\n{visible(transcript)[-2000:]}")
            ready, _, _ = select.select([controller], [], [], 1)
            if not ready:
                if expected is None and process.poll() is not None:
                    return
                continue
            try:
                data = os.read(controller, 65536)
            except OSError:
                return
            if not data:
                return
            transcript += data.decode("utf-8", "replace")

    try:
        for expected, answer in script:
            read_until(expected)
            try:
                os.write(controller, answer + b"\n")
            except OSError:
                break
        read_until(None)
    finally:
        os.close(controller)
        try:
            process.wait(timeout=timeout)
        # A run that ignored the closed terminal must not hold the suite open
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout)
    return transcript, process.returncode


# Returns the indexes where two blank lines follow each other, which is the spacing defect a split introduces
def double_blank_lines(lines, start=0):
    # Trailing blanks are the gap before the shell prompt returns, not spacing between two blocks
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return [index for index in range(start, len(lines) - 1) if not lines[index].strip() and not lines[index + 1].strip()]


# Verifies the doctor report holds its output contract on the path a user actually walks
def test_the_doctor_transcript_holds_the_output_contract(tmp_path):
    config = tmp_path / "psn_monitor.conf"
    config.write_text(OFFLINE_CONFIG, encoding="utf-8")

    transcript, exit_code = drive_pty(["--config-file", str(config), "--env-file", "none", "--doctor", "misiektoja"], tmp_path)

    lines = displayed_lines(transcript)
    text = "\n".join(lines)
    heading = next(index for index, line in enumerate(lines) if line.strip() == "Doctor")
    assert not double_blank_lines(lines, heading), f"double blank lines in the doctor report:\n{text}"

    markers = set(re.findall(r"^\[([A-Z]+)\]", text, flags=re.MULTILINE))
    assert markers <= set(monitor.DOCTOR_STATUSES), markers
    assert text.count("Summary") == 1
    assert monitor.DOCTOR_GUIDE_URL in text
    assert exit_code in (0, 1)


# Verifies the transient progress stays on its own line and is gone before the report prints
def test_the_doctor_progress_never_collides_with_the_report(tmp_path):
    config = tmp_path / "psn_monitor.conf"
    config.write_text(OFFLINE_CONFIG, encoding="utf-8")

    transcript, _exit_code = drive_pty(["--config-file", str(config), "--env-file", "none", "--doctor", "misiektoja"], tmp_path)

    # Ordering is asserted on the raw stream, since the progress is erased before the report is printed
    segments = re.split(r"[\r\n]", visible(transcript))
    notice = next(index for index, segment in enumerate(segments) if "Running preflight checks" in segment)
    progress = [index for index, segment in enumerate(segments) if segment.strip().startswith("* Checking ")]
    heading = next(index for index, segment in enumerate(segments) if segment.strip() == "Doctor")

    assert progress, "no transient progress was written to the terminal"
    assert notice < min(progress)
    assert max(progress) < heading
    for index in progress:
        assert segments[index].strip().endswith("..."), f"output collided with the progress line: {segments[index]!r}"


# Verifies the zero-argument welcome screen names the next commands and keeps its spacing
def test_the_welcome_screen_transcript_holds_the_output_contract(tmp_path):
    transcript, exit_code = drive_pty([], tmp_path, script=[("Run the guided setup wizard now?", b"n")])

    lines = displayed_lines(transcript)
    text = "\n".join(lines)
    assert not double_blank_lines(lines), f"double blank lines on the welcome screen:\n{text}"
    for command in ("--setup", "--doctor", "--help"):
        assert command in text, f"the welcome screen does not name {command}"
    assert monitor.QUICK_START_GUIDE_URL in text
    assert exit_code == 0


# Answers one complete wizard run that saves, keyed on the prompt each answer belongs to
WIZARD_SCRIPT = [
    ("PlayStation online ID to monitor", b"misiektoja"),
    ("Persist this target in the generated config?", b""),
    ("Polling interval while the user is offline", b""),
    ("Polling interval while the user is online", b""),
    ("NPSSO code:", b""),
    ("Continue without the NPSSO code?", b"y"),
    ("Configure email notifications?", b"n"),
    ("Set up webhook alerts (Discord, ntfy etc.)?", b"n"),
    ("Write the normal per-target log file?", b"y"),
    ("Write a CSV file of the changes?", b"n"),
    ("Optional status file path", b""),
    ("Choose [1-3]:", b"1"),
    ("Run doctor now?", b"n"),
]


# Verifies a complete guided setup run holds its spacing and writes the file it says it wrote
def test_the_wizard_transcript_holds_the_output_contract(tmp_path):
    config = tmp_path / "psn_monitor.conf"

    transcript, exit_code = drive_pty(["--setup", "--config-file", str(config), "--env-file", str(tmp_path / ".env")], tmp_path, script=WIZARD_SCRIPT)

    lines = displayed_lines(transcript)
    text = "\n".join(lines)
    summary = next(index for index, line in enumerate(lines) if line.strip() == "Setup summary")
    assert not double_blank_lines(lines, summary), f"double blank lines in the setup summary:\n{text}"

    assert "Saved files" in text
    assert str(config) in text
    assert config.is_file(), "the wizard reported a file it did not write"
    assert exit_code == 0
