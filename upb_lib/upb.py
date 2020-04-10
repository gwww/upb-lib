"""Master class that combines all UPB pieces together."""

import asyncio
import logging
from functools import partial

import serial_asyncio

from .devices import UpbDevices
from .links import Links
from .message import MessageDecode
from .parse_upstart import process_upstart_file
from .proto import Connection
from .util import parse_flags, parse_url

LOG = logging.getLogger(__name__)


class UpbPim:
    """Represents all the components on an UPB PIM."""

    def __init__(self, config, loop=None):
        """Initialize a new PIM instance."""
        self.loop = loop if loop else asyncio.get_event_loop()
        self._config = config
        self._conn = None
        self._transport = None
        self.connection_lost_callbk = None
        self._connection_retry_timer = 1
        self._message_decode = MessageDecode()
        self._sync_handlers = []
        self._heartbeat = None
        self.flags = {}
        self.devices = UpbDevices(self)
        self.links = Links(self)

        self.flags = parse_flags(config.get("flags", ""))

        # Setup for all the types of elements tracked
        export_filepath = config.get("UPStartExportFile")
        if export_filepath:
            process_upstart_file(self, config["UPStartExportFile"])

    async def _connect(self, connection_lost_callbk=None):
        """Asyncio connection to UPB."""
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
            self.loop.call_later(self._connection_retry_timer, self.connect)
            self._connection_retry_timer = (
                2 * self._connection_retry_timer
                if self._connection_retry_timer < 32
                else 60
            )

    def _connected(self, transport, conn):
        """Sync the UPB PIM network to memory."""
        LOG.info("Connected to UPB PIM")
        self._conn = conn
        self._transport = transport
        self._connection_retry_timer = 1

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
        self._transport.close()
        self._heartbeat = None

    def _disconnected(self):
        LOG.warning("PIM at %s disconnected", self._config["url"])
        self._conn = None
        self.loop.call_later(self._connection_retry_timer, self.connect)
        if self._heartbeat:
            self._heartbeat.cancel()
            self._heartbeat = None

    def add_handler(self, msg_type, handler):
        self._message_decode.add_handler(msg_type, handler)

    def _got_data(self, data):  # pylint: disable=no-self-use
        try:
            if data[:2] == "~~":
                if data == "~~PAUSE":
                    LOG.info("PAUSE connection")
                    self.pause()
                elif data == "~~RESUME":
                    LOG.info("RESUME connection")
                    self.resume()
                    self.call_sync_handlers()
                elif data == "~~HEARTBEAT":
                    if self._heartbeat:
                        self._heartbeat.cancel()
                    self._heartbeat = self.loop.call_later(90, self._reset_connection)
            else:
                self._message_decode.decode(data)
        except (ValueError, AttributeError) as err:
            LOG.debug(err)

    def _timeout(self, msg_code):
        LOG.warning(f"Timeout communicating with UPB device {msg_code}")
        pass

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
        return self._conn is not None

    def connect(self):
        """Connect to the panel"""
        asyncio.ensure_future(self._connect())

    def run(self):
        """Enter the asyncio loop."""
        self.loop.run_forever()

    def send(self, msg, response_required=True, raw=False):
        """Send a message to UPB PIM."""
        if self._conn:
            self._conn.write_data(msg, response_required, raw=raw)

    def pause(self):
        """Pause the connection from sending/receiving."""
        if self._conn:
            self._conn.pause()

    def resume(self):
        """Restart the connection from sending/receiving."""
        if self._conn:
            self._conn.resume()
