from copy import copy, deepcopy
from typing import Any, Dict, Optional

class ServerInfo:
    def __init__(
            self,
            klippy_state: str = "error",
            message: Optional[str] = None
    ) -> None:
        super().__init__()
        self.klippy_state: str = klippy_state
        self.message: Optional[str] = message

    def updateWith(self, json: Dict[str, Any]) -> 'ServerInfo':
        n = deepcopy(self)
        if "klippy_state" in json:
            n.klippy_state = json["klippy_state"]
        if "result" in json:
            n.message = json["result"]
        return n


class PrintStats:
    def __init__(
            self,
            filename: Optional[str] = None,
            total_duration: int = 0,
            print_duration: int = 0,
            state: str = "error",
            message: Optional[str] = None
    ) -> None:
        super().__init__()
        self.filename: Optional[str] = filename
        self.total_duration: int = total_duration
        self.print_duration: int = print_duration
        self.state: str = state
        self.message: Optional[str] = message

    def __str__(self) -> str:
        return "PrintStats (filename: %s, total_duration: %s, print_duration: %s, state: %s, message: %s)" % (
            self.filename, self.total_duration, self.print_duration, self.state, self.message)

    def updateWith(self, json: Dict[str, Any]) -> 'PrintStats':
        n = deepcopy(self)
        if "filename" in json:
            n.filename = json["filename"]
        if "total_duration" in json:
            n.total_duration = json["total_duration"]
        if "print_duration" in json:
            n.print_duration = json["print_duration"]
        if "state" in json:
            n.state = json["state"]
        if "message" in json:
            n.message = json["message"]
        return n


class DisplayStatus:

    def __init__(
            self,
            message: Optional[str] = None,
            progress: float = 0
    ) -> None:
        super().__init__()
        self.message: Optional[str] = message
        self.progress: float = progress

    def __str__(self) -> str:
        return "DisplayStatus (progress: %f, message: %s)" % (self.progress, self.message)

    def updateWith(self, json: Dict[str, Any]) -> 'DisplayStatus':
        n = deepcopy(self)
        # Message is M117
        if "message" in json:
            n.message = json["message"]
        if "progress" in json:
            n.progress = json["progress"]

        return n


class VirtualSDCard:

    def __init__(
            self,
            file_position: int = 0,
            progress: float = 0
    ) -> None:
        super().__init__()
        self.file_position: int = file_position
        self.progress: float = progress

    def __str__(self) -> str:
        return "VirtualSDCard (progress: %f, file_position: %d)" % (self.progress, self.file_position)

    def updateWith(self, json: Dict[str, Any]) -> 'VirtualSDCard':
        n = deepcopy(self)
        if "file_position" in json:
            n.file_position = json["file_position"]
        if "progress" in json:
            n.progress = json["progress"]

        return n
