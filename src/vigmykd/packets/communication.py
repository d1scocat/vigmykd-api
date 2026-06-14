import errno
import logging
import queue

from socket import socket, AF_INET, SOCK_DGRAM
from typing import Protocol, runtime_checkable

from vigmykd.generated.proto.v1 import packet_pb2 as packet_pb2
from vigmykd.settings import config


logger = logging.getLogger("socket")


@runtime_checkable
class HasSerializeToString(Protocol):
    def SerializeToString(self) -> bytes:
        ...


class UDPClient:
    def __init__(self):
        self._waits_ack = {}

        self.incoming = queue.Queue(maxsize=2048)
        self.outgoing = queue.Queue(maxsize=2048)

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
                return sock
            except OSError as ex:
                if ex.errno == errno.EADDRINUSE:
                    continue
                raise  # Unexpected path

        sock.close()
        raise RuntimeError(f"No free port for socket in range [{start_port}; {max_port}]")

    def enqueue(self, value: bytes | HasSerializeToString, needs_ack: bool = False, callback=None):
        # Whatever we receive!
        if isinstance(value, bytes):
            data = value
        elif isinstance(value, HasSerializeToString):
            data = value.SerializeToString()
        else:
            logger.warning(f"Cannot send bad packet: {value!r}")
            return

        self._push_drop_oldest(self.outgoing, data)
        if needs_ack and callback is not None:
            self._waits_ack[data.msg_id] = callback

    def pump(self):
        if not self.running:
            return

        self._recv()
        self._send()

    def shutdown(self):
        self.running = False
        self.sock.close()

    def _recv(self):
        try:
            packet, _ = self.sock.recvfrom(2048)
            self._check_ack(packet)
        except BlockingIOError:
            return

        self._push_drop_oldest(self.incoming, packet)

    def _send(self):
        while True:
            try:
                data = self.outgoing.get_nowait()
                self.sock.sendto(data, (config.UDP_ADDR, config.UDP_PORT))
            except BlockingIOError:
                pass
            except OSError:
                logger.exception("Packet send failed")
            except queue.Empty:
                break

    def _check_ack(self, data):
        packet = packet_pb2.Packet()
        packet.ParseFromString(data)
        if packet.WhichOneof("payload") != "server_to_client":
            return

        stc = packet.server_to_client
        if stc.WhichOneof("payload") != "ack":
            return

        ack = stc.ack
        callback = self._waits_ack.pop(ack.acknowledged_msg_id, None)
        if callback is not None:
            callback(ack.ok)

    def _push_drop_oldest(self, q: queue.Queue, item) -> None:
        try:
            q.put_nowait(item)
        except queue.Full:
            try:
                q.get_nowait()
                q.put_nowait(item)
            except queue.Empty:
                pass
