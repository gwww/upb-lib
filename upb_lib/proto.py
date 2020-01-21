"""Async IO."""

import asyncio
from functools import reduce
import logging

from .message import get_pim_command

LOG = logging.getLogger(__name__)


class Connection(asyncio.Protocol):
    """asyncio Protocol with line parsing and queuing writes"""

    # pylint: disable=too-many-instance-attributes
    def __init__(self, loop, connected, disconnected, got_data, timeout):
        self.loop = loop
        self._connected_callback = connected
        self._disconnected_callback = disconnected
        self._got_data_callback = got_data
        self._timeout = timeout

        self._transport = None
        self._timeout_task = None
        self._queued_writes = []
        self._buffer = ""
        self._paused = False
        self._msgmap = { 'A': 'accepted', 'B': 'busy', 'E': 'error',
                        'K': 'ack', 'N': 'nack', 'U': 'update', 'R': 'registers' }

    def connection_made(self, transport):
        LOG.debug("connected callback")
        self._transport = transport
        self._connected_callback(transport, self)

    def connection_lost(self, exc):
        LOG.debug("disconnected callback")
        self._transport = None
        self._cleanup()
        self._disconnected_callback()

    def _cleanup(self):
        self._cancel_timer()
        self._queued_writes = []
        self._buffer = ""

    def pause(self):
        """Pause the connection from sending/receiving."""
        self._cleanup()
        self._paused = True

    def resume(self):
        """Restart the connection from sending/receiving."""
        self._paused = False

    def _response_required_timeout(self):
        self._timeout(True)
        self._timeout_task = None
        self._process_write_queue()

    def _cancel_timer(self):
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None

    def data_received(self, data):
        self._buffer += data.decode("ISO-8859-1")
        while "\r" in self._buffer:
            line, self._buffer = self._buffer.split("\r", 1)
            LOG.debug("message received: %10s '%s'", self._msgmap[line[1]], line)
            pim_command = get_pim_command(line)
            if pim_command == 'PA':
                self._cancel_timer()
                if self._queued_writes:
                    self._queued_writes.pop(0)
            elif pim_command == 'PB':
                self._cancel_timer()
            elif pim_command == 'PE':
                self._cancel_timer()
                if self._queued_writes:
                    self._queued_writes.pop(0)
            elif pim_command == 'PR':
                pass
            elif pim_command == 'PK':
                pass
            elif pim_command == 'PN':
                pass
            elif pim_command == 'PU':
                self._got_data_callback(line[2:])

        self._process_write_queue()

    def write_data(self, data, timeout=5.0):
        """Write data on the asyncio Protocol"""
        if self._paused or self._transport is None:
            return

        self._queued_writes.append((data, timeout))
        if len(self._queued_writes) > 1:
            LOG.debug("deferring write %s", data)
            return

        self._send(data, timeout)

    def _process_write_queue(self):
        if self._queued_writes:
            self._send(self._queued_writes[0][0], self._queued_writes[0][1])

    def _send(self, data, timeout):
        if timeout > 0:
            self._timeout_task = self.loop.call_later(
                timeout, self._response_required_timeout)

        LOG.debug("_send '%s'", data)
        self._transport.write(("\x14{}\r".format(data)).encode())
