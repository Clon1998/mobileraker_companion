
from typing import Dict, Optional
from mobileraker.data.dtos.mobileraker.notification_config_dto import DeviceNotificationEntry
from mobileraker.data.dtos.moonraker.printer_snapshot import PrinterSnapshot
from mobileraker.util.configs import CompanionLocalConfig

from mobileraker.util.functions import compare_version
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
    'state_resumed_body': 'Resumed printing for: "$file"',
    'state_cancelled_body': 'Cancelled printing of: "$file"',
    'm117_custom_title': 'User Notification',
    "filament_sensor_triggered_title": "Filament Sensor Triggered",
    "filament_sensor_triggered_body": "$$sensor triggered on printer $printer_name",
}

_mobileraker_fr: Dict[str, str] = {
    'print_progress_title': 'Progression de l\'impression de $printer_name',
    'print_progress_body': '$progress, ETA : $a_eta, Couche : $cur_layer/$max_layer',
    'state_title': 'État de $printer_name modifié',
    'state_printing_body': 'Impression du fichier commencée : "$file"',
    'state_paused_body': 'Impression en pause du fichier : "$file"',
    'state_completed_body': 'Impression terminée : "$file"',
    'state_error_body': 'Erreur lors de l\'impression du fichier : "$file"',
    'state_standby_body': 'L\'imprimante est en veille',
    'state_resumed_body': 'Impression reprise pour : "$file"',
    'state_cancelled_body': 'Impression annulée de : "$file"',
    'm117_custom_title': 'Notification de l\'utilisateur',
    "filament_sensor_triggered_title": "Capteur de filament déclenché",
    "filament_sensor_triggered_body": "Capteur $$sensor déclenché sur l'imprimante $printer_name",
}

_mobileraker_de: Dict[str, str] = {
    'print_progress_title': 'Druckfortschritt von $printer_name',
    'print_progress_body': '$progress, ETA: $a_eta, Schicht: $cur_layer/$max_layer',
    'state_title': 'Status von $printer_name geändert',
    'state_printing_body': 'Datei wird gedruckt: "$file"',
    'state_paused_body': 'Drucken der Datei angehalten: "$file"',
    'state_completed_body': 'Drucken abgeschlossen: "$file"',
    'state_error_body': 'Fehler beim Drucken der Datei: "$file"',
    'state_standby_body': 'Drucker ist im Standby',
    'state_resumed_body': 'Druck der Datei fortgesetzt: "$file"',
    'state_cancelled_body': 'Drucken der Datei abgebrochen: "$file"',
    'm117_custom_title': 'Benutzers-Benachrichtigung',
    "filament_sensor_triggered_title": "Filamentsensor ausgelöst",
    "filament_sensor_triggered_body": "Sensor $$sensor auf Drucker $printer_name ausgelöst",
}

_mobileraker_hu: Dict[str, str] = {
    'print_progress_title': '$printer_name nyomtatási előrehaladása',
    'print_progress_body': '$progress, Becsült befejezés: $a_eta, Réteg: $cur_layer/$max_layer',
    'state_title': '$printer_name állapota megváltozott',
    'state_printing_body': 'Nyomtatás megkezdődött: "$file"',
    'state_paused_body': 'Nyomtatás szünetel: "$file"',
    'state_completed_body': 'Nyomtatás befejeződött: "$file"',
    'state_error_body': 'Hiba a nyomtatás közben: "$file"',
    'state_standby_body': 'A nyomtató készenléti állapotban van',
    'state_resumed_body': 'Nyomtatás folytatva: "$file"',
    'state_cancelled_body': 'Nyomtatás megszakítva: "$file"',
    'm117_custom_title': 'Felhasználói értesítés',
    "filament_sensor_triggered_title": "Szálérzékelő aktiválva",
    "filament_sensor_triggered_body": "$$sensor érzékelő aktiválva a $printer_name nyomtatón",
}

_mobileraker_uk: Dict[str, str] = {
    'print_progress_title': 'Прогрес друку $printer_name',
    'print_progress_body': '$progress, Очікуваний час: $a_eta, Шар: $cur_layer/$max_layer',
    'state_title': 'Стан $printer_name змінено',
    'state_printing_body': 'Розпочато друк файлу: "$file"',
    'state_paused_body': 'Друк файлу призупинено: "$file"',
    'state_completed_body': 'Друк завершено: "$file"',
    'state_error_body': 'Помилка під час друку файлу: "$file"',
    'state_standby_body': 'Принтер у режимі очікування',
    'state_resumed_body': 'Друк відновлено для: "$file"',
    'state_cancelled_body': 'Друк файлу скасовано: "$file"',
    'm117_custom_title': 'Повідомлення користувача',
    "filament_sensor_triggered_title": "Датчик філамента спрацьовано",
    "filament_sensor_triggered_body": "Датчик $$sensor спрацював на принтері $printer_name",
}

_mobileraker_ptbr: Dict[str, str] = {
    'print_progress_title': 'Progresso da impressão de $printer_name',
    'print_progress_body': '$progress, ETA: $a_eta, Camada: $cur_layer/$max_layer',
    'state_title': 'Estado de $printer_name alterado',
    'state_printing_body': 'Iniciado a impressão do arquivo: "$file"',
    'state_paused_body': 'Impressão do arquivo pausada: "$file"',
    'state_completed_body': 'Impressão concluída: "$file"',
    'state_error_body': 'Erro ao imprimir o arquivo: "$file"',
    'state_standby_body': 'Impressora em espera',
    'state_resumed_body': 'Impressão retomada para: "$file"',
    'state_cancelled_body': 'Impressão cancelada de: "$file"',
    'm117_custom_title': 'Notificação do usuário',
    "filament_sensor_triggered_title": "Sensor de Filamento Ativado",
    "filament_sensor_triggered_body": "Sensor $$sensor ativado na impressora $printer_name",
}

_mobileraker_zhhk: Dict[str, str] = {
    'print_progress_title': '$printer_name 的打印进度',
    'print_progress_body': '$progress, 预计完成时间: $a_eta, 层: $cur_layer/$max_layer',
    'state_title': '$printer_name 的状态已更改',
    'state_printing_body': '开始打印文件: "$file"',
    'state_paused_body': '打印文件暂停: "$file"',
    'state_completed_body': '打印完成: "$file"',
    'state_error_body': '打印文件时出错: "$file"',
    'state_standby_body': '打印机处于待机状态',
    'state_resumed_body': '恢复打印: "$file"',
    'state_cancelled_body': '取消打印: "$file"',
    'm117_custom_title': '用户通知',
    "filament_sensor_triggered_title": "检测到断料",
    "filament_sensor_triggered_body": "打印机 $printer_name 上的 $$sensor 检测到断料",
}

_mobileraker_zhcn: Dict[str, str] = {
    'print_progress_title': '$printer_name 的打印进度',
    'print_progress_body': '$progress, 预计完成时间: $a_eta, 层: $cur_layer/$max_layer',
    'state_title': '$printer_name 的状态已更改',
    'state_printing_body': '开始打印文件: "$file"',
    'state_paused_body': '打印文件暂停: "$file"',
    'state_completed_body': '打印完成: "$file"',
    'state_error_body': '打印文件时出错: "$file"',
    'state_standby_body': '打印机处于待机状态',
    'state_resumed_body': '恢复打印: "$file"',
    'state_cancelled_body': '取消打印: "$file"',
    'm117_custom_title': '用户通知',
    "filament_sensor_triggered_title": "检测到断料",
    "filament_sensor_triggered_body": "打印机 $printer_name 上的 $$sensor 检测到断料",
}



languages: Dict[str, Dict[str, str]] = {
    'de': _mobileraker_de,
    'en': _mobileraker_en,
    'fr': _mobileraker_fr,
    'hu': _mobileraker_hu,
    'uk': _mobileraker_uk,
    'ptbr': _mobileraker_ptbr,
    'zhhk': _mobileraker_zhhk,
    'zhcn': _mobileraker_zhcn,
}


def translate(country_code: str, str_key: str) -> str:
    """
    Translates the given string key to the specified country code's language.

    Args:
        country_code (str): The country code representing the language.
        str_key (str): The string key to be translated.

    Returns:
        str: The translated string.

    Raises:
        AttributeError: If no language entry is found for the given string key.
    """
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

def translate_implicit( cfg: DeviceNotificationEntry, companion_config: CompanionLocalConfig, str_key: str) -> str:
    # Since 2.7.1 the app syncs the app language and makes it available to the companion
    locale = cfg.language.replace('_', '').lower() if cfg.version is not None and compare_version(cfg.version, "2.7.1") >= 0 else companion_config.language
    return translate(locale, str_key)


def translate_replace_placeholders(str_key: str, cfg: DeviceNotificationEntry, snap: PrinterSnapshot, companion_config: CompanionLocalConfig, additional_data: Optional[Dict[str, str]]=None) -> str:
    """
    Translates the given string key and replaces the placeholders with the provided data.

    Args:
        str_key (str): The string key to be translated and replaced.
        cfg (DeviceNotificationEntry): The device notification configuration.
        snap (PrinterSnapshot): The printer snapshot.
        companion_config (CompanionLocalConfig): The companion local configuration.
        additional_data (Dict[str, str], optional): Additional data to replace the placeholders. Defaults to {}.

    Returns:
        str: The translated and replaced string.
    """
    if additional_data is None:
        additional_data = {}


    # For now users can only globally define the notification language!
    translation = translate_implicit(cfg, companion_config, str_key)
    # translation = translate(cfg.language, str_key)
    return replace_placeholders(translation, cfg, snap, companion_config, additional_data)
