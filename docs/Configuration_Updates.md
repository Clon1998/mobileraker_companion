# Mobileraker Configuration Updates

The v0.5.0 version of Mobileraker Companion introduces significant improvements to how configuration is managed, moving away from relying on the configuration file and instead using settings from the Mobileraker app. This document explains these changes and how they affect your setup.

## Table of Contents
- [Mobileraker Configuration Updates](#mobileraker-configuration-updates)
  - [Table of Contents](#table-of-contents)
  - [Overview of Changes](#overview-of-changes)
  - [New Settings in the App](#new-settings-in-the-app)
  - [Configuration Priority](#configuration-priority)
  - [Simplified Configuration File](#simplified-configuration-file)
  - [Migration Guide](#migration-guide)
  - [Webcam Integration](#webcam-integration)
  - [Frequently Asked Questions](#frequently-asked-questions)

## Overview of Changes

Mobileraker Companion now prioritizes settings from the app over the `Mobileraker.conf` file, providing a more streamlined user experience. The following settings have been moved from the configuration file to the app:

1. **Language**: Set in the app and synced to the companion
2. **Time Format**: Choose between 12h and 24h formats in the app
3. **Webcam Selection**: Select from configured webcams in Moonraker
4. **Filament Sensor Exclusions**: Configure which sensors to ignore per device

This change enables device-specific configurations, allowing different devices to have different settings for the same printer.

## New Settings in the App

The following settings are now managed through the Mobileraker app:

| Setting | Description | Location in App |
|---------|-------------|----------------|
| Language | Interface language | Settings > App > Language |
| Time Format | 12h or 24h time display | Settings > App > Time Format |
| Webcam Selection | Choose specific webcam for notifications | Settings > Notifications > Printer > Webcam |
| Filament Sensor Exclusions | Ignore specific filament sensors | Settings  > Notifications > Printer > Excluded Sensors |

## Configuration Priority

Settings are now applied in the following order of priority:

1. **Device-specific settings** from the app
2. **Global app settings** (if device is set to inherit global settings)
3. **Configuration file** (as fallback for older app versions)
4. **Default values**

This ensures backward compatibility while providing the benefits of device-specific settings.

## Simplified Configuration File

With many settings now managed in the app, your `Mobileraker.conf` file can be simplified to include only necessary information. Here's an example of a minimal configuration:

```ini
[general]
timezone: Europe/Berlin
include_snapshot: True

[printer My Printer]
moonraker_uri: ws://192.168.1.10:7125/websocket
moonraker_api_key: False
```

The following settings can now be removed from your configuration file as they're managed in the app:

- `language`
- `eta_format` (derived from time format preference)
- `snapshot_uri` (derived from webcam selection)
- `snapshot_rotation` (derived from webcam configuration)
- `ignore_filament_sensors` (managed per device in app)

## Migration Guide

To migrate to the new configuration system:

1. **Update Mobileraker Companion** to the latest version
2. **Update the Mobileraker App** to version 2.8.8 or later
3. **Configure your webcams** in Mainsail or Fluidd
4. **Set your preferences** in the Mobileraker app
5. (Optional) **Simplify your configuration file** by removing settings now managed in the app

Your existing configuration file will continue to work as a fallback, so this migration doesn't require immediate changes.

## Webcam Integration

The companion now integrates directly with Moonraker's webcam API, providing several advantages:

- **Configuration Sync**: Webcam settings (rotation, flipping) are automatically synced from Mainsail/Fluidd
- **Multiple Webcams**: Different devices can use different webcams for the same printer
- **No URI Management**: No need to manually specify webcam URIs - just select from configured webcams

To use this feature:

1. Configure your webcams in Mainsail or Fluidd
2. In the Mobileraker app, go to Settings > Printer > Notifications
3. Select your preferred webcam from the dropdown list
4. The companion will automatically use the selected webcam for notifications

## Frequently Asked Questions

**Q: Do I need to update my configuration file?**  
A: No, your existing configuration file will continue to work. The new settings in the app will take precedence when available.

**Q: Will my device-specific settings affect other devices?**  
A: No, each device can have its own settings for the same printer.

**Q: What happens if I use an older version of the app?**  
A: The companion will fall back to the configuration file for any settings not available in the app JSON.

**Q: Do I need to restart the companion after changing settings in the app?**  
A: No, the companion will automatically detect and apply changes from the app within 2 hours (the cache expiration time).

**Q: Can I still use the configuration file for some settings?**  
A: Yes, the timezone and general configuration options are still managed through the configuration file.
