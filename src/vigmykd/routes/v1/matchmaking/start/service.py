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

    match_id = str(uuid.uuid4())
    match_key = "".join(secrets.choice(alphabet) for _ in range(config.MATCH_KEY_LENGTH))
    join_token = secrets.token_urlsafe(config.MATCH_KEY_LENGTH)

    try:
        await redis.set(
            f"match:{match_id}",
            json.dumps({"key": match_key, "players": [uid], "status": "wait"})
        )

        await redis.set(
            f"player:{uid}",
            json.dumps({"match": match_id})
        )

        logger.info(f"💨 MMSTART {log_id}: saved new match data to Redis")
    except Exception as ex:
        logger.warning(f"⚠️ MMSTART {log_id}: could not write match to Redis: {ex}",
                       exc_info=True)
        return err(status_code=500, msg="Matchmaking service is down. Try again later")

    packet = Packets.register_match(
        match_id=match_id,
        players=[uid],
        match_key=match_key,
        join_token=join_token,
        expires=int((datetime.now(timezone.utc) + timedelta(hours=12)).timestamp())
    )

    future = asyncio.get_running_loop().create_future()

    def complete_future(is_ok: bool):
        if not future.done():
            future.set_result(is_ok)

    udp.enqueue(Packets.envelope(Packets.sign(packet)), packet.msg_id, True, complete_future)

    try:
        is_ok = await asyncio.wait_for(future, timeout=3.0)
    except asyncio.TimeoutError:
        return err(status_code=504, msg="Matchmaking service is down. Try again later")

    if not is_ok:
        return err(status_code=500, msg="Could not create match. Try again later")

    return JSONResponse({
        "match_id": match_id,
        "join_token": join_token
    })
