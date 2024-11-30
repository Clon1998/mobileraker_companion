import os

from .Logging import Logger
from .Context import Context
from .Util import Util

# This class does the same function as the Discovery class, but for companion or Bambu Connect plugins.
# Note that "Bambu Connect" is really just a type of companion plugin, but we use different names so it feels correct.
class DiscoveryStandalone:

    # This is the base data folder name that will be used, the plugin id suffix will be added to end of it.
    # The folders will always be in the user's home path.
    # These MUST start with a . and be LOWER CASE for the matching logic below to work correctly!
    # The primary instance (id == "1") will have no "-#" suffix on the folder or service name.
    STANDALONE_DATA_FOLDER_LOWER = ".mobileraker_companion-standalone"


    def start(self, context:Context):
        Logger.Debug("Starting companion discovery.")

        # Used for printing the type, like "would you like to install a new {pluginTypeStr} plugin?"
        pluginTypeStr = "Standalone"

        # Look for existing companion or bambu data installs.
        existingCompanionFolders = []
        # Sort so the folder we find are ordered from 1-... This makes the selection process nicer, since the ID == selection.
        fileAndDirList = sorted(os.listdir(context.user_home))
        for fileOrDirName in fileAndDirList:
            # Use starts with to see if it matches any of our possible folder names.
            # Since each setup only targets companion or bambu connect, only pick the right folder type.
            fileOrDirNameLower = fileOrDirName.lower()
            if context.is_standalone:
                if fileOrDirNameLower.startswith(DiscoveryStandalone.STANDALONE_DATA_FOLDER_LOWER):
                    existingCompanionFolders.append(fileOrDirName)
                    Logger.Debug(f"Found existing companion data folder: {fileOrDirName}")
            else:
                raise Exception("DiscoveryStandalone used in non standalone context.")

        # If there's an existing folders, ask the user if they want to use them.
       # ToDo :: Add "discover of existing companion data" logic here again (See original code)

        # Create a new instance path. Either there is no existing data path or the user wanted to create a new one.
        # There is a special case for instance ID "1", we use no suffix. All others will have the suffix.
        folderNameRoot = DiscoveryStandalone.STANDALONE_DATA_FOLDER_LOWER
        fullFolderName = f"{folderNameRoot}"
        self._setup_context_from_vars(context, fullFolderName)
        Logger.Info(f"Creating a new {pluginTypeStr} data path. Path: {context.standalone_data_path}")
        return


    def _setup_context_from_vars(self, context:Context, folderName:str):
        # Make the full path
        context.standalone_data_path = os.path.join(context.user_home, folderName)

        # Ensure the file exists and we have permissions
        Util.ensure_dir_exists(context.standalone_data_path, context, True)

