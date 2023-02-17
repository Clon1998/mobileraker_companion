## General
>  **_NOTE:_** THIS IS STILL WIP!


Custom notifications are supported through the gcode command `M117` and the prefix `$MR$:`. 
There are two options for issuing a push notification:
1. _Only the body_: `M117 $MR$:<BODY>` e.g. `M117 $MR$:Hey I am a notification`
2. _Title and Body_:`M117 $MR$:<TITLE>|<BODY>` e.g. `M117 $MR$:Printer is at Temp!|The printer reached the target temperature


## Placeholders:

You can include in the title or body string the following placeholders that 
the companion will replace the following:


| Placeholder Key      | Description                                                                                                                                                 | Condition                                                                         |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `$printer_name`      | The name of the printer set in Mobileraker app                                                                                                              | Can always be used                                                                |
| `$file`              | The file that is currently printing                                                                                                                         | Only available while the printer is in state printing, paused or completed |
| `$eta`               | The eta of the current print job in the timezone defined through the config file. Date-Format corresponds to the provided `eta_format` in the config          | Only available during printing or paused                                          |
| `$a_eta`             | In contrast to `$eta`, the adaptive eta returns the eta timestamp if the print ends on the current day, else it returns the date timestamp as the normal eta | Only available during printing or paused                                          |
| `$remaining` | the remaining time for the current print job (Format: days HH:MM)                                                                                           | Only available during printing or paused                                          |
| `$progress`          | The printing progress (0-100)                                                                                                                               | Only available during printing or paused                                          |


> **_Limitations_**
> The custom notifications ensure that only a "new" m117 is pushed to the user's device. Therefore, issuing another M117 with the exact same content won't issue a new notification. 
