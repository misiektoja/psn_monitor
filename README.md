# psn_monitor

psn_monitor is a Python script which allows for real-time monitoring of Sony Playstation (PSN) players activity. 

## Features

- Real-time monitoring of Playstation users gaming activity (including detection when user gets online/offline or played games)
- Basics statistics for user activity (how long in different states, how long played game etc.)
- Email notifications for different events (player gets online/offline, starts/finishes/changes game, errors)
- Saving all gaming activity with timestamps to the CSV file
- Possibility to control the running copy of the script via signals

<p align="center">
   <img src="./assets/psn_monitor.png" alt="psn_monitor_screenshot" width="80%"/>
</p>

## Change Log

Release notes can be found [here](RELEASE_NOTES.md)

## Disclaimer

I'm not a dev, project done as a hobby. Code is ugly and as-is, but it works (at least for me) ;-)

## Requirements

The script requires Python 3.x.

It uses [PSNAWP](https://github.com/isFakeAccount/psnawp) library, also requests, pytz and python-dateutil.

It has been tested succesfully on Linux (Raspberry Pi Bullseye & Bookworm based on Debian) and Mac OS (Ventura & Sonoma). 

Should work on any other Linux OS and Windows with Python.

## Installation

Install the required Python packages:

```sh
python3 -m pip install requests python-dateutil pytz PSNAWP
```

Or from requirements.txt:

```sh
pip3 install -r requirements.txt
```

Copy the *[psn_monitor.py](psn_monitor.py)* file to the desired location. 

You might want to add executable rights if on Linux or MacOS:

```sh
chmod a+x psn_monitor.py
```

## Configuration

Edit the *[psn_monitor.py](psn_monitor.py)* file and change any desired configuration variables in the marked **CONFIGURATION SECTION** (all parameters have detailed description in the comments).

### PSN npsso code

Log in to your [My Playstation](https://my.playstation.com/) account.

In another tab, go to: [https://ca.account.sony.com/api/v1/ssocookie](https://ca.account.sony.com/api/v1/ssocookie)

Copy the value of **npsso** code.

Change the **PSN_NPSSO** variable to respective value (or use **-n** parameter).

The refresh token that is generated from npsso should be valid for 2 months. You will be informed by the tool once the token expires (proper message on the console and in email if errors notifications have not been disabled).

### SMTP settings

If you want to use email notifications functionality you need to change the SMTP settings (host, port, user, password, sender, recipient).

### Other settings

All other variables can be left at their defaults, but feel free to experiment with it.

## Getting started

### List of supported parameters

To get the list of all supported parameters:

```sh
./psn_monitor.py -h
```

or 

```sh
python3 ./psn_monitor.py -h
```

### Monitoring mode

To monitor specific user activity, just type the Playstation (PSN) id (**misiektoja** in the example below):

```sh
./psn_monitor.py misiektoja
```

The tool will run infinitely and monitor the player until the script is interrupted (Ctrl+C) or killed the other way.

You can monitor multiple PSN players by spawning multiple copies of the script. 

It is suggested to use sth like **tmux** or **screen** to have the script running after you log out from the server.

The tool automatically saves its output to *psn_monitor_psnid.log* file (can be changed in the settings or disabled with **-d**).

The tool also saves the timestamp and last status (after every change) to *psn_psnid_last_status.json* file, so the last status is available after the restart of the tool.

## How to use other features

### Email notifications

If you want to get email notifications once the user gets online or offline use **-a** parameter:

```sh
./psn_monitor.py misiektoja -a
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="./assets/psn_monitor_email_notifications.png" alt="psn_monitor_email_notifications" width="70%"/>
</p>

If you also want to be informed about any game changes (user started/stopped playing or changed game) then use  **-g** parameter:

```sh
./psn_monitor.py misiektoja -g
```

### Saving gaming activity to the CSV file

If you want to save the gaming activity of the PSN user, use **-b** parameter with the name of the file (it will be automatically created if it does not exist):

```sh
./psn_monitor.py misiektoja -b psn_misiektoja.csv
```

### Check intervals

If you want to change the check interval when the user is online to 30 seconds (**-k**) and when is offline to 2 mins - 120 seconds (**-c**):

```sh
./psn_monitor.py misiektoja -k 30 -c 120
```

### Controlling the script via signals


The tool has several signal handlers implemented which allow to change behaviour of the tool without a need to restart it with new parameters.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets online or offline |
| USR2 | Toggle email notifications when user starts/stops playing or changes game |
| TRAP | Increase the check timer for player activity when user is online (by 30 seconds) |
| ABRT | Decrease check timer for player activity when user is online (by 30 seconds) |

So if you want to change functionality of the running tool, just send the proper signal to the desired copy of the script.

I personally use **pkill** tool, so for example to toggle email notifications when user gets online or offline, for the tool instance monitoring the *misiektoja* user:

```sh
pkill -f -USR1 "python3 ./psn_monitor.py misiektoja"
```

### Other

Check other supported parameters using **-h**.

You can of course combine all the parameters mentioned earlier together.

## Colouring log output with GRC

If you use [GRC](https://github.com/garabik/grc) and want to have the output properly coloured you can use the configuration file available [here](grc/conf.monitor_logs)

Change your grc configuration (typically *.grc/grc.conf*) and add this part:

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the *conf.monitor_logs* to your .grc directory and psn_monitor log files should be nicely coloured.

## License

This project is licensed under the GPLv3 - see the [LICENSE](LICENSE) file for details
