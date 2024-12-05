"""Master class that combines all UPB pieces together."""

import asyncio
import logging
from functools import partial

import serial_asyncio_fast

from .const import PimCommand
from .devices import UpbAddr, UpbDevices
from .links import Links
from .message import MessageDecode, MessageEncode
from .parse_upstart import process_upstart_file
from .proto import Connection
from .util import parse_flags, parse_url

LOG = logging.getLogger(__name__)


class UpbPim:
    """Represents all the components on an UPB PIM."""

    # pylint: disable=too-many-instance-attributes
    def __init__(self, config, loop=None):
        """Initialize a new PIM instance."""
        self.flags = parse_flags(config.get("flags", ""))
        LOG.info("Using flags: %s", str(self.flags))
        self._decoder = MessageDecode()
        self.encoder = MessageEncode(config.get("tx_count", 1))

        self.loop = loop if loop else asyncio.get_event_loop()
        self._config = config
        self._connection = None
        self._connection_retry_time = 1
        self._reconnect_task = None
        self._sync_handlers = []

        self.devices = UpbDevices(self)
        self.links = Links(self)
        self.config_ok = False
        self.network_id = None
        self.connected_callbk = None

    async def _connect(self, connected_callbk=None):
        """Asyncio connection to UPB."""

        if not self.config_ok:
            # Setup for all the types of elements tracked
            export_filepath = self._config.get("UPStartExportFile")
            if export_filepath:
                # Load config from the UPStart file (run in executor to avoid blocking IO)
                self.config_ok = await asyncio.get_running_loop().run_in_executor(
                    None, process_upstart_file, self, export_filepath
                )
                if self.flags.get("tx_count"):
                    self.encoder.tx_count = self.flags["tx_count"]

        self.connected_callbk = connected_callbk
        url = self._config["url"]
        LOG.info("Connecting to UPB PIM at %s", url)
        scheme, dest, param = parse_url(url)
        heartbeat_time = (
            self.flags.get("heartbeat_timeout_sec", 90) if scheme == "tcp" else -1
        )
        conn = partial(
            Connection,
            self.loop,
            heartbeat_time,
            self._connected,
            self._disconnected,
            self._got_data,
            self._timeout,
        )
        try:
            if scheme == "serial":
                await serial_asyncio_fast.create_serial_connection(
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
                self._connection_retry_time,
            )
            self._start_connection_retry_timer()

    def _start_connection_retry_timer(self):
        timeout = self._connection_retry_time
        if timeout > 0:
            self._reconnect_task = self.loop.call_later(timeout, self.connect)
            self._connection_retry_time = min(timeout * 2, 60)

    def _connected(self, conn):
        """Sync the UPB PIM network to memory."""
        LOG.info("Connected to UPB PIM")
        self._connection = conn
        self._connection_retry_time = 1
        if self.connected_callbk:
            self.connected_callbk()
        self._connection_status_change("connected")

        # The intention of this is to clear anything in the PIM receive buffer.
        # A number of times on startup error(s) (PE) are returned. This too will
        # return an error, but hopefully resets the PIM
        self.send("", response_required=False, command=None)
        # Ensure we're in "message" (and not "pulse") mode.
        # See PCS PIM Protocol 2.2.3
        self.send(
            "70028E", response_required=False, command=PimCommand.WRITE_PIM_REGISTERS
        )

        if self.flags.get("no_sync"):
            LOG.warning("Initial device sync turned off")
        else:
            self.call_sync_handlers()

    def _disconnected(self):
        LOG.warning("PIM at %s disconnected", self._config["url"])
        self._connection = None
        self._connection_status_change("disconnected")
        self._start_connection_retry_timer()

    def add_handler(self, msg_type, handler):
        """Add handler for a message type."""
        self._decoder.add_handler(msg_type, handler)

    def _got_data(self, data):  # pylint: disable=no-self-use
        try:
            if data[:2] == "~~":
                self._handle_control_command(data)
            else:
                self._decoder.handle(data)
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
        elif data == "~~ANOTHER_TCP_CLIENT_IS_CONNECTED":
            self._connection_retry_time = 60
            LOG.warning("%s to ser2tcp, disconnecting", log_msg)

    def _connection_status_change(self, status):
        self.devices.connection_status_change(status)
        self.links.connection_status_change(status)
        self._decoder.call_handlers(status, {})

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

    def connect(self, connected_callbk=None):
        """Connect to the PIM"""
        asyncio.ensure_future(self._connect(connected_callbk))

    async def async_connect(self, connected_callbk=None):
        """Connect to the PIM"""
        await self._connect(connected_callbk)

    def disconnect(self):
        """Disconnect the connection from sending/receiving."""
        self._connection_retry_time = -1  # Stop from reconnecting automatically
        if self._connection:
            self._connection.close()
            self._connection = None
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

    def run(self):
        """Enter the asyncio loop."""
        self.loop.run_forever()

    def send(self, msg, response_required=True, command=PimCommand.TX_UPB_MSG):
        """Send a message to UPB PIM."""
        if self._connection:
            self._connection.write_data(command, msg, response_required)

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
