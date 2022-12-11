## General
>  **_NOTE:_** THIS IS STILL WIP

Custom notifications are supported trough `M117` and the prefix `$MR$:`. There are two options to issue a push a notification:
1. Only the body: `M117 $MR$:<BODY>` e.g. `M117 $MR$:Hey I am a notification`
2. Title+Body ;`M117 $MR$:<TITLE>|<BODY>` e.g. `M117 $MR$:Printer is at Temp!|The printer reached the target temperature`


## Placeholders:
You can include in the title or body string the following placeholders that the companion will replace:

- `$printer_name` : The name of the printer in the app
- `$file` : If available, the currently printing file
- `$eta` : If available, the eta of the print job #WIP
- `$progress` : If printing, the printing progress (0-100)
- ..more to come
- 