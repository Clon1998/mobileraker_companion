import configparser
import datetime
import logging
import os
import pathlib
from typing import Any, Dict, Optional, Union
from dateutil import tz

home_dir = os.path.expanduser("~/")
companion_dir = pathlib.Path(__file__).parent.parent.parent.resolve()
klipper_config_dir = os.path.join(
    home_dir, "klipper_config")
printer_data_config_dir = os.path.join(
    home_dir, "printer_data", "config")

printer_data_logs_dir = os.path.join(
    home_dir, "printer_data", "logs")



def get_local_timezone() -> str:
    """
    Returns the local timezone.

    return: The local timezone.
    """
    # Get the system's current local timezone
    local_timezone = tz.tzlocal()
    # Convert the timezone to a string representation
    timezone_abbr = local_timezone.tzname(datetime.datetime.now())

    return timezone_abbr if timezone_abbr is not None else 'UTC'

class CompanionRemoteConfig:

    def __init__(self) -> None:
        super().__init__()
        self.increments: int = 5
        self.uri: str = "some url"


# Taken from Klipper Screen : https://github.com/jordanruthe/KlipperScreen/blob/eedf5448a0e6540d7eb75385f4c5c72d75b41040/ks_includes/config.py#L266-L281
class CompanionLocalConfig:
    default_file_name: str = "Mobileraker.conf"

    def __init__(self, passed_config_file: str) -> None:
        super().__init__()
        self.config: configparser.ConfigParser = configparser.ConfigParser()
        self.printers: Dict[str, Dict[str, Any]] = {}

        config_file_path = self.get_config_file_location(passed_config_file)
        if config_file_path:
            self.config.read(config_file_path)

        printer_sections = sorted(
            [i for i in self.config.sections() if i.startswith("printer ")])

        # Taken from Klipper Screen: https://github.com/jordanruthe/KlipperScreen/blob/37c10fc8b373944ea138574a44bbfa0a5dcf0a98/ks_includes/config.py#L68-L85
        for printer in printer_sections:
            api_key = self.config.get(
                printer, "moonraker_api_key", fallback=None)

            rotation = self.config.getint(
                printer, "snapshot_rotation", fallback=0)
            if rotation not in [0, 90, 180, 270]:
                rotation = 0

            self.printers[printer[8:]] = {
                "moonraker_uri": self.config.get(printer, "moonraker_uri", fallback="ws://127.0.0.1:7125/websocket"),
                "moonraker_api_key": None if api_key == 'False' or not api_key else api_key,
                "snapshot_uri": self.config.get(printer, "snapshot_uri", fallback="http://127.0.0.1/webcam/?action=snapshot"),
                "snapshot_rotation": rotation
            }

        if len(self.printers) <= 0:
            self.printers['_Default'] = {
                "moonraker_uri": "ws://127.0.0.1:7125/websocket",
                "moonraker_api_key": None,
                "snapshot_uri": "http://127.0.0.1/webcam/?action=snapshot",
                "snapshot_rotation": 0
            }
        logging.info("Read %i printer config sections" % len(self.printers))

        self.language: str = self.config.get(
            'general', 'language', fallback='en')
        self.timezone_str: str = self.config.get(
            'general', 'timezone', fallback=get_local_timezone())  # fallback to system timezone (Hopefully)

        parsed_tz = tz.gettz(self.timezone_str)
        self.timezone: datetime.tzinfo = parsed_tz if parsed_tz is not None else tz.UTC
        self.eta_format: str = self.config.get(
            'general', 'eta_format', fallback='%d.%m.%Y, %H:%M:%S')
        self.include_snapshot: bool = self.config.getboolean(
            'general', 'include_snapshot', fallback=True)

        logging.info(
            f'Main section read, language:"{self.language}", timezone:"{self.timezone_str}", eta_format:"{self.eta_format}", include_snapshot:"{self.include_snapshot}"')

    def get_config_file_location(self, passed_config: str) -> Optional[str]:
        foundFile = self.__check_passed_config(passed_config) or self.__check_companion_dir() or self.__check_klipper_config_dir(
        ) or self.__check_printer_data_config_dir() or self.__check_user_dir()

        if foundFile and os.path.exists(foundFile):
            logging.info("Found configuration file at: %s" %
                         os.path.abspath(foundFile))
        else:
            logging.warn(
                "No config file was found, using default fallback values!")
        return foundFile

    # Check if file exists, ignoring if it starts capatilized or lowercase!
    def __check_file_exists(self, path: Union[pathlib.Path, str], filename: str) -> Optional[str]:
        file = os.path.join(path, filename)
        if os.path.exists(file) and filename in os.listdir(path):
            return file
        # Also check lower case config name!
        file = os.path.join(path, filename.lower())
        if os.path.exists(file) and filename.lower() in os.listdir(path):
            return file.lower()

    # Checks the companion dir
    def __check_companion_dir(self) -> Optional[str]:
        logging.info("Checking mobileraker_companion dir")
        return self.__check_file_exists(companion_dir, self.default_file_name)

    # Checks deprecated klipper_config dir
    def __check_klipper_config_dir(self) -> Optional[str]:
        logging.info("Checking klipper_config dir")
        return self.__check_file_exists(klipper_config_dir, self.default_file_name)

    # Check new ~/printer_data/config
    def __check_printer_data_config_dir(self) -> Optional[str]:
        logging.info("Checking printer_data/config dir")
        return self.__check_file_exists(printer_data_config_dir, self.default_file_name)

    # Check user-dir -> ~/Mobileraker.conf
    def __check_user_dir(self) -> Optional[str]:
        logging.info("Checking user dir")
        return self.__check_file_exists(home_dir, self.default_file_name)
    
    # Check user-dir -> ~/Mobileraker.conf
    def __check_passed_config(self, passed_config: str) -> Optional[str]:
        logging.info("Checking if passed config exists: %s" % passed_config)
    
        if os.path.exists(passed_config):
            return passed_config
    

