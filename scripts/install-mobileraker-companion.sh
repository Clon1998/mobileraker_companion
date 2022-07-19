#!/bin/bash
# This script installs the Mobileraker-Companion on a Raspi

PYTHONDIR="${MOBILERAKER_VENV:-${HOME}/envs/mobileraker}"
REBUILD_ENV="${MOBILERAKER_REBUILD_ENV:-n}"
FORCE_DEFAULTS="${MOBILERAKER_FORCE_DEFAULTS:-n}"
LOG_PATH="${MOBILERAKER_LOG_PATH:-/tmp/mobileraker.log}"

SYSTEMDDIR="/etc/systemd/system"

create_virtualenv()
{
    report_status "Installing python virtual environment..."

    # If venv exists and user prompts a rebuild, then do so
    if [ -d ${PYTHONDIR} ] && [ $REBUILD_ENV = "y" ]; then
        report_status "Removing old virtualenv"
        rm -rf ${PYTHONDIR}
    fi

    if [ ! -d ${PYTHONDIR} ]; then
        virtualenv -p /usr/bin/python3 ${PYTHONDIR}
    fi

    # Install/update dependencies
    ${PYTHONDIR}/bin/pip install -r ${SRCDIR}/scripts/mobileraker-requirements.txt
}

install_script()
{
# Create systemd service file
    SERVICE_FILE="${SYSTEMDDIR}/mobileraker.service"
    [ -f $SERVICE_FILE ] && [ $FORCE_DEFAULTS = "n" ] && return
    report_status "Installing system start script..."
    sudo /bin/sh -c "cat > ${SERVICE_FILE}" << EOF
#Systemd service file for mobileraker
[Unit]
Description=Companion app to enable push notifications on mobileraker
Requires=network-online.target
After=network-online.target

[Install]
WantedBy=multi-user.target

[Service]
Type=simple
User=$USER
RemainAfterExit=yes
WorkingDirectory=${SRCDIR}
ExecStart=${LAUNCH_CMD} -l ${LOG_PATH}
Restart=always
RestartSec=10
EOF
# Use systemctl to enable the klipper systemd service script
    sudo systemctl enable mobileraker.service
    sudo systemctl daemon-reload
}


start_software()
{
    report_status "Launching mobileraker Companion..."
    sudo systemctl restart mobileraker
}

# Helper functions
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

# Find SRCDIR from the pathname of this script
SRCDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/.. && pwd )"
LAUNCH_CMD="${PYTHONDIR}/bin/python ${SRCDIR}/mobileraker.py"

# Parse command line arguments
while getopts "rfc:l:" arg; do
    case $arg in
        r) REBUILD_ENV="y";;
        f) FORCE_DEFAULTS="y";;
        l) LOG_PATH=$OPTARG;;
    esac
done

# Run installation steps defined above
verify_ready
create_virtualenv
install_script
start_software
