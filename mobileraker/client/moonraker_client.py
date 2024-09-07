import asyncio
import json
import logging
import random
from asyncio import AbstractEventLoop, Future, Task
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, cast


from websockets import client, exceptions, typing, connection


class MoonrakerClient:
    def __init__(
            self,
            moonraker_uri: str,
            moonraker_api: Optional[str],
            printer_name: str,
            loop: AbstractEventLoop,
    ) -> None:
        super().__init__()
        self.moonraker_uri: str = moonraker_uri
        self.moonraker_api_key: Optional[str] = moonraker_api
        self._loop: AbstractEventLoop = loop
        self._websocket: Optional[client.WebSocketClientProtocol] = None
        self._method_callbacks: Dict[str, List[Callable]] = {}
        self._req_cb: Dict[int, Callable[[
            Dict[str, Any], Optional[str]], Any]] = {}
        self._req_blocking: Dict[int, Future] = {}
        self._rec_task: Optional[Task] = None
        self._logger: logging.Logger = logging.getLogger(f'mobileraker.{printer_name}.jrpc')
        self._connection_listeners: List[Callable[[bool], None]] = []

    async def connect(self) -> None:
        '''
        Establishes a WebSocket connection with the specified moonraker_uri and API key.

        The method attempts to connect to the moonraker_uri using the provided API key, if available.
        It logs connection status and notifies connection listeners accordingly.

        Raises:
            ConnectionError: If the connection attempt fails.

        Returns:
            None
        '''
        self._logger.info("Trying to connect to: %s api key %s", self.moonraker_uri,
                          '<NO API KEY>' if self.moonraker_api_key is None else self.moonraker_api_key[
                              :6] + '##########################')
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
                self._notify_connection_listeners(True)
                await self._websocket.wait_closed()
                self._logger.info("websocket closed ?????...")
            except exceptions.ConnectionClosed:
                self._logger.info("websocket was closed...")
            except Exception as err:
                self._logger.info("Unexpected exception occured %s", err)
            finally:
                self._notify_connection_listeners(False)

    async def send_method(self, method: str, callback: Optional[Callable[[Dict[str, Any], Optional[str]], Any]] = None, params: Optional[dict] = None, timeout: float = 10.0) -> int:

        '''
        Sends a JSON-RPC method request through the established WebSocket connection.

        This method constructs a JSON-RPC request from the provided method and parameters,
        sends it to the server via the WebSocket connection, and optionally sets a callback
        function to handle the response when received.

        Args:
            method (str): The JSON-RPC method to be called.
            callback (Optional[Callable]): A function that will be called with the response
                                        when received from the server (optional).
            params (Optional[dict]): Parameters to be included in the JSON-RPC request (optional).

        Returns:
            int: The request ID associated with the sent JSON-RPC request.

        Raises:
            ConnectionError: If the WebSocket connection is not established.
            asyncio.TimeoutError: If the request to send the message times out.
        '''
        if self._websocket is None:
            self._logger.error('Websocket is not yet connected?')
            raise ConnectionError('Websocket is NONE')
        req_dict = self._construct_json_rpc(method, params)
        message_json: str = json.dumps(req_dict)
        if callback:
            self._req_cb[req_dict["id"]] = callback

        self._logger.debug("Sending message %s", message_json)
        await asyncio.wait_for(self._websocket.send(message_json), timeout=timeout)
        return req_dict["id"]

    async def send_and_receive_method(self, method: str, params: Optional[dict] = None, timeout: float = 10.0) -> Tuple[
            Dict[str, Any], Optional[str]]:
        '''
        Sends a JSON-RPC method request through the established WebSocket connection
        and waits for the corresponding response.

        This method constructs a JSON-RPC request from the provided method and parameters,
        sends it to the server via the WebSocket connection, and waits for the server's
        response. The response is returned to the caller.

        Args:
            method (str): The JSON-RPC method to be called.
            params (Optional[dict]): Parameters to be included in the JSON-RPC request (optional).

        Returns:
            Any: The response received from the server after executing the JSON-RPC request.

        Raises:
            ConnectionError: If the WebSocket connection is not established.
            asyncio.TimeoutError: If the response is not received within a certain time frame.
                        (This might not be explicitly mentioned in the code snippet,
                        but could be an assumption for a production implementation.)
        '''
        if self._websocket is None:
            self._logger.error('Websocket is not yet connected?')
            raise ConnectionError('Websocket is NONE')
        req_dict = self._construct_json_rpc(method, params)
        message_json = json.dumps(req_dict)
        m_id = req_dict["id"]
        response_future = self._loop.create_future()

        self._req_cb[m_id] = self._receive_blocking_cb
        self._req_blocking[m_id] = response_future

        self._logger.debug("Sending message (Blocking) %s", message_json)
        await asyncio.wait_for(self._websocket.send(message_json), timeout=timeout)
        return await asyncio.wait_for(response_future, timeout=timeout)

    def register_method_listener(self, method: str, callback: Callable) -> None:
        '''
        Registers a callback function to listen for specific JSON-RPC methods.

        This method allows you to register a callback function to listen for responses
        or events associated with a particular JSON-RPC method. Whenever a JSON-RPC
        message with the specified method is received, the associated callback will be
        invoked to handle the message.

        Args:
            method (str): The JSON-RPC method to listen for.
            callback (Callable): The callback function to be invoked when a message
                                with the specified method is received.

        Returns:
            None
        '''
        if method in self._method_callbacks:
            self._method_callbacks[method].append(callback)
        else:
            self._method_callbacks[method] = [callback]

    def register_connection_listener(self, listener: Callable[[bool], Any]) -> None:
        '''
        Registers a listener function to receive connection status updates.

        This method allows you to register a listener function to receive updates on the
        WebSocket connection status. The registered listener will be invoked whenever
        there is a change in the connection status, and it will be passed a boolean value
        indicating whether the connection is currently active (True) or inactive (False).

        Args:
            listener (Callable[[bool], None]): The listener function that will be called
                                            with the connection status updates.

        Returns:
            None
        '''
        self._connection_listeners.append(listener)
        if self._websocket is not None and self._websocket.state == connection.State.OPEN:
            listener(True)

    async def _start_receiving(self) -> None:
        if self._websocket:
            async for message in self._websocket:
                await self._process_message(message)
        else:
            self._logger.error('The websocket connection is none?')

    async def _process_message(self, message: typing.Data) -> None:
        response: Dict[str, Any] = json.loads(message)
        mid = response.get("id")
        if "error" in response and "message" in response["error"]:
            self._logger.warning(
                "Error message received from WebSocket-Server %s", response["error"]["message"])
            if mid and mid in self._req_cb:
                callback = self._req_cb.pop(mid)

                if asyncio.iscoroutinefunction(callback):
                    self._loop.create_task(
                        callback(response, response["error"]["message"]))
                else:
                    callback(response, response["error"]["message"])
        else:
            mmethod: str = cast(str, response.get("method"))

            if mid and self._req_cb:
                if mid in self._req_cb:
                    self._logger.debug(
                        "Received a response to request: %s", mid)
                    callback = self._req_cb.pop(mid)

                    if asyncio.iscoroutinefunction(callback):
                        self._loop.create_task(callback(response, None))
                    else:
                        callback(response, None)
                else:
                    self._logger.error(
                        "Received a response to unknown request: %s", mid)
            else:
                self._logger.debug(
                    "Received a method notification for method: %s", mmethod)
                if mmethod in self._method_callbacks:
                    to_call = self._method_callbacks[mmethod]
                    for listener in to_call:
                        listener(response)  # provide the raw entire message!

    async def _receive_blocking_cb(self, message: Dict[str, Any], err=None):
        mid: int = cast(int, message.get("id"))
        if mid in self._req_blocking:
            response_future = self._req_blocking.pop(mid)
            response_future.set_result((message, err))
        else:
            self._logger.error('MessageID: %s had no callback?', mid)

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

    def _notify_connection_listeners(self, is_connected: bool):
        self._logger.info(
            "Notifying listeners about connection state %s", is_connected)
        for callback in self._connection_listeners:
            callback(is_connected)
