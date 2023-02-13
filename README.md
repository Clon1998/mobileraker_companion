# mobileraker_companion
![GitHub](https://img.shields.io/github/license/Clon1998/mobileraker_companion?style=for-the-badge)
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/clon1998/mobileraker_companion?style=for-the-badge)
![GitHub issues](https://img.shields.io/github/issues/Clon1998/mobileraker_companion?style=for-the-badge)

![GitHub all releases](https://img.shields.io/github/downloads/clon1998/mobileraker_companion/total?style=for-the-badge)

Companion for [Mobileraker](https://github.com/Clon1998/mobileraker), enabling push notification for [Klipper](https://github.com/Klipper3d/klipper) using [Moonraker](https://github.com/arksine/moonraker).

## Companion - Installation
Execute the following commands:
```
cd ~/
git clone https://github.com/Clon1998/mobileraker_companion.git
cd mobileraker_companion
./scripts/install-mobileraker-companion.sh
```

## Companion - Config
By default you should not need to create a config file. However, in case you want to use multiple printers with a single companion instance, enforce logins via moonraker or want to change some of the notification behavior here is a overview of the available sections and configs:

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
```

By default the companion searches for a `Mobileraker.conf` file in:
1. `~/Mobileraker.conf`
2. `<mobileraker_companion DIR>/mobileraker.conf`
3. `~/klipper_config/mobileraker.conf`


A single companion instance can support multiple printers.
Just add more printer sections to your config!
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

> **_NOTE:_**  Please restart the system service to ensure the new config values are used!  
> You can do that trough the `sudo systemctl restart mobileraker.service` terminal command.


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

### [v0.3.0] - 2023-01-xx

- Added support for the new notification architecture of mobileraker v2.1.0
- Added support for custom `M117` notifications see [Custom Notification](docs/Custom_Notifications.md) documentation

### [v0.2.1] - 2022-07-07

- Added support for multiple printers using a single companion instance
- Added support for trusted clients using the API key of moonraker
