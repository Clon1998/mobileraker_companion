import os

from .Context import Context, OperationMode
from .Logging import Logger
from .Util import Util


class Permissions:
    # Must be lower case.
    ROOT_USER_NAME = "root"


    def ensure_valid_username_for_root_installation(self, context: Context) -> None:
        """
        Validate and correct the username for root-based installations.

        In some companion or Bambu setups with a single root user, the username 
        might not be explicitly set. This method ensures the username is correctly 
        configured when the home directory indicates a root installation.

        Specifically, this method:
        - Checks if the installation is standalone
        - Verifies if the username is unset or empty
        - Sets the username to 'root' if the home path starts with '/root/'

        Note: This method runs before the first context validation, 
        so context variables may be None.

        Args:
            context (Context): The installation context containing user information.
        """
        # If this is a standalone installation, validate the username
        if context.is_standalone:
            if context.username is None or len(context.username) == 0:
                if context.user_home is not None and (context.user_home.lower() == "/root" or context.user_home.lower().startswith("/root/")):
                    Logger.Debug("No user passed, but we detected the user is root.")
                    context.username = Permissions.ROOT_USER_NAME

    def validate_root_privileges(self, context:Context) -> None:
        """
        Validates the root privileges for the installer script.

        Args:
            context (Context): The context object containing information about the installation.

        Raises:
            RuntimeError: If the installer is run under the root user and it's not a standalone installation or Creality OS.
            RuntimeError: If the script is not run as root or using sudo.
        """

        # IT'S NOT OK TO INSTALL AS ROOT for the normal klipper setup.
        # This is because the moonraker updater system needs to get able to access the .git repo.
        # If the repo is owned by the root, it can't do that.
        # For the Sonic Pad and K1 setup, the only user is root, so it's ok.
    
        # IT'S NOT OK TO INSTALL AS ROOT for the local klipper setup.
        # This is because the moonraker updater system needs to get able to access the .git repo.
        # If the repo is owned by the root, it can't do that.
        # For the Sonic Pad and K1 setup, the only user is root, so it's ok.
        if context.is_standalone is False and context.is_creality_os is False:
            if context.username.lower() == Permissions.ROOT_USER_NAME:
                raise Exception("The installer was ran under the root user, this will cause problems with Moonraker. Please run the installer script as a non-root user, usually that's the `pi` user or 'mks' for MKS PI.")

        
        # But regardless of the user, we must have sudo permissions.
        # pylint: disable=no-member # Linux only
        if os.geteuid() != 0:
            if context.debug:
                Logger.Warn("Not running as root, but ignoring since we are in debug.")
            else:
                raise RuntimeError("Script not ran as root or using sudo. This is required to integrate into Moonraker.")


    # Called at the end of the setup process, just before the service is restarted or updated.
    # The point of this is to ensure we have permissions set correctly on all of our files,
    # so the plugin can access them.
    #
    # We always set the permissions for all of the files we touch, to ensure if something in the setup process
    # did it wrong, a user changed them, or some other service changed them, they are all correct.
    def validate_context_permissions(self, context:Context):
        """
        Validates the permissions of the given context.

        Args:
            context (Context): The context containing the necessary information.

        Returns:
            None
        """
        # A helper to set file permissions.
        # We try to set permissions to all paths and files in the context, some might be null
        # due to the setup mode. We don't care to difference the setup mode here, because the context
        # validation will do that for us already. Thus if a field is None, its ok.
        def ensure_permissions(path:str):
            if path is not None and len(path) != 0 and os.path.exists(path):
                Util.update_file_ownership(path, context.username)

        # For all setups, make sure the entire repo is owned by the user who launched the script.
        # This is required, in case the user accidentally used the wrong user at first and some part of the git repo is owned by the root user.
        # If Moonraker is running locally and this is owned by root for example, the Moonraker Updater can't access it, and will show errors.
        Util.update_file_ownership(context.repo_root, context.username)

        # These following files or folders must be owned by the user the service is running under.
        ensure_permissions(context.mobileraker_conf_path)
        if context.has_moonraker_config_file_path:
            ensure_permissions(context.moonraker_config_file_path)
        if context.has_mobileraker_conf_link:
            ensure_permissions(context.mobileraker_conf_link)

