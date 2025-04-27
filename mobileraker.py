import asyncio
import argparse
import logging
import os
import sys
from asyncio import AbstractEventLoop

from mobileraker.client.mobileraker_fcm_client import MobilerakerFcmClient
from mobileraker.client.moonraker_client import MoonrakerClient
from mobileraker.client.webcam_snapshot_client import WebcamSnapshotClient
from mobileraker.mobileraker_companion import MobilerakerCompanion
from mobileraker.service.data_sync_service import DataSyncService
from mobileraker.util.configs import CompanionLocalConfig, printer_data_logs_dir
from mobileraker.util.functions import get_software_version
from mobileraker.util.logging import setup_logging


# Main entry point
async def main(args):
    # Parse arguments
    parser = argparse.ArgumentParser(description="MobilerakerCompanion - An app for push notifications for Klipper/Moonraker")
    parser.add_argument(
        "-l", "--logfile", default=os.path.join(printer_data_logs_dir if os.path.exists(printer_data_logs_dir) else '/tmp', "mobileraker.log"), metavar='<logfile>',
        help="Log File Location or log file absolute path")
    parser.add_argument(
        "-n", "--nologfile", action='store_true',
        help="disable logging to a file")
    parser.add_argument(
        "-c", "--configfile", default="~/Mobileraker.conf", metavar='<configfile>',
        help="Location of the configuration file for Mobileraker Companion"
    )
    
    parsed_args = parser.parse_args(args)

    version = get_software_version()

    # Setup logging
    if not parsed_args.nologfile:
        setup_logging(os.path.normpath(os.path.expanduser(
            parsed_args.logfile)), version)
    
    logging.info(f"MobilerakerCompanion version: {version}")
    
    # Load the config
    config = CompanionLocalConfig(parsed_args.configfile)
    
    # Get the event loop
    loop = asyncio.get_event_loop()
    
    try:
        # Create a task for each printer
        tasks = []
        for printer_name, printer_cfg in config.printers.items():
            task = loop.create_task(
                setup_printer_companion(
                    printer_name,
                    printer_cfg,
                    config,
                    loop
                )
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logging.exception(f"Unhandled exception: {e}")
    finally:
        # Close the event loop
        loop.close()


async def setup_printer_companion(
    printer_name: str,
    printer_cfg: dict,
    companion_config: CompanionLocalConfig,
    loop: AbstractEventLoop
):
    """
    Set up the MobilerakerCompanion for a specific printer.
    
    Args:
        printer_name (str): The name of the printer.
        printer_cfg (dict): The printer configuration.
        companion_config (CompanionLocalConfig): The companion configuration.
        loop (AbstractEventLoop): The event loop.
    """
    moonraker_uri = printer_cfg["moonraker_uri"]
    moonraker_api_key = printer_cfg["moonraker_api_key"]
    snapshot_uri = printer_cfg["snapshot_uri"]
    snapshot_rotation = printer_cfg["snapshot_rotation"]
    exclude_sensors = printer_cfg["excluded_filament_sensors"]
    
    # Create the JRPC client
    jrpc = MoonrakerClient(
        moonraker_uri=moonraker_uri,
        moonraker_api=moonraker_api_key,
        printer_name=printer_name,
        loop=loop
    )
    
    # Create the data sync service
    data_sync_service = DataSyncService(
        jrpc=jrpc,
        printer_name=printer_name,
        loop=loop
    )
    
    # Create the FCM client
    fcm_client  = MobilerakerFcmClient(
        # 'http://127.0.0.1:8080',
        'https://mobileraker.eliteschw31n.de',
        loop)
    
    # Create the default snapshot client (will be used as fallback)
    snapshot_client = WebcamSnapshotClient(
        uri_or_data=snapshot_uri,
        rotation=snapshot_rotation
    )
    
    # Create the MobilerakerCompanion
    companion = MobilerakerCompanion(
        jrpc=jrpc,
        data_sync_service=data_sync_service,
        fcm_client=fcm_client,
        webcam_snapshot_client=snapshot_client,
        printer_name=printer_name,
        loop=loop,
        companion_config=companion_config,
        exclude_sensors=exclude_sensors
    )
    
    logging.info("Starting MobilerakerCompanion for printer: %s", printer_name)
    await companion.start()
    
    # Keep the task running
    while True:
        await asyncio.sleep(3600)  # Sleep for an hour and check again


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))