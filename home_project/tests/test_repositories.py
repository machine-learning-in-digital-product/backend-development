import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from repositories.users import UserRepository
from repositories.items import ItemRepository


class TestUserRepository:
    
    @pytest.mark.asyncio
    async def test_create_user(self, db_pool):
        repo = UserRepository()
        user = await repo.create_user(seller_id=1, is_verified_seller=True)
        assert user is not None
        assert user["seller_id"] == 1
        assert user["is_verified_seller"] is True
        assert "id" in user
        assert "created_at" in user
    
    @pytest.mark.asyncio
    async def test_get_user_by_seller_id(self, db_pool):
        repo = UserRepository()
        await repo.create_user(seller_id=2, is_verified_seller=False)
        user = await repo.get_user_by_seller_id(2)
        assert user is not None
        assert user["seller_id"] == 2
        assert user["is_verified_seller"] is False
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, db_pool):
        repo = UserRepository()
        user = await repo.get_user_by_seller_id(99999)
        assert user is None
    
    @pytest.mark.asyncio
    async def test_update_user_on_conflict(self, db_pool):
        repo = UserRepository()
        await repo.create_user(seller_id=3, is_verified_seller=False)
        user = await repo.create_user(seller_id=3, is_verified_seller=True)
        assert user["is_verified_seller"] is True


class TestItemRepository:
    
    @pytest.mark.asyncio
    async def test_create_item(self, db_pool):
        user_repo = UserRepository()
        await user_repo.create_user(seller_id=10, is_verified_seller=True)
        
        repo = ItemRepository()
        item = await repo.create_item(
            item_id=100,
            seller_id=10,
            name="Тестовый товар",
            description="Описание",
            category=1,
            images_qty=5
        )
        assert item is not None
        assert item["item_id"] == 100
        assert item["seller_id"] == 10
        assert item["name"] == "Тестовый товар"
        assert item["description"] == "Описание"
        assert item["category"] == 1
        assert item["images_qty"] == 5
    
    @pytest.mark.asyncio
    async def test_get_item_by_item_id(self, db_pool):
        user_repo = UserRepository()
        await user_repo.create_user(seller_id=11, is_verified_seller=False)
        
        repo = ItemRepository()
        await repo.create_item(
            item_id=101,
            seller_id=11,
            name="Товар",
            description="Описание",
            category=2,
            images_qty=3
        )
        item = await repo.get_item_by_item_id(101)
        assert item is not None
        assert item["item_id"] == 101
        assert item["seller_id"] == 11
        assert "is_verified_seller" in item
    
    @pytest.mark.asyncio
    async def test_get_item_not_found(self, db_pool):
        repo = ItemRepository()
        item = await repo.get_item_by_item_id(99999)
        assert item is None
    
    @pytest.mark.asyncio
    async def test_get_item_with_user_data(self, db_pool):
        user_repo = UserRepository()
        await user_repo.create_user(seller_id=12, is_verified_seller=True)
        
        repo = ItemRepository()
        await repo.create_item(
            item_id=102,
            seller_id=12,
            name="Товар",
            description="Описание",
            category=1,
            images_qty=0
        )
        item = await repo.get_item_by_item_id(102)
        assert item is not None
        assert item["is_verified_seller"] is True
