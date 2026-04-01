import pytest

from models.predictions import PredictionRequest, PredictionResponse
from models.moderation import ModerationResultResponse
from storage.prediction_cache import PredictionCacheStorage


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_simple_predict_roundtrip_in_redis(integration_redis):
    storage = PredictionCacheStorage()
    body = PredictionResponse(is_violation=False, probability=0.33)
    await storage.set_simple_predict(42, body)
    cached = await storage.get_simple_predict(42)
    assert cached is not None
    assert cached.is_violation is False
    assert cached.probability == 0.33


@pytest.mark.asyncio
async def test_moderation_result_roundtrip_in_redis(integration_redis):
    storage = PredictionCacheStorage()
    body = ModerationResultResponse(
        task_id=99,
        status="completed",
        is_violation=True,
        probability=0.8,
        error_message=None,
    )
    await storage.set_moderation_result(99, body)
    cached = await storage.get_moderation_result(99)
    assert cached is not None
    assert cached.status == "completed"
    assert cached.is_violation is True


@pytest.mark.asyncio
async def test_invalidate_item_removes_keys(integration_redis):
    storage = PredictionCacheStorage()
    await storage.set_simple_predict(5, PredictionResponse(is_violation=True, probability=0.1))
    req = PredictionRequest(
        seller_id=1,
        is_verified_seller=True,
        item_id=5,
        name="x",
        description="y",
        category=1,
        images_qty=1,
    )
    await storage.set_full_predict(
        req, PredictionResponse(is_violation=False, probability=0.2)
    )
    await storage.set_moderation_result(
        1000,
        ModerationResultResponse(
            task_id=1000,
            status="pending",
            is_violation=None,
            probability=None,
            error_message=None,
        ),
    )
    await storage.invalidate_item(5, [1000])
    assert await storage.get_simple_predict(5) is None
    assert await storage.get_full_predict(req) is None
    assert await storage.get_moderation_result(1000) is None
