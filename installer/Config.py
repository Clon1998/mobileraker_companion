import configparser
from io import TextIOBase
import os
from typing import Optional

import tzlocal


from mobileraker.util.i18n import languages

from .Logging import Logger
from .Context import Context


class Config:
    CONFIG_FILE_NAME = "mobileraker.conf"
    UPDATE_MANAGER_FILE_NAME = "mobileraker-moonraker.conf"

    CONFIG_HELPERS = {
        "general.language": ["one of the supported languages defined in i18n.py#languages (de,en,...)", "Default: en"],
        "general.timezone": ["The system's timezone e.g. Europe/Berlin for Berlin time or US/Central.", "For more values see https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568", "Default: Tries to use system timezone", "Optional"],
        "general.eta_format": ["Format used for eta and adaptive_eta placeholder variables", "For available options see https://strftime.org/", "Note that you will have to escape the % char by using a 2nd one e.g.: %d/%m/%Y -> %%d/%%m/%%Y", "Default: %%d.%%m.%%Y, %%H:%%M:%%S", "Optional"],
        "general.include_snapshot": ["!! SUPPORTER ONLY - This feature requires beeing a supporter of Mobileraker as of now!", "Include a snapshot of the webcam in any print status/progress update notifications", "Default: True", "Optional"],

        "printer.moonraker_uri": ["Define the uri to the moonraker instance.", "Default value: ws://127.0.0.1:7125/websocket", "Optional"],
        "printer.moonraker_api_key": ["Moonraker API key if force_logins or trusted clients is active!", "Default value: False", "Optional"],
        "printer.snapshot_uri": ["!! SUPPORTER ONLY - This feature requires beeing a supporter of Mobileraker as of now!", "The ABSOLUT url to the webcam, the companion should make a screenshot of.", "Example MJPEG SnapShot url: http://192.168.178.135/webcam/?action=snapshot", "Optional"],
        "printer.snapshot_rotation": ["!! SUPPORTER ONLY - This feature requires beeing a supporter of Mobileraker as of now!", "The rotation of the snapshot in degrees", "Default value: 0", "Valud Values: 0,90,180,270", "Optional"],
    }


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

        self._setup_mobileraker_conf(context)

        #TODO - Setup the moonraker update manager.


        Logger.Info("Config Writer Completed.")

    def _setup_mobileraker_conf(self, context: Context):
        Logger.Info("Ensuring mobileraker config file exists and is setup correctly.")
        
        config = configparser.ConfigParser()
        path = context.mobileraker_conf_path

        if os.path.exists(path):
            Logger.Info("Config file already exists. Reading it.")
            config.read(path)


        write_section = []
        if not config.has_section("general"):
            write_section.append("general")
            Logger.Info("General section not found, creating it.")
            config.add_section("general")


            config.set("general", "language", self._ask_for_language())
            config.set("general", "timezone", tzlocal.get_localzone_name())
            config.set("general", "eta_format", "%%d.%%m.%%Y, %%H:%%M:%%S")
            config.set("general", "include_snapshot", "True")

        
        printer_sections = [i for i in config.sections() if i.startswith("printer ")]
        
        # If there are no printer sections, add one.
        if len(printer_sections) == 0:
            Logger.Blank()
            Logger.Blank()
            Logger.Warn(f"No printer sections found in {Config.CONFIG_FILE_NAME}, adding a default one.")
            Logger.Warn(f"Please verify the config settings are correct after the install is complete in the {Config.CONFIG_FILE_NAME}.")
            Logger.Info("Note: If you have multiple printers, you will need to add them manually in the same file and format.")
            sec = "printer default"
            write_section.append(sec)
            config.add_section(sec)
            config.set(sec, "moonraker_uri", f"ws://127.0.0.1:/{context.moonraker_port}websocket")
            config.set(sec, "moonraker_api_key", "False")
            config.set(sec, "snapshot_uri", "http://127.0.0.1/webcam/?action=snapshot")
            config.set(sec, "snapshot_rotation", "0")

        if len(write_section) > 0:
            # If the file already exists, just append to it.
            mode = 'a' if os.path.exists(path) else 'w'
            with open(path, mode, encoding="utf-8") as f:
                for section in write_section:
                    self._write_config_section(f, config, section)

            Logger.Info("Wrote mobileraker config file to: "+path)



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
        Logger.Info("Selected language: "+available_languages[respond_index])
        return available_languages[respond_index]


    def _mobileraker_conf_path(self, context: Context) -> str:
        if len(context.printer_data_config_folder) != 0:
            return os.path.join(context.printer_data_config_folder, Config.CONFIG_FILE_NAME)
        
        return os.path.join(context.user_home, Config.CONFIG_FILE_NAME)



    def _mobileraker_update_manager_path(self, context: Context) -> Optional[str]:
        if len(context.printer_data_config_folder) == 0:
            return None
        return os.path.join(context.printer_data_config_folder, Config.CONFIG_FILE_NAME)


    def _write_config_section(self, file_writer: TextIOBase, config: configparser.ConfigParser, section:str):
        if len(config.options(section)) == 0:
            return
        Logger.Debug("Writing config section: "+section)
        file_writer.write(f"[{section}]\n")
        
        for option in config.options(section):
            
            value = config.get(section, option, raw=True, fallback=None)
            if value is None:
                value = ""
            else:
                value = str(value).replace('\n', '\n\t')
            
            Logger.Debug(f"Writing Option: {option}: {value}")


            file_writer.write(f"{option}: {value}\n")
            helper_key = f"{section}.{option}"
            if helper_key in Config.CONFIG_HELPERS:
                for helper in Config.CONFIG_HELPERS[helper_key]:
                    file_writer.write(f"# {helper}\n")
        file_writer.write("\n")