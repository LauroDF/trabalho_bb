import json
import logging
import os
from dataclasses import asdict
from typing import Optional

from redis import Redis

from trabalho_bb.cache.schemas import ClientData

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CLIENT_DATA_TTL_SECONDS = 300

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)


def _client_key(client_id: str) -> str:
    return f"client:{client_id}"


def post_client(client_data: ClientData) -> None:
    redis_client.set(
        _client_key(client_data.id),
        json.dumps(asdict(client_data)),
        ex=CLIENT_DATA_TTL_SECONDS,
    )


def get_client(client_id: str) -> Optional[ClientData]:
    serialized_client = redis_client.get(_client_key(client_id))
    if serialized_client is None:
        return None

    try:
        return ClientData(**json.loads(serialized_client))
    except (json.JSONDecodeError, TypeError, KeyError):
        logger.warning("Removing invalid cached data for client %s", client_id)
        redis_client.delete(_client_key(client_id))
        return None


def delete_client(client_id: str) -> None:
    redis_client.delete(_client_key(client_id))


def close_redis_connection() -> None:
    redis_client.close()