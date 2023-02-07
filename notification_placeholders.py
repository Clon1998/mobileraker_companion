from datetime import datetime
from typing import Optional
from configs import CompanionLocalConfig
from dtos.mobileraker.notification_config_dto import DeviceNotificationEntry
from printer_snapshot import PrinterSnapshot


def replace_placeholders(input: str, cfg: DeviceNotificationEntry, snap: PrinterSnapshot, companion_config: CompanionLocalConfig) -> str:

    eta = snap.get_eta(companion_config.timezone)
    data = {
        'printer_name': cfg.machine_name,
        'file': snap.filename if snap.filename is not None else 'UNKNOWN',
        # ToDo replace with actual ETA calc...
        'eta': eta_formatted(eta, companion_config.eta_format),
        'a_eta': adaptive_eta_formatted(eta, companion_config.eta_format),
        'remaining': snap.get_formatted_remaining_time() if snap.get_formatted_remaining_time() else '--:--'
    }


    if snap.print_state == 'printing':
        if snap.progress is not None:
            data['progress'] = f'{snap.progress}%'
    for name in data:
        input = input.replace(f"${name}", data[name] if data[name] else '')
    return input


def adaptive_eta_formatted(eta: Optional[datetime], eta_format: str) -> Optional[str]:
    if not eta:
        return
    if eta.date() <= datetime.today().date():
        # if today, we only return Hour:Mins:Seconds
        return eta.strftime('%H:%M:%S')
    return eta_formatted(eta, eta_format)


def eta_formatted(eta: Optional[datetime], eta_format: str) -> Optional[str]:
    if not eta:
        return

    return eta.strftime(eta_format)
