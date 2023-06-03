from io import BytesIO
import logging
from PIL import Image
from typing import List, Optional

import requests


class SnapshotClient:
    def __init__(
            self,
            uri: str,
            rotation: int = 0
    ) -> None:
        super().__init__()
        self.uri: str = uri
        self.rotation: int = rotation
        self.logger = logging.getLogger('mobileraker.cam')

    def takeSnapshot(self,) -> Optional[bytes]:

        self.logger.info(
            f"Trying to take a snapshot from URI: {self.uri}")
        try:
            res = requests.get(self.uri, timeout=5)
            res.raise_for_status()

            image = Image.open(BytesIO(res.content)).convert("RGB")
            image = image.rotate(self.rotation)
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            self.logger.info(
                f"Took webcam snapshot! Rotating it using rotation {self.rotation}°")
            return buffered.getvalue()
        except requests.exceptions.ConnectionError as err:
            self.logger.error("Could not connect to webcam!")
        except:
            self.logger.error("Error while trying to process image request")
