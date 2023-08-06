from asyncio import AbstractEventLoop, Lock, sleep
import base64
import logging

import requests
from mobileraker.client.mobileraker_fcm_client import MobilerakerFcmClient
from mobileraker.client.moonraker_client import MoonrakerClient
from mobileraker.client.snapshot_client import SnapshotClient
from mobileraker.data.dtos.mobileraker.companion_meta_dto import CompanionMetaDataDto
from mobileraker.data.dtos.mobileraker.companion_request_dto import DeviceRequestDto, FcmRequestDto, NotificationContentDto
from mobileraker.data.dtos.mobileraker.notification_config_dto import DeviceNotificationEntry, NotificationSnap
from mobileraker.data.dtos.moonraker.printer_objects import DisplayStatus, PrintStats, ServerInfo, VirtualSDCard
from mobileraker.data.dtos.moonraker.printer_snapshot import PrinterSnapshot
from mobileraker.service.data_sync_service import DataSyncService
from mobileraker.util.configs import CompanionLocalConfig, CompanionRemoteConfig
from typing import Any, Dict, List, Optional, cast

from mobileraker.util.functions import get_software_version, is_valid_uuid, normalized_progress_interval_reached
from mobileraker.util.i18n import translate, translate_replace_placeholders
from mobileraker.util.notification_placeholders import replace_placeholders


class MobilerakerCompanion:
    '''
        The companion class is the main coordinator between all logic in this project.
        It takes care of handling data updates, issuing new notifications, and updating any snapshot info
    '''

    def __init__(
            self,
            jrpc: MoonrakerClient,
            data_sync_service: DataSyncService,
            fcm_client: MobilerakerFcmClient,
            snapshot_client: SnapshotClient,
            printer_name: str,
            loop: AbstractEventLoop,
            companion_config: CompanionLocalConfig
    ) -> None:
        super().__init__()
        self._jrpc: MoonrakerClient = jrpc
        self._data_sync_service: DataSyncService = data_sync_service
        self._fcm_client: MobilerakerFcmClient = fcm_client
        self._snapshot_client: SnapshotClient = snapshot_client
        self.printer_name: str = printer_name
        self.loop: AbstractEventLoop = loop
        self.companion_config: CompanionLocalConfig = companion_config
        self.last_request: Optional[DeviceRequestDto] = None
        # TODO: Fetch this from a remote server for easier configuration :)
        self.remote_config = CompanionRemoteConfig()
        self._logger = logging.getLogger(
            f'mobileraker.{printer_name.replace(".","_")}')
        self._last_snapshot: Optional[PrinterSnapshot] = None
        self._evaulate_noti_lock: Lock = Lock(loop=loop)

        self._jrpc.register_connection_listener(
            lambda d: self.loop.create_task(self._update_meta_data()) if d else None)
        self._data_sync_service.register_snapshot_listener(
            self._create_eval_task)

    async def start(self) -> None:
        await self._jrpc.connect()

    def _create_eval_task(self, snapshot: PrinterSnapshot) -> None:
        self.loop.create_task(
            self._evaluate(snapshot))

    async def _evaluate(self, snapshot: PrinterSnapshot) -> None:
        async with self._evaulate_noti_lock:

            # Limit evaluation to state changes and 5% increments(Later m117 can also trigger notifications, but might use other stuff)
            if not self._fulfills_evaluation_threshold(snapshot):
                return
            self._logger.info(
                'Snapshot passed threshold. LastSnap: %s', self._last_snapshot)
            self._last_snapshot = snapshot

            app_cfgs = await self._fetch_app_cfgs()

            device_requests: List[DeviceRequestDto] = []

            for cfg in app_cfgs:
                if not cfg.fcm_token:
                    continue
                self._logger.info(
                    'Evaluate for machineID %s, cfg.snap: %s, cfg.settings: %s', cfg.machine_id, cfg.snap, cfg.settings)
                notifications: List[NotificationContentDto] = []

                state_noti = self._state_notification(cfg, snapshot)
                if state_noti is not None:
                    notifications.append(state_noti)
                    self._logger.info('StateNoti: %s - %s',
                                      state_noti.title, state_noti.body)

                progress_noti = self._progress_notification(cfg, snapshot)
                if progress_noti is not None:
                    notifications.append(progress_noti)
                    self._logger.info('ProgressNoti: %s - %s',
                                      progress_noti.title, progress_noti.body)

                m117_noti = self._m117_notification(cfg, snapshot)
                if m117_noti is not None:
                    notifications.append(m117_noti)
                    self._logger.info('M117Noti: %s - %s',
                                      m117_noti.title, m117_noti.body)

                self._logger.debug('Notifications for %s: %s',
                                   cfg.fcm_token, notifications)

                self._logger.info('%i Notifications for machineID: %s: state: %s, proggress: %s, M117 %s', len(
                    notifications), cfg.machine_id, state_noti is not None, progress_noti is not None, m117_noti is not None)

                if notifications:
                    # Set a webcam img to all DTOs if available
                    dto = DeviceRequestDto(
                        printer_id=cfg.machine_id,
                        token=cfg.fcm_token,
                        notifcations=notifications
                    )
                    device_requests.append(dto)
                await self._update_app_snapshot(cfg, snapshot)

        self._take_webcam_image(device_requests)
        await self._push_and_clear_faulty(device_requests)
        self._logger.info('---- Completed Evaluations Task! ----')

    async def _update_meta_data(self) -> None:
        client_info = CompanionMetaDataDto(version=get_software_version())
        response, err = await self._jrpc.send_and_receive_method("server.database.post_item",
                                                                 {"namespace": "mobileraker", "key": "fcm.client", "value": client_info.toJSON()})
        if err:
            self._logger.warning(
                "Could not write companion meta into moonraker database")
        else:
            self._logger.info(
                "Updated companion meta data in moonraker database")

    def _fulfills_evaluation_threshold(self, snapshot: PrinterSnapshot) -> bool:
        if self._last_snapshot is None:
            return True

        if self._last_snapshot.print_state != snapshot.print_state:
            return True

        if self._last_snapshot.m117_hash != snapshot.m117_hash:
            return True

        last_progress = self._last_snapshot.progress
        cur_progress = snapshot.progress

        if last_progress == cur_progress:
            return False

        if last_progress is None or cur_progress is None:
            return True

        return normalized_progress_interval_reached(last_progress, cur_progress, self.remote_config.increments)

    async def _fetch_app_cfgs(self) -> List[DeviceNotificationEntry]:
        response, err = await self._jrpc.send_and_receive_method("server.database.get_item",
                                                                 {"namespace": "mobileraker", "key": "fcm"})
        cfgs = []
        if not err:
            rawCfg = response["result"]["value"]
            for entry_id in rawCfg:
                if not is_valid_uuid(entry_id):
                    continue

                deviceJson = rawCfg[entry_id]
                if ('fcmToken' not in deviceJson):
                    await self._remove_old_fcm_cfg(entry_id)
                    continue
                cfg = DeviceNotificationEntry.fromJSON(entry_id, deviceJson)
                cfgs.append(cfg)

        self._logger.info('Fetched %i app Cfgs!', len(cfgs))
        return cfgs

    async def _remove_old_fcm_cfg(self, machine_id: str) -> None:
        await self._jrpc.send_method(
            method="server.database.delete_item",
            params={"namespace": "mobileraker", "key": f"fcm.{machine_id}"},
        )

    def _state_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot) -> Optional[NotificationContentDto]:

        # check if we even need to issue a new notification!
        if cfg.snap.state == cur_snap.print_state:
            return None

        # check if new print state actually should issue a notification trough user configs
        if cur_snap.print_state not in cfg.settings.state_config:
            return None

        # collect title and body to translate it
        title = translate_replace_placeholders(
            'state_title', cfg, cur_snap, self.companion_config)
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
            raise AttributeError("Body or Title are none!")

        body = translate_replace_placeholders(
            body, cfg, cur_snap, self.companion_config)
        return NotificationContentDto(111, f'{cfg.machine_id}-statusUpdates', title, body)

    def _progress_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot) -> Optional[NotificationContentDto]:

        # only issue new progress notifications if the printer is printing
        # also skip if progress is at 100 since this notification is handled via the print state transition from printing to completed
        if cur_snap.print_state != "printing" or cur_snap.progress is None or cur_snap.progress == 100:
            return None

        # If progress notifications are disabled, skip it!
        if cfg.settings.progress_config == -1:
            return None

        self._logger.info(
            'ProgressNoti preChecks: cfg.progress.config: %i - %i = %i < %i',
            cur_snap.progress,
            cfg.snap.progress,
            cur_snap.progress - cfg.snap.progress,
            max(self.remote_config.increments, cfg.settings.progress_config)
        )

        # ensure the progress threshhold of the user's cfg is reached.
        if cfg.snap.state in ["printing", "paused"] and not normalized_progress_interval_reached(cfg.snap.progress, cur_snap.progress, max(self.remote_config.increments, cfg.settings.progress_config)):
            return None

        title = translate_replace_placeholders(
            'print_progress_title', cfg, cur_snap, self.companion_config)
        body = translate_replace_placeholders(
            'print_progress_body', cfg, cur_snap, self.companion_config)
        return NotificationContentDto(222, f'{cfg.machine_id}-progressUpdates', title, body)

    def _m117_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot) -> Optional[NotificationContentDto]:
        # skip if m117 is empty/none
        if not cur_snap.m117:
            return None

        # only issue if
        if not cur_snap.m117.startswith('$MR$:'):
            return None

        # only evaluate if we have a new m117/hash
        if cfg.snap.m117 == cur_snap.m117_hash:
            return None

        msg = cur_snap.m117[5:]
        if not msg:
            return None

        split = msg.split('|')

        has_title = (len(split) == 2)

        title = split[0].strip() if has_title else translate(
            cfg.language, 'm117_custom_title')
        title = replace_placeholders(
            title, cfg, cur_snap, self.companion_config)
        body = (split[1] if has_title else split[0]).strip()
        body = replace_placeholders(body, cfg, cur_snap, self.companion_config)

        self._logger.info(
            'Got M117/Custom: %s. This translated into: %s -  %s', msg, title, body)

        return NotificationContentDto(333, f'{cfg.machine_id}-m117', title, body)

    def _take_webcam_image(self, dtos: List[DeviceRequestDto]) -> None:
        if not self.companion_config.include_snapshot:
            return

        img_bytes = self._snapshot_client.take_snapshot()
        if img_bytes is None:
            return

        img = base64.b64encode(img_bytes).decode("ascii")

        for dto in dtos:
            for notification in dto.notifcations:
                notification.image = img

    async def _push_and_clear_faulty(self, dtos: List[DeviceRequestDto]):
        try:
            if dtos:
                request = FcmRequestDto(dtos)
                response = self._fcm_client.push(request)
            # todo: remove faulty token lol
        except requests.exceptions.RequestException as err:
            self._logger.error(
                "Could not push notifications to mobileraker backend, %s: %s", type(err), err)

    async def _update_app_snapshot(self, cfg: DeviceNotificationEntry, printer_snap: PrinterSnapshot) -> None:
        last = cfg.snap

        progress_update = None
        if last.progress != printer_snap.progress:
            if printer_snap.print_state not in ['printing', 'paused']:
                progress_update = 0

            if printer_snap.progress is not None and normalized_progress_interval_reached(last.progress, printer_snap.progress, max(self.remote_config.increments, cfg.settings.progress_config)):
                progress_update = printer_snap.progress

        updated = last.copy_with(
            state=printer_snap.print_state if printer_snap.m117_hash is not None and last.state != printer_snap.print_state else None,
            progress=progress_update,
            m117=printer_snap.m117_hash if last.m117 != printer_snap.m117_hash else None,
        )

        if updated == last:
            self._logger.info(
                "No snap update necessary for %s", cfg.machine_id)
            return

        self._logger.info('Updating snap in FCM Cfg for %s: %s',
                          cfg.machine_id, updated)
        response, err = await self._jrpc.send_and_receive_method("server.database.post_item",
                                                                 {"namespace": "mobileraker", "key": f"fcm.{cfg.machine_id}.snap", "value": updated.toJSON()})
        if err:
            self._logger.error(
                'Error updating snap in FCM Cfg for %s: %s', cfg.machine_id, err)
        else:
            self._logger.info(
                'Updated snap in FCM Cfg for %s: %s', cfg.machine_id, response)

        return False
