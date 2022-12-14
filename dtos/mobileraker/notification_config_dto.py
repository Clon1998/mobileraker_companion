from ctypes import cast
from typing import Any, Dict, List, Optional

# "5f4d11e8-ad41-4126-88ff-7593b68555d9": {
#     "created": "2022-11-25T23:03:47.656260",
#     "lastModified": "2022-11-26T19:46:59.083649",
#     "fcmToken": "eGcunrDKRPmL7cY-_p_cpR:APA91bETgET6iCPUbPIEaHdh0D4haomGDVdv1TTiW4AQOI6Wm3LJnD8-VfrJY4wbkce94RblhVwACggXUbEj3Q8vq_CAcMFDtid5y6Cipmam5wfoJFHq57Nt3tMwS4AR8sk6Y0Y9fSBZ",
#     "machineName": "V2.1111",
#     "language": "en",
#     "settings": {
#         "created": "2022-11-25T23:03:47.656261",
#         "lastModified": "2022-11-26T19:46:59.083595",
#         "progress": 0.05,
#         "states": [
#             "paused",
#             "complete",
#             "error",
#             "printing",
#             "standby"
#         ]
#     },
#     "snap": {
#        "progress":0.0,
#        "state": "standby"
#     }
# }

# These are bundeleted in moonraker DB in an array/map -> each device has its own config! (Use the uuid of the machine class of flutter as id!)


class DeviceNotificationEntry:
    def __init__(self):
        self.created: str
        self.last_modified: str
        self.fcm_token: str  # Device's FCM token
        self.machine_id: str  # Flutter: machine.uuid
        self.machine_name: str
        self.language: str = 'en'
        self.settings: NotificationSettings
        self.snap: NotificationSnap

    @staticmethod
    def fromJSON(json: Dict[str, Any]) -> 'DeviceNotificationEntry':
        cfg = DeviceNotificationEntry()

        cfg.created = json['created']
        cfg.last_modified = json['lastModified']
        cfg.fcm_token = json['fcmToken']
        cfg.machine_id = json['machineId']
        cfg.machine_name = json['machineName']
        cfg.language = json['language']
        cfg.settings = NotificationSettings.fromJSON(json['settings'])
        cfg.snap = NotificationSnap.fromJSON(
            json['snap']) if 'snap' in json else NotificationSnap()

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


#     "settings": {
#         "created": "2022-11-25T23:03:47.656261",
#         "lastModified": "2022-11-26T19:46:59.083595",
#         "progress": 0.05,
#         "states": [
#             "paused",
#             "complete",
#             "error",
#             "printing",
#             "standby"
#         ]
#     }
class NotificationSettings:
    def __init__(self):
        self.created: str
        self.last_modified: str
        self.progress_config: int = 25
        self.state_config: List[str] = []

    @staticmethod
    def fromJSON(json: Dict[str, Any]) -> 'NotificationSettings':
        cfg = NotificationSettings()

        cfg.created = json['created']
        cfg.last_modified = json['lastModified']
        prog_float = json['progress']
        cfg.progress_config = min(50, round(prog_float * 100)) if prog_float > 0 else -1
        cfg.state_config = json['states']

        return cfg

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

#     "snap": {
#        "progress":0.0,
#        "state": "standby"
#     }


class NotificationSnap:
    def __init__(self,
                 progress: int = 0,
                 state: str = '',
                 m117: str = ''
                 ):
        self.progress: int = progress
        self.state: str = state
        self.m117: str = m117

    @staticmethod
    def fromJSON(json: Dict[str, Any]) -> 'NotificationSnap':
        cfg = NotificationSnap()

        cfg.progress = round(json['progress']*100)
        cfg.state = json['state']
        cfg.m117 = json['m117'] if 'm117' in json else ''

        return cfg

    def toJSON(self) -> Dict[str, Any]:
        return {
            "progress": round(self.progress/100, 2),
            "state": self.state,
            "m117": self.m117,
        }

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )
