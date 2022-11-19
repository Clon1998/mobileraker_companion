import asyncio
import json
import logging
import random
from asyncio import AbstractEventLoop, Future, Task
from typing import Any, Callable, Dict, List, Optional, cast
import coloredlogs

from websockets import client, exceptions, typing


class MoonrakerClient:
    def __init__(
            self,
            moonraker_uri: str,
            moonraker_api: Optional[str],
            loop: AbstractEventLoop,
    ) -> None:
        super().__init__()
        self.moonraker_uri: str = moonraker_uri
        self.moonraker_api_key: Optional[str] = moonraker_api
        self._loop: AbstractEventLoop = loop
        self._websocket: Optional[client.WebSocketClientProtocol] = None
        self._method_callbacks: Dict[str, List[Callable]] = {}
        self._req_cb: Dict[int, Callable] = {}
        self._req_blocking: Dict[int, Future] = {}
        self._rec_task: Optional[Task] = None
        self._logger: logging.Logger = logging.getLogger('mobileraker.jrpc')

    async def connect(self, on_connected: Callable) -> None:
        self._logger.info("Trying to connect to: %s api key %s" % (self.moonraker_uri,
                                                            '<NO API KEY>' if self.moonraker_api_key is None else self.moonraker_api_key[
                                                                :6] + '##########################'))
        async for websocket in client.connect(self.moonraker_uri,
                                              extra_headers=None if self.moonraker_api_key is None else [
                                                  ('X-Api-Key', self.moonraker_api_key)]):
            try:
                self._logger.info("WebSocket connected")
                self._websocket = websocket
                if self._rec_task:
                    self._rec_task.cancel()
                self._rec_task = self._loop.create_task(
                    self._start_receiving())
                on_connected()
                await self._websocket.wait_closed()
            except exceptions.ConnectionClosed:
                self._logger.warning("Connectionec was closed...")
                continue

    async def send_method(self, method: str, callback=None, params: Optional[dict] = None) -> int:
        if self._websocket is None:
            self._logger.error('Websocket is not yet connected?')
            raise Exception('Websocket is NONE')
        req_dict = self._construct_json_rpc(method, params)
        message_json: str = json.dumps(req_dict)
        if callback:
            self._req_cb[req_dict["id"]] = callback

        self._logger.debug("Sending message %s" % message_json)
        await self._websocket.send(message_json)
        return req_dict["id"]

    async def send_and_receive_method(self, method: str, params: Optional[dict] = None):
        if self._websocket is None:
            self._logger.error('Websocket is not yet connected?')
            raise Exception('Websocket is NONE')
        req_dict = self._construct_json_rpc(method, params)
        message_json = json.dumps(req_dict)
        m_id = req_dict["id"]
        response_future = self._loop.create_future()

        self._req_cb[m_id] = self._receive_blocking_cb
        self._req_blocking[m_id] = response_future

        self._logger.debug("Sending message (Blocking) %s" % message_json)
        await self._websocket.send(message_json)
        return await response_future

    def register_method_listener(self, method: str, callback: Callable) -> None:
        if method in self._method_callbacks:
            self._method_callbacks[method].append(callback)
        else:
            self._method_callbacks[method] = [callback]

    async def _start_receiving(self) -> None:
        if self._websocket:
            async for message in self._websocket:
                await self._process_message(message)
        else:
            self._logger.error('The websocket connection is none?')

    async def _process_message(self, message: typing.Data) -> None:
        response: dict[str, Any] = json.loads(message)
        mid = response.get("id")
        if "error" in response and "message" in response["error"]:
            self._logger.warning(
                "Error message received from WebSocket-Server %s" % response["error"]["message"])
            if mid and mid in self._req_cb:
                await self._req_cb.pop(mid)(response, response["error"]["message"])
        else:
            mmethod: str = cast(str, response.get("method"))

            if mid and self._req_cb:
                if mid in self._req_cb:
                    self._logger.debug(f"Received a response to request: {mid}")
                    await self._req_cb.pop(mid)(response)
                else:
                    self._logger.error(
                        f"Received a response to unknown request: {mid}")
            else:
                self._logger.debug(
                    f"Received a method notification for method: {mmethod}")
                if mmethod in self._method_callbacks:
                    to_call = self._method_callbacks[mmethod]
                    for cb in to_call:
                        cb(response)  # provide the raw entire message!

    async def _receive_blocking_cb(self, message: Dict[str, Any], err=None):
        mid: int = cast(int, message.get("id"))
        if mid in self._req_blocking:
            response_future = self._req_blocking.pop(mid)
            response_future.set_result((message, err))
        else:
            self._logger.error(f'MessageID: {mid} had no callback?')

    def _construct_json_rpc(self, method: str, params: Optional[dict] = None) -> dict:
        while True:
            id = random.randrange(10000)
            if id not in self._req_cb.keys():
                break
        req = {
            "jsonrpc": "2.0",
            "method": method,
            "id": id
        }
        if params:
            req["params"] = params

        return req



coloredlogs.install(level=logging.INFO)

if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    try:

        c = MoonrakerClient(
            'ws://192.168.178.135:7125/websocket', None, event_loop)
        event_loop.create_task(c.connect(lambda: print(
            'I AM COOOOOOOOOOOOOOOONECTED!!!!!!!!!!!')))
        event_loop.run_forever()
    finally:
        event_loop.close()
    exit()
