# This is a sample Python script.

# Press Umschalt+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import asyncio
import json
import logging
import random
from asyncio import AbstractEventLoop
from copy import deepcopy

import coloredlogs
import websockets
from websockets.uri import WebSocketURI

from printer_objects import PrintStats, DisplayStatus, VirtualSDCard


class Client:
    def __init__(
            self,
            uri: WebSocketURI,
            loop: AbstractEventLoop,
            apikey: str = None,
    ) -> None:
        super().__init__()
        self.websocket = None
        self.server = uri
        self.apikey = apikey
        self.req_cb = {}
        self.req_blocking = {}
        self.loop = loop
        self.init_done = False
        self.klippy_ready = False
        self.print_stats = PrintStats()
        self.display_status = DisplayStatus()
        self.virtual_sdcard = VirtualSDCard()
        self.config = CompanionConfig()  # TODO: Fetch this from a remote server for easier configuration :)
        self.rec_task = None

    async def connect(self) -> None:
        async for websocket in websockets.connect(self.server):
            try:
                self.websocket = websocket
                if self.rec_task:
                    self.rec_task.cancel()
                self.rec_task = self.loop.create_task(self.start_receiving())
                await self.send_method("server.info", self.parse_server_info)
                await self.websocket.wait_closed()
            except websockets.ConnectionClosed:
                continue

    async def start_receiving(self):
        async for message in self.websocket:
            await self.process_message(message)

    async def process_message(self, message):
        response = json.loads(message)
        mid = response.get("id")
        if "error" in response and "message" in response["error"]:
            self.websocket.logger.warning(
                "Error message received from WebSocket-Server %s" % response["error"]["message"])
            if mid and mid in self.req_cb:
                await self.req_cb.pop(mid)(response, response["error"]["message"])
        else:
            mmethod = response.get("method")

            if mid and self.req_cb:

                if mid in self.req_cb:
                    self.websocket.logger.debug("Received a response to request: %d" % mid)
                    await self.req_cb.pop(mid)(response)
                else:
                    self.websocket.logger.error("Received a response to unknown request: %d" % mid)
                    self.req_cb.pop(mid)
            else:
                self.websocket.logger.debug("Received a method notification for method: %s" % mmethod)
                if mmethod == "notify_status_update":
                    # "params": [{<status object>}, <eventtime>]
                    await self.parse_notify_status_update(response["params"][0])
                elif mmethod == "notify_klippy_shutdown":
                    self.klippy_ready = False
                else:
                    self.websocket.logger.debug("Method %s not implemented/supported" % mmethod)

    async def send_method(self, method: str, callback, params: dict = None) -> int:
        req_dict = self.construct_json_rpc(method, params)
        message_json = json.dumps(req_dict)
        self.req_cb[req_dict["id"]] = callback

        self.websocket.logger.info("Sending message %s" % message_json)
        await self.websocket.send(message_json)
        return req_dict["id"]

    async def send_and_receive_method(self, method: str, params: dict = None):
        req_dict = self.construct_json_rpc(method, params)
        message_json = json.dumps(req_dict)
        m_id = req_dict["id"]
        response_future = self.loop.create_future()

        self.req_cb[m_id] = self.receive_blocking_cb
        self.req_blocking[m_id] = response_future

        self.websocket.logger.info("Sending message (Blocking) %s" % message_json)
        await self.websocket.send(message_json)
        return await response_future

    async def receive_blocking_cb(self, message=None, err=None):
        mid = message.get("id")
        if mid in self.req_blocking:
            response_future = self.req_blocking.pop(mid)
            response_future.set_result((message, err))

    async def parse_subscription_response(self, message=None, err=None):
        await self.parse_notify_status_update(message["result"]["status"])

    async def parse_notify_status_update(self, status_objects):
        for key, object_data in status_objects.items():
            if key == "print_stats":
                await self.parse_print_stats_update(object_data)
            elif key == "display_status":
                await self.parse_display_status_update(object_data)
            elif key == "virtual_sdcard":
                await self.parse_virtual_sdcard_update(object_data)
        if not self.init_done:
            self.init_done = True
            self.send_to_firebase()

    async def parse_server_info(self, message=None, err=None):
        message = message["result"]
        klippy_state = message.get("klippy_state")
        if klippy_state == "ready":
            await self.subscribe_to_notifications()
            self.klippy_ready = True
        else:
            self.klippy_ready = False
            await self.send_method("server.info", self.parse_server_info)

    async def parse_print_stats_update(self, print_stats):
        old = deepcopy(self.print_stats)
        if "filename" in print_stats:
            self.print_stats.filename = print_stats["filename"]
        if "total_duration" in print_stats:
            self.print_stats.total_duration = print_stats["total_duration"]
        if "print_duration" in print_stats:
            self.print_stats.print_duration = print_stats["print_duration"]
        if "state" in print_stats:
            self.print_stats.state = print_stats["state"]
        if "message" in print_stats:
            self.print_stats.message = print_stats["message"]

        if old.state != self.print_stats.state:
            await self.on_print_state_transition(old.state, self.print_stats.state)

    async def parse_display_status_update(self, display_status):
        incoming = DisplayStatus()

        # Tbh. I dont care about the message
        if "message" in display_status:
            incoming.message = display_status["message"]
        if "progress" in display_status:
            incoming.progress = display_status["progress"]

        if self.display_status.progress and incoming.progress - self.display_status.progress >= self.config.increments:
            self.display_status = incoming
            self.send_to_firebase()

    async def parse_virtual_sdcard_update(self, virtual_sdcard):
        incoming = VirtualSDCard()

        # Tbh. I dont care about the message
        if "file_position" in virtual_sdcard:
            incoming.progress = virtual_sdcard["file_position"]
        if "progress" in virtual_sdcard:
            incoming.progress = virtual_sdcard["progress"]

        if incoming.progress - self.virtual_sdcard.progress >= self.config.increments:
            self.virtual_sdcard = incoming
            self.send_to_firebase()

    async def subscribe_to_notifications(self):
        params = {
            "objects": {
                "print_stats": None,
                # "display_status": None,
                "virtual_sdcard": None
            }
        }
        self.init_done = False
        await self.send_method("printer.objects.subscribe", self.parse_subscription_response, params)

    async def on_print_state_transition(self, old, new):
        self.websocket.logger.info("print_state transition %s -> %s" % (old, new))
        self.send_to_firebase()

    def construct_json_rpc(self, method: str, params: dict = None) -> dict:
        while True:
            id = random.randrange(10000)
            if id not in self.req_cb.keys():
                break
        req = {
            "jsonrpc": "2.0",
            "method": method,
            "id": id
        }
        if params:
            req["params"] = params

        return req

    async def collect_for_notification(self) -> dict:
        print_state = self.print_stats.state
        out = {
            "printState": print_state,
            "tokens": await self.fetch_fcm_tokens(),
            "printerUUID": await self.fetch_printer_id()
        }

        if print_state == "printing":
            out["progress"] = self.virtual_sdcard.progress
            out["filename"] = self.print_stats.filename
            out["printingDuration"] = self.print_stats.print_duration
        return out

    def send_to_firebase(self):
        if not self.init_done:
            return
        self.loop.create_task(self.task_firebase())

    async def task_firebase(self):
        # await self.send_method("server.database.get_item", self.fcm_token_received,
        #                        {"namespace": "mobileraker", "key": "fcmTokens"})
        msg = await self.collect_for_notification()
        if msg["printerUUID"] is None:
            self.websocket.logger.warning("Could not send to mobileraker-fcm, no printerUUID found!")
            return
        print("SHOULD SEND TO FIREBASE: %s" % (json.dumps(msg)))

    async def fetch_fcm_tokens(self):
        response, err = await self.send_and_receive_method("server.database.get_item",
                                                           {"namespace": "mobileraker", "key": "fcmTokens"})
        fcm_tokens = []
        if not err:
            fcm_tokens.extend(response["result"]["value"])
        return fcm_tokens

    async def fetch_printer_id(self):
        response, err = await self.send_and_receive_method("server.database.get_item",
                                                           {"namespace": "mobileraker", "key": "printerId"})
        if not err:
            return response["result"]["value"]
        return None


class CompanionConfig:

    def __init__(self) -> None:
        super().__init__()
        self.increments = 0.05
        self.uri = "some url"


def main() -> None:
    event_loop = asyncio.get_event_loop()
    try:
        client = Client(uri="ws://192.168.178.135/websocket", loop=event_loop)
        event_loop.create_task(client.connect())
        event_loop.run_forever()
    finally:
        event_loop.close()
    exit()


coloredlogs.install(level=logging.INFO)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
