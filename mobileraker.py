import argparse
import asyncio
import hashlib
import logging
import os
from asyncio import AbstractEventLoop, Task
from logging.handlers import RotatingFileHandler
from tracemalloc import Snapshot
from typing import Any, Dict, List, Optional, cast

import coloredlogs

from configs import CompanionLocalConfig, CompanionRemoteConfig
from dtos.mobileraker.companion_request_dto import (DeviceRequestDto,
                                                    FcmRequestDto,
                                                    NotificationContentDto)
from dtos.mobileraker.notification_config_dto import (DeviceNotificationEntry,
                                                      NotificationSnap)
from dtos.printer_objects import (DisplayStatus, PrintStats, ServerInfo,
                                  VirtualSDCard)
from i18n import (replace_placeholders, translate,
                  translate_replace_placeholders)
from mobileraker_fcm import MobilerakerFcmClient
from moonraker_client import MoonrakerClient
from printer_snapshot import PrinterSnapshot


class MobilerakerCompanion:
    def __init__(
            self,
            jrpc: MoonrakerClient,
            fcm_client: MobilerakerFcmClient,
            printer_name: str,
            loop: AbstractEventLoop,
    ) -> None:
        super().__init__()
        self._jrpc: MoonrakerClient = jrpc
        self._fcm_client: MobilerakerFcmClient = fcm_client
        self.printer_name: str = printer_name
        self.loop: AbstractEventLoop = loop
        self.init_done: bool = False
        self.klippy_ready: bool = False
        self.server_info: ServerInfo = ServerInfo()
        self.print_stats: PrintStats = PrintStats()
        self.display_status: DisplayStatus = DisplayStatus()
        self.virtual_sdcard: VirtualSDCard = VirtualSDCard()
        self.last_request: Optional[DeviceRequestDto] = None
        # TODO: Fetch this from a remote server for easier configuration :)
        self.remote_config = CompanionRemoteConfig()
        self.logger = logging.getLogger('mobileraker')
        self._printer_fcm_id: Optional[str] = None
        self._last_snapshot: Optional[PrinterSnapshot] = None
        self._evaulate_noti_task: Optional[Task] = None
        self._evaulate_m117_task: Optional[Task] = None
        coloredlogs.install(
            logger=self.logger, fmt=f'%(asctime)s %(hostname)s %(name)s[%(process)d] %(levelname)s [{self.printer_name}] %(message)s')

        self._jrpc.register_method_listener(
            'notify_status_update', lambda resp: self.loop.create_task(self._parse_notify_status_update(resp["params"][0])))

        self._jrpc.register_method_listener(
            'notify_klippy_ready', lambda resp: self._on_klippy_ready())

        self._jrpc.register_method_listener(
            'notify_klippy_shutdown', lambda resp: self._on_klippy_shutdown())

        self._jrpc.register_method_listener(
            'notify_klippy_disconnected', lambda resp: self._on_klippy_disconnected())

    async def connect(self) -> None:
        await self._jrpc.connect(lambda: self.loop.create_task(self._init_printer_objects()))

    async def _init_printer_objects(self, no_try: int = 0) -> None:
        self.logger.info("Fetching printer Objects Try#%i" % no_try)
        response, err = await self._jrpc.send_and_receive_method("server.info")
        self._parse_server_info(response, err)
        self.klippy_ready = self.server_info.klippy_state == 'ready'
        if self.klippy_ready:
            await self._query_printer_objects()

            if not self.init_done:
                self.init_done = True
                self.logger.debug('Src: INIT_DONE')
                self.evaluate_notification()
            await self._subscribe_to_object_notifications()
        else:
            wait_for = min(pow(2, no_try + 1), 30 * 60)
            self.logger.warning(
                "Klippy was not ready. Trying again in %i seconds..." % wait_for)
            await asyncio.sleep(wait_for)
            self.loop.create_task(
                self._init_printer_objects(no_try=no_try + 1))

    async def _parse_objects_response(self, message: Dict[str, Any], err=None):
        self.logger.debug("Received objects response %s" % message)
        await self._parse_notify_status_update(cast(Dict, message["result"]["status"]))

    async def _parse_notify_status_update(self, status_objects: Dict[str, Any]):
        self.logger.debug("Received status update for %s" % status_objects)
        for key, object_data in status_objects.items():
            if key == "print_stats":
                await self._parse_print_stats_update(object_data)
            elif key == "display_status":
                old = self.display_status
                await self._parse_display_status_update(object_data)
                # handle custom/m117 notifications here!
                if old.message != self.display_status.message:
                    self.evaluate_m117()

            elif key == "virtual_sdcard":
                await self._parse_virtual_sdcard_update(object_data)
        self.logger.debug('Src: _parse_notify_status_update')
        self.evaluate_notification()

    def _parse_server_info(self, message: Dict[str, Any], err=None):
        self.logger.info("Received Server Info")
        self.server_info = self.server_info.updateWith(message['result'])

    async def _parse_print_stats_update(self, print_stats):
        self.print_stats = self.print_stats.updateWith(print_stats)

    async def _parse_display_status_update(self, display_status):
        self.display_status = self.display_status.updateWith(display_status)

    async def _parse_virtual_sdcard_update(self, virtual_sdcard):
        self.virtual_sdcard = self.virtual_sdcard.updateWith(virtual_sdcard)

    async def _query_printer_objects(self):
        self.logger.info("Querying printer Objects")
        params = {
            "objects": {
                "print_stats": None,
                # "display_status": None,
                "virtual_sdcard": None
            }
        }
        response, err = await self._jrpc.send_and_receive_method("printer.objects.query", params)
        await self._parse_objects_response(response, err)

    async def _subscribe_to_object_notifications(self):
        self.logger.info("Subscribing to printer Objects")
        params = {
            "objects": {
                "print_stats": None,
                "display_status": None,
                "virtual_sdcard": None
            }
        }
        await self._jrpc.send_method("printer.objects.subscribe", self._parse_objects_response, params)

    def _on_klippy_ready(self):
        self.logger.info("Klippy has reported a ready state")
        self.loop.create_task(self._init_printer_objects())

    def _on_klippy_shutdown(self):
        self.logger.info("Klippy has reported a shutdown state")
        self.klippy_ready = False
        self.logger.debug('Src: _on_klippy_shutdown')
        self.evaluate_notification(True)

    def _on_klippy_disconnected(self):
        self.logger.info(
            "Moonraker's connection to Klippy has terminated/disconnected")
        self.klippy_ready = False

    def _take_snapshot(self) -> PrinterSnapshot:
        snapshot = PrinterSnapshot(
            self.print_stats.state if self.klippy_ready else "error")

        snapshot.filename = self.print_stats.filename
        snapshot.m117 = self.display_status.message
        snapshot.m117_hash = hashlib.sha256(snapshot.m117.encode(
            "utf-8")).hexdigest() if snapshot.m117 is not None else ''
        if self.print_stats.state == "printing":
            snapshot.progress = round(self.virtual_sdcard.progress*100)
            snapshot.printing_duration = self.print_stats.print_duration
        return snapshot

    async def update_snap_in_fcm_cfg(self, machine_id: str, notification_snap: NotificationSnap) -> None:
        self.logger.info(
            f'Updating snap in FCM Cfg for {machine_id} {notification_snap.progress}, {notification_snap.state}')
        response, err = await self._jrpc.send_and_receive_method("server.database.post_item",
                                                                 {"namespace": "mobileraker", "key": f"fcm.{machine_id}.snap", "value": notification_snap.toJSON()})
        #self.logger.info(f'Snap resp: {response}')

    async def update_snap_m117_in_fcm_cfg(self, machine_id: str, m117_hash: str) -> None:
        self.logger.info(
            f'Updating snap.m117 in FCM Cfg for {machine_id} {m117_hash}')
        response, err = await self._jrpc.send_and_receive_method("server.database.post_item",
                                                                 {"namespace": "mobileraker", "key": f"fcm.{machine_id}.snap.m117", "value": m117_hash})

    async def remove_old_fcm_cfg(self, machine_id: str) -> None:
        response, err = await self._jrpc.send_and_receive_method("server.database.delete_item",
                                                                 {"namespace": "mobileraker", "key": f"fcm.{machine_id}"})

    async def fetch_fcm_cfgs(self) -> List[DeviceNotificationEntry]:
        response, err = await self._jrpc.send_and_receive_method("server.database.get_item",
                                                                 {"namespace": "mobileraker", "key": "fcm"})
        cfgs = []

        if not err:
            rawCfg = response["result"]["value"]
            for entry_id in rawCfg:
                deviceJson = rawCfg[entry_id]
                if ('fcmToken' not in deviceJson):
                    await self.remove_old_fcm_cfg(entry_id)
                    continue
                deviceJson['machineId'] = entry_id
                cfg = DeviceNotificationEntry.fromJSON(deviceJson)
                cfgs.append(cfg)

        return cfgs

    async def fetch_printer_id(self) -> Optional[str]:
        response, err = await self._jrpc.send_and_receive_method("server.database.get_item",
                                                                 {"namespace": "mobileraker", "key": "printerId"})
        if not err:
            return response["result"]["value"]
        return None

    def evaluate_notification(self, force: bool = False) -> None:
        if not self.init_done and not force:
            return


        self.loop.create_task(
            self.task_evaluate_notification(force))

    # Calculate if it should push a new notification!
    async def task_evaluate_notification(self, force: bool = False) -> None:
        if self._evaulate_noti_task is not None:
            await asyncio.wait_for(self._evaulate_noti_task, timeout=None)
        self._evaulate_noti_task = asyncio.current_task()


        if not self.init_done and not force:
            return
        if not self._printer_fcm_id:
            id = await self.fetch_printer_id()
            if not id:
                self.logger.info('Was unable to fetch printer_id')
                return
            self.logger.info(f'Fetched printer_id: {id}')
            self._printer_fcm_id = id
        snapshot = self._take_snapshot()

        # Limit evaluation to state changes and 5% increments(Later m117 can also trigger notifications, but might use other stuff)

        if self._last_snapshot is not None:
            if self._last_snapshot.print_state == snapshot.print_state and self._last_snapshot.progress is not None and snapshot.progress is not None and\
                    (snapshot.progress - self._last_snapshot.progress) < self.remote_config.increments:
                return
        self._last_snapshot = snapshot

        dtos = []
        cfgs = await self.fetch_fcm_cfgs()
        #self.logger.info(f'Yes i am here! - {snapshot.progress}')
        self.logger.info(f'Got configs: {cfgs}')
        for c in cfgs:
            self.logger.info(
                f'Evaluate for machineID {c.machine_id}, snap: {c.snap.state} {c.snap.progress}')
            notifications = []

            state_noti = self._state_notification(c, snapshot)
            if state_noti is not None:
                notifications.append(state_noti)
                self.logger.info(
                    f'StateNoti: {state_noti.title} - {state_noti.body}')

            progress_noti = self._progress_notification(
                c, snapshot)
            if progress_noti is not None:
                notifications.append(progress_noti)
                self.logger.info(
                    f'ProgressNoti: {progress_noti.title} - {progress_noti.body}')

            self.logger.debug(
                f'Notifications for {c.fcm_token}: {notifications}')

            self.logger.info(
                f'Notifications for machineID: {c.machine_id}:{len(notifications)}, state:{state_noti is not None}, proggress:{progress_noti is not None}')
            if notifications:
                noti_snap = NotificationSnap()
                # self.logger.info(f'-- {snapshot.progress//c.settings.progress_config} * {c.settings.progress_config} = {((snapshot.progress//c.settings.progress_config)*c.settings.progress_config, 2)}')
                noti_snap.progress = 0 if snapshot.print_state != 'printing' and snapshot.print_state != 'paused' else c.snap.progress \
                    if progress_noti is None else snapshot.progress - (snapshot.progress % c.settings.progress_config) if snapshot.progress is not None else 0
                noti_snap.state = snapshot.print_state

                await self.update_snap_in_fcm_cfg(c.machine_id, noti_snap)
                dto = DeviceRequestDto(
                    printer_id=c.machine_id,
                    token=c.fcm_token,
                    notifcations=notifications
                )
                dtos.append(dto)
                #self.logger.info(f'Dto: {dto.toJSON()}')
        # just ensure the next update is in 5% steps at least!
        if snapshot.progress is not None:
            snapshot.progress = snapshot.progress - \
                (snapshot.progress % self.remote_config.increments)

        await self._push_and_clear_faulty(dtos)
        self.logger.info('---- Done wiht evaluate notification Task! ----')

    def _state_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot) -> Optional[NotificationContentDto]:

        # check if we even need to issue a new notification!
        if cfg.snap.state == cur_snap.print_state:
            return None

        # check if new print state actually should issue a notification trough user configs
        if cur_snap.print_state not in cfg.settings.state_config:
            return None

        self.logger.info(
            f'Got a state transition: {cfg.snap.state} -> {cur_snap.print_state}')

        # collect title and body to translate it
        title = translate_replace_placeholders('state_title', cfg, cur_snap)
        body = None
        if cur_snap.print_state == "printing":
            body = "state_printing_body"
        elif cur_snap.print_state == "paused":
            body = "state_paused_body"
        elif cur_snap.print_state == "complete":
            body = "state_completed_body"
        elif cur_snap.print_state == "error":
            body = "state_error_body"
        elif cur_snap.print_state == "standby":
            body = "state_standby_body"

        if title is None or body is None:
            raise Exception("Body or Title are none!")

        body = translate_replace_placeholders(body, cfg, cur_snap)
        return NotificationContentDto(111, f'{cfg.machine_id}-statusUpdates', title, body)

    def _progress_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot) -> Optional[NotificationContentDto]:

        # only issue new progress notifications if the printer is printing
        # also skip if progress is at 100 since this notification is handled via the print state transition from printing to completed
        if cur_snap.print_state != "printing" or cur_snap.progress == 100 or cur_snap.progress is None:
            return None

        self.logger.info(
            f'ProgressNoti:: cfg.progress.config: {cur_snap.progress} - {cfg.snap.progress} = {(cur_snap.progress - cfg.snap.progress)} < {max(self.remote_config.increments, cfg.settings.progress_config)}')

        # If progress notifications are disabled, skip it!
        if cfg.settings.progress_config == -1:
            return None

        # ensure the progress threshhold of the user's cfg is reached, but only if the client already received an initial state and progress notification!
        if cfg.snap.state == "printing" and (cur_snap.progress - cfg.snap.progress) < max(self.remote_config.increments, cfg.settings.progress_config):
            return None

        title = translate_replace_placeholders(
            'print_progress_title', cfg, cur_snap)
        body = translate_replace_placeholders(
            'print_progress_body', cfg, cur_snap)
        return NotificationContentDto(222, f'{cfg.machine_id}-progressUpdates', title, body)

    async def _push_and_clear_faulty(self, dtos: List[DeviceRequestDto]):
        if dtos:
            request = FcmRequestDto(dtos)
            faulty_tokens = await self._fcm_client.push(request)
            # todo: remove faulty token lol

    def evaluate_m117(self) -> None:
        if not self.init_done:
            return

        self.loop.create_task(
            self.task_evaluate_m117_notification())

    async def task_evaluate_m117_notification(self):
        if self._evaulate_m117_task is not None:
            await asyncio.wait_for(self._evaulate_m117_task, timeout=None)
        self._evaulate_m117_task = asyncio.current_task()
    
        if not self.init_done:
            return
        self.logger.info('Evaluating m117 notifications!')
        dtos = []
        snapshot = self._take_snapshot()
        cfgs = await self.fetch_fcm_cfgs()

        for c in cfgs:
            notification = self._m117_notification(c, snapshot)
            if c.snap.m117 != snapshot.m117_hash:
                await self.update_snap_m117_in_fcm_cfg(c.machine_id, snapshot.m117_hash)

            if notification is None:
                continue

            dto = DeviceRequestDto(
                printer_id=c.machine_id,
                token=c.fcm_token,
                notifcations=[notification]
            )
            dtos.append(dto)
        await self._push_and_clear_faulty(dtos)

    def _m117_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot) -> Optional[NotificationContentDto]:
        # skip if m117 is empty/none
        if cur_snap.m117 is None or not cur_snap.m117:
            return None

        # only issue if
        if not cur_snap.m117.startswith('$MR$:'):
            return None

        # only evaluate if we have a new m117/hash
        if cfg.snap.m117 == cur_snap.m117_hash:
            return None

        msg = cur_snap.m117[5:]
        split = msg.split('|')

        has_title = (len(split) == 2)

        title = split[0] if has_title else translate(cfg.language,
                                                     'm117_custom_title')
        title = replace_placeholders(title, cfg, cur_snap)
        body = split[1] if has_title else split[0]
        body = replace_placeholders(body, cfg, cur_snap)

        self.logger.info(
            f'Got M117/Custom: {msg}: {title} - {body}')

        return NotificationContentDto(333, f'{cfg.machine_id}-m117',
                                      title, body)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mobileraker - Companion")
    parser.add_argument(
        "-l", "--logfile", default="/tmp/mobileraker.log", metavar='<logfile>',
        help="log file name and location")
    parser.add_argument(
        "-n", "--nologfile", action='store_true',
        help="disable logging to a file")
    parser.add_argument(
        "-c", "--configfile", default="~/Mobileraker.conf", metavar='<configfile>',
        help="Location of the configuration file for Mobileraker Companion"
    )

    cmd_line_args = parser.parse_args()

    if cmd_line_args.nologfile:
        log_file = ""
    elif cmd_line_args.logfile:
        log_file = os.path.normpath(
            os.path.expanduser(cmd_line_args.logfile))
        fh = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=5)
        formatter = logging.Formatter(
            '%(asctime)s [%(filename)s:%(funcName)s()] - %(message)s')
        fh.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.addHandler(fh)

    configfile = os.path.normpath(os.path.expanduser(cmd_line_args.configfile))

    local_config = CompanionLocalConfig(configfile)

    event_loop = asyncio.get_event_loop()
    try:
        printers = local_config.printers
        for printer_name in printers:
            p_config = printers[printer_name]

            jrpc = MoonrakerClient(
                p_config['moonraker_uri'],
                p_config['moonraker_api_key'],
                event_loop)
            fcmc = MobilerakerFcmClient(
                # 'http://127.0.0.1:8080',
                'https://mobileraker.eliteschw31n.de',
                event_loop)

            client = MobilerakerCompanion(
                jrpc=jrpc,
                fcm_client=fcmc,
                printer_name=printer_name,
                loop=event_loop)
            event_loop.create_task(client.connect())

        event_loop.run_forever()
    finally:
        event_loop.close()
    exit()


coloredlogs.install(level=logging.INFO)
if __name__ == '__main__':
    main()
