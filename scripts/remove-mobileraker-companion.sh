#!/usr/bin/env bash
# This script installs the Mobileraker-Companion on a Raspi

PYTHONDIR="${MOBILERAKER_VENV:-${HOME}/mobileraker-env}"
SYSTEMDDIR="/etc/systemd/system"

# If we're running as root we don't need sudo.
if [ "$EUID" -eq 0 ]; then
    SUDO=""
else
    SUDO="sudo"
fi

remove_virtualenv()
{
    report_status "Removing python virtual environment..."

    # If venv exists and user prompts a rebuild, then do so
    if [ -d "${PYTHONDIR}" ]; then
        report_status "Removing virtualenv"
        rm -rf "${PYTHONDIR}"
    fi
}

remove_script()
{
# Remove systemd service file
    SERVICE_FILE="${SYSTEMDDIR}/mobileraker.service"
    [ ! -f "$SERVICE_FILE" ] && return
    report_status "Stopping the service ..."
    "$SUDO" systemctl stop mobileraker.service
    "$SUDO" systemctl disable mobileraker.service
    report_status "Removing the service ..."
    "$SUDO" rm "$SERVICE_FILE"

    "$SUDO" systemctl daemon-reload
}

remove_script_creality()
{
# Remove systemd service file
    SERVICE_FILE="/etc/init.d/mobileraker.service"
    [ ! -f "$SERVICE_FILE" ] && return
    report_status "Stopping the service ..."
    /etc/init.d/mobileraker.service stop
    report_status "Removing the service ..."
    rm "$SERVICE_FILE"
}

report_status()
{
    echo -e "\n\n###### $1"
}

verify_ready()
{
    if [ "$EUID" -eq 0 ]; then
        echo "This script must not run as root"
        exit 1
    fi
}

is_creality_device()
{
    if [ -d "/usr/share/creality-env/" ]; then
        return 0
    else
        return 1
    fi
}

# Force script to exit if an error occurs
set -e


# Run uninstallation steps defined above
if is_creality_device; then
    remove_script_creality
    remove_virtualenv
else
    verify_ready
    remove_script
    remove_virtualenv
fi

