from copy import deepcopy
from typing import Any, Dict, List, Optional


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
    
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )


class PrintStats:
    def __init__(
            self,
            filename: Optional[str] = None,
            total_duration: int = 0,
            total_layer: int = 0,
            current_layer: int = 0,
            print_duration: int = 0,
            filament_used: float = 0,
            state: str = "error",
            message: Optional[str] = None
    ) -> None:
        super().__init__()
        self.filename: Optional[str] = filename
        self.total_duration: int = total_duration
        self.total_layer: Optional[int] = total_layer
        self.current_layer: Optional[int] = current_layer
        self.print_duration: int = print_duration
        self.filament_used: float = filament_used
        self.state: str = state
        self.message: Optional[str] = message

    def __str__(self) -> str:
        return "PrintStats (filename: %s, total_duration: %s, print_duration: %s, state: %s, message: %s)" % (
            self.filename, self.total_duration, self.print_duration, self.state, self.message)

    def updateWith(self, json: Dict[str, Any]) -> 'PrintStats':
        n = deepcopy(self)

        info = json["info"] if "info" in json else {}
        n.total_layer = info["total_layer"] if "total_layer" in info else None
        n.current_layer = info["current_layer"] if "current_layer" in info else None

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
        if "filament_used" in json:
            n.filament_used = json["filament_used"]
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
            n.message = json["message"].strip() if isinstance(
                json["message"], str) else None
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


class GCodeFile:
    def __init__(
        self,
        filename: str,
        modified: Optional[float] = None,
        size: Optional[int] = None,
        print_start_time: Optional[float] = None,
        job_id: Optional[str] = None,
        slicer: Optional[str] = None,
        slicer_version: Optional[str] = None,
        gcode_start_byte: Optional[int] = None,
        gcode_end_byte: Optional[int] = None,
        layer_count: Optional[int] = None,
        object_height: Optional[float] = None,
        estimated_time: Optional[float] = None,
        nozzle_diameter: Optional[float] = None,
        layer_height: Optional[float] = None,
        first_layer_height: Optional[float] = None,
        first_layer_bed_temp: Optional[float] = None,
        first_layer_extr_temp: Optional[float] = None,
        chamber_temp: Optional[float] = None,
        filament_name: Optional[str] = None,
        filament_type: Optional[str] = None,
        filament_total: Optional[float] = None,
        filament_weight_total: Optional[float] = None,
        # thumbnails: Optional[List[GCodeThumbnail]] = None
    ):
        self.filename = filename
        self.modified = modified
        self.size = size
        self.print_start_time = print_start_time
        self.job_id = job_id
        self.slicer = slicer
        self.slicer_version = slicer_version
        self.gcode_start_byte = gcode_start_byte
        self.gcode_end_byte = gcode_end_byte
        self.layer_count = layer_count
        self.object_height = object_height
        self.estimated_time = estimated_time
        self.nozzle_diameter = nozzle_diameter
        self.layer_height = layer_height
        self.first_layer_height = first_layer_height
        self.first_layer_bed_temp = first_layer_bed_temp
        self.first_layer_extr_temp = first_layer_extr_temp
        self.chamber_temp = chamber_temp
        self.filament_name = filament_name
        self.filament_type = filament_type
        self.filament_total = filament_total
        self.filament_weight_total = filament_weight_total
        # self.thumbnails = thumbnails if thumbnails is not None else []

    def __eq__(self, other):
        if isinstance(other, GCodeFile):
            return vars(self) == vars(other)
        return False

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    @classmethod
    def from_json(cls, data_dict: Dict[str, Any]) -> 'GCodeFile':
        return cls(
            filename=data_dict.get("filename", ""),
            modified=data_dict.get("modified", 0),
            size=data_dict.get("size", 0),
            print_start_time=data_dict.get("print_start_time"),
            job_id=data_dict.get("job_id"),
            slicer=data_dict.get("slicer"),
            slicer_version=data_dict.get("slicer_version"),
            gcode_start_byte=data_dict.get("gcode_start_byte"),
            gcode_end_byte=data_dict.get("gcode_end_byte"),
            layer_count=data_dict.get("layer_count"),
            object_height=data_dict.get("object_height"),
            estimated_time=data_dict.get("estimated_time"),
            nozzle_diameter=data_dict.get("nozzle_diameter"),
            layer_height=data_dict.get("layer_height"),
            first_layer_height=data_dict.get("first_layer_height"),
            first_layer_bed_temp=data_dict.get("first_layer_bed_temp"),
            first_layer_extr_temp=data_dict.get("first_layer_extr_temp"),
            chamber_temp=data_dict.get("chamber_temp"),
            filament_name=data_dict.get("filament_name"),
            filament_type=data_dict.get("filament_type"),
            filament_total=data_dict.get("filament_total"),
            filament_weight_total=data_dict.get("filament_weight_total"),
        )


class Toolhead:
    def __init__(
        self,
        position: List[float] = [0, 0, 0],
        active_extruder: str = 'extruder',
        print_time: Optional[float] = None,
        estimated_print_time: Optional[float] = None,
        max_velocity: float = 500,
        max_accel: float = 3000,
        max_accel_to_decel: float = 3000,
        square_corner_velocity: float = 1500
    ) -> None:
        self.position: List[float] = position
        self.active_extruder: str = active_extruder
        self.print_time: Optional[float] = print_time
        self.estimated_print_time: Optional[float] = estimated_print_time
        self.max_velocity: float = max_velocity
        self.max_accel: float = max_accel
        self.max_accel_to_decel: float = max_accel_to_decel
        self.square_corner_velocity: float = square_corner_velocity

    def updateWith(self, json_data: dict) -> 'Toolhead':
        n = deepcopy(self)
        n.print_time = json_data['print_time'] if 'print_time' in json_data else None
        n.estimated_print_time = json_data['estimated_print_time'] if 'estimated_print_time' in json_data else None

        if 'position' in json_data:
            n.position = json_data['position']
        if 'active_extruder' in json_data:
            n.active_extruder = json_data['active_extruder']

        if 'max_velocity' in json_data:
            n.max_velocity = json_data['max_velocity']
        if 'max_accel' in json_data:
            n.max_accel = json_data['max_accel']
        if 'max_accel_to_decel' in json_data:
            n.max_accel_to_decel = json_data['max_accel_to_decel']
        if 'square_corner_velocity' in json_data:
            n.square_corner_velocity = json_data['square_corner_velocity']
        return n


class GCodeMove:
    def __init__(
        self,
        position: List[float] = [0, 0, 0,0],
        gcode_position: List[float] = [0, 0, 0, 0],
    ) -> None:
        self.position: List[float] = position
        self.gcode_position: List[float] = gcode_position

    def updateWith(self, json_data: dict) -> 'GCodeMove':
        n = deepcopy(self)

        if 'position' in json_data:
            n.position = json_data['position']
        if 'gcode_position' in json_data:
            n.gcode_position = json_data['gcode_position']
        return n
    
class FilamentSensor:
    def __init__(self,
                 name: str,
                 kind: str,
                 enabled: bool = False,
                 filament_detected: bool = True,
                 ) -> None:
        self.name: str = name
        self.kind: str = kind
        self.enabled: bool = enabled
        self.filament_detected: bool = filament_detected

    def updateWith(self, json_data: dict) -> 'FilamentSensor':
        n = deepcopy(self)
        if 'enabled' in json_data:
            n.enabled = json_data['enabled']
        if 'filament_detected' in json_data:
            n.filament_detected = json_data['filament_detected']
        return n
    
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )