import errno
import logging

from collections import deque
from socket import socket, AF_INET, SOCK_DGRAM
from typing import Protocol, runtime_checkable

import vigmykd.generated.v1.packet_pb2 as packet_pb2
from vigmykd.packets.factory import Packets
from vigmykd.settings import config


logger = logging.getLogger("socket")


@runtime_checkable
class HasSerializeToString(Protocol):
    def SerializeToString(self) -> bytes:
        ...


class UDPClient:
    def __init__(self):
        self._waits_ack = {}

        self.incoming = deque(maxlen=2048)
        self.outgoing = deque()

        self.running = True
        self.sock = self._bind_socket()

    def _bind_socket(self) -> socket:
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.setblocking(False)

        self.bound_port: int
        start_port = config.SOCKET_PORT
        max_port = start_port + 1000

        for port in range(start_port, max_port + 1):
            try:
                sock.bind(('0.0.0.0', port))
                logger.info(f"Internal socket listening on 0.0.0.0:{port}")
                self.bound_port = port

                Packets.call_once__set_port(port)

                return sock
            except OSError as ex:
                if ex.errno == errno.EADDRINUSE:
                    continue
                raise  # Unexpected path

        sock.close()
        raise RuntimeError(f"No free port for socket in range [{start_port}; {max_port}]")

    def enqueue(
        self,
        value: bytes | HasSerializeToString,
        msg_id: int,
        needs_ack: bool = False,
        callback=None
    ):
        # Whatever we receive!
        if isinstance(value, bytes):
            data = value
        elif isinstance(value, HasSerializeToString):
            data = value.SerializeToString()
        else:
            logger.warning(f"Cannot send bad packet: {value!r}")
            return

        self.outgoing.append(data)

        if needs_ack and callback is not None:
            self._waits_ack[msg_id] = callback

    def pump(self):
        if not self.running:
            return

        self._recv()
        self._send()

    def shutdown(self):
        self.running = False
        self.sock.close()

    def _recv(self):
        while True:
            try:
                packet, addr = self.sock.recvfrom(2048)
            except BlockingIOError:
                break

            self._check_ack(packet)
            self.incoming.append(packet)

    def _send(self):
        while self.outgoing:
            data = self.outgoing.popleft()

            try:
                self.sock.sendto(data, (config.UDP_ADDR, config.UDP_PORT))
            except BlockingIOError:
                self.outgoing.insert(0, data)
                break
            except OSError:
                logger.exception("Packet send failed")

    def _check_ack(self, data):
        envelope = packet_pb2.Envelope()
        envelope.ParseFromString(data)
        if envelope.WhichOneof("payload") != "packet":
            return

        packet = envelope.packet
        if packet.WhichOneof("payload") != "server_to_client":
            return

        stc = packet.server_to_client
        if stc.WhichOneof("payload") != "ack":
            return

        ack = stc.ack
        callback = self._waits_ack.pop(ack.acknowledged_msg_id, None)
        if callback is not None:
            callback(ack.ok)

