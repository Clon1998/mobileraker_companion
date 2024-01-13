import configparser
import os
from typing import Optional

import tzlocal


from mobileraker.util.i18n import languages

from .Logging import Logger
from .Context import Context


class Config:
    CONFIG_FILE_NAME = "mobileraker.conf"
    UPDATE_MANAGER_FILE_NAME = "mobileraker-moonraker.conf"


    def run(self, context:Context):
        """
        Runs the Config process.
        Setting up the moonraker update manager and config file for the companion or discovering it.

        Args:
            context (Context): The context object containing the configuration parameters.

        Returns:
            None
        """
        Logger.Header("Starting Config Writer...")
        context.mobileraker_conf_path = self._mobileraker_conf_path(context)
        # mr_moonraker_conf = self._mobileraker_update_manager_path(context)

        # self._setup_mobileraker_conf(context)

        #TODO - Setup the moonraker update manager.


        Logger.Info("Config Writer Completed.")

    def _setup_mobileraker_conf(self, context: Context, path: str):
        Logger.Info("Ensuring mobileraker config file exists and is setup correctly.")
        
        config = configparser.ConfigParser()

        if os.path.exists(path):
            Logger.Info("Config file already exists. Reading it.")
            config.read(path)


        write_config = False
        if not config.has_section("general"):
            write_config = True
            Logger.Info("General section not found, creating it.")
            config.add_section("general")


            config.set("general", "language", self._ask_for_language())
            config.set("general", "timezone", tzlocal.get_localzone_name())

        
        printer_sections = [i for i in config.sections() if i.startswith("printer ")]
        
        # If there are no printer sections, add one.
        if len(printer_sections) == 0:
            write_config = True
            Logger.Info("No printer sections found, adding a default one.")
            Logger.Warn("Please verify the config settings are correct after the install is complete.")
            Logger.Info("Note: If you have multiple printers, you will need to add them manually in the same file and format.")
            sec = "printer default"
            config.add_section(sec)
            config.set(sec, "moonraker_uri", f"ws://127.0.0.1:/{context.moonraker_port}websocket")
            config.set(sec, "moonraker_api_key", "False")
            config.set(sec, "snapshot_uri", "http://127.0.0.1/webcam/?action=snapshot")
            config.set(sec, "snapshot_rotation", "0")

        if write_config:
            with open(path, 'w', encoding="utf-8") as f:
                config.write(f)
            Logger.Info("Config file written to disk. Path: "+path)



    def _ask_for_language(self) -> str:
        Logger.Blank()
        Logger.Blank()
        Logger.Warn("Available Languages:")
        Logger.Blank()
        
        # Print the config files found.
        count = 0
        available_languages = list(languages.keys())

        for k in available_languages:
            count += 1
            Logger.Info(F"  {str(count)}) {k}")
        Logger.Blank()

        # Ask the user which number they want.
        respond_index = -1
        while True:
            try:
                response = input("Enter the number for the language you want to use: ")
                response = response.lower().strip()
                # Parse the input and -1 it, so it aligns with the array length.
                idx = int(response.lower().strip()) - 1
                if idx >= 0 and idx < len(languages):
                    respond_index = idx
                    break
                Logger.Warn("Invalid number selection, try again.")
            except Exception as e:
                Logger.Warn("Invalid input, try again. Logger.Error: "+str(e))
        return available_languages[respond_index]


    def _mobileraker_conf_path(self, context: Context) -> str:
        if len(context.printer_data_config_folder) != 0:
            return os.path.join(context.printer_data_config_folder, Config.CONFIG_FILE_NAME)
        
        return os.path.join(context.user_home, Config.CONFIG_FILE_NAME)



    def _mobileraker_update_manager_path(self, context: Context) -> Optional[str]:
        if len(context.printer_data_config_folder) == 0:
            return None
        return os.path.join(context.printer_data_config_folder, Config.CONFIG_FILE_NAME)
