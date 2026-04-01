"""Юнит-тесты кэша: Redis мокается, проверяются вызовы и аргументы."""

from unittest.mock import AsyncMock, patch

import pytest

from models.predictions import PredictionRequest, PredictionResponse
from models.moderation import ModerationResultResponse
from storage.prediction_cache import PredictionCacheStorage, PRED_TTL_SECONDS


@pytest.mark.asyncio
async def test_get_simple_predict_returns_none_when_redis_unavailable():
    with patch("storage.prediction_cache.get_redis", new_callable=AsyncMock) as gr:
        gr.return_value = None
        storage = PredictionCacheStorage()
        assert await storage.get_simple_predict(1) is None


@pytest.mark.asyncio
async def test_get_simple_predict_uses_redis_get():
    with patch("storage.prediction_cache.get_redis", new_callable=AsyncMock) as gr:
        mock_r = AsyncMock()
        mock_r.get = AsyncMock(
            return_value='{"is_violation": false, "probability": 0.25}'
        )
        gr.return_value = mock_r
        storage = PredictionCacheStorage()
        result = await storage.get_simple_predict(9)
        assert result is not None
        assert result.is_violation is False
        assert result.probability == 0.25
        mock_r.get.assert_awaited_once_with("moderation:simple:9")


@pytest.mark.asyncio
async def test_set_simple_predict_sets_key_with_ttl():
    with patch("storage.prediction_cache.get_redis", new_callable=AsyncMock) as gr:
        mock_r = AsyncMock()
        mock_r.set = AsyncMock()
        gr.return_value = mock_r
        storage = PredictionCacheStorage()
        resp = PredictionResponse(is_violation=True, probability=0.5)
        await storage.set_simple_predict(7, resp)
        mock_r.set.assert_awaited_once()
        assert mock_r.set.await_args[0][0] == "moderation:simple:7"
        assert mock_r.set.await_args[1]["ex"] == PRED_TTL_SECONDS


@pytest.mark.asyncio
async def test_set_full_predict_sets_hash_and_indexes_set():
    with patch("storage.prediction_cache.get_redis", new_callable=AsyncMock) as gr:
        mock_r = AsyncMock()
        mock_r.set = AsyncMock()
        mock_r.sadd = AsyncMock()
        mock_r.expire = AsyncMock()
        gr.return_value = mock_r
        storage = PredictionCacheStorage()
        req = PredictionRequest(
            seller_id=1,
            is_verified_seller=False,
            item_id=100,
            name="n",
            description="d",
            category=1,
            images_qty=0,
        )
        resp = PredictionResponse(is_violation=False, probability=0.1)
        await storage.set_full_predict(req, resp)
        mock_r.set.assert_awaited()
        mock_r.sadd.assert_awaited_once()
        assert mock_r.sadd.await_args[0][0] == "moderation:item:100:pred_hashes"
        mock_r.expire.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalidate_item_deletes_expected_keys():
    with patch("storage.prediction_cache.get_redis", new_callable=AsyncMock) as gr:
        mock_r = AsyncMock()
        mock_r.smembers = AsyncMock(
            return_value={"moderation:predict:abc"}
        )
        mock_r.delete = AsyncMock()
        gr.return_value = mock_r
        storage = PredictionCacheStorage()
        await storage.invalidate_item(3, [10, 11])
        mock_r.delete.assert_awaited_once()
        deleted = set(mock_r.delete.await_args[0])
        assert "moderation:simple:3" in deleted
        assert "moderation:item:3:pred_hashes" in deleted
        assert "moderation:result:10" in deleted
        assert "moderation:result:11" in deleted


@pytest.mark.asyncio
async def test_set_moderation_result_writes_json_with_ttl():
    with patch("storage.prediction_cache.get_redis", new_callable=AsyncMock) as gr:
        mock_r = AsyncMock()
        mock_r.set = AsyncMock()
        gr.return_value = mock_r
        storage = PredictionCacheStorage()
        body = ModerationResultResponse(
            task_id=5,
            status="pending",
            is_violation=None,
            probability=None,
            error_message=None,
        )
        await storage.set_moderation_result(5, body)
        mock_r.set.assert_awaited_once_with(
            "moderation:result:5",
            body.model_dump_json(),
            ex=PRED_TTL_SECONDS,
        )
