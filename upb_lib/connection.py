"""Manage connection and IO to UPB PIM."""

from __future__ import annotations

import asyncio
import logging
from asyncio import timeout as asyncio_timeout
from collections import deque
from dataclasses import dataclass
from typing import Any

from serial_asyncio_fast import open_serial_connection

from .const import PimCommand, PimResponse
from .message import Message, decode
from .notify import Notifier
from .util import parse_url

LOG = logging.getLogger(__name__)
HEARTBEAT_TIME = 120
MESSAGE_RESPONSE_TIME = 5.0
PIM_BUSY_TIMEOUT = 0.10


@dataclass
class QueuedWrite:
    """Structure for entries in the write queue."""

    pim_command: PimCommand
    msg: str
    response_cmd: bytearray | None
    timeout: float = 5.0
    retry_count = 1


class Connection:
    """Manage connection to PIM"""

    def __init__(self, url: str, notifier: Notifier):
        self._url = url
        self._notifier = notifier

        self._writer: asyncio.StreamWriter | None = None
        self._awaiting_response_command: bytearray | None = None
        self._write_queue: deque[QueuedWrite] = deque()
        self._check_write_queue = asyncio.Event()
        self._handled_response_event = asyncio.Event()
        self._heartbeat_event = asyncio.Event()
        self._tasks: set[asyncio.Task[Any]] = set()
        self._last_message = None

    async def connect(self) -> None:
        """Create connection to PIM."""

        LOG.info("Connecting to PIM at %s", self._url)
        retry_time = 1
        scheme, dest, param = parse_url(self._url)
        while not self._writer:
            try:
                async with asyncio_timeout(30):
                    if scheme == "serial":
                        reader, self._writer = await open_serial_connection(
                            url=dest, baudrate=param
                        )
                    else:
                        reader, self._writer = await asyncio.open_connection(
                            host=dest, port=param
                        )
            except (TimeoutError, ValueError, OSError) as err:
                LOG.warning(
                    "Error connecting to PIM (%s). Retrying in %d seconds",
                    err,
                    retry_time,
                )
                await asyncio.sleep(retry_time)
                retry_time = min(60, retry_time * 2)
                continue

            # if scheme != "serial":
            self._tasks.add(asyncio.create_task(self._heartbeat_timer()))
            self._tasks.add(asyncio.create_task(self._read_stream(reader)))
            self._tasks.add(asyncio.create_task(self._write_stream()))
            self._notifier.notify("connected", {})

    def _is_repeated_message(self, msg: Message) -> bool:
        saved_msg = msg._replace(tx_seq=0)
        if not self._last_message:
            self._last_message = saved_msg
            return False

        if saved_msg == self._last_message:
            return True

        self._last_message = saved_msg
        return False

    async def _handle_pim_command(self, pim_command: str, pim_data: str) -> None:
        def _handled_response(done_with_message=True):
            if done_with_message:
                self._write_queue.popleft()
            self._handled_response_event.set()  # enables write stream to start again

        # Ignore PimResponse ACK and NACK
        if pim_command == PimResponse.UPDATE.value:
            reply_from, msg = decode(pim_data)
            if self._is_repeated_message(msg):
                LOG.debug("Repeated message; discarded.")
            else:
                if reply_from == self._awaiting_response_command:
                    _handled_response()
                self._notifier.notify(msg.msg_id, {"msg": msg})
        elif pim_command == PimResponse.ACCEPT.value:
            if not self._awaiting_response_command:
                _handled_response()
        elif pim_command == PimResponse.REGISTER_REPORT.value:
            _handled_response()
        elif pim_command == PimResponse.BUSY.value:
            await asyncio.sleep(PIM_BUSY_TIMEOUT)
            _handled_response(False)
        elif pim_command == PimResponse.ERROR.value:
            _handled_response()

    async def _read_stream(self, reader: asyncio.StreamReader) -> None:
        read_buffer = ""
        while True:
            try:
                if not (data := await reader.read(500)):
                    raise ValueError()
            except (OSError, ValueError) as err:
                LOG.error("Error connecting to PIM (%s)", err)
                self.disconnect("Lost connection to PIM")
                self._notifier.notify("disconnected", {})
                await self.connect()
                break

            self._heartbeat()

            read_buffer += data.decode("ISO-8859-1")
            while "\r" in read_buffer:
                line, read_buffer = read_buffer.split("\r", 1)
                LOG.debug("got_data '%s'", line)
                await self._handle_pim_command(line[:2], line[2:])

    async def _write_stream(self) -> None:
        async def await_msg_response() -> None:
            # pylint: disable=possibly-used-before-assignment
            self._awaiting_response_command = q_entry.response_cmd
            try:
                async with asyncio_timeout(MESSAGE_RESPONSE_TIME):
                    await self._handled_response_event.wait()
            except TimeoutError:
                self._notifier.notify("timeout", {"addr": q_entry.response_cmd})
                self._write_queue[0].retry_count -= 1
                if self._write_queue[0].retry_count < 0:
                    self._write_queue.popleft()

            self._handled_response_event.clear()
            self._awaiting_response_command = None

        while True:
            if not self._write_queue:
                await self._check_write_queue.wait()
            if not self._writer:
                break
            self._check_write_queue.clear()
            if self._write_queue:
                q_entry = self._write_queue[0]
                LOG.debug("Write %s '%s'", q_entry.pim_command.name, q_entry.msg)
                self._writer.write(
                    (f"{q_entry.pim_command.value}{q_entry.msg}\r").encode()
                )
                await await_msg_response()

    def send(
        self, pim_command: PimCommand, msg: str, response: bytearray | None
    ) -> None:
        """Send a message to PIM."""
        LOG.debug("Queued %s '%s'", pim_command.name, msg)
        self._write_queue.append(QueuedWrite(pim_command, msg, response))
        self._check_write_queue.set()

    def is_connected(self) -> bool:
        """Is the connection active?"""
        return self._writer is not None

    def disconnect(self, reason: str = "") -> None:
        """Disconnect and cleanup."""
        LOG.warning("PIM at %s disconnecting %s", self._url, reason)
        if self._writer:
            self._writer.close()
            self._writer = None
        for task in self._tasks:
            if asyncio.current_task() != task:
                task.cancel()
        self._tasks = set()
        self._write_queue = deque()
        self._notifier.notify("disconnected", {})

    def _heartbeat(self) -> None:
        self._heartbeat_event.set()

    async def _heartbeat_timer(self) -> None:
        timeout_time = HEARTBEAT_TIME
        while True:
            self._heartbeat_event.clear()
            try:
                async with asyncio_timeout(timeout_time):
                    await self._heartbeat_event.wait()
                timeout_time = HEARTBEAT_TIME
            except TimeoutError:
                if timeout_time == HEARTBEAT_TIME:
                    # Send message and wait normal msg timeout for response
                    timeout_time = MESSAGE_RESPONSE_TIME
                    self.send(PimCommand.READ_PIM_REGISTERS, "0001FF", None)
                else:
                    self.disconnect("(heartbeat timeout)")
                    await self.connect()
                    break
