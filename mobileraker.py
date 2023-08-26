import argparse
import asyncio
import logging
import os
from mobileraker.client.mobileraker_fcm_client import MobilerakerFcmClient
from mobileraker.client.moonraker_client import MoonrakerClient
from mobileraker.client.snapshot_client import SnapshotClient
from mobileraker.mobileraker_companion import MobilerakerCompanion
from mobileraker.service.data_sync_service import DataSyncService
from mobileraker.util.configs import CompanionLocalConfig, printer_data_logs_dir
from mobileraker.util.functions import get_software_version
from mobileraker.util.logging import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mobileraker - Companion")

    parser.add_argument(
        "-l", "--logfile", default=os.path.join(printer_data_logs_dir if os.path.exists(printer_data_logs_dir) else '/tmp', "mobileraker.log"), metavar='<logfile>',
        help="log file name and location")
    parser.add_argument(
        "-n", "--nologfile", action='store_true',
        help="disable logging to a file")
    parser.add_argument(
        "-c", "--configfile", default="~/Mobileraker.conf", metavar='<configfile>',
        help="Location of the configuration file for Mobileraker Companion"
    )

    cmd_line_args = parser.parse_args()

    version = get_software_version()
    if not cmd_line_args.nologfile:
        setup_logging(os.path.normpath(os.path.expanduser(
            cmd_line_args.logfile)), version)

    logging.info(f"MobilerakerCompanion version: {version}")

    passed_config_location = os.path.normpath(
        os.path.expanduser(cmd_line_args.configfile))

    local_config = CompanionLocalConfig(passed_config_location)

    event_loop = asyncio.get_event_loop()
    fcmc = MobilerakerFcmClient(
        # 'http://127.0.0.1:8080',
        'https://mobileraker.eliteschw31n.de',
        event_loop)
    try:
        printers = local_config.printers
        for printer_name in printers:
            p_config = printers[printer_name]

            jrpc = MoonrakerClient(
                p_config['moonraker_uri'],
                p_config['moonraker_api_key'],
                event_loop)

            snc = SnapshotClient(
                p_config['snapshot_uri'],
                p_config['snapshot_rotation'],
            )

            dsd = DataSyncService(
                jrpc=jrpc,
                loop=event_loop,
            )

            client = MobilerakerCompanion(
                jrpc=jrpc,
                data_sync_service=dsd,
                fcm_client=fcmc,
                snapshot_client=snc,
                printer_name=printer_name,
                loop=event_loop,
                companion_config=local_config,
            )
            event_loop.create_task(client.start())
        event_loop.run_forever()
    finally:
        event_loop.close()
    exit()


if __name__ == '__main__':
    main()
