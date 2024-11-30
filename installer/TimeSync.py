from .Util import Util
from .Logging import Logger

from .Context import Context

# This helper class ensures that the system's ntp clock sync service is enabled and active.
# We found some MKS PI systems didn't have it on, and would be years out of sync on reboot.
# This is a problem because SSL will fail if the date is too far out of sync.
#
# For the most part, this class is best effort. It will try to get everything setup, but if it fails,
# we won't stop the setup.
class TimeSync:

    @staticmethod
    def ensure_ntp_sync_enabled(context:Context):
        if context.skip_sudo_actions:
            Logger.Warn("Skipping time sync since we are skipping sudo actions.")
            return
        Logger.Info("Ensuring that time sync is enabled...")

        # Ensure that NTP is uninstalled, since this conflicts with timesyncd
        TimeSync._run_system_command("sudo apt -y purge ntp ntpdate ntpsec-ntpdate")

        # Ensure timedatectl is installed. On all most systems it will be already.
        TimeSync._run_system_command("sudo apt install -y systemd-timesyncd")
        TimeSync._print_time_sync_dstatus()

        # Ensure time servers are set in the config file.
        TimeSync._update_time_sync_dconfig()

        # Reload and start the systemd service
        TimeSync._run_system_command("sudo systemctl daemon-reload")
        TimeSync._run_system_command("sudo systemctl enable systemd-timesyncd")
        TimeSync._run_system_command("sudo systemctl restart systemd-timesyncd")
        TimeSync._run_system_command("sudo timedatectl set-ntp on")

        # Print the status outcome.
        TimeSync._print_time_sync_dstatus()


    @staticmethod
    def _update_time_sync_dconfig():
        targetFilePath = "/etc/systemd/timesyncd.conf"
        try:
            # After writing, read the file and insert any comments we have.
            outputLines = []
            with open(targetFilePath, 'r', encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    lineLower = line.lower()
                    if lineLower.startswith("#ntp="):
                        # This is case sensitive!
                        outputLines.append("NTP=0.pool.ntp.org 1.pool.ntp.org 2.pool.ntp.org 3.pool.ntp.org\n")
                    else:
                        outputLines.append(line)
            # This will only happen if we have sudo powers.
            with open(targetFilePath, 'w', encoding="utf-8") as f:
                f.writelines(outputLines)
        except Exception as e:
            Logger.Debug(f"TimeSync update config exception. (this is ok) {str(e)}")


    @staticmethod
    def _run_system_command(cmd:str):
        (code, stdOut, errOut) = Util.run_shell_command(cmd, False)
        if code == 0:
            Logger.Debug(f"TimeSync System Command Success. Cmd: {cmd}")
        if code != 0:
            Logger.Debug(f"TimeSync System Command FAILED. (this is ok) Cmd: `{cmd}` - `{str(stdOut)}` - `{str(errOut)}`")


    @staticmethod
    def _print_time_sync_dstatus():
        (_, stdOut, errOut) = Util.run_shell_command("sudo timedatectl status", False)
        Logger.Debug(f"TimeSync Status:\r\n{stdOut} {errOut}")