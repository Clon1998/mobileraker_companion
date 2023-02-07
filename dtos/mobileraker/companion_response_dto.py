from typing import Any, Dict, List, Optional


# public class FirebaseMessageResponseDto {
#     ErrorCode errorCode;
#     MessagingErrorCode messagingErrorCode;
#     boolean successful;

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


    # private List<FirebaseMessageResponseDto> responses = new ArrayList<>();

    # private Integer successCount;
    # private Integer failureCount;
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
