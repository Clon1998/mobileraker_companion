# This is a sample Python script.

# Press Umschalt+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import argparse
import asyncio
import json
import logging
import os
import random
from asyncio import AbstractEventLoop
from copy import deepcopy

import coloredlogs
import requests
import websockets
from websockets.uri import WebSocketURI

from printer_objects import PrintStats, DisplayStatus, VirtualSDCard


class CompanionRequestDto:
    def __init__(self):
        self.print_state = None
        self.tokens = None
        self.printer_identifier = None
        self.filename = None
        self.progress = None
        self.printing_duration = None

    def toJSON(self) -> str:
        out = {
            "printState": self.print_state,
            "tokens": self.tokens,
            "printerIdentifier": self.printer_identifier
        }

        if self.filename:
            out["filename"] = self.filename

        if self.print_state == "printing":
            out["progress"] = self.progress
            out["printingDuration"] = self.printing_duration
        return json.dumps(out)


class Client:
    def __init__(
            self,
            moonraker_uri: WebSocketURI,
            fcm_uri: str,
            loop: AbstractEventLoop,
    ) -> None:
        super().__init__()
        self.websocket = None
        self.moonraker_server = moonraker_uri
        self.mobileraker_fcm = fcm_uri
        self.req_cb = {}
        self.req_blocking = {}
        self.loop = loop
        self.rec_task = None
        self.init_done = False
        self.klippy_ready = False
        self.print_stats: PrintStats or None = None
        self.display_status: DisplayStatus or None = None
        self.virtual_sdcard: VirtualSDCard or None = None
        self.last_request: CompanionRequestDto or None = None
        self.config = CompanionConfig()  # TODO: Fetch this from a remote server for easier configuration :)
        self.logger = logging.getLogger('Client')

    async def connect(self) -> None:
        async for websocket in websockets.connect(self.moonraker_server):
            try:
                self.websocket = websocket
                if self.rec_task:
                    self.rec_task.cancel()
                self.rec_task = self.loop.create_task(self.start_receiving())
                await self.init_printer_objects()
                await self.websocket.wait_closed()
            except websockets.ConnectionClosed:
                continue

    async def init_printer_objects(self):
        self.init_done = False
        self.logger.info("Fetching printer Objects")
        response, err = await self.send_and_receive_method("server.info")
        await self.parse_server_info(response, err)

        if self.klippy_ready:
            await self.query_printer_objects()

            if not self.init_done:
                self.init_done = True
                self.send_to_firebase()
            await self.subscribe_to_notifications()
        else:
            self.loop.create_task(self.init_printer_objects())

    async def start_receiving(self):
        async for message in self.websocket:
            await self.process_message(message)

    async def process_message(self, message):
        response = json.loads(message)
        mid = response.get("id")
        if "error" in response and "message" in response["error"]:
            self.logger.warning(
                "Error message received from WebSocket-Server %s" % response["error"]["message"])
            if mid and mid in self.req_cb:
                await self.req_cb.pop(mid)(response, response["error"]["message"])
        else:
            mmethod = response.get("method")

            if mid and self.req_cb:

                if mid in self.req_cb:
                    self.logger.debug("Received a response to request: %d" % mid)
                    await self.req_cb.pop(mid)(response)
                else:
                    self.logger.error("Received a response to unknown request: %d" % mid)
                    self.req_cb.pop(mid)
            else:
                self.logger.debug("Received a method notification for method: %s" % mmethod)
                if mmethod == "notify_status_update":
                    # "params": [{<status object>}, <eventtime>]
                    await self.parse_notify_status_update(response["params"][0])
                elif mmethod == "notify_klippy_ready":
                    self.logger.info("Klippy has reported a ready state")
                    self.loop.create_task(self.init_printer_objects())
                elif mmethod == "notify_klippy_shutdown":
                    self.logger.info("Klippy has reported a shutdown state")
                    self.klippy_ready = False
                elif mmethod == "notify_klippy_disconnected":
                    self.logger.info("Moonraker's connection to Klippy has terminated")
                    self.klippy_ready = False
                else:
                    self.logger.debug("Method %s not implemented/supported" % mmethod)

    async def send_method(self, method: str, callback=None, params: dict = None) -> int:
        req_dict = self.construct_json_rpc(method, params)
        message_json = json.dumps(req_dict)
        if callback:
            self.req_cb[req_dict["id"]] = callback

        self.logger.debug("Sending message %s" % message_json)
        await self.websocket.send(message_json)
        return req_dict["id"]

    async def send_and_receive_method(self, method: str, params: dict = None):
        req_dict = self.construct_json_rpc(method, params)
        message_json = json.dumps(req_dict)
        m_id = req_dict["id"]
        response_future = self.loop.create_future()

        self.req_cb[m_id] = self.receive_blocking_cb
        self.req_blocking[m_id] = response_future

        self.logger.debug("Sending message (Blocking) %s" % message_json)
        await self.websocket.send(message_json)
        return await response_future

    async def receive_blocking_cb(self, message=None, err=None):
        mid = message.get("id")
        if mid in self.req_blocking:
            response_future = self.req_blocking.pop(mid)
            response_future.set_result((message, err))

    async def parse_objects_response(self, message=None, err=None):
        self.logger.debug("Received objects response %s" % message)
        await self.parse_notify_status_update(message["result"]["status"])

    async def parse_notify_status_update(self, status_objects):
        self.logger.debug("Received status update for %s" % status_objects)
        for key, object_data in status_objects.items():
            if key == "print_stats":
                await self.parse_print_stats_update(object_data)
            elif key == "display_status":
                await self.parse_display_status_update(object_data)
            elif key == "virtual_sdcard":
                await self.parse_virtual_sdcard_update(object_data)

    async def parse_server_info(self, message=None, err=None):
        self.logger.info("Received Server Info")
        message = message["result"]
        klippy_state = message.get("klippy_state")
        if klippy_state == "ready":
            self.klippy_ready = True
        else:
            self.klippy_ready = False

    async def parse_print_stats_update(self, print_stats):
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

        if self.last_request is None or self.last_request.state != self.print_stats.state:
            await self.on_print_state_transition(self.print_stats.state)

    async def parse_display_status_update(self, display_status):
        # Tbh. I dont care about the message
        if "message" in display_status:
            self.display_status.message = display_status["message"]
        if "progress" in display_status:
            self.display_status.progress = display_status["progress"]

        # if self.display_status.progress and incoming.progress - self.display_status.progress >= self.config.increments:
        #     self.display_status = incoming
        #     self.send_to_firebase()

    async def parse_virtual_sdcard_update(self, virtual_sdcard):

        if "file_position" in virtual_sdcard:
            self.virtual_sdcard.file_position = virtual_sdcard["file_position"]
        if "progress" in virtual_sdcard:
            self.virtual_sdcard.progress = virtual_sdcard["progress"]

        if self.last_request is None or self.virtual_sdcard.progress - self.last_request.progress >= self.config.increments:
            self.send_to_firebase()

    async def query_printer_objects(self):
        self.logger.info("Querying printer Objects")
        params = {
            "objects": {
                "print_stats": None,
                # "display_status": None,
                "virtual_sdcard": None
            }
        }
        response, err = await self.send_and_receive_method("printer.objects.query", params)
        await self.parse_objects_response(response, err)

    async def subscribe_to_notifications(self):
        self.logger.info("Subscribing to printer Objects")
        params = {
            "objects": {
                "print_stats": None,
                # "display_status": None,
                "virtual_sdcard": None
            }
        }
        await self.send_method("printer.objects.subscribe", self.parse_objects_response, params)

    async def on_print_state_transition(self, new):
        self.logger.info("print_state transition %s -> %s" % (self.last_request.state, new))
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

    async def collect_for_notification(self) -> CompanionRequestDto:
        req = CompanionRequestDto()

        req.print_state = self.print_stats.state
        req.tokens = await self.fetch_fcm_tokens()
        req.printer_identifier = await self.fetch_printer_id()

        if self.print_stats.filename:
            req.filename = self.print_stats.filename

        if self.print_stats == "printing":
            req.progress = self.virtual_sdcard.progress
            req.printing_duration = self.print_stats.print_duration
        return req

    def send_to_firebase(self):
        if not self.init_done or not self.klippy_ready:
            return
        self.loop.create_task(self.task_firebase())

    async def task_firebase(self):
        # await self.send_method("server.database.get_item", self.fcm_token_received,
        #                        {"namespace": "mobileraker", "key": "fcmTokens"})
        request_dto = await self.collect_for_notification()
        if request_dto.printer_identifier is None:
            self.logger.warning("Could not send to mobileraker-fcm, no printerIdentifier found!")
            return
        self.logger.info("Sending to firebase: %s" % request_dto.toJSON())
        try:
            res = requests.post(self.mobileraker_fcm + '/companion/update', data=request_dto.toJSON())
            await self.handle_fcm_send_response(res)
        except requests.exceptions.ConnectionError as err:
            self.logger.error("Could not reach the mobileraker server!")

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

    async def remove_fcm_token_at(self, index):
        tokens = await self.fetch_fcm_tokens()
        removed_token = tokens.pop(index)
        self.logger.info("Trying to remove token %s" % removed_token)
        await self.send_method("server.database.post_item", params=
        {"namespace": "mobileraker", "key": "fcmTokens",
         "value": tokens})

    async def handle_fcm_send_response(self, res):
        if res.status_code == 200:
            message = res.content
            response = json.loads(message)
            responses = response['responses']
            for idx, res in enumerate(responses):
                if not res["successful"]:
                    await self.remove_fcm_token_at(idx)


class CompanionConfig:

    def __init__(self) -> None:
        super().__init__()
        self.increments = 0.05
        self.uri = "some url"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mobileraker - Companion")
    parser.add_argument(
        "-l", "--logfile", default="/tmp/mobileraker.log", metavar='<logfile>',
        help="log file name and location")
    parser.add_argument(
        "-n", "--nologfile", action='store_true',
        help="disable logging to a file")

    cmd_line_args = parser.parse_args()

    if cmd_line_args.nologfile:
        log_file = ""
    elif cmd_line_args.logfile:
        log_file = os.path.normpath(
            os.path.expanduser(cmd_line_args.logfile))
        fh = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s [%(filename)s:%(funcName)s()] - %(message)s')
        fh.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.addHandler(fh)

    event_loop = asyncio.get_event_loop()
    try:
        client = Client(moonraker_uri='ws://127.0.0.1/websocket',
                        fcm_uri='https://mobileraker-fcm-server.herokuapp.com', loop=event_loop)
        event_loop.create_task(client.connect())
        event_loop.run_forever()
    finally:
        event_loop.close()
    exit()


coloredlogs.install(level=logging.INFO)
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
