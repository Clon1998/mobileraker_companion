import configparser
import os

from installer.Paths import Paths

from .Util import Util
from .Logging import Logger
from .Context import Context, PlatformType


class Configure:

    # This is the common service prefix (or word used in the file name) we use for all of our service file names.
    # This MUST be used for all instances running on this device, both local plugins and companions.
    # This also MUST NOT CHANGE, as it's used by the Updater logic to find all of the locally running services.
    SERVICE_NAME = "mobileraker"

    def run(self, context:Context):
        """
        Runs the configuration process based on the given context.

        Args:
            context (Context): The context object containing the configuration parameters.

        Returns:
            None
        """
        Logger.Header("Starting configuration...")

        Logger.Debug(f"Moonraker Service File Name: {context.moonraker_service_file_name}")

        # Get printer data root and config folder

        # TODO: MR does not need a observer config file, it's only for the observer.
        if context.platform == PlatformType.SONIC_PAD:
            # ONLY FOR THE SONIC PAD, we know the folder setup is different.
            # The user data folder will have /mnt/UDISK/printer_config<number> where the config files are and /mnt/UDISK/printer_logs<number> for logs.
            # Use the normal folder for the config files.
            context.printer_data_config_folder = Util.parent_dir(context.moonraker_config_file_path)

            # There really is no printer data folder, so make one that's unique per instance.
            # So based on the config folder, go to the root of it, and them make the folder "mobileraker_data"
            context.printer_data_folder = os.path.join(Util.parent_dir(context.printer_data_folder), "mobileraker_data")
            Util.ensure_dir_exists(context.printer_data_folder, context, True)
        else:
            # For now we assume the folder structure is the standard Klipper folder config,
            # thus the full moonraker config path will be .../something_data/config/moonraker.conf
            # Based on that, we will define the config folder and the printer data root folder.
            # Note that the K1 uses this standard folder layout as well.
            context.printer_data_config_folder = Util.parent_dir(context.moonraker_config_file_path)
            context.printer_data_folder = Util.parent_dir(context.printer_data_config_folder)
            Logger.Debug("Printer data folder: "+context.printer_data_folder)


        # This is the name of our service we create. If the port is the default port, use the default name.
        # Otherwise, add the port to keep services unique.
        if context.platform == PlatformType.SONIC_PAD:
            # For Sonic Pad, since the service is setup differently, follow the conventions of it.
            # Both the service name and the service file name must match.
            # The format is <name>_service<number>
            # NOTE! For the Update class to work, the name must start with Configure.SERVICE_NAME
            context.service_file_path = os.path.join(Paths.CrealityOsServiceFilePath,  f"{Configure.SERVICE_NAME}_service")
        elif context.platform == PlatformType.K1:
            # For the k1, there's only ever one moonraker and we know the exact service naming convention.
            # Note we use 76 to ensure we start after moonraker.
            context.service_file_path = os.path.join(Paths.CrealityOsServiceFilePath, f"S66{Configure.SERVICE_NAME}_service")
        else:
            # For normal setups, use the convention that Klipper users
            # NOTE! For the Update class to work, the name must start with Configure.SERVICE_NAME
            context.service_file_path = os.path.join(Paths.SystemdServiceFilePath, f"{Configure.SERVICE_NAME}.service")

        # There's not a great way to find the log path from the config file, since the only place it's located is in the systemd file.

        # First, we will see if we can find a named folder relative to this folder.
        context.printer_data_logs_folder = os.path.join(context.printer_data_folder, "logs")
        if os.path.exists(context.printer_data_logs_folder) is False:
            # Try an older path
            context.printer_data_logs_folder = os.path.join(context.printer_data_folder, "klipper_logs")
            if os.path.exists(context.printer_data_logs_folder) is False:
                # Try the path Creality OS uses, something like /mnt/UDISK/printer_logs<number>
                context.printer_data_logs_folder = os.path.join(Util.parent_dir(context.printer_data_config_folder), "printer_logs")
                if os.path.exists(context.printer_data_logs_folder) is False:
                    # Failed, make a folder in the printer data root.
                    context.printer_data_logs_folder = os.path.join(context.printer_data_folder, "mobileraker-logs")
                    # Create the folder and force the permissions so our service can write to it.
                    Util.ensure_dir_exists(context.printer_data_logs_folder, context, True)

        # Setup default moonraker port
        self._discover_moonraker_port(context)

        # Report
        Logger.Info(f'Configured. Service File Path: {context.service_file_path}, Config Dir: {context.printer_data_config_folder}, Logs: {context.printer_data_logs_folder}')

    def _discover_moonraker_port(self, context:Context):
        """
        Attempts to discover the port moonraker is running on by reading the config file.

        Args:
            context (Context): The context object containing the configuration parameters.

        Returns:
            None
        """

        # First we try to read the port from the moonraker conf
        if os.path.exists(context.moonraker_config_file_path):
            config = configparser.ConfigParser()
            config.read(context.moonraker_config_file_path)

            port = config.getint("server", "port", fallback=None)
            if port is not None:
                Logger.Info(f"Found moonraker port {port} in config file.")
                context.moonraker_port = port
                return
        
        Logger.Info("Failed to find moonraker port in config file, using default port.")
        # Moonraker default port is 7125
        context.moonraker_port = 7125