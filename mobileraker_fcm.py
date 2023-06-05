import logging
from asyncio import AbstractEventLoop
from typing import Optional

import requests

from dtos.mobileraker.companion_request_dto import FcmRequestDto


class MobilerakerFcmClient:
    def __init__(
            self,
            fcm_uri: str,
            loop: AbstractEventLoop,
    ) -> None:
        super().__init__()
        self.fcm_uri: str = fcm_uri
        self.loop: AbstractEventLoop = loop
        self.logger = logging.getLogger('mobileraker.fcm')

    def push(self, request: FcmRequestDto,) -> Optional[requests.Response]:
        jsons = request.toJSON()

        self.logger.debug(
            f"Sending to firebase fcm ({self.fcm_uri}): {jsons}")
        try:
            res = requests.post(
                f'{self.fcm_uri}/companion/v2/update', json=jsons, timeout=60)
            res.raise_for_status()
            return res
        except requests.exceptions.ConnectionError as err:
            self.logger.error("Could not reach the mobileraker server!")
