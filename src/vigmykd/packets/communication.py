import asyncio
import errno
import logging
import time

from collections import defaultdict, deque
from dataclasses import dataclass, field
from socket import socket, AF_INET, SOCK_DGRAM
from typing import Callable, Protocol, runtime_checkable

import vigmykd.generated.v1.packet_pb2 as packet_pb2
from vigmykd.packets.factory import Packets
from vigmykd.settings import config

from google.protobuf.message import Message, DecodeError


logger = logging.getLogger("socket")


@runtime_checkable
class HasSerializeToString(Protocol):
    def SerializeToString(self) -> bytes:
        ...


@dataclass
class _WaitingAck:
    message: bytes
    addr: tuple[str, int]
    last_sent: float = field(default_factory=time.monotonic)
    attempts: int = 0


class UDPClient:
    def __init__(self):
        self._perform_on_ack = {}
        self._waiting_ack = {}
        self._expecting = defaultdict(list)

        self.incoming = deque(maxlen=2048)
        self.outgoing = deque()

        self.running = True
        self.sock = self._bind_socket()

        self._last_unacked_check = time.monotonic()

    def _bind_socket(self) -> socket:
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.setblocking(False)

        self.bound_port: int
        start_port = config.SOCKET_PORT
        max_port = start_port + 1000

        for port in range(start_port, max_port + 1):
            try:
                sock.bind(('0.0.0.0', port))
                logger.info("Internal socket listening on 0.0.0.0:%d", port)
                self.bound_port = port

                Packets.call_once__set_port(port)

                return sock
            except OSError as ex:
                if ex.errno == errno.EADDRINUSE:
                    continue
                raise  # Unexpected path

        sock.close()
        raise RuntimeError(f"No free port for socket in range [{start_port}; {max_port}]")

    def expect(
        self,
        msg_type: type[Message],
        callback: Callable[[Message], None]
    ):
        self._expecting[msg_type].append(callback)

    def enqueue(
        self,
        value: bytes | HasSerializeToString,
        msg_id: int,
        needs_ack: bool = False,
        callback: Callable[[bool], None] | None = None
    ):
        # Whatever we receive!
        if isinstance(value, bytes):
            data = value
        elif isinstance(value, HasSerializeToString):
            data = value.SerializeToString()
        else:
            logger.warning("Cannot send bad packet: %r", value)
            return

        self.outgoing.append(data)

        if needs_ack and callback is not None:
            self._perform_on_ack[msg_id] = callback
            self._waiting_ack[msg_id] = _WaitingAck(
                message=data,
                addr=(config.UDP_ADDR, config.UDP_PORT)
            )

    async def pump(self):
        if not self.running:
            return

        self._recv()
        self._send()
        self._send_unacked()

    def shutdown(self):
        self.running = False
        self.sock.close()

    def _recv(self):
        while True:
            try:
                packet, _ = self.sock.recvfrom(2048)
            except BlockingIOError:
                break

            try:
                envelope = packet_pb2.Envelope()
                envelope.ParseFromString(packet)
            except DecodeError:
                logger.warning("Received malformed packet from server")
                continue

            self._check_ack(envelope)
            self._check_expecting(envelope)
            self.incoming.append(packet)

    def _send(self):
        while self.outgoing:
            data = self.outgoing.popleft()

            try:
                self.sock.sendto(data, (config.UDP_ADDR, config.UDP_PORT))
            except BlockingIOError:
                self.outgoing.appendleft(data)
                break
            except OSError:
                logger.exception("Packet send failed")

    def _send_unacked(self):
        now = time.monotonic()
        if now - self._last_unacked_check < config.REACK_INTERVAL:
            return

        self._last_unacked_check = now

        expired = []

        for m_key, message in list(self._waiting_ack.items()):
            data = message.message
            client = message.addr
            last_sent = message.last_sent
            attempts = message.attempts

            if attempts >= config.MAX_ACK_ATTEMPTS:
                expired.append(m_key)
                continue

            if now - last_sent > config.REACK_INTERVAL:
                try:
                    self.sock.sendto(data, client)
                except Exception:
                    logger.warning("Could not retransmit ack-waiting message to %s", client)
                else:
                    message.last_sent = now
                    message.attempts += 1

        for item in expired:
            logger.debug("Packet %s expired after %s retries", item, config.MAX_ACK_ATTEMPTS)
            self._waiting_ack.pop(item, None)

    def _check_ack(self, envelope: packet_pb2.Envelope):
        if envelope.WhichOneof("payload") != "packet":
            return

        packet = envelope.packet
        if packet.WhichOneof("payload") != "server_to_client":
            return

        stc = packet.server_to_client
        if stc.WhichOneof("payload") != "ack":
            return

        ack = stc.ack
        mid = ack.acknowledged_msg_id

        self._waiting_ack.pop(mid, None)

        callback = self._perform_on_ack.pop(mid, None)
        if callback is not None:
            try:
                callback(ack.ok)
            except Exception:
                logger.exception("Exception handing acking callback for msg_id %d", mid)

    def _check_expecting(self, envelope: packet_pb2.Envelope):
        inner = self._innermost_message(envelope)
        msg_type = type(inner)
        for callback in self._expecting.get(msg_type, []):
            try:
                callback(inner)
            except Exception:
                logger.exception("Exception handing expecting callback")

    def _innermost_message(self, message: Message):
        while True:
            try:
                oneof = message.WhichOneof("payload")
                if oneof is None:
                    return message
                message = getattr(message, oneof)
            except ValueError:  # no 'payload'
                return message

