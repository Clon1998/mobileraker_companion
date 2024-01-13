
import logging
import logging.handlers
import os
from queue import SimpleQueue as Queue
import sys
import traceback
import coloredlogs

# Rotating file handler based on MobilerakerCompanion, Klipper and Moonraker's implementation


class MobilerakerCompanionLoggingHandler(logging.handlers.RotatingFileHandler):
    def __init__(self, software_version, filename, **kwargs):
        super(MobilerakerCompanionLoggingHandler,
              self).__init__(filename, **kwargs)
        self.rollover_info = {
            'header': f"{'-' * 20}MobilerakerCompanion Log Start{'-' * 20}",
            'version': f"Git Version: {software_version}",
        }
        lines = [line for line in self.rollover_info.values() if line]
        if self.stream is not None:
            self.stream.write("\n".join(lines) + "\n")

    def set_rollover_info(self, name, item):
        self.rollover_info[name] = item

    def doRollover(self):
        super(MobilerakerCompanionLoggingHandler, self).doRollover()
        lines = [line for line in self.rollover_info.values() if line]
        if self.stream is not None:
            self.stream.write("\n".join(lines) + "\n")


# Logging based on Arksine's logging setup
def setup_logging(log_file, software_version):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    coloredlogs.install(
        logger=root_logger, fmt=f'%(asctime)s %(name)s %(levelname)s %(message)s')

    # Check if provided log_file is a file or a directory
    if os.path.isdir(log_file):
        log_file = os.path.join(log_file, "mobileraker.log")

    print(f"Logging to file: {os.path.normpath(log_file)}")
    try:
        fh = MobilerakerCompanionLoggingHandler(
            software_version, log_file, maxBytes=4194304, backupCount=3)
        formatter = logging.Formatter(
            '%(asctime)s %(name)s %(levelname)s - %(message)s')
        fh.setFormatter(formatter)

        root_logger.addHandler(fh)

    except Exception as e:
        print(
            f"Unable to create log file at '{os.path.normpath(log_file)}'.\n"
            f"Make sure that the folder '{os.path.dirname(log_file)}' exists\n"
            f"and MobilerakerCompanion has Read/Write access to the folder.\n"
            f"{e}\n"
        )

    def logging_exception_handler(ex_type, value, tb, thread_identifier=None):
        logging.exception(
            f'Uncaught exception {ex_type}: {value}\n'
            + '\n'.join([str(x) for x in [*traceback.format_tb(tb)]])
        )

    sys.excepthook = logging_exception_handler
    logging.captureWarnings(True)

    # Disable websockets info logging
    # logging.getLogger("websockets").setLevel(logging.ERROR)
