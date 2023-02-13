from typing import Any, Dict, List, Optional


class NotificationContentDto:
    def __init__(self,
                 id: int,
                 channel:str,
                 title: str,
                 body: str,
                 ):
        self.id: int = id
        self.channel: str = channel
        self.title: str = title
        self.body: str = body

    def toJSON(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "channel": self.channel,
            "title": self.title,
            "body": self.body,
        }


class DeviceRequestDto:
    def __init__(self,
                 printer_id: str,
                 token: str,
                 notifcations: List[NotificationContentDto],
                 ):
        self.printer_id: str = printer_id
        self.token: str = token
        self.notifcations:  List[NotificationContentDto] = notifcations

    def toJSON(self) -> Dict[str, Any]:
        notifications = []
        for n in self.notifcations:
            notifications.append(n.toJSON())

        return {
            "printerIdentifier": self.printer_id,
            "token": self.token,
            "notifications": notifications,
        }

    # def __eq__(self, o: object) -> bool:
    #     if not isinstance(o, CompanionRequestDto):
    #         return False

    #     return self.print_state == o.print_state and \
    #         self.tokens == o.tokens and self.printer_identifier == o.printer_identifier and \
    #         self.filename == o.filename and self.progress == o.progress and \
    #         self.printing_duration == o.printing_duration


class FcmRequestDto:
    def __init__(self,
                 device_requests: List[DeviceRequestDto],
                 ):
        self.device_requests: List[DeviceRequestDto] = device_requests

    def toJSON(self) ->  Dict[str, Any]:
        dtos = []
        for n in self.device_requests:
            dtos.append(n.toJSON())

        return {
            "version": 1,
            "deviceRequests": dtos,
        }
