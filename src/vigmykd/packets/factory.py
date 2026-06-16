import hmac
import hashlib

from typing import overload

import vigmykd.generated.v1.packet_pb2 as packet_pb2
from vigmykd.settings import config


class Packets:
    _id = 1_000_000_000
    _port = config.SOCKET_PORT

    @staticmethod
    def call_once__set_port(port: int):
        Packets._port = port

    @staticmethod
    def get_next_id() -> int:
        # By my own convention, the server gets message IDs in the range
        # (1'000'000'000-2'000'000'000]. The client gets [1-1'000'000'000]
        Packets._id += 1
        return Packets._id

    @staticmethod
    def sign(packet: packet_pb2.Packet) -> packet_pb2.SignedPacket:
        """`envelope()` a packet before sending!"""
        signed = packet_pb2.SignedPacket()
        signed.payload.CopyFrom(packet)

        signature = PacketSigner.sign(packet)
        signed.signature = signature

        return signed

    @staticmethod
    def register_match(
        match_id: str,
        players: list[str],
        match_key: str,
        join_token: str,
        expires: int,
        msg_id: int | None = None
    ) -> packet_pb2.Packet:
        """`envelope()` a packet before sending!"""
        if msg_id is None:
            msg_id = Packets.get_next_id()

        packet = packet_pb2.Packet()
        packet.msg_id = msg_id

        icp = packet_pb2.InternalCommunicationPacket()

        icp.register_match.match_id = match_id
        icp.register_match.players.extend(players)
        icp.register_match.match_key = match_key
        icp.register_match.join_token = join_token
        icp.register_match.expires = expires

        packet.icp.CopyFrom(icp)

        return packet

    @staticmethod
    @overload
    def envelope(
        payload: packet_pb2.Packet,
    ) -> packet_pb2.Envelope:
        ...

    @staticmethod
    @overload
    def envelope(
        payload: packet_pb2.SignedPacket,
    ) -> packet_pb2.Envelope:
        ...

    @staticmethod
    def envelope(payload):
        env = packet_pb2.Envelope()

        if isinstance(payload, packet_pb2.Packet):
            env.packet.CopyFrom(payload)
        elif isinstance(payload, packet_pb2.SignedPacket):
            env.signed_packet.CopyFrom(payload)
        else:
            raise TypeError(f"Unsupported payload type: {type(payload)}")

        return env


class PacketSigner:
    @staticmethod
    def sign(packet: packet_pb2.Packet) -> bytes:
        data = packet.SerializeToString()
        return hmac.new(
            config.SIGNATURE.encode("utf-8"),
            data,
            hashlib.sha256
        ).digest()
