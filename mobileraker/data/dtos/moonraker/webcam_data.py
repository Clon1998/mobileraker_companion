from typing import Any, Dict


class WebcamData:
    """
    Stores webcam configuration data retrieved from Moonraker.
    """
    def __init__(self, data: Dict[str, Any]):
        data = data or {}
        self.name: str = data.get('name', '')
        self.snapshot_url: str = data.get('snapshot_url', '')
        self.rotation: int = data.get('rotation', 0)
        self.flip_horizontal: bool = data.get('flip_horizontal', False)
        self.flip_vertical: bool = data.get('flip_vertical', False)
        self.uid: str = data.get('uid', '')
    
    def __str__(self):
        return f"WebcamData(name={self.name}, rotation={self.rotation}, uid={self.uid})"
