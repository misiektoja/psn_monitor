# Offline test suite

These tests cover logic in `psn_monitor.py` that can run without network access.
PlayStation Network calls are replaced with test doubles.

## Running

From the repository root:

```bash
pip install -e '.[test]'
python -m pytest
```

`pyproject.toml` puts the repository root first on `sys.path`, so the tests use the
working tree instead of an installed copy of the module.

Lint the same way CI does:

```bash
pip install -e '.[lint]'
python -m ruff check psn_monitor.py tests
```

CI runs both on every push and pull request, across Python 3.10 through 3.14,
and again before anything is published to PyPI.

## Layout

| File | Area under test |
| --- | --- |
| `conftest.py` | Import setup, deterministic globals and the PSN, SMTP and clock test doubles |
| `test_cli_startup.py` | Command line handling, config and dotenv loading, startup validation, logging setup and the effective-settings banner |
| `test_config_loading.py` | Declarative config parsing and refusal of executable config content |
| `test_csv_output.py` | The CSV history file, its header, its rows and its error reporting |
| `test_diagnostic_modes.py` | What `--verbose` and `--debug` report, and which setting wins when both a flag and the config file are present |
| `test_doctor.py` | The `--doctor` report: its output contract, every section it checks and the exit code it returns |
| `test_email_notifications.py` | SMTP validation, the delivered message and failure handling |
| `test_error_classification.py` | The recovery categories, the advice and install-aware commands each failure produces, and the NPSSO auth probe |
| `test_monitoring_loop.py` | End-to-end monitoring runs: status and game changes, session state, CSV history, alerts and every error recovery path |
| `test_output_safety.py` | Secret redaction, terminal control sequence removal, screen truncation and the single output layer |
| `test_presence_parsing.py` | Presence payload parsing, platform labels and title normalization |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and the CI contract |
| `test_repository_metadata.py` | Governance files, citation, funding, line endings, the declared editor style, the pinned linter and release integrity |
| `test_runtime_controls.py` | Signal-driven toggles, interval changes, secret reload and the log output filter |
| `test_time_formatting.py` | Durations, timespans, timestamp formats and timezone handling |
| `test_user_info.py` | The one-shot profile report, trophies and recently played games |

## Conventions

* Keep every test offline. If a code path needs network access, stub it with
  `monkeypatch` rather than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a
  leaked global affects whatever runs next.
* Replace PlayStation Network calls and notification delivery with test doubles.
* Never use a real NPSSO token, SMTP password or webhook URL.

A change to the monitoring loop, authentication or PlayStation Network data handling is not
verified by this suite alone. Exercise it against a real account and say so in the
pull request, without usernames or credentials.
