from datetime import datetime
from typing import Any, Dict, List, Optional, Set

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
#     },
#     "version": "2.6.11-android"
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
        self.version: Optional[str] = None # App version
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
        cfg.version = json['version'] if 'version' in json else None


        return cfg

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    @property
    def is_android(self) -> bool:
        return self.version is not None and 'android' in self.version
    
    @property
    def is_ios(self) -> bool:
        return self.version is not None and 'ios' in self.version

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
        self.android_progressbar: bool = True
        self.eta_sources: List[str] = ['filament','slicer']

    @staticmethod
    def fromJSON(json: Dict[str, Any]) -> 'NotificationSettings':
        cfg = NotificationSettings()

        cfg.created = json['created']
        cfg.last_modified = json['lastModified']
        prog_float = json['progress']
        cfg.progress_config = min(
            50, round(prog_float * 100)) if prog_float > 0 else -1
        cfg.state_config = json['states']
        if 'androidProgressbar' in json:
            cfg.android_progressbar = json['androidProgressbar']
        elif 'android_progressbar' in json:
            cfg.android_progressbar = json['android_progressbar']

        if 'etaSources' in json:
            cfg.eta_sources = json['etaSources']

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
                 progress_live_activity: int = 0,
                 progress_progressbar: int = 0,
                 last_progress: datetime = datetime.fromisocalendar(1970, 1, 1),
                 last_progress_live_activity: datetime = datetime.fromisocalendar(1970, 1, 1),
                 last_progress_progressbar: datetime = datetime.fromisocalendar(1970, 1, 1),
                 state: str = '',
                 m117: str = '',
                 gcode_response: Optional[str] = None,
                 filament_sensors: List[str] = [],
                 ):
        self.progress: int = progress
        self.progress_live_activity: int = progress_live_activity
        self.progress_progressbar: int = progress_progressbar
        self.last_progress: datetime = last_progress # Not used yet...!
        self.last_progress_live_activity: datetime = last_progress_live_activity
        self.last_progress_progressbar: datetime = last_progress_progressbar
        self.state: str = state
        self.m117: str = m117
        self.gcode_response: Optional[str] = gcode_response
        self.filament_sensors: List[str] = filament_sensors

    @staticmethod
    def fromJSON(json: Dict[str, Any]) -> 'NotificationSnap':
        cfg = NotificationSnap()

        cfg.progress = round(
            json['progress']*100) if 'progress' in json else -1
        cfg.progress_live_activity = round(
            json['progress_live_activity']*100) if 'progress_live_activity' in json else -1
        cfg.progress_progressbar = round(
            json['progress_progressbar']*100) if 'progress_progressbar' in json else -1
        cfg.state = json['state'] if 'state' in json else 'standby'
        cfg.m117 = json['m117'] if 'm117' in json else ''
        cfg.gcode_response = json['gcode_response'] if 'gcode_response' in json else None
        cfg.filament_sensors = json['filament_sensors'] if 'filament_sensors' in json else []

        if 'last_progress' in json:
            cfg.last_progress = datetime.fromisoformat(json['last_progress'])
        if 'last_progress_live_activity' in json:
            cfg.last_progress_live_activity = datetime.fromisoformat(json['last_progress_live_activity'])
        if 'last_progress_progressbar' in json:
            cfg.last_progress_progressbar = datetime.fromisoformat(json['last_progress_progressbar'])

        return cfg

    def toJSON(self) -> Dict[str, Any]:
        data = {
            "progress": round(self.progress / 100, 2),
            "progress_live_activity": round(self.progress_live_activity / 100, 2),
            "progress_progressbar": round(self.progress_progressbar / 100, 2),
            "state": self.state,
            "m117": self.m117,
            "filament_sensors": self.filament_sensors,
        }

        if self.gcode_response is not None:
            data["gcode_response"] = self.gcode_response
            
        if self.last_progress is not None:
            data["last_progress"] = self.last_progress.isoformat()
        if self.last_progress_live_activity is not None:
            data["last_progress_live_activity"] = self.last_progress_live_activity.isoformat()
        if self.last_progress_progressbar is not None:
            data["last_progress_progressbar"] = self.last_progress_progressbar.isoformat()

        return data

    def copy_with(self, 
                  progress: Optional[int] = None,
                  progress_live_activity: Optional[int] = None,
                  progress_progressbar: Optional[int] = None,
                  state: Optional[str] = None,
                  m117: Optional[str] = None,
                  gcode_response: Optional[str] = None,
                  filament_sensors: Optional[List[str]] = None,
                  last_progress: Optional[datetime] = None,
                  last_progress_live_activity: Optional[datetime] = None,
                  last_progress_progressbar: Optional[datetime] = None,
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
            progress_live_activity=self.progress_live_activity if progress_live_activity is None else progress_live_activity,
            progress_progressbar=self.progress_progressbar if progress_progressbar is None else progress_progressbar,
            state=self.state if state is None else state,
            m117=self.m117 if m117 is None else m117,
            gcode_response=self.gcode_response if gcode_response is None else gcode_response,
            filament_sensors=self.filament_sensors if filament_sensors is None else filament_sensors,
            last_progress=self.last_progress if last_progress is None else last_progress,
            last_progress_live_activity=self.last_progress_live_activity if last_progress_live_activity is None else last_progress_live_activity,
            last_progress_progressbar=self.last_progress_progressbar if last_progress_progressbar is None else last_progress_progressbar
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
            self.progress_live_activity == other.progress_live_activity and
            self.progress_progressbar == other.progress_progressbar and
            self.state == other.state and
            self.m117 == other.m117 and
            self.gcode_response == other.gcode_response and
            self.filament_sensors == other.filament_sensors and
            self.last_progress == other.last_progress and
            self.last_progress_live_activity == other.last_progress_live_activity and
            self.last_progress_progressbar == other.last_progress_progressbar
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
