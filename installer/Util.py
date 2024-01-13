import os
import subprocess
# pylint: disable=import-error # Only exists on linux
import pwd

from .Logging import Logger
from .Context import Context

class Util:

    # Returns the parent directory of the passed directory or file path.
    @staticmethod
    def parent_dir(path):
        """
        Returns the absolute path of the parent directory of the given path.
        
        Args:
            path (str): The path for which the parent directory is to be determined.
            
        Returns:
            str: The absolute path of the parent directory.
        """
        return os.path.abspath(os.path.join(path, os.pardir))


    # Runs a command as shell and returns the output.
    # Returns (return_code:int, output:str)
    @staticmethod
    def run_shell_command(cmd:str, throwOnNonZeroReturnCode:bool = True):
        # Check=true means if the process returns non-zero, an exception is thrown.
        # Shell=True is required so non absolute commands like "systemctl restart ..." work
        result = subprocess.run(cmd, check=throwOnNonZeroReturnCode, shell=True, capture_output=True, text=True)
        Logger.Debug(f"RunShellCommand - {cmd} - return: {result.returncode}; error - {result.stderr}")
        return (result.returncode, result.stdout, result.stderr)


    # Ensures a folder exists, and optionally, it has permissions set correctly.
    @staticmethod
    def ensure_dir_exists(path, context:Context, set_ownership = False):
        """
        Validates if a directory exists at the given path and creates it if it doesn't exist.
        
        Args:
            path (str): The path of the directory to validate.
            context (Context): The context object containing user information.
            set_ownership (bool, optional): Flag indicating whether to set ownership permissions. Defaults to False.
        """

        # Ensure it exists.
        Logger.Header("Enuring path and permissions ["+path+"]...")
        if os.path.exists(path) is False:
            Logger.Info("Dir doesn't exist, creating...")
            os.mkdir(path)
        else:
            Logger.Info("Dir already exists.")

        if set_ownership:
            Logger.Info("Setting owner permissions to the service user ["+context.UserName+"]...")
            uid = pwd.getpwnam(context.username).pw_uid
            gid = pwd.getpwnam(context.username).pw_gid
            # pylint: disable=no-member # Linux only
            os.chown(path, uid, gid)

        Logger.Info("Directory setup successfully.")


    # Ensures that all files and dirs down stream of this root dir path are owned by the requested user.
    @staticmethod
    def update_file_ownership(file_path:str, username:str):
        """
        Updates the ownership of a directory or file to the specified user.

        Args:
            dirOrFilePath (str): The path to the directory or file.
            userName (str): The name of the user.

        Returns:
            None
        """
        uid = pwd.getpwnam(username).pw_uid
        gid = pwd.getpwnam(username).pw_gid
        # pylint: disable=no-member # Linux only
        os.chown(file_path, uid, gid)
        # For file paths, this walk will do nothing
        for root, dirs, files in os.walk(file_path):
            for d in dirs:
                os.chown(os.path.join(root, d), uid, gid)
            for f in files:
                os.chown(os.path.join(root, f), uid, gid)


    # Helper to ask the user a question.
    @staticmethod
    def AskYesOrNoQuestion(question:str) -> bool:
        val = None
        while True:
            try:
                val = input(question+" [y/n] ")
                val = val.lower().strip()
                if val == "n" or val == "y":
                    break
            except Exception as e:
                Logger.Warn("Invalid input, try again. Logger.Error: "+str(e))
        return val == "y"


    @staticmethod
    def PrintServiceLogsToConsole(context:Context):
        if context.ServiceName is None:
            Logger.Warn("Can't print service logs, there's no service name.")
            return
        try:
            (_, output, _) = Util.run_shell_command("sudo journalctl -u "+context.ServiceName+" -n 20 --no-pager")
            # Use the logger to print the logs, so they are captured in the log file as well.
            Logger.Info(output)
        except Exception as e:
            Logger.Error("Failed to print service logs. "+str(e))
