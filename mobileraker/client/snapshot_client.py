from io import BytesIO
import logging
from PIL import Image
from typing import Optional

import requests


class SnapshotClient:
    """
    A class to take snapshots from a webcam using a provided URI.

    Parameters:
        uri (str): The URI to fetch the snapshot from.
        rotation (int, optional): The rotation angle (in degrees) to apply to the captured snapshot.
            Default is 0 (no rotation).

    Attributes:
        uri (str): The URI to fetch the snapshot from.
        rotation (int): The rotation angle (in degrees) to apply to the captured snapshot.
        logger (logging.Logger): The logger instance for logging messages.
    """

    def __init__(self, uri: str, rotation: int = 0) -> None:
        self.uri: str = uri
        self.rotation: int = rotation
        self.logger = logging.getLogger('mobileraker.cam')

    def take_snapshot(self) -> Optional[bytes]:
        """
        Takes a snapshot from the provided URI and returns it as bytes.

        Returns:
            Optional[bytes]: The snapshot image as bytes if successful, or None on failure.
        """
        self.logger.info("Trying to take a snapshot from URI: %s", self.uri)
        try:
            res = requests.get(self.uri, timeout=5)
            res.raise_for_status()

            image = Image.open(BytesIO(res.content)).convert("RGB")
            image = image.rotate(self.rotation)
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            self.logger.info("Took webcam snapshot! Rotating it using rotation %i°", self.rotation)
            return buffered.getvalue()
        except requests.exceptions.ConnectionError:
            self.logger.error("Could not connect to webcam!")
        except Exception as e:
            self.logger.error("Error while trying to process image request: %s", str(e))


# Example usage:
# snapshot_client = SnapshotClient(uri="http://example.com/webcam/snapshot")
# snapshot_bytes = snapshot_client.take_snapshot()
# if snapshot_bytes:
#     # Do something with the snapshot_bytes


