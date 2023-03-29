import configparser
import datetime
import logging
import os
import pathlib
import time
from typing import Any, Dict, Optional, Union

import pytz
import tzlocal

home_dir = os.path.expanduser("~/")
companion_dir = pathlib.Path(__file__).parent.parent.resolve()
klipper_config_dir = os.path.join(
    home_dir, "klipper_config")
printer_data_config_dir = os.path.join(
    home_dir, "printer_data", "config")

printer_data_logs_dir = os.path.join(
    home_dir, "printer_data", "logs")

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
            self.printers[printer[8:]] = {
                "moonraker_uri": self.config.get(printer, "moonraker_uri", fallback="ws://127.0.0.1:7125/websocket"),
                "moonraker_api_key": None if api_key == 'False' or not api_key else api_key,
            }

        if len(self.printers) <= 0:
            self.printers['_Default'] = {
                "moonraker_uri": "ws://127.0.0.1:7125/websocket",
                "moonraker_api_key": None,
            }
        logging.info("Read %i printer config sections" % len(self.printers))


        self.language: str = self.config.get(
            'general', 'language', fallback='en')
        self.timezone_str: str = self.config.get(
            'general', 'timezone', fallback=tzlocal.get_localzone_name())  # fallback to system timezone (Hopefully)
        self.timezone: datetime.tzinfo = pytz.timezone(self.timezone_str)
        self.eta_format: str = self.config.get(
            'general', 'eta_format', fallback='%d.%m.%Y, %H:%M:%S')
        logging.info(
            f'Main section read, language:"{self.language}", timezone:"{self.timezone_str}", eta_format:"{self.eta_format}"')

    def get_config_file_location(self, passed_config: str) -> Optional[str]:
        logging.info("Passed config file is: %s" % passed_config)

        foundFile = passed_config if os.path.exists(passed_config) else self.__check_companion_dir() or self.__check_klipper_config_dir(
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
        if os.path.exists(file):
            return file
        # Also check lower case config name!
        file = os.path.join(path, filename.lower())
        if os.path.exists(file):
            return file

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