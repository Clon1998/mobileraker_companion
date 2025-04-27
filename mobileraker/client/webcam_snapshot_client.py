from io import BytesIO
import logging
from typing import Optional, Union

from PIL import Image, ImageOps
import requests

from mobileraker.data.dtos.moonraker.webcam_data import WebcamData



class WebcamSnapshotClient:
    """
    A client that captures and processes snapshots from a webcam.

    Parameters:
        uri_or_data (Union[str, WebcamData]): Either a URI string or WebcamData object.
        base_url (str, optional): Base URL of the server to prepend for relative paths. Default is "http://localhost".
        rotation (int, optional): Fallback rotation angle if URI is provided directly. Default is 0.

    Attributes:
        uri (str): The URI to fetch the snapshot from.
        base_url (str): Base URL of the server for handling relative paths.
        rotation (int): The rotation angle (in degrees) to apply to the captured snapshot.
        flip_horizontal (bool): Whether to flip the image horizontally.
        flip_vertical (bool): Whether to flip the image vertically.
        logger (logging.Logger): The logger instance for logging messages.
    """

    def __init__(self, uri_or_data: Union[str, WebcamData], base_url: str = "http://localhost", rotation: int = 0) -> None:
        self.base_url = base_url.rstrip('/')
        
        if isinstance(uri_or_data, WebcamData):
            self.uri = self._normalize_uri(uri_or_data.snapshot_url)
            self.rotation = uri_or_data.rotation
            self.flip_horizontal = uri_or_data.flip_horizontal
            self.flip_vertical = uri_or_data.flip_vertical
            self.name = uri_or_data.name
        else:
            self.uri = self._normalize_uri(uri_or_data)
            self.rotation = rotation
            self.flip_horizontal = False
            self.flip_vertical = False
            self.name = "Unknown"
            
        self.logger = logging.getLogger('mobileraker.webcam')
        
    def _normalize_uri(self, uri: str) -> str:
        """
        Normalize the URI by adding base_url if it's a relative path.
        
        Args:
            uri (str): The URI to normalize.
            
        Returns:
            str: The normalized URI.
        """
        if not uri:
            return ""
            
        # Check if the URI is already absolute
        if uri.startswith(('http://', 'https://')):
            return uri
            
        # Handle relative paths
        if uri.startswith('/'):
            return f"{self.base_url}{uri}"
        else:
            return f"{self.base_url}/{uri}"

    def capture_snapshot(self, max_width: int = 1024, quality: int = 85) -> Optional[bytes]:
        """
        Captures and processes a snapshot from the webcam.

        Args:
            max_width (int): Maximum width for the image, will scale proportionally. Default is 1024.
            quality (int): JPEG compression quality (1-100). Default is 85.

        Returns:
            Optional[bytes]: The processed snapshot image as bytes if successful, or None on failure.
        """
        self.logger.info("Capturing snapshot from webcam: %s at %s", self.name, self.uri)
        try:
            res = requests.get(self.uri, timeout=5)
            res.raise_for_status()

            image = Image.open(BytesIO(res.content)).convert("RGB")
            
            # Resize the image if width exceeds max_width
            if image.width > max_width:
                image = image.resize((max_width, int(image.height * (max_width / image.width))))
            
            # Apply transformations
            if self.flip_horizontal:
                image = ImageOps.mirror(image)
            if self.flip_vertical:
                image = ImageOps.flip(image)
            if self.rotation:
                image = image.rotate(self.rotation)
                
            # Convert to JPEG
            buffered = BytesIO()
            image.save(buffered, format="JPEG", optimize=True, quality=quality)
            
            self.logger.info(
                "Snapshot captured successfully! Applied transformations: rotation=%i°, flip_h=%s, flip_v=%s", 
                self.rotation, self.flip_horizontal, self.flip_vertical
            )
            return buffered.getvalue()
            
        except requests.exceptions.ConnectionError:
            self.logger.error("Could not connect to webcam: %s", self.name)
        except requests.exceptions.Timeout:
            self.logger.error("Connection to webcam timed out: %s", self.name)
        except requests.exceptions.RequestException as e:
            self.logger.error("HTTP error while connecting to webcam: %s - %s", self.name, str(e))
        except Exception as e:
            self.logger.error("Error processing snapshot from %s: %s", self.name, str(e))
            
        return None