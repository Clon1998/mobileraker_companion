from typing import Any, Dict, List, Optional


class ContentDto:
    def __init__(self):
        pass

    def toJSON(self) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement toJSON method")


class NotificationContentDto(ContentDto):
    def __init__(self,
                 id: int,
                 channel: str,
                 title: str,
                 body: str,
                 image: Optional[str] = None,
                 ):
        super().__init__()
        self.id: int = id
        self.channel: str = channel
        self.title: str = title
        self.body: str = body
        self.image: Optional[str] = image

    def toJSON(self) -> Dict[str, Any]:
        json = {
            "id": self.id,
            "channel": self.channel,
            "title": self.title,
            "body": self.body,
        }

        if self.image is not None:
            json['image'] = self.image

        return json


class LiveActivityContentDto(ContentDto):
    def __init__(self,
                 token: str,
                 progress: float,  # (0.0 - 1.0)
                 eta: Optional[int],  # seconds since unix epoch
                 live_activity_event: Optional[str],  # update or end
                 ):
        super().__init__()
        self.live_activity_event: Optional[str] = live_activity_event
        self.token: str = token
        self.progress: float = progress
        self.eta: Optional[int] = eta

    def toJSON(self) -> Dict[str, Any]:
        json = {
            "type": "update" if self.live_activity_event is None else self.live_activity_event,
            "token": self.token,
            "progress": self.progress,
        }
        if self.eta is not None:
            json['eta'] = self.eta
        return json


class DeviceRequestDto:
    def __init__(self,
                 printer_id: str,
                 token: str,
                 notifcations: List[ContentDto],
                 ):
        self.printer_id: str = printer_id
        self.token: str = token
        self.notifcations:  List[ContentDto] = notifcations

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

    def toJSON(self) -> Dict[str, Any]:
        dtos = []
        for n in self.device_requests:
            dtos.append(n.toJSON())

        return {
            "version": 1,
            "deviceRequests": dtos,
        }
