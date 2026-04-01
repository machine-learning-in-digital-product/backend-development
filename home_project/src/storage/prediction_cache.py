import hashlib
import logging
from typing import Optional

from clients.redis_client import get_redis
from models.predictions import PredictionRequest, PredictionResponse
from models.moderation import ModerationResultResponse

logger = logging.getLogger(__name__)

PRED_TTL_SECONDS = 300


class PredictionCacheStorage:

    def __init__(self):
        self._ttl = PRED_TTL_SECONDS

    async def _r(self):
        return await get_redis()

    async def get_simple_predict(self, item_id: int) -> Optional[PredictionResponse]:
        r = await self._r()
        if not r:
            return None
        raw = await r.get(PredictionCacheStorage._key_simple(item_id))
        if not raw:
            return None
        return PredictionResponse.model_validate_json(raw)

    async def set_simple_predict(self, item_id: int, response: PredictionResponse) -> None:
        r = await self._r()
        if not r:
            return
        await r.set(
            PredictionCacheStorage._key_simple(item_id),
            response.model_dump_json(),
            ex=self._ttl,
        )

    @staticmethod
    def _key_simple(item_id: int) -> str:
        return f"moderation:simple:{item_id}"

    def _request_hash(self, request: PredictionRequest) -> str:
        return hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

    async def get_full_predict(self, request: PredictionRequest) -> Optional[PredictionResponse]:
        r = await self._r()
        if not r:
            return None
        h = self._request_hash(request)
        raw = await r.get(f"moderation:predict:{h}")
        if not raw:
            return None
        return PredictionResponse.model_validate_json(raw)

    async def set_full_predict(self, request: PredictionRequest, response: PredictionResponse) -> None:
        r = await self._r()
        if not r:
            return
        h = self._request_hash(request)
        key = f"moderation:predict:{h}"
        await r.set(key, response.model_dump_json(), ex=self._ttl)
        idx = f"moderation:item:{request.item_id}:pred_hashes"
        await r.sadd(idx, key)
        await r.expire(idx, self._ttl)

    async def get_moderation_result(self, task_id: int) -> Optional[ModerationResultResponse]:
        r = await self._r()
        if not r:
            return None
        raw = await r.get(f"moderation:result:{task_id}")
        if not raw:
            return None
        return ModerationResultResponse.model_validate_json(raw)

    async def set_moderation_result(self, task_id: int, response: ModerationResultResponse) -> None:
        r = await self._r()
        if not r:
            return
        await r.set(
            f"moderation:result:{task_id}",
            response.model_dump_json(),
            ex=self._ttl,
        )

    async def invalidate_item(self, item_id: int, task_ids: list[int]) -> None:
        r = await self._r()
        if not r:
            return
        keys = [PredictionCacheStorage._key_simple(item_id)]
        idx = f"moderation:item:{item_id}:pred_hashes"
        pred_keys = await r.smembers(idx)
        for pk in pred_keys:
            keys.append(pk)
        keys.append(idx)
        for tid in task_ids:
            keys.append(f"moderation:result:{tid}")
        if keys:
            await r.delete(*keys)

    async def delete_moderation_result(self, task_id: int) -> None:
        r = await self._r()
        if not r:
            return
        await r.delete(f"moderation:result:{task_id}")


prediction_cache = PredictionCacheStorage()
