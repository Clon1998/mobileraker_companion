
from typing import Dict

from dtos.mobileraker.notification_config_dto import DeviceNotificationEntry
from printer_snapshot import PrinterSnapshot

# List of available tokens
# printer_name - The name of the printer
# progress - Only available if printing, the progress of the current print in %
# eta - Only if printing, the ETA in hh:mm## STIL WIP!
# file - Only if printing, the file that is currently printing

_mobileraker_en: Dict[str, str] = {
    'print_progress_title': 'Print progress of $printer_name',
    'print_progress_body': '$progress $eta',
    'state_title': 'State of $printer_name changed',
    'state_printing_body': 'Started to print file: "$file"',
    'state_paused_body': 'Paused printing file: "$file"',
    'state_completed_body': 'Finished printing: "$file"',
    'state_error_body': 'Error while printing file: "$file"',
    'state_standby_body': 'Printer is in Standby',

}

_mobileraker_de: Dict[str, str] = {
    'print_progress_title': 'Druck-Fortschritt von %s',
}


_mobileraker_hu: Dict[str, str] = {

}

_mobileraker_chtw: Dict[str, str] = {

}

_mobileraker_cnch: Dict[str, str] = {

}


languages: Dict[str, Dict[str, str]] = {
    'de': _mobileraker_de,
    'en': _mobileraker_en,
    'hu': _mobileraker_hu,
    'cn': _mobileraker_cnch,
    'cntw': _mobileraker_chtw,

}

def translate(country_code: str, str_key: str, data: Dict[str, str] = {}):
    if country_code not in languages:
        # fallback to en
        return translate('en', str_key, data)
    translations = languages[country_code]
    if str_key not in translations:
        if country_code == 'en':
            raise Exception(f'No language-entry found for "{str_key}"')
        # fallback to en
        return translate('en', str_key, data)
    translation = translations[str_key]
    for name in data:
        translation = translation.replace(f"${name}", data[name])

    return translation


def translate_using_snapshot(str_key: str, cfg: DeviceNotificationEntry, snap: PrinterSnapshot) -> str:
    data = {
        'printer_name': cfg.machine_name,
        'file': snap.filename if snap.filename is not None else 'UNKNOWN',
        'eta':'' # ToDo replace with actual ETA calc...
    }

    if snap.print_state == 'printing':
        if snap.progress is not None:
            data['progress'] = f'{snap.progress*100:.0f}%'

    return translate(cfg.language, str_key, data)
