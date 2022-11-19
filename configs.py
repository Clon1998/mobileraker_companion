import configparser
import logging
import os
import pathlib
from typing import Any, Dict

script_dir = pathlib.Path(__file__).parent.resolve().parent


class CompanionRemoteConfig:

    def __init__(self) -> None:
        super().__init__()
        self.increments: float = 0.05
        self.uri: str = "some url"


# Taken from Klipper Screen : https://github.com/jordanruthe/KlipperScreen/blob/eedf5448a0e6540d7eb75385f4c5c72d75b41040/ks_includes/config.py#L266-L281
class CompanionLocalConfig:
    default_file_name: str = "Mobileraker.conf"

    def __init__(self, configfile: str) -> None:
        super().__init__()
        self.config: configparser.ConfigParser = configparser.ConfigParser()
        self.printers: Dict[str, Dict[str, Any]] = {}
        self.config.read(self.get_config_file_location(configfile))
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

    def get_config_file_location(self, file: str) -> str:
        logging.info("Passed config file is: %s" % file)
        if not os.path.exists(file):
            file = os.path.join(script_dir, self.default_file_name)
            if not os.path.exists(file):
                file = self.default_file_name.lower()
                if not os.path.exists(file):
                    klipper_config = os.path.join(
                        os.path.expanduser("~/"), "klipper_config")
                    file = os.path.join(klipper_config, self.default_file_name)
                    if not os.path.exists(file):
                        file = os.path.join(
                            klipper_config, self.default_file_name.lower())
                        # if not os.path.exists(file):
                        #     file = self.default_config_path
        if os.path.exists(file):
            logging.info("Found configuration file at: %s" %
                         os.path.abspath(file))
        else:
            logging.warn(
                "No config file was found, using default fallback values!")
        return file
