# Custom Notifications in Mobileraker

Mobileraker offers two alternatives for issuing custom notifications. You can choose the method that best suits your needs:

## Using `M117` with the Prefix `$MR$:`

Custom notifications can be achieved using the `M117` G-code command along with the `$MR$:` prefix. This method provides two variations for creating notifications:

- **Body-Only Notification**: Format: `M117 $MR$:<BODY>`. Example: `M117 $MR$:Hey, I am a notification`.

- **Title and Body Notification**: Format: `M117 $MR$:<TITLE>|<BODY>`. Example: `M117 $MR$:Printer Status|The printer has reached the target temperature`.

> **Recommendation**
> Using `M117` is the simplest method. However, if your printer has a display attached, the entire `M117` message will be shown on it. If this is the case, the next option might be preferable.

## Using the `MR_NOTIFY` Custom Macro

This approach involves using the `MR_NOTIFY` G-code macro. To utilize this method, you need to include the `MR_NOTIFY` macro in your printer's configuration. The `MR_NOTIFY` macro has two parameters: `MESSAGE` and `TITLE`, where only `MESSAGE` is mandatory.

**Example Usage**: `MR_NOTIFY TITLE="I am $printer_name" MESSAGE="Feed me more Filament!"`

```properties
[gcode_macro MR_NOTIFY]
description: Allows you to send a custom notification via Mobileraker without using the M117 command
gcode:
    {% set msg = "MR_NOTIFY:" ~ (params.TITLE ~ "|" if 'TITLE' in params|upper else "") ~ params.MESSAGE %}

    {% if 'MESSAGE' in params|upper %}
        { action_respond_info(msg) }
    {% else %}
        { action_raise_error('Must provide MESSAGE parameter') }
    {% endif %}

```
> **Warning**
> Remember to include this macro in your printer's Klipper configuration file (e.g., printer.cfg). Do **NOT** include it in the mobileraker.conf file.

## Placeholders:

When crafting your custom notification's title or body/message, you have the flexibility to incorporate placeholders that will be dynamically replaced by the companion. These placeholders allow you to convey specific information relevant to the notification context. Below is a list of available placeholders and their corresponding replacements:


| Placeholder Key       | Description                                                                                                                                                      | Condition                                                                  |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `$printer_name`       | The name of the printer set in Mobileraker app                                                                                                                   | Can always be used                                                         |
| `$file`               | The file that is currently printing                                                                                                                              | Only available while the printer is in state printing, paused or completed |
| `$eta`                | The eta of the current print job in the timezone defined through the config file. Date-Format corresponds to the provided `eta_format` in the config             | Only available during printing or paused                                   |
| `$a_eta`              | In contrast to `$eta`, the adaptive eta returns the eta timestamp if the print ends on the current day, else it returns the date timestamp as the normal eta     | Only available during printing or paused                                   |
| `$remaining_avg`      | The avg remaining time for the current print job. Combining all availables sources for the remaining time (File-Position, Filament, Slicer) (Format: days HH:MM) | Only available during printing or paused                                   |
| `$remaining_file`     | The remaining time for the current print job using the File-Position as source (Format: days HH:MM)                                                              | Only available during printing or paused                                   |
| `$remaining_filament` | The remaining time for the current print job using the total and used filament as source (Format: days HH:MM)                                                    | Only available during printing or paused                                   |
| `$remaining_slicer`   | The remaining time for the current print job using the Slicer data as source (Format: days HH:MM)                                                                | Only available during printing or paused                                   |
| `$progress`           | The printing progress (0-100)                                                                                                                                    | Only available during printing or paused                                   |
| `$cur_layer`          | The current layer                                                                                                                                                | Only available during printing or paused                                   |
| `$max_layer`          | The maximum layer of the file that is currently beeing printed                                                                                                   | Only available during printing or paused                                   |


> **Warning**  
> Custom notifications are designed to prevent redundant notifications. If you issue an additional `M117`/`MR_NOTIFY` with identical content to a previous notification, Mobileraker ensures that a new notification won't be triggered. This feature helps prevent unnecessary clutter in the user's notifications by only sending new and distinct information.
