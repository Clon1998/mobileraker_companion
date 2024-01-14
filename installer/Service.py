import os


from .Util import Util
from .Logging import Logger
from .Context import Context, PlatformType
from .Configure import Configure


# Responsible for creating, running, and ensuring the service is installed and running.
class Service:

    

    def install(self, context:Context):
        """
        Installs the system service based on the platform type.

        Args:
            context (Context): The context object containing information about the platform.

        Raises:
            NotImplementedError: If the service install is not supported for the current OS type.
        """
        Logger.Header("Setting Up System Service...")

        # We always re-write the service file, to make sure it's current.
        if os.path.exists(context.service_file_path):
            Logger.Info("Service file already exists, recreating.")

        # Base on the OS type, install the service differently
        if context.platform == PlatformType.DEBIAN:
            self._debian_install(context)
        elif context.platform == PlatformType.SONIC_PAD:
            self._sonic_pad_install(context)
        elif context.platform == PlatformType.K1:
            self._k1_install(context)
        else:
            raise NotImplementedError("Service install is not supported for this OS type yet.")



    # Install for debian setups
    def _debian_install(self, context:Context):
        s = f'''\
    # Mobileraker Companion Service File
    [Unit]
    Description=Companion app to enable push notifications via mobileraker
    # Start after network and moonraker has started.
    After=network-online.target moonraker.service

    [Install]
    WantedBy=multi-user.target

    # Simple service, targeting the user that was used to install the service, simply running our moonraker py host script.
    [Service]
    Type=simple
    User={context.username}
    WorkingDirectory={context.repo_root}
    ExecStart={context.virtual_env}/bin/python3 {context.repo_root}/mobileraker.py -l {context.printer_data_logs_folder} -c {context.mobileraker_conf_path}
    Restart=always
    # Since we will only restart on a fatal Logger.Error, set the restart time to be a bit higher, so we don't spin and spam.
    RestartSec=10
'''
        if context.skip_sudo_actions:
            Logger.Warn("Skipping service file creation, registration, and starting due to skip sudo actions flag.")
            return

        Logger.Debug("Service config file contents to write: "+s)
        Logger.Info("Creating service file "+context.service_file_path+"...")
        with open(context.service_file_path, "w", encoding="utf-8") as file:
            file.write(s)

        Logger.Info("Registering service...")
        Util.run_shell_command("systemctl enable "+ Configure.SERVICE_NAME)
        Util.run_shell_command("systemctl daemon-reload")

        # Stop and start to restart any running services.
        Logger.Info("Starting service...")
        Service.restart_service(Configure.SERVICE_NAME)

        Logger.Info("Service setup and start complete!")


    # Install for sonic pad setups.
    def _sonic_pad_install(self, context:Context):
        # First, write the service file
        # Notes:
        #   Set start to be 80, so we start after Moonraker.
        #   OOM_ADJ=-17 prevents us from being killed in an OOM
        
        s = f'''\
#!/bin/sh /etc/rc.common
# Copyright (C) 2006-2011 OpenWrt.org

START={Configure.SERVICE_NUMBER}
STOP=1
DEPEND=moonraker_service
USE_PROCD=1
OOM_ADJ=-17

start_service() {{
    procd_open_instance
    procd_set_param env HOME=/root
    procd_set_param env PYTHONPATH={context.repo_root}
    procd_set_param oom_adj $OOM_ADJ
    procd_set_param command {context.virtual_env}/bin/python3 {context.repo_root}/mobileraker.py -l {context.printer_data_logs_folder} -c {context.mobileraker_conf_path}
    procd_close_instance
}}
'''
        if context.skip_sudo_actions:
            Logger.Warn("Skipping service file creation, registration, and starting due to skip sudo actions flag.")
            return

        Logger.Debug("Service config file contents to write: "+s)
        Logger.Info("Creating service file "+context.service_file_path+"...")
        with open(context.service_file_path, "w", encoding="utf-8") as file:
            file.write(s)

        # Make the script executable.
        Logger.Info("Making the service executable...")
        Util.run_shell_command(f"chmod +x {context.service_file_path}")

        Logger.Info("Starting the service...")
        Service.restart_sonic_pad_service(context.service_file_path)

        Logger.Info("Service setup and start complete!")


    # Install for k1 and k1 max
    def _k1_install(self, context:Context):
        # On the K1 start-stop-daemon is used to run services.
        # But, to launch our service, we have to use the py module run, which requires a environment var to be
        # set for PYTHONPATH. The command can't set the env, so we write this script to our store, where we then run
        # the service from.



        #TODO: WE DONT USE A LOCAL STORE :(
        script_path = os.path.join(context.repo_root, ".k1", "run-companion-service.sh")
        script = f'''\
#!/bin/sh
#
# Runs Mobileraker service on the K1 and K1 max.
# The start-stop-daemon can't handle setting env vars, but the python module run command needs PYTHONPATH to be set
# to find the module correctly. Thus we point the service to this script, which sets the env and runs py.
#
# Don't edit this script, it's generated by the ./install.sh script during the OE install and update..
#
PYTHONPATH={context.repo_root} {context.virtual_env}/bin/python3 {context.repo_root}/mobileraker.py -l {context.printer_data_logs_folder} -c {context.mobileraker_conf_path}
exit $?
'''
        # Write the required service file, make it point to our run script.
        s = '''\
#!/bin/sh
#
# Starts Mobileraker service.
#

PID_FILE=/var/run/mobileraker.pid

start() {
        HOME=/root start-stop-daemon -S -q -b -m -p $PID_FILE --exec '''+script_path+'''
}
stop() {
        start-stop-daemon -K -q -p $PID_FILE
}
restart() {
        stop
        sleep 1
        start
}

case "$1" in
  start)
        start
        ;;
  stop)
        stop
        ;;
  restart|reload)
        restart
        ;;
  *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
esac

exit $?
}}
'''
        if context.skip_sudo_actions:
            Logger.Warn("Skipping service file creation, registration, and starting due to skip sudo actions flag.")
            return

        # Write the run script
        Logger.Debug("Run script file contents to write: "+script)
        Logger.Info("Creating service run script...")
        with open(script_path, "w", encoding="utf-8") as file:
            file.write(script)

        # Make the script executable.
        Logger.Info("Making the run script executable...")
        Util.run_shell_command(f"chmod +x {script_path}")

        # The file name is specific to the K1 and it's set in the Configure step.
        Logger.Debug("Service config file contents to write: "+s)
        Logger.Info("Creating service file "+context.service_file_path+"...")
        with open(context.service_file_path, "w", encoding="utf-8") as file:
            file.write(s)

        # Make the script executable.
        Logger.Info("Making the service executable...")
        Util.run_shell_command(f"chmod +x {context.service_file_path}")

        # Use the common restart logic.
        Logger.Info("Starting the service...")
        Service.restart_k1_service(context.service_file_path)

        Logger.Info("Service setup and start complete!")


    @staticmethod
    def restart_k1_service(serviceFilePath:str, throwOnBadReturnCode = True):
        # These some times fail depending on the state of the service, which is fine.
        Util.run_shell_command(f"{serviceFilePath} stop", False)

        # Using this start-stop-daemon system, if we issue too many start, stop, restarts in quickly, the PID file gets out of
        # sync and multiple process can spawn. That's bad because the websockets will disconnect each other.
        # So we will run this run command to ensure that all of the process are dead, before we start a new one.
        Util.run_shell_command("ps -ef | grep 'moonraker_octoeverywhere' | grep -v grep | awk '{print $1}' | xargs -r kill -9", throwOnBadReturnCode)
        Util.run_shell_command(f"{serviceFilePath} start", throwOnBadReturnCode)


    @staticmethod
    def restart_sonic_pad_service(serviceFilePath:str, throwOnBadReturnCode = True):
        # These some times fail depending on the state of the service, which is fine.
        Util.run_shell_command(f"{serviceFilePath} stop", False)
        Util.run_shell_command(f"{serviceFilePath} reload", False)
        Util.run_shell_command(f"{serviceFilePath} enable" , False)
        Util.run_shell_command(f"{serviceFilePath} start", throwOnBadReturnCode)


    @staticmethod
    def restart_service(serviceName:str, throwOnBadReturnCode = True):
        serviceName += ".service"
        (returnCode, output, errorOut) = Util.run_shell_command("systemctl restart "+serviceName, throwOnBadReturnCode)
        if returnCode != 0:
            Logger.Warn(f"Service {serviceName} might have failed to restart. Output: {output} Error: {errorOut}")
        # (returnCode, output, errorOut) = Util.run_shell_command("systemctl start "+serviceName, throwOnBadReturnCode)
        # if returnCode != 0:
        #     Logger.Warn(f"Service {serviceName} might have failed to start. Output: {output} Error: {errorOut}")
