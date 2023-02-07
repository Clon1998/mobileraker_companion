import logging
from asyncio import AbstractEventLoop
from typing import List, Optional

import requests

from dtos.mobileraker.companion_request_dto import DeviceRequestDto, FcmRequestDto


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

    async def push(self, request: FcmRequestDto,) -> Optional[requests.Response]:
        jsons = request.toJSON()

        self.logger.info(
            f"Sending to firebase fcm ({self.fcm_uri}): {jsons}")
        try:
            res = requests.post(
                f'{self.fcm_uri}/companion/v2/update', json=jsons)
            return res
        except requests.exceptions.ConnectionError as err:
            self.logger.error("Could not reach the mobileraker server!")
