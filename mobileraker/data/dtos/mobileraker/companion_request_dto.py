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
    
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )


class ProgressNotificationContentDto(ContentDto):
    def __init__(self,
                 progress: int, # (0 - 100)
                 id: int,
                 channel: str,
                 title: str,
                 body: str,
                 ):
        super().__init__()
        self.id: int = id
        self.channel: str = channel
        self.title: str = title
        self.body: str = body
        self.progress: int = progress

    def toJSON(self) -> Dict[str, Any]:
        json = {
            "progress": self.progress,
            "id": self.id,
            "channel": self.channel,
            "title": self.title,
            "body": self.body,
        }

        return json
    
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

class LiveActivityContentDto(ContentDto):
    def __init__(self,
                 live_activity_event: Optional[str],  # update or end
                 token: str,
                 progress: float,  # (0.0 - 1.0)
                 eta: Optional[int],  # seconds since unix epoch
                 print_state: str,
                 file: Optional[str] = None,
                 ):
        super().__init__()
        self.live_activity_event: Optional[str] = live_activity_event
        self.token: str = token
        self.progress: float = progress
        self.eta: Optional[int] = eta
        self.print_state: str = print_state
        self.file: Optional[str] = file

    def toJSON(self) -> Dict[str, Any]:
        json = {
            "type": "update" if self.live_activity_event is None else self.live_activity_event,
            "token": self.token,
            "progress": self.progress,
            "printState": self.print_state,
        }
        if self.eta is not None:
            json['eta'] = self.eta
        if self.file is not None:
            json['file'] = self.file
        return json

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

class DeviceRequestDto:
    def __init__(self,
                 version: int,
                 printer_id: str,
                 token: str,
                 notifcations: List[ContentDto],
                 ):
        self.version: int = version
        self.printer_id: str = printer_id
        self.token: str = token
        self.notifcations:  List[ContentDto] = notifcations

    def toJSON(self) -> Dict[str, Any]:
        notifications = []
        for n in self.notifcations:
            notifications.append(n.toJSON())

        return {
            "version": self.version,
            "printerIdentifier": self.printer_id,
            "token": self.token,
            "notifications": notifications,
        }

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )


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
    
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )