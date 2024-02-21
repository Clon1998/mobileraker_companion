import os
import json
from typing import Any, Optional
from enum import Enum

from .Logging import Logger
from .Paths import Paths


# Indicates the OS type this installer is running on.

class PlatformType(Enum):
    """
    Enumeration representing different types of operating systems.
    
    Attributes:
        DEBIAN (int): Represents the Debian operating system.
        SONIC_PAD (int): Represents the Sonic Pad operating system.
        K1 (int): Represents the K1 operating system (both K1 and K1 Max).
    """
    DEBIAN = 1
    SONIC_PAD = 2
    K1 = 3

class OperationMode(Enum):
    """
    Represents the operation mode for the installer.

    Attributes:
        INSTALL: Install mode.
        # INSTALL_STANDALONE: Install standalone mode.
        UPDATE: Update mode.
        UNINSTALL: Uninstall mode.
    """
    INSTALL = 1
    # INSTALL_STANDALONE = 2
    UPDATE = 3
    UNINSTALL = 4


# This class holds the context of the installer, meaning all of the target vars and paths
# that this instance is using.
# There is a generation system, where generation defines what data is required by when.
# Generation 1 - Must always exist, from the start.
# Generation 2 - Must exist after the discovery phase.
# Generation 3 - Must exist after the configure phase.
class Context:
    """
    The Context class represents the context in which the installation script is running.
    It holds various properties and methods to manage the installation process.
    """
    def __init__(self) -> None:

        #
        # Generation 1
        #

        # This is the repo root. This is common for all instances.
        self._repo_root:Optional[str] = None

        # This is the path to the PY virtual env for Companion. This is common for all instances.
        self._virtual_env:Optional[str] = None

        # This is the user name of the user who launched the install script.
        # Useful because this module is running as a sudo user.
        self._username:Optional[str] = None

        # This is the user home path of the user who launched the install script.
        # Useful because this module is running as a sudo user.
        self._user_home:Optional[str] = None

        # A string containing all of the args the install bash script was launched with.
        self._cmd_args:Optional[str] = None

        # Detected in this installer as we are starting, this indicates what type of OS we are running on.
        self.platform:PlatformType = PlatformType.DEBIAN

        # Parsed from the command line args, if debug should be enabled.
        self.debug:bool = False

        # Parsed from the command line args, if we should show help.
        self.show_help:bool = False

        # Parsed from the command line args, if we should skip sudo actions for debugging.
        self.skip_sudo_actions:bool = False

        # Parsed from the command line args, if set to True, we shouldn't auto select the moonraker instance.
        self.auto_select_moonraker:bool = True

        # Parsed from the command line args, defines how this installer should run.
        self.mode:OperationMode = OperationMode.INSTALL


        #
        # Generation 2
        #

        # This is the full file path to the moonraker config.
        self._moonraker_config_file_path:Optional[str] = None

        # This is the file name of the moonraker service we are targeting.
        self._moonraker_service_file_name:Optional[str] = None

        # self.ObserverDataPath:Optional[str] = None


        #
        # Generation 3
        #

        # Generation 3 - This it the path to the printer data root folder.
        self._printer_data_folder:Optional[str] = None

        # Generation 3 - This it the path to the printer data config folder.
        self._printer_data_config_folder:Optional[str] = None

        # Generation 3 - This it the path to the printer data logs folder.
        self._printer_data_logs_folder:Optional[str] = None

        # Generation 3 - This is the path to the mobileraker systme service file.
        self._service_file_path:Optional[str] = None

        # Generation 3 - This is the port of the moonraker instance we are targeting.
        self._moonraker_port:Optional[int] = None


        # Generation 3 - This is the path to the mobileraker conf file (master).
        self._mobileraker_conf_path:Optional[str] = None
        # Generation 3 - This is the path to the mobileraker conf link, if we linked it to the master.
        self._mobileraker_conf_link:Optional[str] = None

        # Generation 3 - This is the path to the moonraker asvc file.
        self._moonraker_asvc_file_path:Optional[str] = None


    @property
    def is_creality_os(self) -> bool:
        """
        Check if the platform is Creality OS.

        Returns:
            bool: True if the platform is Creality OS, False otherwise.
        """
        return self.platform == PlatformType.SONIC_PAD or self.platform == PlatformType.K1

    @property
    def has_moonraker_config_file_path(self) -> bool:
        """
        Check if the moonraker config file path is set.

        Returns:
            bool: True if the moonraker config file path is set, False otherwise.
        """
        return self._moonraker_config_file_path is not None and len(self._moonraker_config_file_path) > 0
    
    @property
    def has_moonraker_service_file_name(self) -> bool:
        """
        Check if the moonraker service file path is set.

        Returns:
            bool: True if the moonraker service file path is set, False otherwise.
        """
        return self._moonraker_service_file_name is not None and len(self._moonraker_service_file_name) > 0

    @property
    def has_mobileraker_conf_link(self) -> bool:
        """
        Check if the mobileraker conf link is set.

        Returns:
            bool: True if the mobileraker conf link is set, False otherwise.
        """
        return self._mobileraker_conf_link is not None and len(self._mobileraker_conf_link) > 0
    
    @property
    def has_moonraker_asvc_file_path(self) -> bool:
        """
        Check if the moonraker asvc file path is set.

        Returns:
            bool: True if the moonraker asvc file path is set, False otherwise.
        """
        return self._moonraker_asvc_file_path is not None and len(self._moonraker_asvc_file_path) > 0

    # Getters and setters for the properties.
    @property
    def repo_root(self) -> str:
        """
        Get the repo root path.

        Returns:
            str: The repo root path.
        """
        if self._repo_root is None:
            raise AttributeError("Repo root path was not set.")
        return self._repo_root
    
    @repo_root.setter
    def repo_root(self, value:str) -> None:
        """
        Set the repo root path.

        Args:
            value (str): The repo root path.
        """
        self._repo_root = value.strip()
    
    @property
    def virtual_env(self) -> str:
        """
        Get the virtual env path.

        Returns:
            str: The virtual env path.
        """
        if self._virtual_env is None:
            raise AttributeError("Virtual env path was not set.")
        return self._virtual_env
    
    @virtual_env.setter
    def virtual_env(self, value:str) -> None:
        """
        Set the virtual env path.

        Args:
            value (str): The virtual env path.
        """
        self._virtual_env = value.strip()
    
    @property
    def username(self) -> str:
        """
        Get the username.

        Returns:
            str: The username.
        """
        if self._username is None:
            raise AttributeError("Username was not set.")
        return self._username
    
    @username.setter
    def username(self, value:str) -> None:
        """
        Set the username.

        Args:
            value (str): The username.
        """
        self._username = value.strip()

    @property
    def user_home(self) -> str:
        """
        Get the user home path.

        Returns:
            str: The user home path.
        """
        if self._user_home is None:
            raise AttributeError("User home path was not set.")
        return self._user_home
    
    @user_home.setter
    def user_home(self, value:str) -> None:
        """
        Set the user home path.

        Args:
            value (str): The user home path.
        """
        self._user_home = value.strip()

    @property
    def cmd_args(self) -> str:
        """
        Get the command line args.

        Returns:
            str: The command line args.
        """
        if self._cmd_args is None:
            raise AttributeError("Command line args was not set.")
        return self._cmd_args
    
    @cmd_args.setter
    def cmd_args(self, value:str) -> None:
        """
        Set the command line args.

        Args:
            value (str): The command line args.
        """
        self._cmd_args = value.strip()
    
    @property
    def moonraker_config_file_path(self) -> str:
        """
        Get the moonraker config file path.

        Returns:
            str: The moonraker config file path.
        """
        if self._moonraker_config_file_path is None:
            raise AttributeError("Moonraker config file path was not set.")
        return self._moonraker_config_file_path
    
    @moonraker_config_file_path.setter
    def moonraker_config_file_path(self, value:str) -> None:
        """
        Set the moonraker config file path.

        Args:
            value (str): The moonraker config file path.
        """
        self._moonraker_config_file_path = value.strip()

    @property
    def moonraker_service_file_name(self) -> str:
        """
        Get the moonraker service file name.

        Returns:
            str: The moonraker service file name.
        """
        if self._moonraker_service_file_name is None:
            raise AttributeError("Moonraker service file name was not set.")
        return self._moonraker_service_file_name
    
    @moonraker_service_file_name.setter
    def moonraker_service_file_name(self, value:str) -> None:
        """
        Set the moonraker service file name.

        Args:
            value (str): The moonraker service file name.
        """
        self._moonraker_service_file_name = value.strip()

    @property
    def printer_data_folder(self) -> str:
        """
        Get the printer data folder path.

        Returns:
            str: The printer data folder path.
        """
        if self._printer_data_folder is None:
            raise AttributeError("Printer data folder path was not set.")
        return self._printer_data_folder
    
    @printer_data_folder.setter
    def printer_data_folder(self, value:str) -> None:
        """
        Set the printer data folder path.

        Args:
            value (str): The printer data folder path.
        """
        self._printer_data_folder = value.strip()

    @property
    def printer_data_config_folder(self) -> str:
        """
        Get the printer data config folder path.

        Returns:
            str: The printer data config folder path.
        """
        if self._printer_data_config_folder is None:
            raise AttributeError("Printer data config folder path was not set.")
        return self._printer_data_config_folder
    
    @printer_data_config_folder.setter
    def printer_data_config_folder(self, value:str) -> None:
        """
        Set the printer data config folder path.

        Args:
            value (str): The printer data config folder path.
        """
        self._printer_data_config_folder = value.strip()

    @property
    def printer_data_logs_folder(self) -> str:
        """
        Get the printer data logs folder path.

        Returns:
            str: The printer data logs folder path.
        """
        if self._printer_data_logs_folder is None:
            raise AttributeError("Printer data logs folder path was not set.")
        return self._printer_data_logs_folder
    
    @printer_data_logs_folder.setter
    def printer_data_logs_folder(self, value:str) -> None:
        """
        Set the printer data logs folder path.

        Args:
            value (str): The printer data logs folder path.
        """
        self._printer_data_logs_folder = value.strip()

    @property
    def service_file_path(self) -> str:
        """
        Get the service file path.

        Returns:
            str: The service file path.
        """
        if self._service_file_path is None:
            raise AttributeError("Service file path was not set.")
        return self._service_file_path
    
    @service_file_path.setter
    def service_file_path(self, value:str) -> None:
        """
        Set the service file path.

        Args:
            value (str): The service file path.
        """
        self._service_file_path = value.strip()


    @property
    def moonraker_port(self) -> int:
        """
        Get the moonraker port.

        Returns:
            int: The moonraker port.
        """
        if self._moonraker_port is None:
            raise AttributeError("Moonraker port was not set.")
        return self._moonraker_port
    
    @moonraker_port.setter
    def moonraker_port(self, value:int) -> None:
        """
        Set the moonraker port.

        Args:
            value (int): The moonraker port.
        """
        self._moonraker_port = value

    @property
    def mobileraker_conf_path(self) -> str:
        """
        Get the mobileraker conf path.

        Returns:
            str: The mobileraker conf path.
        """
        if self._mobileraker_conf_path is None:
            raise AttributeError("Mobileraker conf path was not set.")
        return self._mobileraker_conf_path

    @mobileraker_conf_path.setter
    def mobileraker_conf_path(self, value:str) -> None:
        """
        Set the mobileraker conf path.

        Args:
            value (str): The mobileraker conf path.
        """
        self._mobileraker_conf_path = value.strip()

    @property
    def mobileraker_conf_link(self) -> str:
        """
        Get the mobileraker conf link.

        Returns:
            str: The mobileraker conf link.
        """
        if self._mobileraker_conf_link is None:
            raise AttributeError("Mobileraker conf link was not set.")
        return self._mobileraker_conf_link
    
    @mobileraker_conf_link.setter
    def mobileraker_conf_link(self, value:str) -> None:
        """
        Set the mobileraker conf link.

        Args:
            value (str): The mobileraker conf link.
        """
        self._mobileraker_conf_link = value.strip()


    @property
    def moonraker_asvc_file_path(self) -> str:
        """
        Get the moonraker asvc file path.

        Returns:
            str: The moonraker asvc file path.
        """
        if self._moonraker_asvc_file_path is None:
            raise AttributeError("Moonraker asvc file path was not set.")
        return self._moonraker_asvc_file_path
    
    @moonraker_asvc_file_path.setter
    def moonraker_asvc_file_path(self, value:str) -> None:
        """
        Set the moonraker asvc file path.

        Args:
            value (str): The moonraker asvc file path.
        """
        self._moonraker_asvc_file_path = value.strip()

    @staticmethod
    def setup(json_args: str):
        """
        Bootstrap the context object from JSON arguments.

        Args:
            json_args (str): JSON string containing the arguments.

        Returns:
            Context: The initialized context object.

        Raises:
            Exception: If there is an error parsing the JSON arguments.
        """
        Logger.Debug("Found CMD config: " + json_args)
        try:
            args = json.loads(json_args)
            context = Context()
            context.repo_root = args["REPO_DIR"]
            context.virtual_env = args["ENV_DIR"]
            context.username = args["USERNAME"]
            context.user_home = args["USER_HOME"]
            context.cmd_args = args["CMD_LINE_ARGS"]
            return context
        except Exception as e:
            Logger.Error(f"Failed to parse bootstrap json args. args string: `{json_args}`")
            raise e


    def validate_phase_one(self) -> None:
        """
        Validates the required environment variables and command line arguments for phase one of the installation process.
        
        Raises:
            AttributeError: If any of the required environment variables are not found.
        """
        
        error = "Required Env Var %s was not found; make sure to run the install.sh script to begin the installation process"
        self._validate_path(self._repo_root, error % "REPO_DIR")
        self._validate_path(self._virtual_env, error % "ENV_DIR")
        self._validate_path(self._user_home, error % "USER_HOME")
        self._validate_property(self._username, error % "USERNAME")

        # Can be an empty string, but not None.
        if self._cmd_args is None:
            raise AttributeError(error % "CMD_LINE_ARGS")
        
    def validate_phase_two(self) -> None:
        """
        Validates the configuration in phase two of the installation process.
        
        Raises:
            ValueError: If the mode is INSTALL_STANDALONE and the platform is not Debian based.
        """
        
        self._validate_path(self._moonraker_config_file_path, "Required config var Moonraker Config File Path was not found")
        self._validate_property(self._moonraker_service_file_name, "Required config var Moonraker Service File Name was not found")


    def validate_phase_three(self) -> None:
        """
        Validates the configuration in phase three of the installation process.
        """
        error = "Required config var %s was not found"

        self._validate_path(self._printer_data_folder, error % "Printer Data Folder")
        self._validate_path(self._printer_data_config_folder, error % "Printer Data Config Folder")
        self._validate_path(self._printer_data_logs_folder, error % "Printer Data Logs Folder")
        self._validate_property(self._moonraker_port, error % "Moonraker Port")
        # This path wont exist on the first install, because it won't be created until the end of the install.
        self._validate_property(self._service_file_path, error % "Service File Path")
        self._validate_property(self._mobileraker_conf_path, error % "Mobileraker Conf Path")
        # Var self._mobileraker_conf_link can be null for K1 or if the instance is the master instance (We did not create one)


    def parse_bash_args(self):
        """
        Parses the command line arguments passed to the install script (Not this python installer).

        The format of the command line arguments is:
        install.sh <moonraker config file path> <moonraker service file path> -other -args

        If only one file path is given, it is assumed to be the config file path.

        Raises:
            AttributeError: If an unknown argument is found.
            AttributeError: If the required environment variable CMD_LINE_ARGS is not found.
        """

        # We must have a string, indicating the ./install script passed the var.
        # But it can be an empty string, that's fine.
        if self._cmd_args is None:
            raise AttributeError("Required Env Var CMD_LINE_ARGS was not found; make sure to run the install.sh script to begin the installation process")

        # Handle the original cmdline args.
        # The format is <moonraker config file path> <moonraker service file path> -other -args
        # Where both file paths are optional, but if only one is given, it's assumed to be the config file path.
        args = self._cmd_args.split(' ')
        for a in args:
            # Ensure there's a string and it's not empty.
            # If no args are passed, there will be one empty string after the split.
            if isinstance(a, str) is False or len(a) == 0:
                continue

            # Handle and flags passed.
            if a[0] == '-':
                raw_arg = a[1:].lower()
                if raw_arg == "debug":
                    # Enable debug printing.
                    self.debug = True
                    Logger.enable_debug_logging()
                elif raw_arg == "help" or raw_arg == "usage" or raw_arg == "h":
                    self.show_help = True
                elif raw_arg == "skipsudoactions":
                    Logger.Warn("Skipping sudo actions. ! This will not result in a valid install! ")
                    self.skip_sudo_actions = True
                elif raw_arg == "noatuoselect":
                    Logger.Info("Disabling Moonraker instance auto selection.")
                    self.auto_select_moonraker = False
                # elif raw_arg == "update":
                #     Logger.Info("Setup running in update mode.")
                #     self.mode = OperationMode.UPDATE
                elif raw_arg == "uninstall":
                    Logger.Info("Setup running in uninstall mode.")
                    self.mode = OperationMode.UNINSTALL
                else:
                    raise AttributeError("Unknown argument found. Use install.sh -help for options.")

            # If there's a raw string, assume its a config path or service file name.
            # We assume the first string is the config file path, and the second is the service file name.
            else:
                if not self.has_moonraker_config_file_path:
                    self.moonraker_config_file_path= a
                    Logger.Debug("Moonraker config file path found as argument:"+a)
                elif not self.has_moonraker_service_file_name:
                    self.moonraker_service_file_name = a
                    Logger.Debug("Moonraker service file name found as argument:"+a)
                else:
                    raise AttributeError("Unknown argument found. Use install.sh -help for options.")


    def _validate_path(self, path:Optional[str], error:str):
        if path is None or os.path.exists(path) is False:
            raise ValueError(error)


    def _validate_property(self, s:Optional[Any], error:str):
        if s is None:
            raise ValueError(error)
        
        if isinstance(s, str) and len(s) == 0:
            raise ValueError(error)
        


    def identify_platform(self):
        """
        Identifies the platform based on the operating system.

        This method checks the operating system to determine the platform type.
        It looks for specific files (/etc/os-release and /etc/openwrt_release)
        and their contents to identify the platform.

        Raises:
            AttributeError: If the platform is detected but the data path does not exist.

        Returns:
            None
        """

        # For the k1 and k1 max, we look for the "buildroot" OS.
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r", encoding="utf-8") as osInfo:
                lines = osInfo.readlines()
                for l in lines:
                    if "ID=buildroot" in l:
                        # If we find it, make sure the user data path is where we expect it to be, and we are good.
                        if os.path.exists(Paths.CrealityOsUserDataPath_K1):
                            self.platform = PlatformType.K1
                            return
                        raise AttributeError("We detected a K1 or K1 Max OS, but can't determine the data path.")

        # For the Sonic Pad, we look for the openwrt os
        if os.path.exists("/etc/openwrt_release"):
            with open("/etc/openwrt_release", "r", encoding="utf-8") as osInfo:
                lines = osInfo.readlines()
                for l in lines:
                    if "sonic" in l:
                        # If we find it, make sure the user data path is where we expect it to be, and we are good.
                        if os.path.exists(Paths.CrealityOsUserDataPath_SonicPad):
                            self.platform = PlatformType.SONIC_PAD
                            return
                        raise AttributeError("We detected a Sonic Pad, but can't determine the data path.")

        # The OS is debian
        self.platform = PlatformType.DEBIAN
        return
