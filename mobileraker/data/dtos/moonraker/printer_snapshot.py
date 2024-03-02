from datetime import datetime, timedelta
from typing import Dict, Optional
import math
from dateutil import tz

from mobileraker.data.dtos.moonraker.printer_objects import FilamentSensor, GCodeFile, GCodeMove, PrintStats, Toolhead, VirtualSDCard


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
        self.virtual_sdcard: Optional[VirtualSDCard] = None
        self.print_stats: Optional[PrintStats] = None
        self.current_file: Optional[GCodeFile] = None
        self.toolhead: Optional[Toolhead] = None
        self.gcode_move: Optional[GCodeMove] = None
        self.gcode_response: Optional[str] = None
        self.gcode_response_hash: Optional[str] = None
        self.timelapse_pause: Optional[bool] = None
        self.filament_sensors: Dict[str, FilamentSensor] = {}

    def __str__(self):
        filament_sensors_str = ', '.join(str(v) for v in self.filament_sensors.values())
        return f"PrinterSnapshot(klippy_ready={self.klippy_ready}, print_state={self.print_state}, m117={self.m117}, m117_hash={self.m117_hash}, virtual_sdcard={self.virtual_sdcard}, print_stats={self.print_stats}, current_file={self.current_file}, toolhead={self.toolhead}, gcode_move={self.gcode_move}, gcode_response={self.gcode_response}, gcode_response_hash={self.gcode_response_hash}, timelapse_pause={self.timelapse_pause}, filament_sensors={filament_sensors_str})"

    def __eq__(self, other):
        if not isinstance(other, PrinterSnapshot):
            return False

        return (
            self.klippy_ready == other.klippy_ready
            and self.print_state == other.print_state
            and self.m117 == other.m117
            and self.m117_hash == other.m117_hash
            and self.virtual_sdcard == other.virtual_sdcard
            and self.current_file == other.current_file
            and self.gcode_response == other.gcode_response
            and self.timelapse_pause == other.timelapse_pause
            and self.filament_sensors == other.filament_sensors
        )

    @property
    def remaining_time_by_file(self) -> Optional[int]:
        """
        Calculate the remaining time based on the file progress.

        Returns:
            Optional[int]: Remaining time in seconds, or None if calculation is not possible.
        """
        print_duration = self.print_stats.print_duration if self.print_stats else None
        print_progress = self.virtual_sdcard.progress if self.virtual_sdcard else None
        if print_duration is None or print_duration <= 0 or print_progress is None or print_progress <= 0:
            return None
        return int((print_duration / print_progress - print_duration))

    @property
    def remaining_time_by_filament(self) -> Optional[int]:
        """
        Calculate the remaining time based on filament usage and progress.

        Returns:
            Optional[int]: Remaining time in seconds, or None if calculation is not possible.
        """
        print_duration = self.print_stats.print_duration if self.print_stats else None
        filament_used = self.print_stats.filament_used if self.print_stats else None
        filament_total = self.current_file.filament_total if self.current_file else None
        if (
            print_duration is None
            or print_duration <= 0
            or filament_total is None
            or filament_used is None
            or filament_total <= filament_used
        ):
            return None
        return int((print_duration / (filament_used / filament_total) - print_duration))

    @property
    def remaining_time_by_slicer(self) -> Optional[int]:
        """
        Calculate the remaining time based on slicer estimate and progress.

        Returns:
            Optional[int]: Remaining time in seconds, or None if calculation is not possible.
        """
        print_duration = self.print_stats.print_duration if self.print_stats else None
        slicer_estimate = self.current_file.estimated_time if self.current_file else None
        if slicer_estimate is None or print_duration is None or print_duration <= 0 or slicer_estimate <= 0:
            return None
        return int((slicer_estimate - print_duration))

    @property
    def remaining_time_avg(self) -> Optional[int]:
        """
        Calculate the average of remaining times from different criteria.

        Returns:
            Optional[int]: Average remaining time in seconds, or None if calculation is not possible.
        """
        remaining = 0
        cnt = 0

        r_file = self.remaining_time_by_file or 0
        if r_file > 0:
            remaining += r_file
            cnt += 1

        r_filament = self.remaining_time_by_filament or 0
        if r_filament > 0:
            remaining += r_filament
            cnt += 1

        r_slicer = self.remaining_time_by_slicer or 0
        if r_slicer > 0:
            remaining += r_slicer
            cnt += 1

        if cnt == 0:
            return None

        return remaining // cnt

    @property
    def print_progress_by_fileposition_relative(self) -> Optional[float]:
        """
        Calculate the printing progress based on file position.

        Returns:
            float: Printing progress, ranging from 0 to 1.
        """
        file_position = self.virtual_sdcard.file_position if self.virtual_sdcard else None
        if (
            self.current_file
            and file_position is not None
            and self.current_file.gcode_start_byte is not None
            and self.current_file.gcode_end_byte is not None
            and self.current_file.filename == (self.print_stats.filename if self.print_stats else None)
        ):
            gcode_start_byte = self.current_file.gcode_start_byte
            gcode_end_byte = self.current_file.gcode_end_byte
            if file_position <= gcode_start_byte:
                return 0
            if file_position >= gcode_end_byte:
                return 1

            current_position = file_position - gcode_start_byte
            max_position = gcode_end_byte - gcode_start_byte
            if current_position > 0 and max_position > 0:
                return current_position / max_position

        return self.virtual_sdcard.progress if self.virtual_sdcard else None

    @property
    def remaining_time_formatted(self) -> Optional[str]:
        sec = self.remaining_time_avg
        if sec:
            return str(timedelta(seconds=sec))[:-3]  # remove the seconds part

    @property
    def eta(self) -> Optional[datetime]:
        remaining = self.remaining_time_avg
        if remaining:
            now = datetime.now()
            return now + timedelta(seconds=remaining)
        
    @property
    def eta_seconds_utc(self) -> Optional[int]:
        return int(self.eta.astimezone(
            tz.UTC).timestamp()) if self.eta else None
        

    @property
    def filename(self) -> Optional[str]:
        return self.current_file.filename if self.current_file else None

    @property
    def max_layer(self) -> int:
        total_layer = self.print_stats.total_layer if self.print_stats else None
        object_height = self.current_file.object_height if self.current_file else None
        first_layer_height = self.current_file.first_layer_height if self.current_file else None
        file_layer_count = self.current_file.layer_count if self.current_file else None
        layer_height = self.current_file.layer_height if self.current_file else None

        if total_layer:
            return total_layer
        if file_layer_count is not None:
            return file_layer_count
        if object_height is None or first_layer_height is None or layer_height is None:
            return 0

        return max(0, math.ceil((object_height - first_layer_height) / layer_height + 1))

    @property
    def current_layer(self) -> int:
        current_layer = self.print_stats.current_layer if self.print_stats else None
        print_duration = self.print_stats.print_duration if self.print_stats else 0
        first_layer_height = self.current_file.first_layer_height if self.current_file else None
        layer_height = self.current_file.layer_height if self.current_file else None
        gcode_z_position = self.gcode_move.gcode_position[2] if self.gcode_move else 0

        if current_layer:
            return current_layer
        if first_layer_height is None or layer_height is None or print_duration <= 0:
            return 0

        return max(
            0, min(self.max_layer, math.ceil((gcode_z_position - first_layer_height) / layer_height + 1)))

    @property
    def progress(self) -> Optional[int]:
        return int(self.print_progress_by_fileposition_relative * 100) if self.print_progress_by_fileposition_relative else None
    
    @property
    def is_timelapse_pause(self) -> bool:
        return self.print_state == "paused" and self.timelapse_pause is True

