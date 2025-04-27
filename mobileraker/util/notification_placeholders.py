from datetime import datetime, timedelta
from typing import Dict, Optional
from mobileraker.data.dtos.mobileraker.notification_config_dto import DeviceNotificationEntry
from mobileraker.data.dtos.moonraker.printer_snapshot import PrinterSnapshot
from mobileraker.util.configs import CompanionLocalConfig


def replace_placeholders(raw: str, cfg: DeviceNotificationEntry, snap: PrinterSnapshot, companion_config: CompanionLocalConfig, additional_data: Optional[Dict[str, str]]=None) -> str:
    """
    Replaces placeholders in the input string with corresponding values from the provided parameters.

    Args:
        input (str): The input string containing placeholders to be replaced.
        cfg (DeviceNotificationEntry): The device notification entry configuration.
        snap (PrinterSnapshot): The printer snapshot.
        companion_config (CompanionLocalConfig): The companion local configuration.
        additional_data (Dict[str, str], optional): Additional data to be used for placeholder replacement. Defaults to {}.

    Returns:
        str: The input string with placeholders replaced by their corresponding values.
    """
    if additional_data is None:
        additional_data = {}
    eta_source = cfg.settings.eta_sources

    eta = snap.calc_eta(eta_source)
    if eta is not None:
        eta = eta.astimezone(companion_config.timezone)

    progress = snap.print_progress_by_fileposition_relative if snap.print_state == 'printing' else None
    remaining_time_avg = snap.remaining_time_avg(eta_source)

    # Get the time format based on device preferences
    eta_format = get_eta_format(cfg, companion_config)

    data = {
        'printer_name': cfg.machine_name,
        'progress': f'{progress:.0%}' if progress is not None else None,
        'file': snap.filename if snap.filename is not None else 'UNKNOWN',
        'eta': eta_formatted(eta, eta_format),
        'a_eta': adaptive_eta_formatted(eta, eta_format),
        'remaining_avg': format_time_duration(remaining_time_avg) if remaining_time_avg else '--:--',
        'remaining_file': format_time_duration(snap.remaining_time_by_file) if snap.remaining_time_by_file else '--:--',
        'remaining_filament': format_time_duration(snap.remaining_time_by_filament) if snap.remaining_time_by_filament else '--:--',
        'remaining_slicer': format_time_duration(snap.remaining_time_by_slicer) if snap.remaining_time_by_slicer else '--:--',
        'cur_layer': snap.current_layer,
        'max_layer': snap.max_layer,
    }

    for name, value in data.items():
        raw = raw.replace(f"${name}", str(value) if value is not None else '')

    for name, value in additional_data.items():
        raw = raw.replace(f"${name}", str(value) if value is not None else '')

    return raw


def get_eta_format(cfg: DeviceNotificationEntry, companion_config: CompanionLocalConfig) -> str:
    """
    Determine the ETA format based on the device's time format preference.
    
    Args:
        cfg (DeviceNotificationEntry): The device notification entry with time format preference.
        companion_config (CompanionLocalConfig): Fallback configuration.
        
    Returns:
        str: The format string to use for formatting date/time.
    """
    # If the device has a time format preference, use it
    if hasattr(cfg, 'time_format') and cfg.time_format:
        if cfg.time_format == '12h':
            return '%m/%d/%Y, %I:%M %p'
        else:  # '24h' format
            return '%d.%m.%Y, %H:%M:%S'
    
    # Otherwise fall back to the companion config
    return companion_config.eta_format


def adaptive_eta_formatted(eta: Optional[datetime], eta_format: str) -> Optional[str]:
    if not eta:
        return '--'
    if eta.date() <= datetime.today().date():
        # If today, show only time based on the time format preference
        if '12h' in eta_format:
            return eta.strftime('%I:%M %p')
        else:
            return eta.strftime('%H:%M:%S')
    return eta_formatted(eta, eta_format)


def eta_formatted(eta: Optional[datetime], eta_format: str) -> Optional[str]:
    if not eta:
        return '--'

    return eta.strftime(eta_format)


def format_time_duration(seconds: Optional[int]) -> str:
    """
    Format a duration in seconds as a human-readable string.
    
    Args:
        seconds (Optional[int]): The duration in seconds.
        
    Returns:
        str: The formatted duration string (HH:MM).
    """
    if seconds is None:
        return '--:--'
        
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    return f"{hours:02d}:{minutes:02d}"


def get_relative_date_string(date):
    today = datetime.today().date()
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)

    if date == today:
        return "Today"
    elif date == tomorrow:
        return "Tomorrow"
    elif date == yesterday:
        return "Yesterday"
    else:
        # Return the date in the format YYYY-MM-DD
        return date.strftime("%Y-%m-%d")