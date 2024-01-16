import os
import subprocess
# pylint: disable=import-error # Only exists on linux
import pwd
from typing import List, Optional

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
        Logger.Debug("Updating file ownership for ["+file_path+"] to ["+username+"]...")

        # Helper to set the ownership of a file or link.
        def chown(path:str, uid:int, gid: int):
            if os.path.islink(path):
                os.lchown(path, uid, gid)
                return
            os.chown(path, uid, gid)

        uid = pwd.getpwnam(username).pw_uid
        gid = pwd.getpwnam(username).pw_gid
        # pylint: disable=no-member # Linux only
        chown(file_path, uid, gid)
        # For file paths, this walk will do nothing
        for root, dirs, files in os.walk(file_path):
            for d in dirs:
                chown(os.path.join(root, d), uid, gid)
            for f in files:
                chown(os.path.join(root, f), uid, gid)



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
    def scan_files(path:str, prefix:Optional[str] = None, suffix:Optional[str] = None, depth:int = 0) -> List[str]:
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
                tmp = Util.scan_files(full_path, prefix, suffix, depth + 1)
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