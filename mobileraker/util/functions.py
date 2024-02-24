

import logging
import os
import subprocess
import uuid

# Based on the implementation of Klipperscreen https://github.com/jordanruthe/KlipperScreen/blob/e9df355b3b8c33b63d5cbb9f7f2c75bd879597c5/ks_includes/functions.py#L83


def get_software_version():
    prog = ('git', '-C', os.path.dirname(__file__), 'describe', '--always',
            '--tags', '--long', '--dirty')
    try:
        process = subprocess.Popen(prog, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        ver, err = process.communicate()
        retcode = process.wait()
        if retcode == 0:
            version = ver.strip()
            if isinstance(version, bytes):
                version = version.decode()
            return version
        else:
            logging.debug(f"Error getting git version: {err}")
    except OSError:
        logging.exception("Error runing git describe")
    return "?"


def is_valid_uuid(value):
    try:
        uuid.UUID(str(value))

        return True
    except ValueError:
        return False


def normalized_progress_interval_reached(last: int, current: int, interval: int) -> bool:
    """
    Check if the current progress has exceeded the normalized threshold based on increments.

    Parameters:
        last_progress (int): The previous progress value.
        current_progress (int): The current progress value.
        increment (int): The predefined increment to consider.

    Returns:
        bool: True if the current progress exceeds the normalized threshold, False otherwise.
    """
    # logging.info(f"!!!last: {last}, current: {current}, interval: {interval}")
    noramlized = last - (last % interval)
    return abs(current - noramlized) >= interval

def generate_notifcation_id_from_uuid(uuid_string: str, offset: int) -> int:
    """
    Generate a notification ID from a UUID string and an offset.

    Args:
        uuid_string (str): The UUID string.
        offset (int): The offset value.

    Returns:
        int: The generated notification ID.
    """
    # Convert the UUID into an integer and take the modulus in a single line
    return (uuid.UUID(uuid_string).int + offset) % 2147483647 + 1



def compare_version(a: str, b: str) -> int:
    """
    Compare two version strings.
    

    Args:
        a (str): The first version string.
        b (str): The second version string.

    Returns:
        int: 0 if the versions are equal, 1 if a is greater than b, -1 if a is less than b.
    """
    a = a.split("-")[0]
    b = b.split("-")[0]
    aVersions = list(map(int, a.split(".")))
    bVersions = list(map(int, b.split(".")))

    for i in range(3):
        if aVersions[i] > bVersions[i]:
            return 1
        if aVersions[i] < bVersions[i]:
            return -1
    return 0