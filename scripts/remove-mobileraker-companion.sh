#!/bin/bash
# This script installs the Mobileraker-Companion on a Raspi

PYTHONDIR="${MOBILERAKER_VENV:-${HOME}/mobileraker-env}"
SYSTEMDDIR="/etc/systemd/system"

remove_virtualenv()
{
    report_status "Removing python virtual environment..."

    # If venv exists and user prompts a rebuild, then do so
    if [ -d ${PYTHONDIR} ]; then
        report_status "Removing virtualenv"
        rm -rf ${PYTHONDIR}
    fi
}

remove_script()
{
# Create systemd service file
    SERVICE_FILE="${SYSTEMDDIR}/mobileraker.service"
    [ ! -f $SERVICE_FILE ] && return
    report_status "Stopping the service ..."
	sudo systemctl stop mobileraker.service
	sudo systemctl disable mobileraker.service
	report_status "Removing the service ..."
	sudo rm $SERVICE_FILE 

    sudo systemctl daemon-reload
    sudo systemctl reset-failed
}

report_status()
{
    echo -e "\n\n###### $1"
}

verify_ready()
{
    if [ "$EUID" -eq 0 ]; then
        echo "This script must not run as root"
        exit -1
    fi
}


# Force script to exit if an error occurs
set -e



# Run installation steps defined above
verify_ready
remove_script
remove_virtualenv