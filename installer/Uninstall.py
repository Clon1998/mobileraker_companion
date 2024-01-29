import os
import shutil

from installer import Config

from .Context import Context, PlatformType
from .Logging import Logger
from .Configure import Configure
from .Paths import Paths
from .Util import Util

class Uninstall:

    def uninstall(self, context:Context):

        Logger.Blank()
        Logger.Blank()
        Logger.Header("You're about to uninstall Mobileraker Companion.")
        Logger.Blank()
        r =     input("Are you want to uninstall? [y/n]")
        r = r.lower().strip()
        if r != "y":
            Logger.Info("Uninstall canceled.")
            Logger.Blank()
            return
        Logger.Blank()
        Logger.Blank()
        Logger.Header("Starting Mobileraker Companion uninstall")

        # Since all service names must use the same identifier in them, we can find any services using the same search.
        found_services = []
        service_path_content = sorted(os.listdir(Paths.service_file_folder(context)))
        for file in service_path_content:
            Logger.Debug(f" Searching for Companion services to remove, found: {file}")
            if Configure.SERVICE_NAME in file.lower():
                found_services.append(file)

        if len(found_services) == 0:
            Logger.Warn("No companion was found to remove")
            return
        Logger.Info(f"Found {len(found_services)} services to remove.")

        # TODO - We need to cleanup more, but for now, just make sure any services are shutdown.
        Logger.Info("Stopping service...")
        for service in found_services:
            service_file = os.path.join(Paths.service_file_folder(context), service)
            os.remove(service_file)
            if context.platform == PlatformType.SONIC_PAD:
                Logger.Debug(f"Full service path: {service_file}")
                Logger.Info(f"Stopping and deleting {service}...")
                Util.run_shell_command(f"{service_file} stop", False)
                Util.run_shell_command(f"{service_file} disable", False)
                self._delete_if_exists(service_file)
            elif context.platform == PlatformType.K1:
                Logger.Debug(f"Full service path: {service_file}")
                Logger.Info(f"Stopping and deleting {service}...")
                Util.run_shell_command(f"{service_file} stop", False)
                Util.run_shell_command("ps -ef | grep 'mobileraker' | grep -v grep | awk '{print $1}' | xargs -r kill -9", False)
                self._delete_if_exists(service_file)
            elif context.platform == PlatformType.DEBIAN:
                Logger.Info(f"Stopping and deleting {service}...")
                Util.run_shell_command("systemctl stop "+service, False)
                Util.run_shell_command("systemctl disable "+service, False)
                Util.run_shell_command("systemctl daemon-reload")
                self._delete_if_exists(service_file)
            else:
                raise Exception("This OS type doesn't support uninstalling at this time.")

        # For now, systems that have fixed setups, set will remove files
        # TODO - We need to do a total cleanup of all files.
        if context.platform == PlatformType.K1:
            self._cleanup_k1()
        elif context.platform == PlatformType.SONIC_PAD:
            self._cleanup_sonic_pad()
        elif context.platform == PlatformType.DEBIAN:
            self._cleanup_debian(context)
        
        
        # Common cleanup for all platforms.
    
        # Delete the installer log file.
        self._delete_if_exists(os.path.join(Util.parent_dir(context.repo_root), 'mr-companion-installer.log') )
        # Delete the python virtual env.
        self._delete_if_exists(context.virtual_env)
        # Delete the repo root.
        self._delete_if_exists(context.repo_root)

        Logger.Blank()
        Logger.Blank()
        Logger.Header("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        Logger.Info(  "           Mobileraker Uninstall Complete              ")
        Logger.Info(  "     We will miss you, please come back anytime!       ")
        Logger.Header("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        Logger.Blank()
        Logger.Blank()


    def _cleanup_debian(self, context:Context):
        # Cleanup the companion config file for each printer.

        # Show a formatted message to the user that states, that he will have to manually remove the config file.
        Logger.Blank()
        Logger.Warn("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        Logger.Warn("  The companion config file for each printer will not be removed, you must do this manually.")
        Logger.Warn("  The config file is normally located at the same location as the moonraker config file.")
        Logger.Warn("  It will be named something like: mobileraker.conf")
        Logger.Warn("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        Logger.Blank()
        Logger.Blank()

        # Ask the user to confirm they understand.
        r =  input("Press enter to continue.")
        return


    # For the K1, we know a the fixed paths where everything must be installed.
    # There's only one instance of moonraker, so there's no need to worry about multiple setups.
    def _cleanup_k1(self):

        # Delete any log files we have, there might be some rolling backups.
        self._delete_files_in_dir("/usr/data/printer_data/logs", "mobileraker")
        # Delete any config files.
        self._delete_files_in_dir("/usr/data/printer_data/config", "mobileraker")
        # Remove our system config file include in the moonraker file, if there is one.
        # self._cleanup_moonraker_cfg("/usr/data/printer_data/config/moonraker.conf")
        


    def _cleanup_sonic_pad(self):
        # Delete config file, for sonic pad, we know that it must be in the master:
        self._delete_files_in_dir(f"{Paths.CrealityOsUserDataPath_SonicPad}/printer_config", "mobileraker")
        # Delete any log files we have, there might be some rolling backups.
        self._delete_files_in_dir(f"{Paths.CrealityOsUserDataPath_SonicPad}/printer_logs", "mobileraker")

        # Remove our system config file include in the moonraker file, if there is one.
        # self._cleanup_moonraker_cfg("/usr/data/printer_data/config/moonraker.conf")



    # Deletes a file or directory, if it exists.
    def _delete_if_exists(self, path:str):
        Logger.Debug(f"Deleting file or dir [{path}]")
        try:
            if os.path.exists(path) is False:
                return
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
            else:
                Logger.Error(f"DeleteDirOrFileIfExists can delete file type {path}")
        except Exception as e:
            Logger.Error(f"DeleteDirOrFileIfExists failed to delete {path} - {e}")


    # Deletes any in the dir that match the search string.
    def _delete_files_in_dir(self, path:str, searchStr:str):
        try:
            searchLower = searchStr.lower()
            for fileName in os.listdir(path):
                fullpath = os.path.join(path, fileName)
                if os.path.isfile(fullpath):
                    if searchLower in fileName.lower():
                        Logger.Debug(f"Deleting matched file: {fullpath}")
                        os.remove(fullpath)
        except Exception as e:
            Logger.Error(f"DeleteAllFilesContaining failed to delete {path} - {e}")


    # # Deletes the octoEverywhere-system.cfg file include if it exists in the moonraker config.
    # def _cleanup_moonraker_cfg(self, moonrakerConfigPath:str):
    #     try:
    #         Logger.Debug(f"Looking for OE system config include in {moonrakerConfigPath}")
    #         output = []
    #         lineFound = False
    #         with open(moonrakerConfigPath, encoding="utf-8") as f:
    #             lines = f.readlines()
    #             for l in lines:
    #                 if "octoeverywhere-system.cfg" in l.lower():
    #                     lineFound = True
    #                 else:
    #                     output.append(l)

    #         if lineFound is False:
    #             Logger.Debug("system config include not found.")
    #             return

    #         # Output the file without the line.
    #         with open(moonrakerConfigPath, encoding="utf-8", mode="w") as f:
    #             for o in output:
    #                 f.write(f"{o}")

    #         Logger.Debug(f"Removed octoeverywhere system config from {moonrakerConfigPath}")
    #     except Exception as e:
    #         Logger.Error(f"DeleteAllFilesContaining failed to delete {moonrakerConfigPath} - {e}")
