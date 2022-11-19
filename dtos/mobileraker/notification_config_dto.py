from ctypes import cast
from typing import Any, Dict, List, Optional


# "fcm": {
#     "eGcunrDKRPmL7cY-_p_cpR:APA91bETgET6iCPUbPIEaHdh0D4haomGDVdv1TTiW4AQOI6Wm3LJnD8-VfrJY4wbkce94RblhVwACggXUbEj3Q8vq_CAcMFDtid5y6Cipmam5wfoJFHq57Nt3tMwS4AR8sk6Y0Y9fSBZ": {
#         "machineId": "70c7f23d-e7ec-4129-b1d8-949802d5bc3c",
#         "machineName": "V2.1111",
#         "language": "en",
#         "progressConfig": 0.25,
#         "stateConfig": [
#             "error",
#             "printing",
#             "paused"
#         ]
#     }
# },

# These are bundeleted in moonraker DB in an array/map -> each device has its own config! (Use the uuid of the machine class of flutter as id!)
class DeviceNotificationConfig:
    def __init__(self):
        self.fcm_token: str  # Device's FCM token
        self.machine_id: str  # Flutter: machine.uuid
        self.machine_name: str
        self.language: str = 'en'
        self.progress_config: float = 0.25
        self.state_config: List[str] = []

    @staticmethod
    def fromJSON(json: Dict[str, Any]) -> 'DeviceNotificationConfig':
        cfg = DeviceNotificationConfig()

        cfg.fcm_token = json['fcmToken']
        cfg.machine_id = json['machineId']
        cfg.machine_name = json['machineName']
        cfg.language = json['language']
        cfg.progress_config = json['progressConfig']
        cfg.state_config = json['stateConfig']

        return cfg

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    # def __eq__(self, o: object) -> bool:
    #     if not isinstance(o, CompanionRequestDto):
    #         return False

    #     return self.print_state == o.print_state and \
    #         self.tokens == o.tokens and self.printer_identifier == o.printer_identifier and \
    #         self.filename == o.filename and self.progress == o.progress and \
    #         self.printing_duration == o.printing_duration
