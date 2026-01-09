from asyncio import AbstractEventLoop, Lock
import asyncio
import base64
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
import time


import requests
from mobileraker.client.mobileraker_fcm_client import MobilerakerFcmClient
from mobileraker.client.moonraker_client import MoonrakerClient
from mobileraker.client.webcam_snapshot_client import WebcamSnapshotClient
from mobileraker.data.dtos.mobileraker.companion_meta_dto import CompanionMetaDataDto
from mobileraker.data.dtos.mobileraker.companion_request_dto import ContentDto, DeviceRequestDto, FcmRequestDto, LiveActivityContentDto, NotificationContentDto, ProgressNotificationContentDto
from mobileraker.data.dtos.mobileraker.notification_config_dto import DeviceNotificationEntry
from mobileraker.data.dtos.moonraker.printer_snapshot import PrinterSnapshot
from mobileraker.service.data_sync_service import DataSyncService
from mobileraker.service.notification_evaluator import NotificationEvaluator
from mobileraker.service.webcam_manager import WebcamManager
from mobileraker.util.configs import CompanionLocalConfig, CompanionRemoteConfig

from mobileraker.util.functions import compare_version, generate_notifcation_id_from_uuid, get_software_version, is_valid_uuid, normalized_progress_interval_reached
from mobileraker.util.i18n import translate_implicit, translate_replace_placeholders
from mobileraker.util.notification_placeholders import replace_placeholders


class MobilerakerCompanion:
    '''
        The companion class is the main coordinator between all logic in this project.
        It takes care of handling data updates, issuing new notifications, and updating any snapshot info
    '''

    DEFAULT_WEBCAM_KEY = '_webcamMR'

    def __init__(
            self,
            jrpc: MoonrakerClient,
            data_sync_service: DataSyncService,
            fcm_client: MobilerakerFcmClient,
            webcam_snapshot_client: WebcamSnapshotClient,
            printer_name: str,
            loop: AbstractEventLoop,
            companion_config: CompanionLocalConfig,
            exclude_sensors: List[str] = []
    ) -> None:
        super().__init__()
        self._jrpc: MoonrakerClient = jrpc
        self._data_sync_service: DataSyncService = data_sync_service
        self._fcm_client: MobilerakerFcmClient = fcm_client
        self._default_snapshot_client: WebcamSnapshotClient = webcam_snapshot_client
        self._webcam_manager = WebcamManager(jrpc)
        self.printer_name: str = printer_name
        self.loop: AbstractEventLoop = loop
        self.companion_config: CompanionLocalConfig = companion_config
        self.exclude_sensors: List[str] = exclude_sensors
        self.last_request: Optional[DeviceRequestDto] = None
        # TODO: Fetch this from a remote server for easier configuration :)
        self.remote_config = CompanionRemoteConfig()
        self._logger = logging.getLogger(
            f'mobileraker.{printer_name.replace(".","_")}')
        self._last_snapshot: Optional[PrinterSnapshot] = None
        self._last_apns_message: Optional[int] = None
        self._evaulate_noti_lock: Lock = Lock()
        self._notification_evaluator = NotificationEvaluator(companion_config, self.remote_config)

        self._logger.info('MobilerakerCompanion client created for %s, it will ignore the following sensors: %s',
                          printer_name, exclude_sensors)

        self._jrpc.register_connection_listener(
            lambda d: self.loop.create_task(self._update_meta_data()) if d else None)
        self._data_sync_service.register_snapshot_listener(
            self._create_eval_task)

    async def start(self) -> None:
        await self._jrpc.connect()

    def _create_eval_task(self, snapshot: PrinterSnapshot) -> None:
        self.loop.create_task(self._evaluate_with_timeout(snapshot))

    async def _evaluate_with_timeout(self, snapshot: PrinterSnapshot) -> None:
        """
        This method starts the evaluation process with a timeout.
        It tries to acquire a lock before starting the evaluation.
        If the lock cannot be acquired within 60 seconds, or if the evaluation takes longer than 60 seconds,
        it logs a warning and releases the lock.
        """
        lock_acquired = False
        try:
            lock_acquired = await asyncio.wait_for(self._evaulate_noti_lock.acquire(), timeout=60)
            if lock_acquired:
                await asyncio.wait_for(self._evaluate(snapshot), timeout=60)
        except asyncio.TimeoutError:
            if lock_acquired:
                self._logger.warning('Evaluation task execution timed out after 60 seconds!')
            else:
                self._logger.warning('Evaluation task was unable to acquire lock after 60 seconds!')
        finally:
            if lock_acquired:
                self._evaulate_noti_lock.release()


    async def _evaluate(self, snapshot: PrinterSnapshot) -> None:
        # Limit evaluation to state changes and 5% increments(Later m117 can also trigger notifications, but might use other stuff)
        if not self._fulfills_evaluation_threshold(snapshot):
            return
        self._logger.info(
            'Snapshot passed threshold. LastSnap: %s, NewSnap: %s', self._last_snapshot, snapshot)
        self._last_snapshot = snapshot

        app_cfgs = await self._fetch_app_cfgs()

        device_requests: List[DeviceRequestDto] = []

        # Cache for webcam images to avoid multiple requests for the same image
        webcam_snapshots: Dict[str, str] = {}

        for cfg in app_cfgs:
            if not cfg.fcm_token:
                continue
            self._logger.info(
                'Evaluate for machineID %s, cfg.version: %s , cfg.snap: %s, cfg.settings: %s', cfg.machine_id, cfg.version, cfg.snap, cfg.settings)

            # Use device-specific exclude_filament_sensors if available
            exclude_sensors = cfg.settings.exclude_filament_sensors if hasattr(cfg.settings, 'exclude_filament_sensors') else self.exclude_sensors
            
            # Evaluate all notifications for this device
            result = self._notification_evaluator.evaluate_all_notifications_for_device(
                cfg, snapshot, self._last_snapshot, exclude_sensors
            )

            # Handle live activity side effect
            if result.has_live_activity:
                self._last_apns_message = time.monotonic_ns()

            # Log notifications using isinstance() for clean type checking
            self._logger.info('%i notifications generated for machineID: %s', len(result.notifications), cfg.machine_id)
            
            # Debug logging with proper type checking
            if result.notifications:
                notification_types = []
                for notification in result.notifications:
                    if isinstance(notification, LiveActivityContentDto):
                        notification_types.append('liveActivity')
                        self._logger.info('LiveActivity notification: progress=%s, eta=%s', 
                                         notification.progress, notification.eta)
                    elif isinstance(notification, ProgressNotificationContentDto):
                        notification_types.append('progressBar')
                        self._logger.info('ProgressBar notification: %s - %s (progress: %s%%)', 
                                         notification.title, notification.body, notification.progress)
                    elif isinstance(notification, NotificationContentDto):
                        # Determine type from channel for logging
                        noti_type = notification.channel.split('-')[-1] if '-' in notification.channel else 'unknown'
                        notification_types.append(noti_type)
                        self._logger.info('%s notification: %s - %s', noti_type, 
                                         notification.title, notification.body)
                
                self._logger.info('Notification types: %s', ', '.join(notification_types))
            
            if result.notifications:
                # Take a webcam image specific to this device's preferences
                ascii_img = await self._take_webcam_image_for_device(webcam_snapshots, cfg)
                if ascii_img:
                    # Set the webcam image to all notification DTOs
                    for notification in result.notifications:
                        if isinstance(notification, NotificationContentDto):
                            notification.image = ascii_img
                
                # Create device request
                dto = DeviceRequestDto(
                    # Version 2 is used to indicate that we want to use flattened structure of awesome notifications. This is only available in 2.6.10 and later
                    version= 2 if cfg.version is not None and compare_version(cfg.version, "2.6.10") >= 0 else 1,
                    printer_id=cfg.machine_id,
                    token=cfg.fcm_token,
                    notifcations=result.notifications
                )
                device_requests.append(dto)
            
            await self._update_app_snapshot(cfg, snapshot, result.has_progress_notification, result.has_progressbar_notification, result.has_live_activity)
            await self._clean_up_apns(cfg, snapshot)

        if device_requests:
            await self._push_and_clear_faulty(device_requests)
        
        self._logger.info('---- Completed Evaluations Task! ----')

    async def _update_meta_data(self) -> None:
        client_info = CompanionMetaDataDto(version=get_software_version())
        try:
            _, k_err = await self._jrpc.send_and_receive_method("server.database.post_item",
                                                                {"namespace": "mobileraker", "key": "fcm.client", "value": client_info.toJSON()})
            if k_err:
                self._logger.warning(
                    "Could not write companion meta into moonraker database, moonraker returned error %s", k_err)
            else:
                self._logger.info(
                    "Updated companion meta data in moonraker database")
        except (ConnectionError, asyncio.TimeoutError) as err:
            self._logger.warning(
                "Could not write companion meta into moonraker database, %s: %s", type(err), err)

    def _fulfills_evaluation_threshold(self, snapshot: PrinterSnapshot) -> bool:
        if self._last_snapshot is None:
            self._logger.info('No last snapshot available. Evaluating!')
            return True

        if self._last_snapshot.print_state != snapshot.print_state and not snapshot.is_timelapse_pause:
            self._logger.info('State changed. Evaluating!')
            return True

        if self._last_snapshot.m117_hash != snapshot.m117_hash and snapshot.m117 is not None and snapshot.m117.startswith('$MR$:'):
            self._logger.info('M117 changed. Evaluating!')
            return True

        if self._last_snapshot.gcode_response_hash != snapshot.gcode_response_hash and snapshot.gcode_response is not None and snapshot.gcode_response.startswith('MR_NOTIFY:'):
            self._logger.info('GcodeResponse changed. Evaluating!')
            return True


        if not self._last_snapshot.eta_available and snapshot.eta_available:
            self._logger.info('ETA is available. Evaluating!')
            return True

        # TODO: This is not yet working as intended. The eta does not trigger an evaluation with the current code!
        # Check if eta changed by more than 10 minutes and the last live activity update was more than 30 seconds ago
        # if (self._last_apns_message is not None and 
        #     (time.monotonic_ns() - self._last_apns_message) / 1e9 > 30 and
        #     self._last_snapshot.eta is not None and snapshot.eta is not None and 
        #     abs((self._last_snapshot.eta - snapshot.eta).seconds) > 600):
        #     self._logger.info('ETA changed by more than 10 minutes after 30 sec. Evaluating!')
        #     return True

        # Progress evaluation
        last_progress = self._last_snapshot.progress
        cur_progress = snapshot.progress
        if last_progress != cur_progress:
            if last_progress is None or cur_progress is None:
                self._logger.info('Progress is None. Evaluating!')
                return True

            if normalized_progress_interval_reached(last_progress, cur_progress, self.remote_config.increments):
                self._logger.info('Progress reached minimum interval. Evaluating!')
                return True
        
        # Filament sensor evaluation 
        
        last_sensors = self._last_snapshot.filament_sensors
        cur_sensors = snapshot.filament_sensors

        # check if any of the new sensors is enabled and 
        for key, sensor in cur_sensors.items():
            # Skip sensors the user wants to ignore
            if key in self.exclude_sensors:
                continue

            # do not skip disabled sensors, as they might have been enabled in the meantime
            last_sensor = last_sensors.get(key)
            if last_sensor is None:
                self._logger.info('Initial filament sensor "%s" detected. Evaluating!', key)
                return True
            if last_sensor.filament_detected != sensor.filament_detected:
                self._logger.info('Filament sensor "%s" triggered. Evaluating!', key)
                return True
            if last_sensor.enabled != sensor.enabled:
                self._logger.info('Filament sensor "%s" enabled/disabled. Evaluating!', key)
                return True

        # Time evaluation
        if (datetime.now() - self._last_snapshot.timestamp).seconds >= (self.remote_config.interval+5): # add 5 seconds to ensure other values are also updated
            self._logger.info('Time-Interval reached. Evaluating!')
            return True


        # Yes I know I can return on the last if, but I want to log the reason why it triggered an evaluation
        return False

    async def _fetch_app_cfgs(self) -> List[DeviceNotificationEntry]:
        try:
            response, k_error = await self._jrpc.send_and_receive_method("server.database.get_item",
                                                                         {"namespace": "mobileraker", "key": "fcm"})
            if k_error:
                self._logger.warning(
                    "Could not fetch app cfgs from moonraker, moonraker returned error %s", k_error)
                return []
            cfgs = []
            raw_cfgs = response["result"]["value"]
            for entry_id in raw_cfgs:
                if not is_valid_uuid(entry_id):
                    continue

                device_json = raw_cfgs[entry_id]
                if ('fcmToken' not in device_json):
                    await self._remove_old_fcm_cfg(entry_id)
                    continue
                cfg = DeviceNotificationEntry.fromJSON(
                    entry_id, device_json)
                cfgs.append(cfg)

            self._logger.info('Fetched %i app Cfgs!', len(cfgs))
            return cfgs
        except (ConnectionError, asyncio.TimeoutError) as err:
            self._logger.warning(
                "Could not fetch app cfgs from moonraker, %s: %s", type(err), err)
            return []

    async def _remove_old_fcm_cfg(self, machine_id: str) -> None:
        try:
            await self._jrpc.send_method(
                method="server.database.delete_item",
                params={"namespace": "mobileraker",
                        "key": f"fcm.{machine_id}"},
            )
        except (ConnectionError, asyncio.TimeoutError)as err:
            self._logger.warning(
                "Could not remove old fcm cfg for %s, %s", machine_id, err)


    async def _push_and_clear_faulty(self, dtos: List[DeviceRequestDto]):
        try:
            if dtos:
                request = FcmRequestDto(dtos)
                response = self._fcm_client.push(request)
            # todo: remove faulty token lol
        except requests.exceptions.RequestException as err:
            self._logger.error(
                "Could not push notifications to mobileraker backend, %s: %s", type(err), err)

    async def _update_app_snapshot(self, cfg: DeviceNotificationEntry, printer_snap: PrinterSnapshot, had_progress: bool, had_progressbar: bool, had_progress_liveactivity: bool) -> None:
        try:
            last = cfg.snap

            progress_update = None
            if printer_snap.print_state not in ['printing', 'paused']:
                progress_update = 0
            elif had_progress:
                progress_update = printer_snap.progress

            progress_live_activity_update = None
            if printer_snap.print_state not in ['printing', 'paused']:
                progress_live_activity_update = 0
            elif had_progress_liveactivity:
                progress_live_activity_update = printer_snap.progress

            progressbar_update = None
            if printer_snap.print_state not in ['printing', 'paused']:
                progressbar_update = 0
            elif had_progressbar:
                progressbar_update = printer_snap.progress

            # get list of all filament that have no filament detected (Enabled and Disabled, if we only use enabled once, this might trigger a notification if the user enables a sensor and it detects no filament)
            filament_sensors = [key for key, sensor in printer_snap.filament_sensors.items() if not sensor.filament_detected and not key in self.exclude_sensors]
            now = datetime.now()
            
            updated = last.copy_with(
                state=printer_snap.print_state if last.state != printer_snap.print_state and not printer_snap.is_timelapse_pause else None,
                progress=progress_update,
                progress_live_activity=progress_live_activity_update,
                progress_progressbar=progressbar_update,
                m117=printer_snap.m117_hash if last.m117 != printer_snap.m117_hash else None,
                gcode_response=printer_snap.gcode_response_hash if last.gcode_response != printer_snap.gcode_response_hash else None,
                filament_sensors=filament_sensors if last.filament_sensors != filament_sensors else None,
                last_progress=now if had_progress else last.last_progress,
                last_progress_live_activity=now if had_progress_liveactivity else last.last_progress_live_activity,
                last_progress_progressbar=now if had_progressbar else last.last_progress_progressbar
            )

            if updated == last:
                self._logger.info(
                    "No snap update necessary for %s", cfg.machine_id)
                return

            self._logger.info('Updating snap in FCM Cfg for %s: %s',
                              cfg.machine_id, updated)
            response, k_err = await self._jrpc.send_and_receive_method("server.database.post_item",
                                                                       {"namespace": "mobileraker", "key": f"fcm.{cfg.machine_id}.snap", "value": updated.toJSON()})
            if k_err:
                self._logger.warning(
                    "Could not update snap in FCM Cfg for %s, moonraker returned error %s", cfg.machine_id, k_err)
            else:
                self._logger.info(
                    'Updated snap in FCM Cfg for %s: %s', cfg.machine_id, response)

        except (ConnectionError, asyncio.TimeoutError) as err:
            self._logger.warning(
                "Could not update snap in FCM Cfg for %s, %s: %s", cfg.machine_id, type(err), err)

    async def _clean_up_apns(self, cfg: DeviceNotificationEntry, printer_snap: PrinterSnapshot) -> None:
        if (cfg.apns is None):
            return
        if (printer_snap.print_state in ['printing', 'paused']):
            return
        machine_id = cfg.machine_id

        try:
            self._logger.info('Deleting APNS for %s', machine_id)
            _, k_err = await self._jrpc.send_and_receive_method(
                method="server.database.delete_item",
                params={"namespace": "mobileraker",
                        "key": f"fcm.{machine_id}.apns"},
            )
            if k_err:
                self._logger.warning(
                    "Could not remove apns for %s, moonraker returned error %s", machine_id, k_err)
            else:
                self._logger.info(
                    "Removed apns for %s", machine_id)
        except (ConnectionError, asyncio.TimeoutError)as err:
            self._logger.warning(
                "Could not remove apns for %s, %s", machine_id, err)
    
    async def _take_webcam_image_for_device(self, cache: Dict[str, str], cfg: DeviceNotificationEntry) -> Optional[str]:
        """
        Takes a webcam snapshot for a specific device based on its webcam preferences.
        
        Args:
            cfg (DeviceNotificationEntry): The device configuration
            
        Returns:
            Optional[bytes]: The snapshot image as bytes if successful, or None on failure
        """
        
        # Legacy support for snapshot_webcam in conf file
        if not hasattr(cfg.settings, 'snapshot_webcam') and not self.companion_config.include_snapshot:
            self._logger.info('Legacy config detected and disables including of webcam snapshots.')
            return None
        
        #new device specific snapshot_webcam
        if hasattr(cfg.settings, 'snapshot_webcam') and not cfg.settings.snapshot_webcam:
            self._logger.info('Device specific snapshot_webcam is set to false. Skipping webcam snapshot.')
            return None
        
        webcam_key = cfg.settings.snapshot_webcam if hasattr(cfg.settings, 'snapshot_webcam') else self.DEFAULT_WEBCAM_KEY
        
        if webcam_key in cache :
            return cache[webcam_key]
                
        try:
            # Get the appropriate snapshot client for this device
            snapshot_client = await self._get_snapshot_client_for_device(webcam_key) # type: ignore
            
            if snapshot_client is None:
                self._logger.warning("No snapshot client found for webcam: %s", webcam_key)
                return None
            # Take a snapshot
            img_bytes = snapshot_client.capture_snapshot()
            
            if img_bytes:
                img = base64.b64encode(img_bytes).decode("ascii")
                cache[webcam_key] = img # type: ignore -> we are sure that the key is a str ant not a none
                return img
            return None
        except Exception as e:
            self._logger.error("Error taking webcam image: %s", str(e))
            return None
        
    async def _get_snapshot_client_for_device(self, webcam: str) -> Optional[WebcamSnapshotClient]:
        """
        Get an appropriate SnapshotClient for a device based on its webcam preference.
        
        Args:
            cfg (DeviceNotificationEntry): The device configuration
            
        Returns:
            SnapshotClient: A snapshot client configured for the device
        """

        # Legacy support for snapshot_webcam in conf file
        if webcam == self.DEFAULT_WEBCAM_KEY:
            return self._default_snapshot_client

        # Create a new client for this webcam
        try:
            # Fetch webcam data from Moonraker
            return await self._webcam_manager.get_webcam_client(webcam)

        except Exception as e:
            self._logger.error("Error creating snapshot client: %s", str(e))