import asyncio
import unittest
from unittest.mock import MagicMock

from mobileraker.client.moonraker_client import MoonrakerClient
from mobileraker.data.dtos.moonraker.printer_objects import DisplayStatus, PrintStats, ServerInfo, VirtualSDCard
from mobileraker.data.dtos.moonraker.printer_snapshot import PrinterSnapshot
from mobileraker.service.data_sync_service import DataSyncService


class TestDataSyncService(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.jrpc = MagicMock()
        self.data_sync_service = DataSyncService(self.jrpc, self.loop, 2)

    def test_initialization(self):
        self.assertFalse(self.data_sync_service.klippy_ready)
        self.assertIsInstance(self.data_sync_service.server_info, ServerInfo)
        self.assertIsInstance(self.data_sync_service.print_stats, PrintStats)
        self.assertIsInstance(
            self.data_sync_service.display_status, DisplayStatus)
        self.assertIsInstance(
            self.data_sync_service.virtual_sdcard, VirtualSDCard)

    def test_parse_objects_with_print_stats(self):
        status_objects = {
            "print_stats": {"filename": "test.gcode", "state": "printing"}
        }
        self.data_sync_service._parse_objects(status_objects)
        self.assertEqual(
            self.data_sync_service.print_stats.filename, "test.gcode")
        self.assertEqual(self.data_sync_service.print_stats.state, "printing")

    def test_parse_objects_with_display_status(self):
        status_objects = {
            "display_status": {"message": "Printing in progress"}
        }
        self.data_sync_service._parse_objects(status_objects)
        self.assertEqual(
            self.data_sync_service.display_status.message, "Printing in progress")

    def test_parse_objects_with_virtual_sdcard(self):
        status_objects = {
            "virtual_sdcard": {"progress": 0.5}
        }
        self.data_sync_service._parse_objects(status_objects)
        self.assertEqual(self.data_sync_service.virtual_sdcard.progress, 0.5)

    def test_parse_objects_with_all_status_objects(self):
        status_objects = {
            "print_stats": {"filename": "test.gcode", "state": "printing"},
            "display_status": {"message": "Printing in progress"},
            "virtual_sdcard": {"progress": 0.5}
        }
        self.data_sync_service._parse_objects(status_objects)
        self.assertEqual(
            self.data_sync_service.print_stats.filename, "test.gcode")
        self.assertEqual(self.data_sync_service.print_stats.state, "printing")
        self.assertEqual(
            self.data_sync_service.display_status.message, "Printing in progress")
        self.assertEqual(self.data_sync_service.virtual_sdcard.progress, 0.5)

    def test_parse_objects_with_no_status_objects(self):
        status_objects = {}
        self.data_sync_service._parse_objects(status_objects)
        # Verify that the attributes are not changed
        self.assertIsNone(self.data_sync_service.print_stats.filename)
        self.assertEqual(self.data_sync_service.print_stats.state, "error")
        self.assertIsNone(self.data_sync_service.display_status.message)
        self.assertEqual(self.data_sync_service.virtual_sdcard.progress, 0)

    def test_resync_with_parse_objects(self):
        # Simulate status objects returned by the MoonrakerClient
        status_objects = {
            "print_stats": {"filename": "test.gcode", "state": "printing"},
            "display_status": {"message": "Printing in progress"},
            "virtual_sdcard": {"progress": 0.5}
        }

        # Set the side_effect for send_and_receive_method to return the status_objects
        async def mock_send_and_receive_method(method, params=None):
            if method == "server.info":
                return {"result": {"klippy_state": "ready"}}, None
            elif method == "printer.objects.query":
                return {"result": {"status": status_objects}}, None

        self.jrpc.send_and_receive_method.side_effect = mock_send_and_receive_method

        # Call resync and verify the updated attributes using public methods
        self.loop.run_until_complete(self.data_sync_service.resync())

        self.assertEqual(
            self.data_sync_service.print_stats.filename, "test.gcode")
        self.assertEqual(
            self.data_sync_service.print_stats.state, "printing")
        self.assertEqual(
            self.data_sync_service.display_status.message, "Printing in progress")
        self.assertEqual(
            self.data_sync_service.virtual_sdcard.progress, 0.5)

    def test_resync_klippy_ready(self):
        # Test resync when Klippy is ready
        async def mock_send_and_receive_method(method, params=None):
            if method == "server.info":
                return {"result": {"klippy_state": "ready"}}, None
            elif method == "printer.objects.query":
                return {"result": {"status": {}}}, None

        self.jrpc.send_and_receive_method.side_effect = mock_send_and_receive_method

        self.loop.run_until_complete(self.data_sync_service.resync())

        # Assert that the data is updated correctly after resync
        self.assertTrue(self.data_sync_service.klippy_ready)
        # Add more assertions for other updated attributes if applicable

    # def test_resync_klippy_not_ready(self):
    #     # Test resync when Klippy is not ready and then becomes ready after a few retries
    #     async def mock_non_ready(method, params=None):
    #         return {"result": {"klippy_state": "not_ready"}}, None

    #     async def mock_ready(method, params=None):
    #         return {"result": {"klippy_state": "not_ready"}}, None

    #     async def mock_printer_query(method, params=None):
    #         return {"result": {"status": {}}}, None

    #     self.jrpc.send_and_receive_method.side_effect = [
    #         mock_non_ready, mock_ready, mock_printer_query]

    #     # Run resync and assert that it eventually becomes ready after retries
    #     self.loop.run_until_complete(self.data_sync_service.resync())
    #     self.assertTrue(self.data_sync_service.klippy_ready)

    def test_resync_klippy_not_ready_timeout(self):
        # Test resync when Klippy is not ready and it times out after 2 retries
        async def mock_send_and_receive_method(method, params=None):
            if method == "server.info":
                return {"result": {"klippy_state": "not_ready"}}, None

        self.jrpc.send_and_receive_method.side_effect = mock_send_and_receive_method

        # Run resync and assert that it raises TimeoutError after 2 retries
        with self.assertRaises(TimeoutError):
            self.loop.run_until_complete(self.data_sync_service.resync())

    # Add more test cases for other methods as needed

    # Add more unit tests for other methods if needed


if __name__ == '__main__':
    unittest.main()
