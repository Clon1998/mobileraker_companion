
# A simple holder of commonly used paths.
class Paths:

    # The systemd path where we expect to find moonraker service files AND where we will put our service file.
    SystemdServiceFilePath = "/etc/systemd/system"

    # For the Creality OS, the service path is different.
    # The OS is based on WRT, so it's not Debian.
    CrealityOsServiceFilePath = "/etc/init.d"

    # For the Sonic Pad, this is the path we know we will find the printer configs and printer log locations.
    # The printer data will not be standard setup, so it will be like <root folder>/printer_config, <root folder>/printer_logs
    CrealityOsUserDataPath_SonicPad = "/mnt/UDISK"

    # For the K1/K1Max, this is the path we know we will find the printer configs and printer log locations.
    # They will be the standard Klipper setup, such as printer_data/config, printer_data/logs, etc.
    CrealityOsUserDataPath_K1 = "/usr/data"


    @staticmethod
    def service_file_folder(context) -> str:
        """
        Returns the path of the service file folder based on the given context (os).

        Args:
            context: The context object.

        Returns:
            The path of the service file folder.
        """
        return Paths.CrealityOsServiceFilePath if context.is_creality_os else Paths.SystemdServiceFilePath