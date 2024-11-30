import configparser
from io import TextIOBase
import os
from typing import List, Optional


from mobileraker.util.i18n import languages
from mobileraker.util.configs import get_local_timezone

from .Logging import Logger
from .Context import Context, PlatformType
from .Paths import Paths
from .Util import Util


class Config:
    CONFIG_FILE_NAME = "mobileraker.conf"
    UPDATE_MANAGER_FILE_NAME = "mobileraker-moonraker.conf"

    CONFIG_HELPERS = {
        "general.language": ["!!! DEPRECATED. The app now syncs the app's language to the companion", "one of the supported languages defined in i18n.py#languages (de,en,...)", "!!! For users from the UK: entering 'uk' will resolve to Ukrainian language, not English. Use 'en' for English!","Default: en"],
        "general.timezone": ["The system's timezone e.g. Europe/Berlin for Berlin time or US/Central.", "For more values see https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568", "Default: Tries to use system timezone", "Optional"],
        "general.eta_format": ["Format used for eta and adaptive_eta placeholder variables", "For available options see https://strftime.org/", "Note that you will have to escape the % char by using a 2nd one e.g.: %d/%m/%Y -> %%d/%%m/%%Y", "Default: %%d.%%m.%%Y, %%H:%%M:%%S", "Optional"],
        "general.include_snapshot": ["!! SUPPORTER ONLY - This feature requires beeing a supporter of Mobileraker as of now!", "Include a snapshot of the webcam in any print status/progress update notifications", "Default: True", "Optional"],

        "printer.moonraker_uri": ["Define the uri to the moonraker instance.", "Default value: ws://127.0.0.1:7125/websocket", "Optional"],
        "printer.moonraker_api_key": ["Moonraker API key if force_logins or trusted clients is active!", "Default value: False", "Optional"],
        "printer.snapshot_uri": ["!! SUPPORTER ONLY - This feature requires beeing a supporter of Mobileraker as of now!", "The ABSOLUT url to the webcam, the companion should make a screenshot of.", "Example MJPEG SnapShot url: http://192.168.178.135/webcam/?action=snapshot", "Optional"],
        "printer.snapshot_rotation": ["!! SUPPORTER ONLY - This feature requires beeing a supporter of Mobileraker as of now!", "The rotation of the snapshot in degrees", "Default value: 0", "Valud Values: 0,90,180,270", "Optional"],
        "printer.ignore_filament_sensors": ["Comma separated list of filament sensors to ignore, ignored filament sensors do not trigger", "a notification if they are triggered. This is useful if you have a filament sensor that is used", "in a MMU setup like ERCF.","IMPORTANT, do not include the sensor type. E.g. if your sensor is configured", "like: [filament_switch_sensor printhead_sensor] add `printhead_sensor` to the list.", "Default: empty", "Optional"],
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
        context.mobileraker_conf_path = self._discover_mobileraker_conf_path(context)
        Logger.Debug("Mobileraker Config Path: "+context.mobileraker_conf_path)
        
        self._setup_mobileraker_conf(context)
        
        #TODO - Setup the moonraker update manager.
        # mr_moonraker_conf = self._mobileraker_update_manager_path(context)

        #TODO - Add to MOONRAKER service file

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
            config.set("general", "timezone", get_local_timezone())
            config.set("general", "eta_format", "%%d.%%m.%%Y, %%H:%%M:%%S")
            config.set("general", "include_snapshot", "True")

        
        printer_sections = [i for i in config.sections() if i.startswith("printer ")]
        
        
        # If there are no printer sections, add one.
        if len(printer_sections) == 0:
            Logger.Blank()
            Logger.Blank()
            Logger.Warn(f"No printer sections found in {Config.CONFIG_FILE_NAME}, adding a default one.")
            self._add_printer_with_user_input(context, config, write_section, "default")
        elif not self._printer_in_config(context, config, printer_sections):
            Logger.Blank()
            Logger.Blank()
            Logger.Warn(f"Printer section for Moonraker Instance with port {context.moonraker_port} not found in {Config.CONFIG_FILE_NAME}, adding it as new one.")
            self._add_printer_with_user_input(context, config, write_section, f"moonraker_{context.moonraker_port}")
        else:
            Logger.Blank()
            Logger.Blank()
            Logger.Info(f"Printer section for Moonraker Instance with port {context.moonraker_port} found in {Config.CONFIG_FILE_NAME}, skipping adding it as new one.")

        if len(write_section) > 0:
            # If the file already exists, just append to it.
            mode = 'a' if os.path.exists(path) else 'w'
            with open(path, mode, encoding="utf-8") as f:
                for section in write_section:
                    self._write_config_section(f, config, section)

            Logger.Info("Wrote mobileraker config file to: "+path)

        self._link_mobileraker_conf(context)

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
        Logger.Warn("Note: The language selection can be changed in the mobileraker.conf file later.")
        Logger.Error("Deprecation Warning: The selected language will only be used for app-versions below 2.7.1. For newer versions, the app will sync your mobile device language with the companion.")

        return available_languages[respond_index]

    def _link_mobileraker_conf(self, context: Context) -> None:
        if context.platform == PlatformType.K1 or context.is_standalone:
            # K1 has only a single moonraker instance, so we can just skip this.
            # Standalone plugins don't need this either.
            return

        # Creates a link to the mobileraker config file in the moonraker config folder if it is not the master config file.
        if Util.parent_dir(context.mobileraker_conf_path) != context.printer_data_config_folder:
            Logger.Info("Linking master mobileraker config file to moonraker config folder of selected printer.")
            context.mobileraker_conf_link = os.path.join(context.printer_data_config_folder, Config.CONFIG_FILE_NAME)
            os.link(context.mobileraker_conf_path, context.mobileraker_conf_link)
            Logger.Info(f"Hard link `{context.mobileraker_conf_path} ->  {context.mobileraker_conf_link}` created successfully.")

    def _discover_mobileraker_conf_path(self, context: Context) -> str:
        if context.platform == PlatformType.DEBIAN:
            return self._discover_mobileraker_conf_path_for_native(context)
        elif context.platform == PlatformType.K1:
            return self._discover_mobileraker_conf_path_for_k1(context)
        elif context.platform == PlatformType.SONIC_PAD:
            return self._discover_mobileraker_conf_path_for_sonic_pad(context)
        raise NotImplementedError(f"Config discovery is not supported for Platform type {context.platform} yet.")

    def _discover_mobileraker_conf_path_for_native(self, context: Context) -> str:
        service_files = Util.scan_files(Paths.SystemdServiceFilePath, "mobileraker.service")

        for service_file in service_files:
            path = self._mobileraker_conf_path_from_service_file(service_file)
            if path is not None:
                return path

        # If we didn't find any service files, we assume it is a new install and we should create the file.
        return self._default_mobileraker_conf_path(context)
    
    def _discover_mobileraker_conf_path_for_k1(self, context: Context) -> str:
        # If we are on a K1, there should always only be a single moonraker instance, so we can just use the default path.
        return self._default_mobileraker_conf_path(context)

    def _discover_mobileraker_conf_path_for_sonic_pad(self, context: Context) -> str:
        # The Sonic Pad can have multiple moonraker instances. However, we always use the default/base one for the master config.
        return f"{Paths.CrealityOsUserDataPath_SonicPad}/printer_config/{Config.CONFIG_FILE_NAME}"
        

    def _default_mobileraker_conf_path(self, context: Context) -> str:
        if context.is_standalone:
            return os.path.join(context.standalone_data_path, Config.CONFIG_FILE_NAME)
        
        if len(context.printer_data_config_folder) != 0:
            return os.path.join(context.printer_data_config_folder, Config.CONFIG_FILE_NAME)
        
        return os.path.join(context.user_home, Config.CONFIG_FILE_NAME)

    def _mobileraker_conf_path_from_service_file(self, service_file: str) -> Optional[str]:
        try:
            Logger.Debug("Parsing mobileraker config path from service file: "+service_file)

            with open(service_file, "r", encoding="utf-8") as file:
                lines = file.readlines()
                for line in lines:
                    # We are lokign for the ExecStart since this should contain the path to the config file or the absolute path to the config file.
                    
                    
                    # ExecStart=/home/fly/mobileraker-env/bin/python3 /home/fly/mobileraker_companion/mobileraker.py -l /home/fly/printer_data/logs -c /home/fly/printer_data/config/mobileraker.conf
                    if line.startswith("ExecStart="):
                        # We found the line, parse the path from it.
                        path = self._parse_exec_start_line(line)
                        if path is not None:
                            Logger.Debug("Found mobileraker config path from service file: "+path)
                            return path
            




        except Exception as e:
            Logger.Warn("Failed to parse mobileraker config path from service file: "+str(e))
        return None


    def _parse_exec_start_line(self, line: str) -> Optional[str]:
        #ExecStart=/home/fly/mobileraker-env/bin/python3 /home/fly/mobileraker_companion/mobileraker.py -l /home/fly/printer_data/logs -c /home/fly/printer_data/config/mobileraker.conf

        # Find the index of -d
        index = line.find("-c")
        if index == -1:
            return None
        # Get the substring after -d
        sub = line[index+2:].strip()
        # Split by space and take the first item.
        sub = sub.split(" ")[0]
        return sub



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
            helper_key = f"{section}.{option}" if not section.startswith("printer ") else f"printer.{option}"
            Logger.Debug("Checking for helpers: "+helper_key)
            if helper_key in Config.CONFIG_HELPERS:
                for helper in Config.CONFIG_HELPERS[helper_key]:
                    Logger.Debug("Writing helper: # "+helper)
                    file_writer.write(f"# {helper}\n")
        file_writer.write("\n")

    def _printer_in_config(self, context: Context, config: configparser.ConfigParser, printer_sections: List[str]) -> bool:
        for sec in printer_sections:
            uri = config.get(sec, "moonraker_uri", fallback="")
            
            if uri.find(f":{context.moonraker_port}/") != -1 and (uri.find("localhost") or uri.find("127.0.0.1")):
                return True
        return False

    def _add_printer(self, name: str,context: Context, config: configparser.ConfigParser, write_section: List[str]):
        sec = f"printer {name}"
        write_section.append(sec)
        config.add_section(sec)
        config.set(sec, "moonraker_uri", f"ws://127.0.0.1:{context.moonraker_port}/websocket")
        config.set(sec, "moonraker_api_key", "False")
        if context.platform == PlatformType.K1:
            config.set(sec, "snapshot_uri", "http://127.0.0.1:4408/webcam/?action=snapshot")
        else:
            config.set(sec, "snapshot_uri", "http://127.0.0.1/webcam/?action=snapshot")
        config.set(sec, "snapshot_rotation", "0")
        config.set(sec, "ignore_filament_sensors", "")
    
    def _add_printer_with_user_input(self, context: Context, config: configparser.ConfigParser, write_section: List[str], printer_name: str):
        Logger.Blank()
        Logger.Blank()
        Logger.Info(f"Do you want me to help you add a printer to the {Config.CONFIG_FILE_NAME} file or should I use the default settings?")
        help = self._ask_input("y/n", "y")
        if help.lower() == 'n':
            Logger.Info("Using default settings for printer.")
            self._add_printer("default", context, config, write_section)
            return
        Logger.Info("Okay... I will guide you through the process of adding a printer to the config file.")
        Logger.Blank()
        Logger.Info("Please provide the following information:")
        defaults = {
            "name": printer_name,
            "moonraker_uri": "127.0.0.1",
            "moonraker_port": str(context.moonraker_port),
            "moonraker_api_key": "False",
            "snapshot_rotation": "0"
        }
        user_input = defaults

        while True:
            Logger.Blank()
            name = self._ask_input("Printer Name", user_input["name"])
            moonraker_uri = self._ask_input("Moonraker URI (Without Port)", user_input["moonraker_uri"])
            moonraker_port = self._ask_input("Moonraker Port", user_input["moonraker_port"])
            api_key = self._ask_input("Moonraker API Key, False if none is used", user_input["moonraker_api_key"])
            snapshot_rotation = self._ask_input("Snapshot Rotation", user_input["snapshot_rotation"])

            # Prepare the configuration section
            sec = f"printer {name}"
            user_input = {
                "name": name,
                "moonraker_uri": moonraker_uri,
                "moonraker_port": moonraker_port,
                "moonraker_api_key": api_key,
                "snapshot_rotation": snapshot_rotation
            }

            # Display the configuration
            Logger.Blank()
            Logger.Info(f"Printer Configuration for '{name}':")
            for key, value in user_input.items():
                Logger.Info(f"  {key}: {value}")

            # Confirm or modify
            confirm = self._ask_input("Is this configuration correct? (y/n/edit)", "y")
            
            if confirm.lower() == 'y':
                # Add the section and values to the config
                write_section.append(sec)
                config.add_section(sec)
                config.set(sec, "moonraker_uri", f"ws://{moonraker_uri}:{moonraker_port}/websocket")
                config.set(sec, "moonraker_api_key", api_key)
                config.set(sec, "snapshot_uri", f"http://{moonraker_uri}/webcam/?action=snapshot")
                config.set(sec, "snapshot_rotation", snapshot_rotation)
                config.set(sec, "ignore_filament_sensors", "")
                
                # Ask about adding another printer
                add_more = self._ask_input("Add another printer? (y/n)", "n")
                if add_more.lower() != "y":
                    break
                user_input = defaults
            
            elif confirm.lower() == 'edit':
                # If user wants to edit, the loop will restart and ask for inputs again
                continue
            
            else:
                # If user doesn't confirm, restart the input process
                continue

    def _ask_input(self, hint: str, default: Optional[str]) -> str:
        while True:
            try:
                if default is not None:
                    hint += f" [Default = {default}]"
                response = input(f"{hint}: ")
                response = response.strip()
                if len(response) == 0:
                    if default is not None:
                        return default
                    Logger.Warn("Empty input, try again.")
                    continue
                
                return response
            except Exception as e:
                Logger.Warn("Invalid input, try again. Logger.Error: "+str(e))