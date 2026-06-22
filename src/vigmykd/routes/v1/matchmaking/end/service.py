import hashlib
import hmac
import logging
import math
import uuid

from fastapi.responses import JSONResponse

from vigmykd.routes.v1.matchmaking.end import models
from vigmykd.services.db import Database
from vigmykd.settings import config
from vigmykd.utils import err


logger = logging.getLogger("matchmaking.end")


async def end(
    query: models.GameOverQuery,
    db: Database
):
    log_id = uuid.uuid4()
    logger.info(f"▶️ MESTART {log_id}")

    try:
        envelope = packet_pb2.Envelope()
        envelope.ParseFromString(query)
        packet = envelope.signed_packet

        payload = packet.payload
        signature = packet.signature

        if not hmac.compare_digest(
            hmac.new(
                config.SIGNATURE.encode("utf-8"),
                payload.SerializeToString(),
                hashlib.sha256
            ).digest(),
            signature
        ):
            raise ValueError("Bad packet")
        
        data = packet.icp.game_over
        won_id = uuid.UUID(data.won_id)
        lost_id = uuid.UUID(data.lost_id)
    except Exception:
        logger.exception(f"MESTART {log_id} | Could not decrypt accepted packet")
        return err(400, "Bad packet")
    
    winner = await db.users.find_one({"uuid": str(won_id)})
    loser = await db.users.find_one({"uuid": str(lost_id)})

    if not winner or not loser:
        return err(400, "Could not find the winner or the loser")

    winner_elo = winner.get("elo", 1200)
    loser_elo = loser.get("elo", 1200)

    winner_games_played = winner.get("games_played", 0)
    loser_games_played = loser.get("games_played", 0)

    winner_k = 64 if winner_games_played < 10 else 32
    loser_k = 64 if loser_games_played < 10 else 32

    winner_expected = 1 / (1 + math.pow(10, (loser_elo - winner_elo) / 400))
    loser_expected = 1 / (1 + math.pow(10, (winner_elo - loser_elo) / 400))

    winner_new_elo = round(
        winner_elo + winner_k * (1 - winner_expected)
    )

    loser_new_elo = round(
        loser_elo + loser_k * (0 - loser_expected)
    )

    await db.users.update_one(
        {"uuid": str(won_id)},
        {
            "$set": {
                "elo": winner_new_elo
            },
            "$inc": {
                "games_played": 1,
                "wins": 1
            }
        }
    )

    await db.users.update_one(
        {"uuid": str(lost_id)},
        {
            "$set": {
                "elo": loser_new_elo
            },
            "$inc": {
                "games_played": 1,
                "losses": 1
            }
        }
    )

    return JSONResponse({})
