"""Master class that combines all UPB pieces together."""

import asyncio
import logging
from functools import partial

import serial_asyncio

from .devices import UpbAddr, UpbDevices
from .links import Links
from .message import MessageDecode
from .parse_upstart import process_upstart_file
from .proto import Connection
from .util import parse_flags, parse_url

LOG = logging.getLogger(__name__)


class UpbPim:
    """Represents all the components on an UPB PIM."""

    # pylint: disable=too-many-instance-attributes
    def __init__(self, config, loop=None):
        """Initialize a new PIM instance."""
        self.loop = loop if loop else asyncio.get_event_loop()
        self._config = config
        self._connection = None
        self._connection_retry_timer = 1
        self._connection_retry_task = None
        self._message_decode = MessageDecode()
        self._sync_handlers = []
        self._disconnect_requested = False
        self._heartbeat = None

        self.flags = {}
        self.devices = UpbDevices(self)
        self.links = Links(self)
        self.config_ok = True
        self.network_id = None
        self.connection_lost_callbk = None
        self.connected_callbk = None

        self.flags = parse_flags(config.get("flags", ""))

        # Setup for all the types of elements tracked
        export_filepath = config.get("UPStartExportFile")
        if export_filepath:
            self.config_ok = process_upstart_file(self, config["UPStartExportFile"])

    async def _connect(self, connected_callbk=None, connection_lost_callbk=None):
        """Asyncio connection to UPB."""
        self.connected_callbk = connected_callbk
        self.connection_lost_callbk = connection_lost_callbk
        url = self._config["url"]
        LOG.info("Connecting to UPB PIM at %s", url)
        scheme, dest, param = parse_url(url)
        conn = partial(
            Connection,
            self.loop,
            self._connected,
            self._disconnected,
            self._got_data,
            self._timeout,
        )
        try:
            if scheme == "serial":
                await serial_asyncio.create_serial_connection(
                    self.loop, conn, dest, baudrate=param
                )
            else:
                await asyncio.wait_for(
                    self.loop.create_connection(conn, host=dest, port=param, ssl=None),
                    timeout=5,
                )
        except (ValueError, OSError, asyncio.TimeoutError) as err:
            LOG.warning(
                "Could not connect to UPB PIM (%s). Retrying in %d seconds",
                err,
                self._connection_retry_timer,
            )
            self._connection_retry_task = self.loop.call_later(
                self._connection_retry_timer, self.connect
            )
            self._connection_retry_timer = (
                2 * self._connection_retry_timer
                if self._connection_retry_timer < 32
                else 60
            )

    def _connected(self, conn):
        """Sync the UPB PIM network to memory."""
        LOG.info("Connected to UPB PIM")
        self._connection = conn
        self._connection_retry_timer = 1
        if self.connected_callbk:
            self.connected_callbk()
        self._connection_status_change("connected")

        # The intention of this is to clear anything in the PIM receive buffer.
        # A number of times on startup error(s) (PE) are returned. This too will
        # return an error, but hopefully resets the PIM
        self.send("", response_required=False, raw=True)

        if self.flags.get("no_sync"):
            LOG.warning("Initial device sync turned off")
        else:
            self.call_sync_handlers()

    def _reset_connection(self):
        LOG.warning("PIM connection heartbeat timed out, disconnecting")
        self._connection.close()
        self._heartbeat = None

    def _disconnected(self):
        LOG.warning("PIM at %s disconnected", self._config["url"])
        self._connection = None
        self._connection_status_change("disconnected")
        if self.connection_lost_callbk:
            self.connection_lost_callbk()
        if self._heartbeat:
            self._heartbeat.cancel()
            self._heartbeat = None
        if not self._disconnect_requested:
            self._connection_retry_task = self.loop.call_later(
                self._connection_retry_timer, self.connect
            )

    def add_handler(self, msg_type, handler):
        """Add handler for a message type."""
        self._message_decode.add_handler(msg_type, handler)

    def _got_data(self, data):  # pylint: disable=no-self-use
        try:
            if data[:2] == "~~":
                self._handle_control_command(data)
            else:
                self._message_decode.decode(data)
        except (ValueError, AttributeError) as err:
            LOG.debug(err)

    def _handle_control_command(self, data):
        log_msg = data[2:].lower().replace("_", " ")
        if data == "~~PAUSE" or data.startswith("~~SERIAL_DISCONNECTED"):
            LOG.info("Pausing connection (%s)", log_msg)
            self.pause()
        elif data in ["~~RESUME", "~~SERIAL_CONNECTED"]:
            LOG.info("Resuming connection (%s)", log_msg)
            self.resume()
            self.call_sync_handlers()
        elif data == "~~HEARTBEAT":
            if self._heartbeat:
                self._heartbeat.cancel()
            self._heartbeat = self.loop.call_later(90, self._reset_connection)
        elif data == "~~ANOTHER_TCP_CLIENT_IS_CONNECTED":
            self._connection_retry_timer = 60
            LOG.warning("%s to ser2tcp, disconnecting", log_msg)

    def _connection_status_change(self, status):
        self.devices.connection_status_change(status)
        self.links.connection_status_change(status)

    def _timeout(self, kind, addr):
        if kind == "PIM":
            LOG.warning("Timeout communicating with PIM, is it connected?")
        else:
            device_id = UpbAddr(int(addr[0:2], 16), int(addr[2:4], 16), 0).index
            device = self.devices.elements.get(device_id)
            if device:
                LOG.warning(
                    "Timeout communicating with UPB device '%s' (%s)",
                    device.name,
                    device_id,
                )
            else:
                LOG.warning("Timeout communicating with UPB device %s", device_id)

    def add_sync_handler(self, sync_handler):
        """Register a fn that synchronizes elements."""
        self._sync_handlers.append(sync_handler)

    def call_sync_handlers(self):
        """Invoke the synchronization handlers."""
        LOG.debug("Synchronizing status of UPB network...")
        for sync_handler in self._sync_handlers:
            sync_handler()

    def is_connected(self):
        """Status of connection to PIM."""
        return self._connection is not None and not self._connection.is_paused()

    def connect(self, connected_callbk=None, connection_lost_callbk=None):
        """Connect to the panel"""
        self._disconnect_requested = False
        asyncio.ensure_future(self._connect(connected_callbk, connection_lost_callbk))

    def disconnect(self):
        """Disconnect the connection from sending/receiving."""
        self._disconnect_requested = True
        if self._connection:
            self._connection.close()
            self._connection = None
        if self._connection_retry_task:
            self._connection_retry_task.cancel()
            self._connection_retry_task = None
        if self._heartbeat:
            self._heartbeat.cancel()
            self._heartbeat = None

    def run(self):
        """Enter the asyncio loop."""
        self.loop.run_forever()

    def send(self, msg, response_required=True, raw=False):
        """Send a message to UPB PIM."""
        if self._connection:
            self._connection.write_data(msg, response_required, raw=raw)

    def pause(self):
        """Pause the connection from sending/receiving."""
        if self._connection:
            self._connection_status_change("paused")
            self._connection.pause()

    def resume(self):
        """Restart the connection from sending/receiving."""
        if self._connection:
            self._connection_status_change("resume")
            self._connection.resume()
