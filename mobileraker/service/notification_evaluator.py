from typing import List, Optional, Tuple, NamedTuple
from datetime import datetime

from mobileraker.data.dtos.mobileraker.companion_request_dto import ContentDto, NotificationContentDto, ProgressNotificationContentDto, LiveActivityContentDto
from mobileraker.data.dtos.mobileraker.notification_config_dto import DeviceNotificationEntry
from mobileraker.data.dtos.moonraker.printer_snapshot import PrinterSnapshot
from mobileraker.util.configs import CompanionLocalConfig, CompanionRemoteConfig
from mobileraker.util.functions import compare_version, generate_notifcation_id_from_uuid, normalized_progress_interval_reached
from mobileraker.util.i18n import translate_implicit, translate_replace_placeholders
from mobileraker.util.notification_placeholders import replace_placeholders


class NotificationEvaluationResult(NamedTuple):
    """Result of notification evaluation including notifications and side effects."""
    notifications: List[ContentDto]
    has_live_activity: bool
    has_progress_notification: bool  
    has_progressbar_notification: bool


class NotificationEvaluator:
    """
    Pure logic class for evaluating notification conditions based on printer snapshots and device configurations.
    This class contains no I/O operations and is designed to be easily testable.
    """

    def __init__(self, companion_config: CompanionLocalConfig, remote_config: CompanionRemoteConfig):
        self.companion_config = companion_config
        self.remote_config = remote_config

    def evaluate_all_notifications_for_device(self, cfg: DeviceNotificationEntry, snapshot: PrinterSnapshot, 
                                             last_snapshot: Optional[PrinterSnapshot], 
                                             exclude_sensors: List[str]) -> NotificationEvaluationResult:
        """
        Evaluate all notification types for a single device and return notifications with side effect information.
        
        This method encapsulates the core notification evaluation logic - it determines which notifications
        should be sent for a given device based on the current printer state and device configuration.
        
        Args:
            cfg: The device notification configuration
            snapshot: Current printer snapshot
            last_snapshot: Previous printer snapshot (for ETA calculations)
            exclude_sensors: List of sensor names to exclude from notifications
            
        Returns:
            NotificationEvaluationResult containing notifications and side effect flags
        """
        notifications: List[ContentDto] = []

        # State notifications (print state changes)
        state_noti = self.evaluate_state_notification(cfg, snapshot)
        if state_noti is not None:
            notifications.append(state_noti)

        # Progress notifications (text-based progress updates)
        progress_noti = self.evaluate_progress_notification(cfg, snapshot)
        if progress_noti is not None:
            notifications.append(progress_noti)
            
        # Progressbar notifications (Android progress bars)
        progressbar_noti = self.evaluate_progressbar_notification(cfg, snapshot)
        if progressbar_noti is not None:
            notifications.append(progressbar_noti)

        # Custom M117 notifications
        m117_noti = self.evaluate_custom_notification(cfg, snapshot, True)
        if m117_noti is not None:
            notifications.append(m117_noti)

        # Custom GCode response notifications
        gcode_response_noti = self.evaluate_custom_notification(cfg, snapshot, False)
        if gcode_response_noti is not None:
            notifications.append(gcode_response_noti)

        # Live Activity updates (iOS)
        live_activity_update = self.evaluate_live_activity_update(cfg, snapshot, last_snapshot)
        if live_activity_update is not None:
            notifications.append(live_activity_update)

        # Filament sensor notifications
        filament_sensor_notifications = self.evaluate_filament_sensor_notifications(cfg, snapshot, exclude_sensors)
        if filament_sensor_notifications is not None:
            notifications.extend(filament_sensor_notifications)

        return NotificationEvaluationResult(
            notifications=notifications,
            has_live_activity=live_activity_update is not None,
            has_progress_notification=progress_noti is not None,
            has_progressbar_notification=progressbar_noti is not None
        )

    def evaluate_state_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot) -> Optional[NotificationContentDto]:
        """
        Evaluate if a state notification should be issued.
        
        Args:
            cfg: The device notification configuration.
            cur_snap: The current printer snapshot.
            
        Returns:
            The notification content, if any.
        """
        # Check if we even need to issue a new notification!
        if cfg.snap.state == cur_snap.print_state:
            return None

        # Only allow notifications of type error for the state transition printing -> error
        if cfg.snap.state != "printing" and cur_snap.print_state == "error":
            return None

        # Check if new print state actually should issue a notification through user configs
        if cur_snap.print_state not in cfg.settings.state_config:
            return None
                
        # Ignore paused state caused by timelapse plugin
        if cur_snap.is_timelapse_pause:
            return None

        # Collect title and body to translate it
        title = translate_replace_placeholders(
            'state_title', cfg, cur_snap, self.companion_config)
        body = None
        if cur_snap.print_state == "printing":
            # Transitions from paused to printing should be resumed
            body = "state_resumed_body" if cfg.snap.state == "paused" else "state_printing_body"
        elif cur_snap.print_state == "paused":
            body = "state_paused_body"
        elif cur_snap.print_state == "complete":
            body = "state_completed_body"
        elif cur_snap.print_state == "error":
            body = "state_error_body"
        elif cur_snap.print_state == "standby":
            body = "state_standby_body"
        elif cur_snap.print_state == "cancelled":
            body = "state_cancelled_body"

        if title is None or body is None:
            raise AttributeError("Body or Title are none!")

        body = translate_replace_placeholders(
            body, cfg, cur_snap, self.companion_config)
        return NotificationContentDto(generate_notifcation_id_from_uuid(cfg.machine_id, 0), f'{cfg.machine_id}-statusUpdates', title, body)

    def evaluate_progress_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot) -> Optional[NotificationContentDto]:
        """
        Evaluate if a progress notification should be issued.
        
        Args:
            cfg: The device notification configuration.
            cur_snap: The current printer snapshot.
            
        Returns:
            The notification content, if any.
        """
        # If progress notifications are disabled, skip it!
        if cfg.settings.progress_config == -1:
            return None
        
        # Only issue new progress notifications if the printer is printing, or paused
        # also skip if progress is at 100 since this notification is handled via the print state transition from printing to completed
        if cur_snap.print_state not in ["printing", "paused"] or cur_snap.progress is None or cur_snap.progress == 100:
            return None

        # Ensure the progress threshold of the user's cfg is reached. If the cfg.snap is not yet printing also issue a notification
        if (cfg.snap.state in ["printing", "paused"]
                    and not normalized_progress_interval_reached(cfg.snap.progress, cur_snap.progress, max(self.remote_config.increments, cfg.settings.progress_config))
                ):
            return None

        nid = generate_notifcation_id_from_uuid(cfg.machine_id, 1)
        channel = f'{cfg.machine_id}-progressUpdates'
        title = translate_replace_placeholders(
            'print_progress_title', cfg, cur_snap, self.companion_config)
        body = translate_replace_placeholders(
            'print_progress_body', cfg, cur_snap, self.companion_config)

        return NotificationContentDto(nid, channel, title, body)

    def evaluate_progressbar_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot) -> Optional[ProgressNotificationContentDto]:
        """
        Evaluate if a progressbar notification (Android) should be issued.
        
        Args:
            cfg: The device notification configuration.
            cur_snap: The current printer snapshot.
            
        Returns:
            The notification content, if any.
        """
        # If progressbar notifications are disabled, skip it!
        if not cfg.settings.android_progressbar:
            return None
        
        # If device is not an android device, skip it!
        if not cfg.is_android:
            return None

        # If version is below 2.6.10, skip it!
        if cfg.version is None or compare_version(cfg.version, "2.6.10") < 0:
            return None

        # Only issue new progress notifications if the printer is printing, or paused
        # also skip if progress is at 100 since this notification is handled via the print state transition from printing to completed
        if cur_snap.print_state not in ["printing", "paused"] or cur_snap.progress is None or cur_snap.progress == 100:
            return None

        perc_interval_reached = normalized_progress_interval_reached(cfg.snap.progress_progressbar, cur_snap.progress, self.remote_config.increments)
        time_interval_reached = (datetime.now() - cfg.snap.last_progress_progressbar).seconds >= self.remote_config.interval and cur_snap.print_state in ["printing", "paused"]

        # Ensure the progress threshold of the user's cfg is reached. If the cfg.snap is not yet printing also issue a notification
        if (cfg.snap.state in ["printing", "paused"]
                    and not perc_interval_reached and not time_interval_reached
                ):
            return None

        nid = generate_notifcation_id_from_uuid(cfg.machine_id, 4)
        channel = f'{cfg.machine_id}-progressUpdates' if cfg.version is None or compare_version(cfg.version, "2.7.2") < 0 else f'{cfg.machine_id}-progressBarUpdates'
        title = translate_replace_placeholders(
            'print_progress_title', cfg, cur_snap, self.companion_config)
        body = translate_replace_placeholders(
            'print_progress_body', cfg, cur_snap, self.companion_config)

        return ProgressNotificationContentDto(cur_snap.progress, nid, channel, title, body)

    def evaluate_live_activity_update(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot, last_snapshot: Optional[PrinterSnapshot]) -> Optional[LiveActivityContentDto]:
        """
        Evaluate if a live activity update should be issued.
        
        Args:
            cfg: The device notification configuration.
            cur_snap: The current printer snapshot.
            last_snapshot: The previous printer snapshot.
            
        Returns:
            The live activity content, if any.
        """
        # If uuid is none or empty return
        if cfg.apns is None or not cfg.apns.liveActivity:
            return None

        if cur_snap.progress is None:
            return None

        # Calculate the eta delta based on the estimated time of the current file or 15 minutes (whichever is higher)
        eta_delta = max(15, cur_snap.eta_window) if cur_snap.eta_window is not None else 15

        last_remaining_time = last_snapshot.remaining_time_avg(cfg.settings.eta_sources) if last_snapshot is not None else None
        cur_remaining_time = cur_snap.remaining_time_avg(cfg.settings.eta_sources)

        eta_update = last_remaining_time is None and cur_remaining_time is not None or last_remaining_time is not None and cur_remaining_time is not None and \
                    abs(last_remaining_time - cur_remaining_time) > eta_delta

        perc_interval_reached = normalized_progress_interval_reached(cfg.snap.progress_live_activity, cur_snap.progress, self.remote_config.increments)
        time_interval_reached = (datetime.now() - cfg.snap.last_progress_live_activity).seconds >= self.remote_config.interval and cur_snap.print_state in ["printing", "paused"]

        # The live activity can be updated more frequently. Max however in 5 percent steps or if there was a state change
        if not perc_interval_reached and cfg.snap.state == cur_snap.print_state and not eta_update and not time_interval_reached:
            return None
        
        remote_event = "update" if cur_snap.print_state in ["printing", "paused"] else "end"

        return LiveActivityContentDto(
            remote_event,
            cfg.apns.liveActivity,
            cur_snap.progress,
            cur_snap.calc_eta_seconds_utc(cfg.settings.eta_sources),
            cur_snap.print_state,
            cur_snap.filename,
        )

    def evaluate_custom_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot, is_m117: bool) -> Optional[NotificationContentDto]:
        """
        Evaluate if a custom notification (M117 or GCode response) should be issued.
        
        Args:
            cfg: The device notification configuration.
            cur_snap: The current printer snapshot.
            is_m117: Whether the notification is for an M117 message.
            
        Returns:
            The notification content, if any.
        """
        candidate = cur_snap.m117 if is_m117 else cur_snap.gcode_response
        prefix = '$MR$:' if is_m117 else 'MR_NOTIFY:'

        if not candidate:
            return None

        if not candidate.startswith(prefix):
            return None

        message = candidate[len(prefix):]
        if not message:
            return None

        # Check if this is a new notification
        if is_m117 and cfg.snap.m117 == cur_snap.m117_hash:
            return None
        elif not is_m117 and cfg.snap.gcode_response == cur_snap.gcode_response_hash:
            return None

        return self._construct_custom_notification(cfg, cur_snap, message)

    def evaluate_filament_sensor_notifications(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot, exclude_sensors: List[str]) -> Optional[List[NotificationContentDto]]:
        """
        Evaluate if filament sensor notifications should be issued.
        
        Args:
            cfg: The device notification configuration.
            cur_snap: The current printer snapshot.
            exclude_sensors: List of sensor names to exclude from notifications.
            
        Returns:
            List of notification content DTOs, if any.
        """
        # Check if the printer has filament sensors
        if len(cur_snap.filament_sensors) == 0:
            return None

        # Sensors KEYS that triggered a notification
        sensors_triggered: List[str] = []

        # Check if any of the sensors is enabled and no filament was detected before
        for key, sensor in cur_snap.filament_sensors.items():
            # Skip sensors the user wants to ignore
            # First part is for legacy conf file support as there only the sensor name was used while the 
            if key in exclude_sensors or f'{sensor.kind}#{sensor.name}' in exclude_sensors:
                continue

            # If the sensor is not enabled, skip it
            if not sensor.enabled:
                continue
            
            # If sensor detected no filament and no notification was issued before, add it to the list
            if not sensor.filament_detected and key not in cfg.snap.filament_sensors:
                sensors_triggered.append(key)

        if len(sensors_triggered) == 0:
            return None

        # Create a notification for each triggered sensor
        notifications: List[NotificationContentDto] = []
        for key in sensors_triggered:
            sensor = cur_snap.filament_sensors[key] 
            title = translate_replace_placeholders(
                'filament_sensor_triggered_title', cfg, cur_snap, self.companion_config, {'$sensor': sensor.name})
            
            body = translate_replace_placeholders(
                'filament_sensor_triggered_body', cfg, cur_snap, self.companion_config, {'$sensor': sensor.name})
            notifications.append(NotificationContentDto(generate_notifcation_id_from_uuid(cfg.machine_id, 3), f'{cfg.machine_id}-filamentSensor', title, body))

        return notifications

    def _construct_custom_notification(self, cfg: DeviceNotificationEntry, cur_snap: PrinterSnapshot, message: str) -> Optional[NotificationContentDto]:
        """
        Construct a custom notification from a message string.
        
        Args:
            cfg: The device notification configuration.
            cur_snap: The current printer snapshot.
            message: The custom message.
            
        Returns:
            The notification content.
        """
        split = message.split('|')

        has_title = (len(split) == 2)

        title = split[0].strip() if has_title else translate_implicit(
            cfg, self.companion_config, 'm117_custom_title')
        title = replace_placeholders(
            title, cfg, cur_snap, self.companion_config)
        body = (split[1] if has_title else split[0]).strip()
        body = replace_placeholders(body, cfg, cur_snap, self.companion_config)

        return NotificationContentDto(generate_notifcation_id_from_uuid(cfg.machine_id, 2), f'{cfg.machine_id}-m117', title, body)