from asyncio import AbstractEventLoop, sleep
import asyncio
import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional
from mobileraker.client.moonraker_client import MoonrakerClient
from mobileraker.data.dtos.moonraker.printer_objects import DisplayStatus, FilamentSensor, GCodeFile, GCodeMove, PrintStats, ServerInfo, Toolhead, VirtualSDCard
from mobileraker.data.dtos.moonraker.printer_snapshot import PrinterSnapshot
from mobileraker.util.functions import to_klipper_object_identifier


class KlippyNotReadyError(Exception):
    '''
    Exception to be raised when Klippy is not ready after a resync process.
    '''
    pass

class DataSyncService:
    # Static list to define the objects to subscribe for updates if they are available.
    _OBJECTS_TO_SUBSCRIBE = [ 
        "print_stats",
        "display_status",
        "virtual_sdcard",
        "toolhead",
        "gcode_move",
        "gcode_macro TIMELAPSE_TAKE_FRAME",
        "filament_switch_sensor",
        "filament_motion_sensor",
    ]

    '''
    This service is responsible for keeping track of the latest printer data and then
    providing a snapshot of all data to any service that requires it.

    Attributes:
        jrpc (MoonrakerClient): The MoonrakerClient instance used for communication.
        printer_name (str): The name of the printer.
        loop (AbstractEventLoop): The event loop used for handling asynchronous tasks.
        resync_retries (int): The number of retries to perform when resyncing data.
    '''

    def __init__(
            self,
            jrpc: MoonrakerClient,
            printer_name: str,
            loop: AbstractEventLoop,
            resync_retries: int = 30,
    ) -> None:
        super().__init__()
        self._jrpc: MoonrakerClient = jrpc
        self._loop: AbstractEventLoop = loop
        self._logger: logging.Logger = logging.getLogger(f'mobileraker.{printer_name}.sync')
        self._queried_for_session: bool = False
        self._objects: Dict[str, Any] = {}
        self._reset_timelapse_pause: Optional[bool] = None # Helper to reset the timelapse_pause attribute after the printer switched back from paused to printing
        self.klippy_ready: bool = False
        self.server_info: ServerInfo = ServerInfo()
        self.print_stats: PrintStats = PrintStats()
        self.toolhead: Toolhead = Toolhead()
        self.gcode_move: GCodeMove = GCodeMove()
        self.display_status: DisplayStatus = DisplayStatus()
        self.virtual_sdcard: VirtualSDCard = VirtualSDCard()
        self.current_file: Optional[GCodeFile] = None
        self.gcode_response: Optional[str] = None
        self.timelapse_pause: Optional[bool] = None
        self.filament_sensors: Dict[str, FilamentSensor] = {}
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

        self._jrpc.register_method_listener(
            'notify_gcode_response', lambda resp: self._on_gcode_response(resp["params"][0]))

        self._jrpc.register_connection_listener(self._on_jrpc_connection_state)

    def _parse_objects(self, status_objects: Dict[str, Any], err: Optional[str] = None) -> None:
        '''
        Parse status objects and update the corresponding attributes.

        Parameters:
            status_objects (Dict[str, Any]): The dictionary containing status objects.

        Returns:
            None
        '''
        self._logger.debug("Received status update for %s", status_objects)
        fetchMeta = False
        for rawObjectKey, object_data in status_objects.items():
            object_identifier, object_name = to_klipper_object_identifier(rawObjectKey)


            if object_identifier == 'print_stats':
                self.print_stats = self.print_stats.updateWith(object_data)
            
                # If the state is printing and _reset_timelapse_pause is True, we reset the timelapse_pause attribute
                if self.print_stats.state != 'paused' and self._reset_timelapse_pause:
                    self.timelapse_pause = False
                    self._reset_timelapse_pause = False
                    self._logger.info("Printer has unpaused after Timelapse plugin took frame. Resetting timelapse_pause attribute.")

                # When the print_stats object is updated, we need to fetch the metadata for the current file
                fetchMeta = True
            elif object_identifier == 'display_status':
                self.display_status = self.display_status.updateWith(
                    object_data)
            elif object_identifier == 'virtual_sdcard':
                self.virtual_sdcard = self.virtual_sdcard.updateWith(
                    object_data)
            elif object_identifier == 'toolhead':
                self.toolhead = self.toolhead.updateWith(object_data)
            elif object_identifier == 'gcode_move':
                self.gcode_move = self.gcode_move.updateWith(object_data)
            elif object_identifier == 'filament_switch_sensor' or object_identifier == 'filament_motion_sensor':
                if object_name is None:
                    self._logger.warning("Received filament sensor object without name. Skipping...")
                    continue
                
                #check if the sensor is already in the list, if not create a default one and call updateWith
                sensor = self.filament_sensors[object_name] if object_name in self.filament_sensors else FilamentSensor(name= object_name, kind = object_identifier)
                self.filament_sensors[object_name] = sensor.updateWith(object_data)

            elif rawObjectKey == 'gcode_macro TIMELAPSE_TAKE_FRAME':
                if 'is_paused' in object_data:
                    is_paused = object_data['is_paused']
                    if is_paused is True:
                        self.timelapse_pause = True
                        self._reset_timelapse_pause = False
                        self._logger.info("Timelapse plugin has paused the printer. Ignoring the next paused printer state.")
                    elif is_paused is False and self._reset_timelapse_pause is False:
                        # We need to use a helper attribute to reset the timelapse_pause attribute after the printer switched back from paused to printing
                        # This is because the printer state is not (always) updated in the same jrpc notification as the gcode_macro TIMELAPSE_TAKE_FRAME
                        # Which causes a race condition where the timelapse_pause attribute is reset before the printer state is updated.
                        self._reset_timelapse_pause = True
                        self._logger.info("Timelapse plugin took frame. Will reset timelapse_pause attribute after printer-state change.")
                

        # Kinda hacky but this works!
        # It would be better if the _notify_listeners()/sync current file is called in a different context since this method should only parse!
        if fetchMeta:
            self._loop.create_task(self._sync_current_file())
        else:
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
        self._queried_for_session = False
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
        self._queried_for_session = False
        self._notify_listeners()

    def _on_gcode_response(self, response: str) -> None:
        '''
        Handle theGcode Response event.

        Returns:
            None
        '''
        # strip "// " from response as it is always part of the Gcode Response (https://www.klipper3d.org/Command_Templates.html?h=action_respond_info#actions)
        response = response[3:]

        self._logger.debug(
            "Received an Gcode Response from Klippy: %s", response)
        self.gcode_response = response
        self._notify_listeners()

    def _on_jrpc_connection_state(self, is_connected: bool):
        self._logger.info("Connection state changed to <is_connected: %s>", is_connected)
        if is_connected:
            self._loop.create_task(self.resync())
        else:
            self._queried_for_session = False
            self.klippy_ready = False


    async def _sync_klippy_data(self) -> None:
        '''
        Synchronize data with Klippy.

        Returns:
            None
        '''
        try:
            self._logger.info("Syncing klippy Objects")
            response, k_err = await self._jrpc.send_and_receive_method("server.info")
            if k_err:
                self._logger.warning("Could not sync klippy data. Moonraker returned error %s", k_err)
                return

            self._logger.info("Received server info: %s", response)
            self.server_info = self.server_info.updateWith(response['result'])
            self.klippy_ready = self.server_info.klippy_state == 'ready'
        except (asyncio.TimeoutError, ConnectionError) as err:
            self._logger.error("Could not sync klippy data: %s", err)

    async def _sync_printer_data(self) -> None:
        '''
        Synchronize printer data with Moonraker.

        Returns:
            None
        '''
        try:
            self._logger.info("Syncing printer Objects")

            # We need to get all subscribable objects from the printer, as we might not have all of them yet.

            response, k_err = await self._jrpc.send_and_receive_method("printer.objects.list")

            if k_err:
                self._logger.warning("Could not sync printer data. Moonraker returned error while fetching objects list: %s", k_err)
                return

            object_list: List[str] = response["result"]["objects"]

            self._objects = {}
            for obj in object_list:
                object_identifier, _ = to_klipper_object_identifier(obj)
                if object_identifier in self._OBJECTS_TO_SUBSCRIBE or obj in self._OBJECTS_TO_SUBSCRIBE:
                    self._objects[obj] = None

            self._logger.info("Subscribing to printer Objects: %s", self._objects.keys())

            response, k_err = await self._jrpc.send_and_receive_method("printer.objects.query", {"objects": self._objects})
            if k_err:
                self._logger.warning("Could not sync printer data. Moonraker returned error %s", k_err)
                return
            self._parse_objects(response["result"]["status"])
        except (asyncio.TimeoutError, ConnectionError) as err:
            self._logger.error("Could not sync printer data: %s", err)

    async def _sync_current_file(self) -> None:
        '''
        Synchronize the current file with Moonraker.

        Returns:
            None
        '''

        if self.print_stats.filename and (self.current_file is None or self.current_file.filename != self.print_stats.filename):
            self.current_file = await self._fetch_gcode_meta(self.print_stats.filename)
        elif not self.print_stats.filename and self.current_file:
            self.current_file = None

        self._notify_listeners()

    async def _subscribe_for_object_updates(self) -> None:
        '''
        Subscribe to printer objects for updates.

        Returns:
            None
        '''
        self._logger.info("Subscribing to printer Objects")
        await self._jrpc.send_method("printer.objects.subscribe", None, {"objects": self._objects})
        self._logger.info("Subscribed to printer Objects")

    def _notify_listeners(self):
        '''
        Internal method to notify all registered listeners when data changes.

        Returns:
            None
        '''
        snap = self.take_snapshot()
        for callback in self._snapshot_listeners:
            callback(snap)

    async def _resync(self, no_try: int = 0) -> None:
        if no_try >= self.resync_retries:
            raise KlippyNotReadyError(
                f"Resync process was not completed after {no_try} retries. Klippy was not ready after {self.resync_retries} retries.")

        await self._sync_klippy_data()

        if self.klippy_ready:
            await self._sync_printer_data()
        else:
            wait_for = min(pow(2, no_try + 1), 5 * 60)
            self._logger.warning(
                "Klippy was not ready. Trying resync again in %i seconds...", wait_for)
            await sleep(wait_for)
            await self._resync(no_try=no_try + 1)

    async def _fetch_gcode_meta(self, file_name: str) -> Optional[GCodeFile]:
        try:
            self._logger.info("Fetching metadata for %s", file_name)
            meta,  k_err = await self._jrpc.send_and_receive_method('server.files.metadata', {'filename': file_name})
            if k_err:
                self._logger.warning("Could not fetch metadata for %s. Moonraker returned error %s", file_name, k_err)

                # If just no metadata is available, we return a GCodeFile instance with empty metadata, this prevents the service from fetching the metadata again.
                if ('Metadata not availabe for' in k_err):
                    self._logger.warning("No metadata available for %s, returning empty GCodeFile instance", file_name)
                    return GCodeFile(filename=file_name)
                
                return None
            self._logger.debug("Metadata for %s: %s", file_name, meta)
            return GCodeFile.from_json(meta['result'])
        except (asyncio.TimeoutError, ConnectionError) as err:
            self._logger.error(
                "Could not fetch metadata for %s: %s", file_name, err)
            return None

    async def resync(self) -> None:
        '''
        Perform a (Re)Sync with Moonraker.

        Returns:
            None
        '''
        try:
            self._logger.info("Doing a (Re)Sync with moonraker")
            self.server_info: ServerInfo = ServerInfo()
            self.print_stats: PrintStats = PrintStats()
            self.toolhead: Toolhead = Toolhead()
            self.gcode_move: GCodeMove = GCodeMove()
            self.display_status: DisplayStatus = DisplayStatus()
            self.virtual_sdcard: VirtualSDCard = VirtualSDCard()
            self.current_file: Optional[GCodeFile] = None
            self.gcode_response: Optional[str] = None
            self.timelapse_pause: Optional[bool] = None
            self.filament_sensors: Dict[str, FilamentSensor] = {}

            await self._resync()
            # We only subscribe for updates if Klippy is ready
            if self.klippy_ready and not self._queried_for_session:
                self._queried_for_session = True
                await self._subscribe_for_object_updates()
            else:
                self._logger.warning("Not subscribing to updates because either klippy was not ready or session already subed. klippy_ready: %s, _queried_for_session: %s", self.klippy_ready, self._queried_for_session)   

            self._logger.info("(Re)Sync completed")
        except KlippyNotReadyError:
            self._logger.error("Resync process was not completed. Klippy was not ready after %i retries.", self.resync_retries)
        except asyncio.TimeoutError:
            self._logger.warning("Timeout error occured while resyncing...")
        except ConnectionError:
            self._logger.warning("Connection error occured while resyncing...")
        except asyncio.CancelledError:
            self._logger.info("Resync task was cancelled")

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
        snapshot.print_stats = self.print_stats
        snapshot.virtual_sdcard = self.virtual_sdcard
        snapshot.toolhead = self.toolhead
        snapshot.gcode_move = self.gcode_move
        snapshot.current_file = self.current_file
        snapshot.m117 = self.display_status.message
        snapshot.m117_hash = hashlib.sha256(snapshot.m117.encode(
            "utf-8")).hexdigest() if snapshot.m117 else ''
        snapshot.gcode_response = self.gcode_response
        snapshot.gcode_response_hash = hashlib.sha256(snapshot.gcode_response.encode(
            "utf-8")).hexdigest() if snapshot.gcode_response else ''
        snapshot.timelapse_pause = self.timelapse_pause
        snapshot.filament_sensors = dict(self.filament_sensors)

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
