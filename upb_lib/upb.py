"""Main class that combines all UPB pieces together."""

import asyncio
import logging
from typing import Any

from .connection import Connection
from .const import PimCommand
from .devices import UpbAddr, UpbDevices
from .links import Links
from .message import MessageEncode
from .notify import Notifier, NotifyHandler
from .parse_upstart import process_upstart_file
from .util import parse_flags

LOG = logging.getLogger(__name__)


class UpbPim:
    """Represents all the components on an UPB PIM."""

    # pylint: disable=too-many-instance-attributes
    def __init__(
        self, config: dict[str, Any], loop: asyncio.AbstractEventLoop | None = None
    ) -> None:
        """Initialize a new Elk instance."""
        self._config = config
        if not loop:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        self._loop = loop

        self.flags = parse_flags(config.get("flags", ""))

        self._notifier = Notifier()
        self._connection = Connection(config["url"], self._notifier)

        self.encoder = MessageEncode(config.get("tx_count", 1))
        self.devices = UpbDevices(self)
        self.links = Links(self)
        self.config_ok = True
        self.network_id = None

        self._notifier.attach("connected", self._connected)
        self._notifier.attach("disconnected", self._disconnected)
        self._notifier.attach("timeout", self._timeout)

    async def load_upstart_file(self):
        """Parse and load the UPStart UPE export file"""
        if path := self._config.get("UPStartExportFile"):
            self.config_ok = await asyncio.get_running_loop().run_in_executor(
                None, process_upstart_file, self, path
            )
            if self.flags.get("tx_count"):
                self.encoder.tx_count = self.flags["tx_count"]

    def _connected(self) -> None:
        LOG.info("Connected to UPB PIM; getting status of devices")

        # The intention of this message is to clear anything in the PIM receive buffer.
        # A number of times on startup error(s) (PE) are returned. This might
        # return OK or it might return an error, but hopefully resets the PIM.
        self._connection.send(PimCommand.READ_PIM_REGISTERS, "0001FF", None)

        # Ensure we're in "message" (and not "pulse") mode. See PCS PIM Protocol 2.2.3
        self._connection.send(PimCommand.WRITE_PIM_REGISTERS, "70028E", None)

        if self.flags.get("no_sync"):
            LOG.warning("Initial device sync turned off")
        else:
            self.devices.sync()
            self.links.sync()

    def _disconnected(self) -> None:
        LOG.warning("PIM at %s disconnected", self._config["url"])

    def add_handler(self, msg_type: str, handler: NotifyHandler) -> None:
        """Add handler for a message type."""
        self._notifier.attach(msg_type, handler)

    def _timeout(self, addr) -> None:
        if addr:
            device_id = UpbAddr(addr[0], addr[1], 0).index
            device = self.devices.elements.get(device_id)
            LOG.warning(
                "Timeout communicating with UPB device: %s(%s)",
                f"{device.name} " if device else "",
                device_id,
            )
        else:
            LOG.warning("Timeout communicating with PIM, is it connected?")

    def is_connected(self) -> bool:
        """Status of connection to PIM."""
        return self._connection.is_connected()

    async def async_connect(self) -> None:
        """Connect to the PIM"""
        await self._connection.connect()

    def disconnect(self) -> None:
        """Disconnect the connection from sending/receiving."""
        self._connection.disconnect()

    def send(self, msg, rsp: bytearray | None = None, command=PimCommand.TX_UPB_MSG):
        """Send a message to UPB PIM."""
        self._connection.send(command, msg, rsp)
