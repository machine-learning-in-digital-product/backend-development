from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import workers.moderation_worker as mw
from models.predictions import PredictionResponse


@pytest.mark.asyncio
async def test_process_message_success():
    message = {"item_id": 201, "task_id": 42, "timestamp": "2025-01-01T00:00:00"}
    task_row = {"id": 42, "item_id": 201, "status": "pending"}
    item_row = {
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 201,
        "name": "n",
        "description": "d",
        "category": 1,
        "images_qty": 2,
    }

    with patch.object(mw.moderation_repository, "get_task_by_id", new_callable=AsyncMock) as gt, \
            patch.object(mw.item_repository, "get_item_by_item_id", new_callable=AsyncMock) as gi, \
            patch.object(mw.prediction_service, "predict", new_callable=MagicMock) as pred, \
            patch.object(mw.moderation_repository, "update_task_completed", new_callable=AsyncMock) as uc, \
            patch.object(mw.prediction_cache, "set_moderation_result", new_callable=AsyncMock) as cache_set:
        gt.return_value = task_row
        gi.return_value = item_row
        pred.return_value = PredictionResponse(is_violation=False, probability=0.2)

        await mw.process_message_with_retry(message)

        pred.assert_called_once()
        uc.assert_awaited_once_with(42, False, 0.2)
        cache_set.assert_awaited_once()
        assert cache_set.await_args[0][0] == 42


@pytest.mark.asyncio
async def test_process_message_missing_task_id_sends_dlq():
    message = {"item_id": 201, "timestamp": "2025-01-01T00:00:00"}

    with patch.object(mw, "send_to_dlq", new_callable=AsyncMock) as dlq:
        await mw.process_message_with_retry(message)
        dlq.assert_awaited_once()
        err = dlq.await_args.args[1].lower()
        assert "task_id" in err


@pytest.mark.asyncio
async def test_process_message_task_item_mismatch_fails_and_dlq():
    message = {"item_id": 201, "task_id": 42, "timestamp": "2025-01-01T00:00:00"}
    task_row = {"id": 42, "item_id": 999, "status": "pending"}

    with patch.object(mw.moderation_repository, "get_task_by_id", new_callable=AsyncMock) as gt, \
            patch.object(mw.moderation_repository, "update_task_failed", new_callable=AsyncMock) as uf, \
            patch.object(mw.prediction_cache, "set_moderation_result", new_callable=AsyncMock) as cache_set, \
            patch.object(mw, "send_to_dlq", new_callable=AsyncMock) as dlq:
        gt.return_value = task_row

        await mw.process_message_with_retry(message)

        uf.assert_awaited_once()
        cache_set.assert_awaited_once()
        dlq.assert_awaited_once()


@pytest.mark.asyncio
async def test_retryable_error_exponential_backoff_then_success():
    message = {"item_id": 201, "task_id": 42, "timestamp": "2025-01-01T00:00:00"}
    task_row = {"id": 42, "item_id": 201, "status": "pending"}
    item_row = {
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 201,
        "name": "n",
        "description": "d" * 10,
        "category": 1,
        "images_qty": 2,
    }

    with patch.object(mw.moderation_repository, "get_task_by_id", new_callable=AsyncMock) as gt, \
            patch.object(mw.item_repository, "get_item_by_item_id", new_callable=AsyncMock) as gi, \
            patch.object(mw.prediction_service, "predict", new_callable=MagicMock) as pred, \
            patch.object(mw.moderation_repository, "update_task_completed", new_callable=AsyncMock) as uc, \
            patch.object(mw.prediction_cache, "set_moderation_result", new_callable=AsyncMock) as cache_set, \
            patch("workers.moderation_worker.asyncio.sleep", new_callable=AsyncMock) as sleep_mock:
        gt.return_value = task_row
        gi.return_value = item_row
        pred.side_effect = [ConnectionError("temporary"), PredictionResponse(is_violation=True, probability=0.9)]

        await mw.process_message_with_retry(message)

        assert sleep_mock.await_count == 1
        first_delay = sleep_mock.await_args_list[0].args[0]
        assert first_delay == pytest.approx(mw.RETRY_DELAY_BASE_SECONDS * (2 ** 0))
        uc.assert_awaited_once_with(42, True, 0.9)
        cache_set.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_exhausted_sends_dlq():
    message = {"item_id": 201, "task_id": 42, "timestamp": "2025-01-01T00:00:00"}
    task_row = {"id": 42, "item_id": 201, "status": "pending"}
    item_row = {
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 201,
        "name": "n",
        "description": "d",
        "category": 1,
        "images_qty": 2,
    }

    with patch.object(mw.moderation_repository, "get_task_by_id", new_callable=AsyncMock) as gt, \
            patch.object(mw.item_repository, "get_item_by_item_id", new_callable=AsyncMock) as gi, \
            patch.object(mw.prediction_service, "predict", new_callable=MagicMock) as pred, \
            patch.object(mw.moderation_repository, "update_task_failed", new_callable=AsyncMock) as uf, \
            patch.object(mw.prediction_cache, "set_moderation_result", new_callable=AsyncMock) as cache_set, \
            patch.object(mw, "send_to_dlq", new_callable=AsyncMock) as dlq, \
            patch("workers.moderation_worker.asyncio.sleep", new_callable=AsyncMock) as sleep:
        gt.return_value = task_row
        gi.return_value = item_row
        pred.side_effect = RuntimeError("Модель не загружена")

        await mw.process_message_with_retry(message)

        assert sleep.await_count == mw.MAX_RETRIES - 1
        expected_delays = [
            mw.RETRY_DELAY_BASE_SECONDS * (2 ** i) for i in range(mw.MAX_RETRIES - 1)
        ]
        actual = [c.args[0] for c in sleep.await_args_list]
        assert actual == expected_delays
        uf.assert_awaited_once()
        cache_set.assert_awaited_once()
        dlq.assert_awaited_once()


@pytest.mark.asyncio
async def test_non_retryable_failure_no_sleep():
    message = {"item_id": 201, "task_id": 42, "timestamp": "2025-01-01T00:00:00"}
    task_row = {"id": 42, "item_id": 201, "status": "pending"}
    item_row = {
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 201,
        "name": "n",
        "description": "d",
        "category": 1,
        "images_qty": 2,
    }

    with patch.object(mw.moderation_repository, "get_task_by_id", new_callable=AsyncMock) as gt, \
            patch.object(mw.item_repository, "get_item_by_item_id", new_callable=AsyncMock) as gi, \
            patch.object(mw.prediction_service, "predict", new_callable=MagicMock) as pred, \
            patch.object(mw.moderation_repository, "update_task_failed", new_callable=AsyncMock) as uf, \
            patch.object(mw.prediction_cache, "set_moderation_result", new_callable=AsyncMock) as cache_set, \
            patch.object(mw, "send_to_dlq", new_callable=AsyncMock) as dlq, \
            patch("workers.moderation_worker.asyncio.sleep", new_callable=AsyncMock) as sleep:
        gt.return_value = task_row
        gi.return_value = item_row
        pred.side_effect = ValueError("не повторяемая ошибка")

        await mw.process_message_with_retry(message)

        sleep.assert_not_awaited()
        uf.assert_awaited_once()
        cache_set.assert_awaited_once()
        dlq.assert_awaited_once()
