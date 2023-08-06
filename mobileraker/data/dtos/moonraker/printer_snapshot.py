from datetime import datetime, tzinfo, timedelta
from typing import Optional


class PrinterSnapshot:
    def __init__(
        self,
        klippy_ready: bool,
        print_state: str,
    ) -> None:
        super().__init__()
        self.klippy_ready: bool = klippy_ready
        self.print_state: str = print_state
        self.m117: Optional[str] = None
        self.m117_hash: str = ''
        self.progress: Optional[int] = None
        self.filename: Optional[str] = None
        self.printing_duration: Optional[int] = None

    def get_remaining_seconds(self) -> Optional[int]:
        if self.printing_duration and self.progress and self.printing_duration > 0 and self.progress > 0:
            return round(self.printing_duration/(self.progress/100) - self.printing_duration)

    def get_formatted_remaining_time(self) -> Optional[str]:
        sec = self.get_remaining_seconds()
        if sec:
            return str(timedelta(seconds=sec))[:-3]  # remove the seconds part

    def get_eta(self, timezone: tzinfo) -> Optional[datetime]:
        remaining = self.get_remaining_seconds()
        if remaining:
            now = datetime.now(timezone)
            eta = now + timedelta(seconds=remaining)
            return eta

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )