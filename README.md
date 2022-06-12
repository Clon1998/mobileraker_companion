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
