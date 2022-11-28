from typing import Optional


class PrinterSnapshot:
    def __init__(
        self,
        print_state: str,
    ) -> None:
        super().__init__()
        self.print_state: str = print_state
        self.progress: Optional[int] = None
        self.filename: Optional[str] = None
        self.printing_duration: Optional[int] = None