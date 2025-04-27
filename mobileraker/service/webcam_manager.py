import logging
from typing import Dict, Optional
from urllib.parse import urlsplit

from mobileraker.client.moonraker_client import MoonrakerClient
from mobileraker.client.webcam_snapshot_client import WebcamSnapshotClient
from mobileraker.data.dtos.moonraker.webcam_data import WebcamData

class WebcamManager:
    """
    Manages webcam configurations and snapshot clients with caching.
    """
    
    def __init__(self, jrpc: MoonrakerClient):
        self._jrpc = jrpc
        self._logger = logging.getLogger('mobileraker.webcam')
        # Cache stores tuple of (WebcamSnapshotClient, timestamp)
        self._client_cache: Dict[str, WebcamSnapshotClient] = {}
        
        # Register for webcam configuration changes
        self._jrpc.register_method_listener('notify_webcams_changed', self.clear_cache)
    
    async def get_webcam_client(self, webcam_uid: str) -> Optional['WebcamSnapshotClient']:
        """
        Get or create a WebcamSnapshotClient for the specified webcam UID.
        Uses cache if available and not expired.
        
        Args:
            webcam_uid (str): The UID of the webcam to fetch.
            
        Returns:
            Optional[WebcamSnapshotClient]: The webcam client if found, None otherwise.
        """
        # Check if we have this client in cache and it's not expired
        if webcam_uid in self._client_cache:
            return self._client_cache[webcam_uid]

        try:
            # Fetch webcam data from Moonraker
            self._logger.info("Fetching webcam data for UID: %s", webcam_uid)
            response, k_err = await self._jrpc.send_and_receive_method(
                "server.webcams.get_item",
                {"uid": webcam_uid}
            )

            if k_err:
                self._logger.warning("Failed to fetch webcam data: %s", k_err)
                return None
            
            if "result" not in response or "webcam" not in response["result"]:
                self._logger.warning("Invalid response format from webcam API")
                return None
            
            webcam_data = WebcamData(response["result"]["webcam"])
            
            split_url = urlsplit(self._jrpc.moonraker_uri)
            base_url = f"http://{split_url.hostname}"
            
            # Create client from the data
            client = WebcamSnapshotClient(webcam_data, base_url=base_url)
            
            # Cache this client with current timestamp
            self._client_cache[webcam_uid] = client
            self._logger.info("Successfully fetched and cached webcam client for: %s", webcam_data.name)
            return client
            
        except Exception as e:
            self._logger.error("Error fetching webcam data: %s", str(e))
            return None
    
    def clear_cache(self):
        """
        Clears the webcam client cache.
        """
        self._client_cache.clear()
        self._logger.info("Webcam client cache cleared")