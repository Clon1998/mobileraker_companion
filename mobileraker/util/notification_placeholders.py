from datetime import datetime, timedelta
from typing import Dict, Optional
from mobileraker.data.dtos.mobileraker.notification_config_dto import DeviceNotificationEntry
from mobileraker.data.dtos.moonraker.printer_snapshot import PrinterSnapshot
from mobileraker.util.configs import CompanionLocalConfig


def replace_placeholders(input: str, cfg: DeviceNotificationEntry, snap: PrinterSnapshot, companion_config: CompanionLocalConfig, additional_data: Dict[str, str]={}) -> str:
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
    eta_source = cfg.settings.eta_sources

    eta = snap.calc_eta(eta_source)
    if eta is not None:
        eta = eta.astimezone(companion_config.timezone)

    progress = snap.print_progress_by_fileposition_relative if snap.print_state == 'printing' else None
    remaining_time_avg = snap.remaining_time_avg(eta_source)

    data = {
        'printer_name': cfg.machine_name,
        'progress': f'{progress:.0%}' if progress is not None else None,
        'file': snap.filename if snap.filename is not None else 'UNKNOWN',
        'eta': eta_formatted(eta, companion_config.eta_format),
        'a_eta': adaptive_eta_formatted(eta, companion_config.eta_format),
        'remaining_avg': remaining_time_avg if remaining_time_avg else '--:--',
        'remaining_file': snap.remaining_time_by_file if snap.remaining_time_by_file else '--:--',
        'remaining_filament': snap.remaining_time_by_filament if snap.remaining_time_by_filament else '--:--',
        'remaining_slicer': snap.remaining_time_by_slicer if snap.remaining_time_by_slicer else '--:--',
        'cur_layer': snap.current_layer,
        'max_layer': snap.max_layer,
    }

    for name, value in data.items():
        input = input.replace(f"${name}", str(value) if value is not None else '')

    for name, value in additional_data.items():
        input = input.replace(f"${name}", str(value) if value is not None else '')

    return input


def adaptive_eta_formatted(eta: Optional[datetime], eta_format: str) -> Optional[str]:
    if not eta:
        return '--'
    if eta.date() <= datetime.today().date():
        # if today, we only return Hour:Mins:Seconds
        return eta.strftime('%H:%M:%S')
    return eta_formatted(eta, eta_format)


def eta_formatted(eta: Optional[datetime], eta_format: str) -> Optional[str]:
    if not eta:
        return '--'

    return eta.strftime(eta_format)


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
