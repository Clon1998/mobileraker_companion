import logging
from asyncio import AbstractEventLoop
from typing import Optional

import requests

from mobileraker.data.dtos.mobileraker.companion_request_dto import FcmRequestDto


class MobilerakerFcmClient:
    """
    A client class to communicate with the mobileraker server using Firebase Cloud Messaging (FCM) to push notifications.

    Attributes:
        fcm_uri (str): The URI for the mobileraker FCM server.
        loop (AbstractEventLoop): The asyncio event loop.
    """

    def __init__(
        self,
        fcm_uri: str,
        loop: AbstractEventLoop,
    ) -> None:
        """
        Initialize the MobilerakerFcmClient.

        Args:
            fcm_uri (str): The URI for the mobileraker FCM server.
            loop (AbstractEventLoop): The asyncio event loop.
        """
        self.fcm_uri: str = fcm_uri
        self.loop: AbstractEventLoop = loop
        self.logger = logging.getLogger('mobileraker.fcm')

    def push(self, request: FcmRequestDto,) -> Optional[requests.Response]:
        """
        Push notifications to the mobileraker server.

        Args:
            request (FcmRequestDto): The request containing the notifications to be pushed.

        Returns:
            Optional[requests.Response]: The response from the mobileraker server, or None if an error occurred.

        Raises:
            requests.exceptions.RequestException: If there was an error while communicating with the mobileraker server.
        """
        jsons = request.toJSON()
        self.logger.info("Submitting %i notifications to mobileraker server", len(
            request.device_requests))
        self.logger.debug("Sending to firebase fcm (%s): %s",
                          self.fcm_uri, jsons)
        try:
            res = requests.post(
                f'{self.fcm_uri}/companion/v2/update', json=jsons, timeout=30
            )
            # Handle error responses, log warnings, etc.
            if res.status_code != 200:
                self.logger.warning(
                    "Received an error response from the mobileraker server. Status code: %s, Response: %s", res.status_code, res.text)
            res.raise_for_status()
            return res
        except requests.exceptions.Timeout as timeout_err:
            self.logger.error(
                "Timeout while communicating with the mobileraker server: %s", timeout_err)
            # Rethrow the exception to the caller
            raise
        except requests.exceptions.RequestException as err:
            self.logger.error(
                "Error while communicating with the mobileraker server: %s", err)
            # Propagate the exception to the caller
            raise
