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
A config is only required if you want to connect to multiple printers or enfroce_logins!

```properties
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
![Sys Diag](assets/Mobileraker-System_witthbg.png)


## Changelog

### [v0.2.1] - 2022-07-07

- Added support for multiple printers using a single companion instance
- Added support for trusted clients using the API key of moonraker
