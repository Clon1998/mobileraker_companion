# mobileraker_companion
![GitHub](https://img.shields.io/github/license/Clon1998/mobileraker_companion?style=for-the-badge)
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/clon1998/mobileraker_companion?style=for-the-badge)
![GitHub issues](https://img.shields.io/github/issues/Clon1998/mobileraker_companion?style=for-the-badge)

![GitHub all releases](https://img.shields.io/github/downloads/clon1998/mobileraker_companion/total?style=for-the-badge)

Companion for [Mobileraker](https://github.com/Clon1998/mobileraker), enabling push notification for [Klipper](https://github.com/Klipper3d/klipper) using [Moonraker](https://github.com/arksine/moonraker).

## Table of Contents
- [mobileraker\_companion](#mobileraker_companion)
  - [Table of Contents](#table-of-contents)
  - [Companion - Installation](#companion---installation)
    - [Run the Companion in Docker](#run-the-companion-in-docker)
  - [Companion - Config](#companion---config)
  - [Moonraker - Update manager](#moonraker---update-manager)
  - [How it works](#how-it-works)
    - [Visualization of the architecture](#visualization-of-the-architecture)
  - [Changelog](#changelog)
    - [\[v0.3.0\] - 2023-03-29](#v030---2023-03-29)
    - [\[v0.2.1\] - 2022-07-07](#v021---2022-07-07)

## Companion - Installation
To install the Companion, follow these steps:

1. Open a terminal or establish an SSH connection on the host running Klipper.
2. Change the directory to your home directory by running the following command:
```bash
cd ~/
```
1. Clone the Companion repository by executing the following command:
```bash
git clone https://github.com/Clon1998/mobileraker_companion.git
```
1. Navigate to the mobileraker_companion directory:
```bash
cd mobileraker_companion
```
1. Run the installation script to set up the Companion:
```bash
./scripts/install-mobileraker-companion.sh
```

### Run the Companion in Docker
Create a mobileraker.conf and run the following command
```
docker run -d \
    -n mobileraker_companion
    -v /path/to/mobileraker.conf:/opt/printer_data/config/mobileraker.conf
    ghcr.io/Clon1998/mobileraker_companion:latest
```

or via docker compose:
```yaml
services:
  mobileraker_companion:
    image: ghcr.io/Clon1998/mobileraker_companion:latest
    volumes:
    - /path/to/mobileraker.conf:/opt/printer_data/config/mobileraker.conf
```

## Companion - Config
By default, you don't need to create a config file. However, if you want to use multiple printers with a single Companion instance, enforce logins via Moonraker, or modify the notification behavior, you can customize the configuration. Below is an overview of the available sections and configurations

```properties
[general]
language: en 
# one of the supported languages defined in i18n.py#languages (de,en,...)
# Default: en
timezone: Europe/Berlin 
# correct timezone e.g. Europe/Berlin for Berlin time or US/Central. 
# For more values see https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568
# Default: Tries to use system timezone
# Optional
eta_format: %%d.%%m.%%Y, %%H:%%M:%%S
# Format used for eta and adaptive_eta placeholder variables
# For available options see https://strftime.org/
# Note that you will have to escape the % char by using a 2nd one e.g.: %d/%m/%Y -> %%d/%%m/%%Y
# Default: %%d.%%m.%%Y, %%H:%%M:%%S
# Optional
include_snapshot: True
# !! SUPPORTER ONLY - This feature requires beeing a supporter of Mobileraker as of now!
# Include a snapshot of the webcam in any print status/progress update notifications
# Default: True
# Optional



# Add a [printer ...] section for every printer you want to add
[printer <NAME OF YOUR PRINTER: optional>]
moonraker_uri: ws://127.0.0.1:7125/websocket
# Define the uri to the moonraker instance.
# Default value: ws://127.0.0.1:7125/websocket
# Optional
moonraker_api_key: False
# Moonraker API key if force_logins or trusted clients is active!
# Default value: False
# Optional
snapshot_uri: http://127.0.0.1/webcam/?action=snapshot
# !! SUPPORTER ONLY - This feature requires beeing a supporter of Mobileraker as of now!
# The ABSOLUT url to the webcam, the companion should make a screenshot of. 
# Default: 
# Optional
snapshot_rotation: 0
# The rotation tapplied to the image. Valid values : 0, 90, 180, 270
# Default: 0
# Optional

```

The Companion searches for a `Mobileraker.conf` file in the following locations (in order of precedence):
1. `~/Mobileraker.conf`
2. `<mobileraker_companion DIR>/mobileraker.conf`
3. `~/klipper_config/mobileraker.conf`


A single Companion instance can support multiple printers. To configure multiple printers, add more `[printer ...]` sections to your config. Here's an example of a multi-printer config:
Example multi-printer config: 
```properties
[printer V2.1111]
moonraker_uri: ws://127.0.0.1:7125/websocket
# Define the uri to the moonraker instance.
# Default value: ws://127.0.0.1:7125/websocket
moonraker_api_key: False
# Moonraker API key if force_logins or trusted clients is active!

[printer Ratty]
moonraker_uri: ws://ratrig.home:7125/websocket
# Define the uri to the moonraker instance.
# Default value: ws://127.0.0.1:7125/websocket
moonraker_api_key: False
# Moonraker API key if force_logins is active!
```

> **Note**  
>   Please restart the system service to ensure the new config values are used. 
> You can do this by running the following terminal command:  
> ```bash
> sudo systemctl restart mobileraker.service
> ```


## Moonraker - Update manager
In order to get moonrakers update manager working with the companion add the following section to your `moonraker.conf`. 
```
[update_manager mobileraker]
type: git_repo
path: ~/mobileraker_companion
origin: https://github.com/Clon1998/mobileraker_companion.git
primary_branch:main
managed_services: mobileraker
env: ~/mobileraker-env/bin/python
requirements: scripts/mobileraker-requirements.txt
install_script: scripts/install-mobileraker-companion.sh
```
## How it works
The companion connects directly to your printer(s) and listens to the websocket for updates. Whenever the print status changes or a new M117 message is received, the companion triggers to process of constructing a new notification.
To construct a new noticiation it follows the following schema:
1. Get the notification configuration for all registered devices from moonrakers database. The Mobileraker Android/IOS app automatically registers your device into your printer's moonraker device and syncs the notification configs to it.
2. Construct the notification's title and content based on the fetched notificaton configs
3. Pass the notification to the FCM Backend in order to submit it to Apple's/Google's Push services



### Visualization of the architecture
![Sys Diag](assets/Mobileraker-System_witthbg.png)


## Changelog

### [v0.3.0] - 2023-03-29

- Added support for the new notification architecture of mobileraker v2.1.0
- Added support for custom `M117` notifications see [Custom Notification](docs/Custom_Notifications.md) documentation
- Moved logs to klipper's printer_dir/logs

### [v0.2.1] - 2022-07-07

- Added support for multiple printers using a single companion instance
- Added support for trusted clients using the API key of moonraker
