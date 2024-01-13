import os

from .Util import Util
from .Logging import Logger
from .Context import Context, PlatformType
from .Paths import Paths
from typing import List, Optional

COMMAND_FLAG_TERM = " -c "

class ServiceFileConfigPathPair:
    """
    Represents a pair of service file and moonraker config file path.
    """
    def __init__(self, service_file, moonraker_config_file_path) -> None:
        self.moonraker_service_file_name = service_file # Name of the service file.
        self.moonraker_config_file_path = moonraker_config_file_path # Absolute path to the moonraker config file.


# This class is used for the hardest part of the install, mapping the moonraker service instances to the moonraker config files.
# I wish this was easier, but it's quite hard because the service files don't exactly reference the moonraker.conf.
# On top of that, there's variations in how the config files are created for different Klipper based systems.
#
# TODO - One thing we could do is use systemctl status moonraker<id> and check the actual cmd line args. That will resolve all of the macros
# and we should be able to parse out the -d flag for the older klipper_config flags.
class Discovery:
    """
    The Discovery class is responsible for finding Moonraker instances and selecting the appropriate configuration.
    """
    
    def start(self, context:Context):
        """
        Starts the discovery process to find Moonraker instances and select the appropriate configuration.

        Args:
            context (Context): The context object containing the necessary information for the discovery process.

        Raises:
            Exception: If no Moonraker instances could be detected on the device.

        Returns:
            None
        """
        Logger.Debug("Starting discovery.")

        # Print all of the file options, so we have them for debugging.
        # We always print these, so they show up in the log file.
        self._print_debug(context)

        # If we were passed a valid moonraker config file and service name, we don't need to do anything else.
        if context.has_moonraker_config_file_path:
            if os.path.exists(context.moonraker_config_file_path):
                if context.has_moonraker_service_file_name:
                    Logger.Info(f"Installer script was passed a valid Moonraker config and service name. [{context.moonraker_service_file_name}:{context.moonraker_config_file_path}]")
                    return


        # If we are here, we either have no service file name but a config path, or neither.
        discovery_result = []
        if context.platform == PlatformType.SONIC_PAD:
            # For the Sonic Pad, we know exactly where the files are, so we don't need to do a lot of searching.
            discovery_result = self._discover_pairings_for_sonic_pad()
        elif context.platform == PlatformType.K1:
            # For the K1 and K1 max, we know exactly where the files are, so we don't need to do a lot of searching.
            discovery_result = self._discover_pairings_for_k1()
        else:
            # To start, we will enumerate all moonraker service files we can find and their possible moonraker config parings.
            # For details about why we need these, read the readme.py file in this module.
            discovery_result = self._discover_pairings_for_native()

        # Ensure we found something.
        if discovery_result is None or len(discovery_result) == 0:
            raise ValueError("No moonraker instances could be detected on this device.")

        # Now that we have list of all moonraker config and service file pairs, match the moonraker config passed in, if there is one.
        if context.moonraker_config_file_path is not None:
            for p in discovery_result:
                if p.moonraker_config_file_path == context.moonraker_config_file_path:
                    # Update the context and return!
                    context.moonraker_service_file_name = p.moonraker_service_file_name
                    Logger.Info(f"The given moonraker config was found with a service file pair. [{p.moonraker_service_file_name}:{p.moonraker_config_file_path}]")
                    return
            Logger.Warn(f"Moonraker config path [{context.moonraker_config_file_path}] was given, but no found pair matched it.")

        # If there is just one pair, always use it.
        if len(discovery_result) == 1 and context.auto_select_moonraker:
            # Update the context and return!
            context.moonraker_config_file_path = discovery_result[0].moonraker_config_file_path
            context.moonraker_service_file_name = discovery_result[0].moonraker_service_file_name
            Logger.Info(f"Only one moonraker instance was found, so we are using it! [{context.moonraker_service_file_name}:{context.moonraker_config_file_path}]")
            return





        # We found multiple configs, let the user choose for which he wants to add the companion. Note that a single companion instance will serve all printers.
        Logger.Blank()
        Logger.Blank()
        Logger.Warn("Multiple Moonraker Instances Detected.")
        Logger.Warn("Mobileraker Companion can manage multiple printers.")
        Logger.Warn("The installer will either add the new printer to an existing instance or install a new one.")
        Logger.Blank()
        if context.is_creality_os:
            Logger.Header("Sonic Pad/K1 Users - If you're only using one printer, select number 1")
            Logger.Blank()

        # Print the config files found.
        count = 0
        for p in discovery_result:
            count += 1
            Logger.Info(F"  {str(count)}) {p.moonraker_service_file_name} [{p.moonraker_config_file_path}]")
        Logger.Blank()

        # Ask the user which number they want.
        respond_index = -1
        while True:
            try:
                response = input("Enter the number for the config you would like to setup now: ")
                response = response.lower().strip()
                # Parse the input and -1 it, so it aligns with the array length.
                idx = int(response.lower().strip()) - 1
                if idx >= 0 and idx < len(discovery_result):
                    respond_index = idx
                    break
                Logger.Warn("Invalid number selection, try again.")
            except Exception as e:
                Logger.Warn("Invalid input, try again. Logger.Error: "+str(e))

        # We have a selection, use it!
        context.moonraker_config_file_path = discovery_result[respond_index].moonraker_config_file_path
        context.moonraker_service_file_name = discovery_result[respond_index].moonraker_service_file_name
        Logger.Info(f"Moonraker instance selected! [{context.moonraker_service_file_name}:{context.moonraker_config_file_path}]")
        return

    # Note this must return the same result list as _CrealityOsFindAllServiceFilesAndPairings
    def _discover_pairings_for_native(self) -> list:
        # Look for any service file that matches moonraker*.service.
        # For simple installs, there will be one file called moonraker.service.
        # For more complex setups, we assume it will use the kiauh naming system, of moonraker-<name or number>.service
        service_files = self._scan_files(Paths.SystemdServiceFilePath, "moonraker", ".service")

        # Based on the possible service files, see what moonraker config files we can match.
        results = []
        for service_file in service_files:
            # Try to find a matching moonraker config file, based off the service file.
            config_path = self._discover_moonraker_config(service_file)
            if config_path is None:
                Logger.Debug(f"Moonraker config file not found for service file [{service_file}]")
                try:
                    with open(service_file, "r", encoding="utf-8") as file:
                        lines = file.readlines()
                        for l in lines:
                            Logger.Debug(l)
                except Exception:
                    pass
            else:
                Logger.Debug(f"Moonraker service [{service_file}] matched to [{config_path}]")
                # Only return fully matched pairs
                # Pair the service file and the moonraker config file path.
                results.append(ServiceFileConfigPathPair(os.path.basename(service_file), config_path))
        return results


    # A special function for Sonic Pad installs, since the location of the printer data is much more well known.
    # Note this must return the same result list as _FindAllServiceFilesAndPairings
    def _discover_pairings_for_sonic_pad(self):
        # For the Sonic Pad, we know the name of the service files and the path.
        # They will be named moonraker_service and moonraker_service.*
        service_files = self._scan_files(Paths.CrealityOsServiceFilePath, "moonraker_service")

        # Based on the possible service files, see what moonraker config files we can match.
        results = []
        for service_file in service_files:
            # Parse out the service number for each file. We know the exact file format.
            # If it has a ., it's .<number>. No . means it's the base printer.
            file_name = os.path.basename(service_file)
            suffix = ""
            if "." in file_name:
                suffix = file_name.split(".")[1]

            moonraker_config_file_path = f"{Paths.CrealityOsUserDataPath_SonicPad}/printer_config{suffix}/moonraker.conf"
            if os.path.exists(moonraker_config_file_path):
                Logger.Debug(f"Found moonraker config file {moonraker_config_file_path}")
                results.append(ServiceFileConfigPathPair(file_name, moonraker_config_file_path))
            else:
                # Since we should find these, warn if we don't.
                Logger.Warn(f"Failed to find moonraker config file {moonraker_config_file_path}")
        return results


    # A special function for K1 and K1 max installs.
    # Note this must return the same result list as _FindAllServiceFilesAndPairings
    def _discover_pairings_for_k1(self):

        # The K1 doesn't have moonraker by default, but most users use a 3rd party script to install it.
        # For now we will just assume the setup that the script produces.
        service_file = None
        config_file_path = None

        # The service file should be something like this "/etc/init.d/S56moonraker_service"
        for file_name in os.listdir(Paths.CrealityOsServiceFilePath):
            full_path = os.path.join(Paths.CrealityOsServiceFilePath, file_name)
            if os.path.isfile(full_path) and os.path.islink(full_path) is False:
                if "moonraker" in file_name.lower():
                    Logger.Debug(f"Found service file: {full_path}")
                    service_file = file_name
                    break

        # The moonraker config file should be here: "/usr/data/printer_data/config/moonraker.conf"
        config_file_path = "/usr/data/printer_data/config/moonraker.conf"
        if os.path.isfile(config_file_path):
            Logger.Debug(f"Found moonraker config file: {config_file_path}")
        else:
            config_file_path = None

        # Check if we are missing either. If so, the user most likely didn't install Moonraker.
        if config_file_path is None or service_file is None:
            Logger.Blank()
            Logger.Blank()
            Logger.Blank()
            Logger.Header("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            Logger.Error( "                                  Moonraker Not Found!                                    ")
            Logger.Warn(  "      The K1 and K1 Max don't have Moonraker or a web frontend installed by default.      ")
            Logger.Warn(  " Moonraker and a frontend like Fluidd or Mainsail are required for Mobileraker Companion. ")
            Logger.Blank()
            Logger.Purple("             Octoeverywhere has a guide to help you install Moonraker and a UI.           ")
            Logger.Purple("                            Follow this link: https://oe.ink/s/k1                         ")
            Logger.Purple("                        Step 4 `Install Moonraker, Fluidd, and Mainsail`                  ")
            Logger.Blank()
            Logger.Header("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            Logger.Blank()
            Logger.Blank()
            Logger.Blank()
            raise Exception("Moonraker isn't installed on this K1 or K1 Max. Use the guide on this link to install it: https://oe.ink/s/k1 until step 4 `Install Moonraker, Fluidd, and Mainsail`")

        return [ ServiceFileConfigPathPair(service_file, config_file_path) ]


    def _discover_moonraker_config(self, service_file_path:str) -> Optional[str]:
        """
        Searches for the moonraker configuration file path associated with the given service file path.
        It does that by using the service file to try to find the moonraker configuration file path.

        Args:
            service_file_path (str): The path to the service file.

        Returns:
            Optional[str]: The path to the moonraker configuration file if found, None otherwise.
        """
        try:
            # Using the service file to try to find the moonraker config that's associated.
            Logger.Debug(f"Searching for moonraker config for {service_file_path}")
            with open(service_file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
                for l in lines:
                    # Search for lines that might indicate the config path.
                    # For newer setups, we expect to see this EnvironmentFile line in the service.
                    # Ex EnvironmentFile=/home/pi/printer_1_data/systemd/moonraker.env
                    #
                    # For some older setups, we will find lines like these in the service file.
                    # Environment=MOONRAKER_CONF=/home/mks/klipper_config/moonraker.conf
                    # Environment=MOONRAKER_LOG=/home/mks/klipper_logs/moonraker.log
                    #
                    # Even older setups might also have:
                    # [ExecStart=/home/pi/moonraker-env/bin/python /home/pi/moonraker/moonraker/moonraker.py -c /home/pi/klipper_config/moonraker.conf -l /home/pi/klipper_logs/moonraker.log
                    #
                    # The logic below must be able to handle getting the path out of any of these!
                    #
                    if "moonraker.env" in l.lower() or "moonraker.conf" in l.lower():
                        Logger.Debug("Found possible path line: "+l)

                        # Try to parse the target path
                        # In some cases this path will be the full moonraker config file path, while in other cases it might be the printer data root folder, systemd folder, config folder.
                        target_path = ""
                        if l.lower().find(COMMAND_FLAG_TERM) != -1:
                            #
                            # Handle the -c service file line.
                            #
                            flag_start = l.lower().find(COMMAND_FLAG_TERM) + len(COMMAND_FLAG_TERM)

                            # Truncate the string after the known " -c ", so we can strip any more leading spaces off the string before trying to find the end.
                            string_after_flag_start = l[flag_start:].strip()

                            # Now find the next space, which will be the next cmd line arg part.
                            flag_end = string_after_flag_start.find(' ')
                            if flag_end == -1:
                                # This is the end of the command line string.
                                flag_end = len(string_after_flag_start)

                            # Get the parsed moonraker path.
                            target_path = string_after_flag_start[:flag_end]
                            Logger.Debug(f"Parsed moonraker config path is [{target_path}] - '-c' parse.")
                        else:
                            #
                            # Handle the Environment* path
                            #
                            # When found, try to file the config path.
                            # It's important to use rfind, to find the last = for cases like
                            # Environment=MOONRAKER_CONF=/home/mks/klipper_config/moonraker.conf
                            equals_pos = l.rfind('=')
                            if equals_pos == -1:
                                continue
                            # Move past the = sign.
                            equals_pos += 1

                            # Find the end of the path.
                            path_end = l.find(' ', equals_pos)
                            if path_end == -1:
                                path_end = len(l)

                            # Get the file path.
                            # Sample path /home/pi/printer_1_data/systemd/moonraker.env
                            target_path = l[equals_pos:path_end]
                            target_path = target_path.strip()
                            Logger.Debug(f"Parsed moonraker config path is [{target_path}] - From env parse.")

                        # Once the path is parsed, it can be the full path to the moonraker config file, the path to the printer data folder, a path to the printer data systemd folder, or config folder.
                        # We must handle all of these cases!

                        # First, test if the moonraker config is in this parent path.
                        # This is needed for the case where the path is the full moonraker config file path, the parent will be the dir and then we will find the file.
                        #
                        # For the second case [Environment=MOONRAKER_CONF=/home/mks/klipper_config/moonraker.conf] we do expect the config to be in this folder
                        # Or for the case of  [ExecStart=/home/pi/moonraker-env/bin/python /home/pi/moonraker/moonraker/moonraker.py -c /home/pi/klipper_config/moonraker.conf -l /home/pi/klipper_logs/moonraker.log
                        search_path = Util.parent_dir(target_path)
                        moonraker_config_path = self._scan_path_for_moonraker_config(search_path)
                        if moonraker_config_path is not None:
                            Logger.Debug(f"Moonraker config found in {search_path}")
                            return moonraker_config_path

                        # Move to the parent and look explicitly in the config folder, if there is one, this is where we expect to find it.
                        # We do this to prevent finding config files in other printer_data folders, like backup.
                        search_path = Util.parent_dir(Util.parent_dir(target_path))
                        search_path = os.path.join(search_path, "config")
                        if os.path.exists(search_path):
                            moonraker_config_path = self._scan_path_for_moonraker_config(search_path)
                            if moonraker_config_path is not None:
                                Logger.Debug(f"Moonraker config found in {search_path}")
                                return moonraker_config_path

                        # If we still didn't find it, move the printer_data root, and look one last time.
                        search_path = Util.parent_dir(Util.parent_dir(target_path))
                        moonraker_config_path = self._scan_path_for_moonraker_config(search_path)
                        if moonraker_config_path is not None:
                            Logger.Debug(f"Moonraker config found from printer data root {search_path}")
                            return moonraker_config_path

                        Logger.Debug(f"No matching config file was found for line [{l}] in service file, looking for more lines...")
        except Exception as e:
            Logger.Warn(f"Failed to read service config file for config find.: {service_file_path} {str(e)}")
        return None


    # Recursively looks from the root path for the moonraker config file.
    def _scan_path_for_moonraker_config(self, path, depth = 0):
        """
        Recursively scans the given path and its subdirectories to find the moonraker.conf file.
        
        Args:
            path (str): The path to start the search from.
            depth (int, optional): The current depth of recursion. Defaults to 0.
        
        Returns:
            str or None: The full absolute path of the moonraker.conf file if found, None otherwise.
        """

        if depth > 20:
            return None

        try:
            # Get all files and dirs in this dir
            # This throws if the path doesn't exist.
            files: List[str] = os.listdir(path)

            # First, check all of the files.
            dirs_to_search: List[str] = []
            for file in files:
                file_path = os.path.join(path, file)
                normalized_file = file.lower()
                # If we find a dir, cache it, so we check all of the files in this folder first.
                # This is important, because some OS images like RatOS have moonraker.conf files in nested folders
                # that we don't want to find first.
                if os.path.isdir(file_path):
                    dirs_to_search.append(file)
                # If it's a file, and not a link test if it matches our target.
                elif os.path.isfile(file_path) and os.path.islink(file_path) is False:
                    # We use an exact match, to prevent things like moonraker.conf.backup from matching, which is common.
                    if normalized_file == "moonraker.conf":
                        return file_path

            # We didn't find a matching file, process the sub dirs.
            for file in dirs_to_search:
                file_path = os.path.join(path, file)
                normalized_file = file.lower()
                # Ignore backup folders
                if normalized_file == "backup":
                    continue
                # For RatOS (a prebuilt pi image) there's a folder named RatOS in the config folder.
                # That folder is a git repo for the RatOS project, and it contains a moonraker.conf, but it's not the one we should target.
                # The community has told us to target the moonraker.conf in the ~/printer_data/config/
                # Luckily, this is quite a static image, so there aren't too many variants of it.
                if normalized_file == "ratos":
                    continue
                temp = self._scan_path_for_moonraker_config(file_path, depth + 1)
                if temp is not None:
                    return temp
        except Exception as e:
            # This is mostly used to catch os.listdir which might throw.
            Logger.Debug(f"Failed to _FindMoonrakerConfigFromPath from path {path}: "+str(e))

        # We didn't find it.
        return None


    def _scan_files(self, path:str, prefix:Optional[str] = None, suffix:Optional[str] = None, depth:int = 0) -> List[str]:
        """
        Recursively scans files in a given directory and its subdirectories.
        
        Args:
            path (str): The path of the directory to scan.
            prefix (Optional[str]): Optional prefix filter for file names. Only files with names starting with the prefix will be included.
            suffix (Optional[str]): Optional suffix filter for file names. Only files with names ending with the suffix will be included.
            depth (int): The current depth of the recursion. Used to limit the depth of the scan.
        
        Returns:
            List[str]: A list of file paths that match the specified filters.
        """
        results = []
        if depth > 10:
            return results
        # Use sorted, so the results are in a nice user presentable order.
        contents = sorted(os.listdir(path))
        for file_name in contents:
            full_path = os.path.join(path, file_name)
            # Search sub folders
            if os.path.isdir(full_path):
                tmp = self._scan_files(full_path, prefix, suffix, depth + 1)
                if tmp is not None:
                    for t in tmp:
                        results.append(t)
            # Only accept files that aren't links, since there are a lot of those in the service files.
            elif os.path.isfile(full_path) and os.path.islink(full_path) is False:
                include = True
                if prefix is not None:
                    include = file_name.lower().startswith(prefix)
                if include is True and suffix is not None:
                    include = file_name.lower().endswith(suffix)
                if include:
                    results.append(full_path)
        return results


    def _print_debug(self, context:Context):
        """
        Prints debug information related to service files and config files.

        Args:
            context (Context): The context object containing relevant information.

        Returns:
            None
        """
        # Print all service files.
        Logger.Debug("Discovery - Service Files")
        self._print_path(Paths.service_file_folder(context))

        # We want to print files that might be printer data folders or names of other folders on other systems.
        Logger.Blank()
        Logger.Debug("Discovery - Config Files In Home Path")
        if context.is_creality_os:
            if os.path.exists(Paths.CrealityOsUserDataPath_SonicPad):
                self._print_path(Paths.CrealityOsUserDataPath_SonicPad, ".conf")
            if os.path.exists(Paths.CrealityOsUserDataPath_K1):
                self._print_path(Paths.CrealityOsUserDataPath_K1, ".conf")
        else:
            self._print_path(context.user_home, ".conf")

    def _print_path(self, path:str, targetSuffix:Optional[str] = None, depth = 0, depthStr = " "):
        """
        Recursively prints the file or folder paths in the given directory.

        Args:
            path (str): The directory path to start the search from.
            targetSuffix (Optional[str]): The suffix of the files to be printed. If None, all files will be printed. Default is None.
            depth (int): The current depth level of the recursion. Default is 0.
            depthStr (str): The string representation of the current depth level. Default is " ".

        Returns:
            None
        """
        if depth > 5:
            return
        # Use sorted, so the results are in a nice user presentable order.
        fileAndDirList = sorted(os.listdir(path))
        for fileOrDirName in fileAndDirList:
            fullFileOrDirPath = os.path.join(path, fileOrDirName)
            # Print the file or folder if it starts with the target suffix.
            if targetSuffix is None or fileOrDirName.lower().endswith(targetSuffix):
                Logger.Debug(f"{depthStr}{fullFileOrDirPath}")
            # Look through child folders.
            if os.path.isdir(fullFileOrDirPath):
                self._print_path(fullFileOrDirPath, targetSuffix, depth + 1, depthStr + "  ")
