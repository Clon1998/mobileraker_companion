from asyncio import AbstractEventLoop, sleep
import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional, cast
from mobileraker.client.moonraker_client import MoonrakerClient
from mobileraker.data.dtos.moonraker.printer_objects import DisplayStatus, PrintStats, ServerInfo, VirtualSDCard
from mobileraker.data.dtos.moonraker.printer_snapshot import PrinterSnapshot


class DataSyncService:
    '''
    This service is responsible for keeping track of the latest printer data and then
    providing a snapshot of all data to any service that requires it.

    Attributes:
        jrpc (MoonrakerClient): The MoonrakerClient instance used for communication.
        loop (AbstractEventLoop): The event loop used for handling asynchronous tasks.
        klippy_ready (bool): A flag indicating whether Klippy is ready or not.
        server_info (ServerInfo): An instance of ServerInfo to hold server-related data.
        print_stats (PrintStats): An instance of PrintStats to hold printer stats data.
        display_status (DisplayStatus): An instance of DisplayStatus to hold display status data.
        virtual_sdcard (VirtualSDCard): An instance of VirtualSDCard to hold virtual SD card data.
    '''

    def __init__(
            self,
            jrpc: MoonrakerClient,
            loop: AbstractEventLoop,
            resync_retries: int = 30,
    ) -> None:
        super().__init__()
        self._jrpc: MoonrakerClient = jrpc
        self._loop: AbstractEventLoop = loop
        self._logger: logging.Logger = logging.getLogger('mobileraker.sync')
        self.klippy_ready: bool = False
        self.server_info: ServerInfo = ServerInfo()
        self.print_stats: PrintStats = PrintStats()
        self.display_status: DisplayStatus = DisplayStatus()
        self.virtual_sdcard: VirtualSDCard = VirtualSDCard()
        self.resync_retries: int = resync_retries

        self._snapshot_listeners: List[Callable[[PrinterSnapshot], None]] = []

        self._jrpc.register_method_listener(
            'notify_status_update', lambda resp: self._parse_objects(resp["params"][0]))

        self._jrpc.register_method_listener(
            'notify_klippy_ready', lambda resp: self._on_klippy_ready())

        self._jrpc.register_method_listener(
            'notify_klippy_shutdown', lambda resp: self._on_klippy_shutdown())

        self._jrpc.register_method_listener(
            'notify_klippy_disconnected', lambda resp: self._on_klippy_disconnected())

        self._jrpc.register_connection_listener(
            lambda is_conncected: self._loop.create_task(self._jrpc_connection_listener(is_conncected)))

    def _parse_objects(self, status_objects: Dict[str, Any], err: Optional[str] = None) -> None:
        '''
        Parse status objects and update the corresponding attributes.

        Parameters:
            status_objects (Dict[str, Any]): The dictionary containing status objects.

        Returns:
            None
        '''
        self._logger.debug("Received status update for %s", status_objects)
        for key, object_data in status_objects.items():
            if key == 'print_stats':
                self.print_stats = self.print_stats.updateWith(object_data)
            elif key == 'display_status':
                self.display_status = self.display_status.updateWith(
                    object_data)
            elif key == 'virtual_sdcard':
                self.virtual_sdcard = self.virtual_sdcard.updateWith(
                    object_data)

        self._notify_listeners()

    def _on_klippy_ready(self) -> None:
        '''
        Handle the Klippy ready event.

        Returns:
            None
        '''
        self._logger.info("Klippy has reported a ready state")
        self._loop.create_task(self.resync())

    def _on_klippy_shutdown(self) -> None:
        '''
        Handle the Klippy shutdown event.

        Returns:
            None
        '''
        self._logger.info("Klippy has reported a shutdown state")
        self.klippy_ready = False
        self._notify_listeners()

    def _on_klippy_disconnected(self) -> None:
        '''
        Handle the Klippy disconnected event.

        Returns:
            None
        '''
        self._logger.info(
            "Moonraker's connection to Klippy has terminated/disconnected")
        self.klippy_ready = False
        self._notify_listeners()

    async def _sync_klippy_data(self) -> None:
        '''
        Synchronize data with Klippy.

        Returns:
            None
        '''
        self._logger.info("Syncing klippy Objects")
        response, err = await self._jrpc.send_and_receive_method("server.info")
        self.server_info = self.server_info.updateWith(response['result'])
        self.klippy_ready = self.server_info.klippy_state == 'ready'

    async def _sync_printer_data(self) -> None:
        '''
        Synchronize printer data with Moonraker.

        Returns:
            None
        '''
        self._logger.info("Syncing printer Objects")
        params = {
            "objects": {
                "print_stats": None,
                # "display_status": None,
                "virtual_sdcard": None
            }
        }
        response, err = await self._jrpc.send_and_receive_method("printer.objects.query", params)
        self._parse_objects(response["result"]["status"])

    async def _subscribe_for_object_updates(self) -> None:
        '''
        Subscribe to printer objects for updates.

        Returns:
            None
        '''
        self._logger.info("Subscribing to printer Objects")
        params = {
            "objects": {
                "print_stats": None,
                "display_status": None,
                "virtual_sdcard": None
            }
        }
        await self._jrpc.send_method("printer.objects.subscribe", None, params)

    def _notify_listeners(self):
        '''
        Internal method to notify all registered listeners when data changes.

        Returns:
            None
        '''
        snap = self.take_snapshot()
        for callback in self._snapshot_listeners:
            callback(snap)

    async def _jrpc_connection_listener(self, is_connected: bool):
        if is_connected:
            try:
                await self.resync()
                await self._subscribe_for_object_updates()
            except TimeoutError as err:
                self._logger.error("Could not setup sync client: %s", err)

    async def _resync(self, no_try: int = 0) -> None:
        if no_try >= self.resync_retries:
            raise TimeoutError(
                f"Resync process was not completed after {no_try} retries.")

        await self._sync_klippy_data()

        if self.klippy_ready:
            await self._sync_printer_data()
        else:
            wait_for = min(pow(2, no_try + 1), 5 * 60)
            self._logger.warning(
                "Klippy was not ready. Trying resync again in %i seconds...", wait_for)
            await sleep(wait_for)
            await self._resync(no_try=no_try + 1)

    async def resync(self) -> None:
        '''
        Perform a (Re)Sync with Moonraker.

        Returns:
            None
        '''
        self._logger.info("Doing a (Re)Sync with moonraker")
        await self._resync()
        self._logger.info("(Re)Sync completed")

    def take_snapshot(self) -> PrinterSnapshot:
        '''
        Take a snapshot of the current printer data.

        Returns:
            PrinterSnapshot: An instance of PrinterSnapshot representing the current printer data.
        '''
        # Create a new PrinterSnapshot instance with the current Klippy state or "error" if Klippy is not ready.
        snapshot = PrinterSnapshot(self.klippy_ready,
                                   self.print_stats.state if self.klippy_ready else "error")

        # Update the snapshot attributes with relevant data
        snapshot.filename = self.print_stats.filename
        snapshot.m117 = self.display_status.message
        snapshot.m117_hash = hashlib.sha256(snapshot.m117.encode(
            "utf-8")).hexdigest() if snapshot.m117 else ''

        # If the printer is currently printing, update progress and printing duration
        if self.print_stats.state == "printing":
            snapshot.progress = round(self.virtual_sdcard.progress * 100)
            snapshot.printing_duration = self.print_stats.print_duration

        self._logger.debug('Took a PrinterSnapshot: %s', snapshot)
        return snapshot

    def register_snapshot_listener(self, callback: Callable[[PrinterSnapshot], Any]) -> None:
        '''
        Register a callback function to be called whenever data changes in the service.

        Parameters:
            callback (Callable[[PrinterSnapshot], None]): The callback function to be registered.

        Returns:
            None
        '''
        self._snapshot_listeners.append(callback)
