#!/bin/bash
# This script installs the Mobileraker-Companion on a Raspi

PYTHONDIR="${MOBILERAKER_VENV:-${HOME}/mobileraker-env}"
LOG_PATH="${MOBILERAKER_LOG_PATH}"
REBUILD_ENV="${REBUILD_ENV:-n}"
FORCE_DEFAULTS="${FORCE_DEFAULTS:-n}"

SYSTEMDDIR="/etc/systemd/system"

MOONRAKER_ASVC=~/printer_data/moonraker.asvc



# Function to detect Linux distribution
detect_distribution() {
    if [[ -f /etc/os-release ]]; then
        # Read the distribution information
        source /etc/os-release
        # Set the distribution variable based on ID or ID_LIKE
        if [[ -n $ID ]]; then
            DISTRIBUTION=$ID
        elif [[ -n $ID_LIKE ]]; then
            DISTRIBUTION=$ID_LIKE
        else
            DISTRIBUTION=""
        fi
    else
        # Unable to detect distribution
        DISTRIBUTION=""
    fi
}

# Function to install dependencies based on distribution
install_dependencies() {
    case $DISTRIBUTION in
        "debian" | "ubuntu" | "linuxmint")
            sudo apt-get update
            sudo apt-get install -y libjpeg8-dev zlib1g-dev
            ;;
        "fedora" | "centos" | "rhel")
            sudo dnf install -y libjpeg-devel zlib-devel
            ;;
        "arch" | "manjaro" | "endeavouros")
            sudo pacman -Sy --noconfirm  libjpeg-turbo zlib
            ;;
        *)
            echo "Unsupported distribution. Please install pillow dependencies manually. (https://pillow.readthedocs.io/en/stable/installation.html#external-libraries)"
            exit 1
            ;;
    esac
}

# install_dependencies()
# {
#     sudo apt update
#     sudo apt install -y \
#             git \
#             zlib1g \
#             libtiff5 libjpeg62-turbo libopenjp2-7
# }

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
if [ -z "$LOG_PATH" ]
then
    CMD="${LAUNCH_CMD}"
else
    CMD="${LAUNCH_CMD} -l ${LOG_PATH}"

fi
# Create systemd service file
    SERVICE_FILE="${SYSTEMDDIR}/mobileraker.service"
    [ -f $SERVICE_FILE ] && [ $FORCE_DEFAULTS = "n" ] && return
    report_status "Installing system start script..."
    sudo /bin/sh -c "cat > ${SERVICE_FILE}" << EOF
#Systemd service file for mobileraker
[Unit]
Description=Companion app to enable push notifications on mobileraker
After=network-online.target moonraker.service

[Install]
WantedBy=multi-user.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SRCDIR
ExecStart=$CMD
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



add_to_asvc()
{
    report_status "Trying to add mobileraker to service list"
    if [ -f $MOONRAKER_ASVC ]; then
        echo "moonraker.asvc was found"
        if ! grep -q mobileraker $MOONRAKER_ASVC; then
            echo "moonraker.asvc does not contain 'mobileraker'! Adding it..."
            echo -e "\nmobileraker" >> $MOONRAKER_ASVC
        fi
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
detect_distribution
install_dependencies
create_virtualenv
install_script
add_to_asvc
start_software
