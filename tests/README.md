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
| `test_notification_receipts.py` | SMTP acceptance despite cleanup failures, receipt controls and unchanged notification content |
| `test_configuration_notification_boundaries.py` | Invalid output settings, CLI precedence and strict webhook fields with legacy JSON support |
| `test_resource_boundaries.py` | Real PSNAWP info flow stops after resource exhaustion |
| `test_boundary_regressions.py` | Real notification transports, literal secret resolution and malformed startup paths |
| `test_release_boundaries.py` | Real HTTP retries, Discord mention safety, unrenderable templates, SMTP password round trips, split terminal writes and the width cap without wcwidth |
| `test_real_psn_boundaries.py` | Real PSNAWP trophy iteration, private errors, quiet recovery and future history |
| `test_compact_commands.py` | Literal short command prefixes, real help output and dependency hints |
| `test_release_safety.py` | Credential preservation, private errors, timing checks, saved-state compatibility and real PSN rate limits |
| `test_recovery_safety.py` | Real dotenv reloads, setup backups, oversized counts and provider-error privacy |
| `test_secret_policy.py` | Shared credential priority, reload ownership and setup destination conflicts |
| `test_smtp_error_privacy.py` | Short and escaped passwords in rejected SMTP sign-ins through commands, setup, Doctor and delivery |
| `test_setup_resolution_regressions.py` | Saved dotenv destinations, empty secrets, export precedence and recovery paths |
| `test_dotenv_quoted_keys.py` | Quoted dotenv keys, export prefixes, multiline values and duplicate removal |
| `test_documentation_layout.py` | Unique anchors, main screenshot placement and matching entry-page feature summaries |
| `conftest.py` | Import setup, deterministic globals and the PSN, SMTP and clock test doubles |
| `test_cli_startup.py` | Command line handling, config and dotenv loading, startup validation and logging setup |
| `test_config_loading.py` | Declarative config parsing and refusal of executable config content |
| `test_config_writing.py` | Timestamped backups, atomic replacement, the guard on replacing a config and the replay of every released template |
| `test_csv_output.py` | The CSV history file, its header, its rows and its error reporting |
| `test_diagnostic_modes.py` | What `--verbose` and `--debug` report, and which setting wins when both a flag and the config file are present |
| `test_documentation.py` | The documentation site: its page set, navigation, links and anchors, and the claims its pages make about the code |
| `test_doctor.py` | The `--doctor` report: its output contract, every section it checks and the exit code it returns |
| `test_email_notifications.py` | SMTP validation, the delivered message and failure handling |
| `test_error_classification.py` | The recovery categories, the advice and install-aware commands each failure produces, and the NPSSO auth probe |
| `test_monitoring_loop.py` | End-to-end monitoring runs: status and game changes, session state, CSV history, alerts and every error recovery path |
| `test_help_screen.py` | The `--help` screen: the option groups, the worked examples and the version banner |
| `test_output_safety.py` | Secret redaction, terminal control sequence removal, screen truncation and the single output layer |
| `test_presence_parsing.py` | Presence payload parsing, platform labels and title normalization |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and the CI contract |
| `test_repository_metadata.py` | Governance files, citation, funding, line endings, the declared editor style, the pinned linter and release integrity |
| `test_startup_summary.py` | The startup summary rows, which view each one appears in, what the log file keeps and the welcome screen |
| `test_startup_summary_channels.py` | Summary rows naming the webhook provider, the mail server, the masked recipient, the delivery confirmations and the runtime |
| `test_tls_verification.py` | The `VERIFY_SSL` setting: which requests honour it, what is reported while it is off, its shipped default and a sweep requiring every outbound request to carry it |
| `test_terminal_transcripts.py` | What the doctor report, the welcome screen and the guided setup print on a real terminal |
| `test_terminal_color.py` | The colour theme, which part colours which token, where colour must never reach and how it is switched off |
| `test_setup_wizard.py` | The guided setup: what it asks, what it writes, when it writes nothing and the welcome screen offer |
| `test_partial_setup_save.py` | Real wizard inputs and filesystem failures after configuration replacement |
| `test_secret_commands.py` | The one-shot secret commands, their validation before writing and the dotenv file they update |
| `test_runtime_controls.py` | Signal-driven toggles, interval changes, secret reload and the log output filter |
| `test_time_formatting.py` | Durations, timespans, timestamp formats and timezone handling |
| `test_user_info.py` | The one-shot profile report, trophies and recently played games |
| `test_webhook_notifications.py` | Webhook destinations, the request each provider receives, the bounded retry and the two delivery channels |
| `test_moved_private_settings.py` | Kept credentials across dotenv destination changes and startup error handling |

## Conventions

* Keep every test offline. If a code path needs network access, stub it with
  `monkeypatch` rather than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a
  leaked global affects whatever runs next.
* Replace PlayStation Network calls and notification delivery with test doubles.
* Never use a real NPSSO token, SMTP password, webhook URL or ntfy access token.

A change to the monitoring loop, authentication or PlayStation Network data handling is not
verified by this suite alone. Exercise it against a real account and say so in the
pull request, without usernames or credentials.
