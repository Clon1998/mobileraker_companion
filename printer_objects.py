class PrintStats:
    def __init__(
            self,
            filename=None,
            total_duration=0,
            print_duration=0,
            state="error",
            message=None
    ):
        self.filename = filename
        self.total_duration = total_duration
        self.print_duration = print_duration
        self.state = state
        self.message = message

    def __str__(self) -> str:
        return "PrintStats (filename: %s, total_duration: %s, print_duration: %s, state: %s, message: %s)" % (
            self.filename, self.total_duration, self.print_duration, self.state, self.message)


class DisplayStatus:

    def __init__(
            self,
            message=None,
            progress=0
    ) -> None:
        super().__init__()
        self.message = message
        self.progress = progress

    def __str__(self) -> str:
        return "DisplayStatus (progress: %f, message: %s)" % (self.progress, self.message)


class VirtualSDCard:

    def __init__(
            self,
            file_position=0,
            progress=0
    ) -> None:
        super().__init__()
        self.file_position = file_position
        self.progress = progress

    def __str__(self) -> str:
        return "VirtualSDCard (progress: %f, file_position: %d)" % (self.progress, self.file_position)

