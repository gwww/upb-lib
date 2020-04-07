"""Async IO."""

import asyncio
import logging

from .const import PimCommand

LOG = logging.getLogger(__name__)
PIM_BUSY_TIMEOUT = 0.10
PROTO_RETRY_COUNT = 1

# _awaiting states:
NOTHING = 0
PIM_RESPONSE_MESSAGE = 1
UPB_PACKET = 2
PIM_TO_BE_READY = 3


class _Packet:
    """Details about a packet being sent"""

    def __init__(self, data, response, timeout, raw):
        self.data = data
        self.response = response
        self.raw = raw
        self.timeout = timeout
        self.retry_count = PROTO_RETRY_COUNT

    def __repr__(self):
        return str(self.__dict__)


class Connection(asyncio.Protocol):
    """asyncio Protocol with line parsing and queuing writes"""

    # pylint: disable=too-many-instance-attributes
    def __init__(self, loop, connected, disconnected, got_data, timeout):
        self.loop = loop
        self._connected_callback = connected
        self._disconnected_callback = disconnected
        self._got_data_callback = got_data
        self._timeout_callback = timeout

        self._last_message = bytearray()
        self._last_sequence = 0

        self._transport = None
        self._awaiting = NOTHING
        self._timeout_task = None
        self._write_queue = []
        self._buffer = ""
        self._paused = False

        self._msgmap = {
            "PA": "accepted",
            "PB": "busy",
            "PE": "error",
            "PK": "ack",
            "PN": "nack",
            "PU": "update",
            "PR": "registers",
            "~~": "CONTROL",
        }

    def connection_made(self, transport):
        LOG.debug("connected callback")
        self._transport = transport
        self._connected_callback(transport, self)

    def connection_lost(self, exc):
        LOG.debug("disconnected callback")
        self._transport = None
        self._cleanup()
        if self._disconnected_callback:
            self._disconnected_callback()

    def stop(self):
        """Stop the connection from sending/receiving/reconnecting."""
        self._transport = None
        self._cleanup()
        self._disconnected_callback = None

    def pause(self):
        """Pause the connection from sending/receiving."""
        self._cleanup()
        self._paused = True

    def resume(self):
        """Restart the connection from sending/receiving."""
        self._paused = False

    def write_data(self, data, response_required=True, timeout=5.0, raw=False):
        """Queue data and process the write queue."""
        response = data[4:8] if response_required else None
        pkt = _Packet(data, response, timeout, raw)
        self._write_queue.append(pkt)
        LOG.debug("queued write '%s'", pkt.data)
        self._process_write_queue()

    def _response_timeout(self):
        kind = "PIM" if self._awaiting == PIM_RESPONSE_MESSAGE else "packet"
        self._awaiting = NOTHING
        self._timeout_task = None

        if not self._write_queue:
            LOG.warning(f"_response_timeout: No writes are queued.")
            return

        pkt = self._write_queue[0]
        LOG.debug(f"Timeout waiting for {kind}; retrying {pkt.retry_count} more times.")
        if pkt.retry_count == 0:
            self._write_queue.pop(0)
            self._timeout_callback(pkt.response)

        pkt.retry_count -= 1

        self._process_write_queue()

    def _pim_busy_timeout(self):
        self._awaiting = NOTHING
        self._process_write_queue()

    def _is_repeated_message(self, msg):
        current_message = msg.copy()
        current_sequence = current_message[1] & 0b00000011

        if current_sequence <= self._last_sequence:
            self._last_sequence = current_sequence
            self._last_message = current_message
            return False

        self._last_sequence = current_sequence

        # Clear sequence field
        current_message[1] = current_message[1] & 0b11111100
        if current_message == self._last_message:
            return True

        self._last_message = current_message
        return False

    def _handle_pim_update_msg(self, line):
        msg = bytearray.fromhex(line[2:-2])  # strip PIM command & cksum
        if self._is_repeated_message(msg):
            LOG.debug("Repeated message; discarded.")
            return

        if self._awaiting == UPB_PACKET:
            if self._write_queue:
                response_from = f"{line[6:8]}{line[10:12]}"
                if response_from == self._write_queue[0].response:
                    self._done_with_write_queue_head()
            else:
                self._done_with_write_queue_head()

        self._got_data_callback(msg)

    def data_received(self, data):
        self._buffer += data.decode("ISO-8859-1")
        pim_busy = False
        while "\r" in self._buffer:
            line, self._buffer = self._buffer.split("\r", 1)
            pim_command = line[:2]
            LOG.debug(f"data_received: {self._msgmap.get(pim_command):10} '{line}'")

            if pim_command == "PU":
                self._handle_pim_update_msg(line)
            elif pim_command == "PA":
                if self._awaiting == PIM_RESPONSE_MESSAGE:
                    self._done_with_write_queue_head()
            elif pim_command == "PB":
                pim_busy = True
            elif pim_command == "PE":
                self._done_with_write_queue_head()
            elif pim_command == "~~":
                # Received when connected to ser2tcp (github.com/gwww/ser2tcp)
                self._got_data_callback(line)

        if pim_busy:
            LOG.debug(f"PIM busy received, retrying in {PIM_BUSY_TIMEOUT} seconds")
            self._start_timer(PIM_BUSY_TIMEOUT, self._pim_busy_timeout)
            self._awaiting = PIM_TO_BE_READY
        else:
            self._process_write_queue()

    def _process_write_queue(self):
        if self._awaiting or not self._write_queue:
            return
        if not self._transport or self._paused:
            return

        pkt = self._write_queue[0]
        self._start_timer(pkt.timeout, self._response_timeout)
        self._awaiting = UPB_PACKET if pkt.response else PIM_RESPONSE_MESSAGE

        LOG.debug(f"write_data '{pkt.data}'")
        pim_command = "" if pkt.raw else PimCommand.TX_UPB_MSG.value
        self._transport.write(f"{pim_command}{pkt.data}\r".encode())

    def _done_with_write_queue_head(self):
        self._cancel_timer()
        self._awaiting = NOTHING
        if self._write_queue:
            self._write_queue.pop(0)

    def _cancel_timer(self):
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None

    def _start_timer(self, timeout, callback):
        self._cancel_timer()
        self._timeout_task = self.loop.call_later(timeout, callback)

    def _cleanup(self):
        self._cancel_timer()
        self._write_queue = []
        self._buffer = ""
