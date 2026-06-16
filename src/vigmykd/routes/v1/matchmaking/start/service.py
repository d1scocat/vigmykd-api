import asyncio
import json
import logging
import secrets
import string
import uuid

from datetime import datetime, timedelta, timezone

from fastapi.responses import JSONResponse
from jwt import JWT
from redis.asyncio import Redis

import vigmykd.generated.v1.packet_pb2 as packet_pb2

from vigmykd.packets import Packets
from vigmykd.packets.communication import UDPClient
from vigmykd.settings import config
from vigmykd.utils import err, jwt_full_flow_takeover


alphabet = string.ascii_letters + string.digits


logger = logging.getLogger("matchmaking.start")


async def start(
    scheme: str,
    token: str,
    redis: Redis,
    jwt: JWT,
    udp: UDPClient,
):
    log_id = uuid.uuid4()
    logger.info(f"▶️ MMSTART {log_id}")

    parsed_jwt = await jwt_full_flow_takeover(
        scheme, token, jwt, redis,
        logger, log_id, "MMSTART",
    )
    if isinstance(parsed_jwt, JSONResponse):
        return parsed_jwt

    uid = parsed_jwt["uid"]
    name = parsed_jwt["name"]

    match_id = str(uuid.uuid4())
    match_key = "".join(secrets.choice(alphabet) for _ in range(config.MATCH_KEY_LENGTH))
    join_token = secrets.token_urlsafe(config.MATCH_KEY_LENGTH)

    packet = Packets.register_match(
        match_id=match_id,
        players=[(uid, name)],
        match_key=match_key,
        join_token=join_token,
        expires=int((datetime.now(timezone.utc) + timedelta(hours=12)).timestamp())
    )

    future_ack = asyncio.get_running_loop().create_future()
    future_response = asyncio.get_running_loop().create_future()

    def complete_ack(is_ok: bool):
        if not future_ack.done():
            future_ack.set_result(is_ok)

    def complete_response(response: packet_pb2.InternalCommunicationPacket.RegisterMatchResponse):
        if not future_response.done():
            if response.old_match_id == match_id:
                future_response.set_result(response.joined_match_id)

    udp.enqueue(Packets.envelope(Packets.sign(packet)), packet.msg_id, True, complete_ack)
    udp.expect(packet_pb2.InternalCommunicationPacket.RegisterMatchResponse, complete_response)

    try:
        is_ok, mid = await asyncio.wait_for(
            asyncio.gather(future_ack, future_response),
            timeout=3.0
        )
    except asyncio.TimeoutError:
        return err(status_code=504, msg="Matchmaking service is down. Try again later")

    if not is_ok:
        return err(status_code=500, msg="Could not create match. Try again later")

    return JSONResponse({
        "match_id": mid,
        "join_token": join_token
    })
