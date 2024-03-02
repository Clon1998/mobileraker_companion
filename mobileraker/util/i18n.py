
from typing import Dict
from mobileraker.data.dtos.mobileraker.notification_config_dto import DeviceNotificationEntry
from mobileraker.data.dtos.moonraker.printer_snapshot import PrinterSnapshot
from mobileraker.util.configs import CompanionLocalConfig

from mobileraker.util.notification_placeholders import replace_placeholders

# List of available tokens
# printer_name - The name of the printer
# progress - Only available if printing, the progress of the current print in %
# eta - Only if printing, the ETA in hh:mm## STIL WIP!
# file - Only if printing, the file that is currently printing

_mobileraker_en: Dict[str, str] = {
    'print_progress_title': 'Print progress of $printer_name',
    'print_progress_body': '$progress, ETA: $a_eta, Layer: $cur_layer/$max_layer',
    'state_title': 'State of $printer_name changed',
    'state_printing_body': 'Started to print file: "$file"',
    'state_paused_body': 'Paused while printing file: "$file"',
    'state_completed_body': 'Finished printing: "$file"',
    'state_error_body': 'Error while printing file: "$file"',
    'state_standby_body': 'Printer is in Standby',
    'm117_custom_title': 'User Notification',
    "filament_sensor_triggered_title": "Filament Sensor Triggered",
    "filament_sensor_triggered_body": "$$sensor triggered on printer $printer_name",
}

mobileraker_fr: Dict[str, str] = {
    'print_progress_title': 'Progression de l\'impression de $printer_name',
    'print_progress_body': '$progress, ETA: $a_eta, Couche: $cur_layer/$max_layer',
    'state_title': 'L\'état de $printer_name a changé',
    'state_printing_body': 'A commencé à imprimer le fichier: "$file"',
    'state_paused_body': 'En pause pendant l\'impression du fichier: "$file"',
    'state_completed_body': 'Impression terminé: "$file"',
    'state_error_body': 'Erreur lors de l\'impression du fichier: "$file"',
    'state_standby_body': 'L\'imprimante est en veille',
    'm117_custom_title': 'Notification aux utilisateurs'
}

_mobileraker_de: Dict[str, str] = {
    'print_progress_title': 'Druck-Fortschritt von $printer_name',
    'print_progress_body': '$progress, ETA: $a_eta',
    'state_title': 'Status von $printer_name geändert',
    'state_printing_body': 'Starte Druck der Datei: "$file"',
    'state_paused_body': 'Druck der Datei pausiert: "$file"',
    'state_completed_body': 'Druck abgeschlossen: "$file"',
    'state_error_body': 'Fehler beim Drucken der Datei: "$file"',
    'state_standby_body': 'Drucker im Standby',
    'm117_custom_title': 'Nutzer-Benachrichtigung',
    "filament_sensor_triggered_title": "Filament Sensor ausgelöst",
    "filament_sensor_triggered_body": "$$sensor auf Drucker $printer_name ausgelöst",
}

_mobileraker_ptbr: Dict[str, str] = {
    'print_progress_title': 'Progresso de Impressão de $printer_name',
    'print_progress_body': '$progresso, ETA: $a_eta',
    'state_title': 'Status de $printer_name Alterado',
    'state_printing_body': 'Iniciou a impressão do arquivo: "$file"',
    'state_paused_body': 'Pausou durante a impressão do arquivo: "$file"',
    'state_completed_body': 'Concluiu a impressão do arquivo: "$file"',
    'state_error_body': 'Erro durante a impressão do arquivo: "$file"',
    'state_standby_body': 'A impressora está em modo de espera',
    'm117_custom_title': 'Notificação do Usuário'
}

_mobileraker_hu: Dict[str, str] = {

}
    
_mobileraker_uk: Dict[str, str] = {
    'print_progress_title': 'Прогрес друку $printer_name',
    'print_progress_body': '$progress, ETA: $a_eta, Шар: $cur_layer/$max_layer',
    'state_title': 'Стан $printer_name змінився',
    'state_printing_body': 'Почав друкувати файл: "$file"',
    'state_paused_body': 'Призупинено під час друку файлу: "$file"',
    'state_completed_body': 'Друк завершено: "$file"',
    'state_error_body': 'Помилка під час друку файлу: "$file"',
    'state_standby_body': 'Принтер у режимі очікування',
    'm117_custom_title': 'Сповіщення користувача'
}

_mobileraker_zhhk: Dict[str, str] = {
    'print_progress_title': '$printer_name$printer_name 的列印進度',
    'print_progress_body': '$progress, 預計完成時間： $a_eta, 層： $cur_layer/$max_layer',
    'state_title': '$printer_name 的狀態已更改',
    'state_printing_body': '開始列印檔案：“$file”',
    'state_paused_body': '列印檔案時暫停：“$file”',
    'state_completed_body': '列印完成：“$file”',
    'state_error_body': '列印檔案時發生錯誤：“$file”',
    'state_standby_body': '印表機處於待機狀態',
    'm117_custom_title': '用戶通知'
}

_mobileraker_zhcn: Dict[str, str] = {
    'print_progress_title': '$printer_name$printer_name 的打印进度',
    'print_progress_body': '$progress, 预计完成时间： $a_eta, 层： $cur_layer/$max_layer',
    'state_title': '$printer_name 的状态已更改',
    'state_printing_body': '开始打印档案：“$file”',
    'state_paused_body': '打印档案时暂停：“$file”',
    'state_completed_body': '打印完成：“$file”',
    'state_error_body': '打印档案时发生错误：“$file”',
    'state_standby_body': '打印机处于待机状态',
    'm117_custom_title': '用户通知'
}


languages: Dict[str, Dict[str, str]] = {
    'de': _mobileraker_de,
    'en': _mobileraker_en,
    'fr': mobileraker_fr,
    'hu': _mobileraker_hu,
    'uk': _mobileraker_uk,
    'ptbr': _mobileraker_ptbr,
    'zhhk': _mobileraker_zhhk,
    'zhcn': _mobileraker_zhcn,
}


def translate(country_code: str, str_key: str) -> str:
    if country_code not in languages:
        # fallback to en
        return translate('en', str_key)
    translations = languages[country_code]
    if str_key not in translations:
        if country_code == 'en':
            raise AttributeError('No language-entry found for "%s"', str_key)
        # fallback to en
        return translate('en', str_key)
    translation = translations[str_key]

    return translation


def translate_replace_placeholders(str_key: str, cfg: DeviceNotificationEntry, snap: PrinterSnapshot, companion_config: CompanionLocalConfig, additional_data: Dict[str, str]={}) -> str:
    # For now users can only globally define the notification language!
    translation = translate(companion_config.language, str_key)
    # translation = translate(cfg.language, str_key)
    return replace_placeholders(translation, cfg, snap, companion_config, additional_data)
