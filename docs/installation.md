# Installation

PSN Monitor runs as a local Python program. Choose the PyPI package for the shortest command or the manual script to run a downloaded file.

New to Python? Start with [New to Python: check and install](#new-to-python-install-everything).

## Requirements

* Python 3.10 or higher
* Libraries: [PSNAWP](https://codeberg.org/YoshikageKira/psnawp), `requests`, `python-dateutil`, `pytz`, `tzlocal`, `python-dotenv`, `wcwidth`, `colorama` (Windows only, optional)

`tzlocal`, `python-dotenv`, `wcwidth` and `colorama` are optional. Without `tzlocal` the local time zone has to be set manually. Without `python-dotenv` secrets have to come from the environment or the command line. Without `wcwidth` screen truncation is switched off. `colorama` matters only in the older Windows Command Prompt. `--doctor` reports each one it finds missing, reporting `colorama` only on Windows.

Tested on:

* **macOS**: Tahoe, Sequoia, Sonoma, Ventura
* **Linux**: Raspberry Pi OS (Trixie, Bookworm, Bullseye), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2026/2025/2024
* **Windows**: 11, 10

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="new-to-python-install-everything"></a>
## New to Python: check and install

Use this section if you are new to Python or do not know what is already installed. The platform sections only prepare Python and `pip`. Everyone then uses the same PSN Monitor installation and setup commands. PSN Monitor requires Python 3.10 or newer.

### Check whether PSN Monitor is already installed

Open Windows PowerShell on Windows or Terminal on macOS and Linux then run:

    psn_monitor --version

If this prints a PSN Monitor version, skip to [Run the setup wizard](#run-the-setup-wizard). If the command is not recognized or not found, continue with the section for your operating system.

### Windows 10 or 11

Open Windows PowerShell. Select **Start**, type `PowerShell` then open **Windows PowerShell**.

Check Python and `pip`:

    python --version
    pip --version

If both commands work and Python reports version 3.10 or newer, skip to [Install PSN Monitor](#install-psn-monitor-after-python-check).

If either command fails or Python is older than the required version:

1. Open the official [Python Install Manager in Microsoft Store](https://apps.microsoft.com/detail/9NQ7512CXL7T), select **View in Store** then select **Install**. If Microsoft Store is unavailable, download the manager from [python.org](https://www.python.org/downloads/).

2. Close PowerShell then open it again.

3. Run `py install default` to install the default Python release then run `python --version`. If an older installation still takes precedence, use the troubleshooting guide below to correct the command aliases.

4. Check both commands again:

        python --version
        pip --version

If `pip` is still not recognized, run `py install --refresh`, close PowerShell then open it again. This Python Install Manager command repairs its command aliases.

See the official [Python Install Manager troubleshooting table](https://docs.python.org/3/using/windows.html#troubleshooting) if either check is still unavailable.

### macOS

Open Terminal. Press **Command+Space**, type `Terminal` then press **Return**.

Check Python and `pip`:

    python3 --version
    pip --version

If both commands work and Python reports version 3.10 or newer, skip to [Install PSN Monitor](#install-psn-monitor-after-python-check).

If either command fails or Python is older than the required version:

1. Open the official [Python downloads for macOS](https://www.python.org/downloads/macos/). Select a stable Python release that meets the requirement above then download its **macOS 64-bit universal2 installer**. This single installer supports Apple Silicon and Intel Macs.

2. Open the downloaded `.pkg` file. Keep the standard options, select **Continue** through the installer then enter your macOS password when requested.

3. Open the new **Python 3.x** folder for the version you installed in Applications then double-click **Install Certificates.command**. Wait until its Terminal window reports `update complete` then close that window.

4. Close Terminal then open it again.

5. Check both commands again:

        python3 --version
        pip --version

The official [Using Python on macOS](https://docs.python.org/3/using/mac.html) guide shows every installer screen and explains the installed applications.

### Ubuntu, Debian, Raspberry Pi OS or Kali

Open Terminal then check Python and `pip`:

    python3 --version
    pip --version

If both commands work and Python reports version 3.10 or newer, skip to [Install PSN Monitor](#install-psn-monitor-after-python-check).

If either command fails or Python is too old, install or update the packages:

    sudo apt update
    sudo apt install python3 python3-pip

The package manager keeps an existing current package instead of reinstalling it. Terminal may ask for your password. Type the password you use to sign in then press **Enter**. Terminal does not show password characters while you type.

Check both commands again:

    python3 --version
    pip --version

If Python reports a version older than 3.10, follow your distribution's instructions to install a supported Python version before continuing. For another Linux distribution, install Python 3.10 or newer plus `pip` through its package manager.

<a id="install-psn-monitor-after-python-check"></a>
### Install PSN Monitor

Every operating system uses the same command:

    pip install psn_monitor

Verify the installation:

    psn_monitor --version

On Linux, `pip` may report that the system Python is externally managed. If that happens, install PSN Monitor with the isolated `pipx` tool instead:

    sudo apt install pipx
    pipx ensurepath
    pipx install psn_monitor

Close Terminal, open it again then run `psn_monitor --version`.

### Run the setup wizard

Every operating system uses the same command:

    psn_monitor --setup

The setup wizard collects the target, service credentials and optional notifications. Continue to [Setup & First Run](setup-and-first-run.md) for a walkthrough of its questions.

## Choose an Installation Method

| Method | Best for | Command used in later examples |
| --- | --- | --- |
| PyPI | Users who already have Python or followed the beginner steps above | `psn_monitor [OPTIONS]` |
| Manual script | Users who want to download and run one Python file | `python3 psn_monitor.py [OPTIONS]` on macOS/Linux or `python psn_monitor.py [OPTIONS]` on Windows |

Later pages use the short PyPI command. If you chose the manual script, keep the options after `psn_monitor` and replace the command itself with the one in the table. The setup wizard and `--help` also print commands for the detected installation.

## Install from PyPI

```sh
pip install psn_monitor
```

## Manual Installation

Download the *[psn_monitor.py](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/psn_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install PSNAWP requests python-dateutil pytz tzlocal python-dotenv wcwidth
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

A manual install is started as `python3 psn_monitor.py ...` rather than `psn_monitor ...`. The tool detects which way it was started and prints its own commands to match, so the examples in this documentation work either way.

## Next Step

Continue to [Setup & First Run](setup-and-first-run.md) to prepare credentials, choose a target and run the wizard.

## Upgrading

Use the same installation method and Python environment you used originally.

To upgrade to the latest version when installed from PyPI:

```sh
pip install psn_monitor -U
```

If you installed manually, download the newest *[psn_monitor.py](https://raw.githubusercontent.com/misiektoja/psn_monitor/refs/heads/main/psn_monitor.py)* file to replace your existing installation.

For a manual upgrade, also download the matching `requirements.txt` and rerun the dependency installation command above. Keep your configuration, dotenv files and saved history when replacing the script.

If you used `pipx`, upgrade with:

```sh
pipx upgrade psn_monitor
```

Check the upgraded version with `psn_monitor --version` or the [manual equivalent](usage.md#command-format), then run `psn_monitor --doctor <psn_user_id>` before monitoring.
