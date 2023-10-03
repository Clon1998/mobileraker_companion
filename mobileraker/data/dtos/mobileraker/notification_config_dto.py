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
#     },
#     "apns": {
#       "created": "",
#       "lastModified": "",
#       "liveActivity": ""
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
        self.apns: Optional[APNs] = None

    @staticmethod
    def fromJSON(machine_id: str, json: Dict[str, Any]) -> 'DeviceNotificationEntry':
        cfg = DeviceNotificationEntry()

        cfg.machine_id = machine_id
        cfg.created = json['created']
        cfg.last_modified = json['lastModified']
        cfg.fcm_token = json['fcmToken']
        cfg.machine_name = json['machineName']
        cfg.language = json['language']
        cfg.settings = NotificationSettings.fromJSON(json['settings'])
        cfg.snap = NotificationSnap.fromJSON(
            json['snap']) if 'snap' in json and json['snap'] else NotificationSnap()
        cfg.apns = APNs.fromJSON(json['apns']) if 'apns' in json and json['apns'] else None

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
        cfg.progress_config = min(
            50, round(prog_float * 100)) if prog_float > 0 else -1
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
                 m117: str = '',
                 gcode_response: Optional[str] = None,
                 ):
        self.progress: int = progress
        self.state: str = state
        self.m117: str = m117
        self.gcode_response: Optional[str] = gcode_response

    @staticmethod
    def fromJSON(json: Dict[str, Any]) -> 'NotificationSnap':
        cfg = NotificationSnap()

        cfg.progress = round(
            json['progress']*100) if 'progress' in json else -1
        cfg.state = json['state'] if 'state' in json else 'standby'
        cfg.m117 = json['m117'] if 'm117' in json else ''
        cfg.gcode_response = json['gcode_response'] if 'gcode_response' in json else None

        return cfg

    def toJSON(self) -> Dict[str, Any]:
        data = {
            "progress": round(self.progress / 100, 2),
            "state": self.state,
            "m117": self.m117
        }

        if self.gcode_response is not None:
            data["gcode_response"] = self.gcode_response

        return data

    def copy_with(self, progress: Optional[int] = None,
                  state: Optional[str] = None,
                  m117: Optional[str] = None,
                  gcode_response: Optional[str] = None,
                  ) -> 'NotificationSnap':
        """
        Create a new instance of NotificationSnap with updated attributes.

        Example usage:
        new_snap = old_snap.copyWith(progress=50, state='completed')

        Parameters:
            **kwargs: Keyword arguments to update the attributes.

        Returns:
            NotificationSnap: A new instance with the updated attributes.
        """

        copied_snap = NotificationSnap(
            progress=self.progress if progress is None else progress,
            state=self.state if state is None else state,
            m117=self.m117 if m117 is None else m117,
            gcode_response=self.gcode_response if gcode_response is None else gcode_response
        )

        return copied_snap

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    def __eq__(self, other):
        if not isinstance(other, NotificationSnap):
            return False

        return (
            self.progress == other.progress and
            self.state == other.state and
            self.m117 == other.m117 and
            self.gcode_response == other.gcode_response
        )


#     "apns": {
#       "created":"",
#       "lastModified":"",
#       "liveActivity":
#     }


class APNs:
    def __init__(self,
                 liveActivity: str = '',
                 ):
        self.liveActivity: str = liveActivity

    @staticmethod
    def fromJSON(json: Dict[str, Any]) -> 'APNs':
        apn = APNs()

        apn.liveActivity = json['liveActivity'] if 'liveActivity' in json else ''

        return apn

    def toJSON(self) -> Dict[str, Any]:
        data = {
            "liveActivity": self.liveActivity
        }

        return data

    def copy_with(self,
                  liveActivity: Optional[str] = None,
                  ) -> 'APNs':

        copied_apns = APNs(
            liveActivity=self.liveActivity if liveActivity is None else liveActivity
        )

        return copied_apns

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    def __eq__(self, other):
        if not isinstance(other, APNs):
            return False

        return (
            self.liveActivity == other.liveActivity
        )
