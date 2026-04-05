import pytest
from services.dialogue_router import DialogueRouter
from db.repositories.user_repository import UserRepository
from db.repositories.memory_repository import MemoryRepository

class FailingLLM:
    async def complete(self, prompt: str) -> str:
        raise RuntimeError("LLM failure")

@pytest.mark.asyncio
async def test_dialogue_router_fallback(tmp_path):
    db_path = tmp_path / "test.db"
    from db.database import initialise_database
    initialise_database(str(db_path))
    user_repo = UserRepository(str(db_path))
    memory_repo = MemoryRepository(str(db_path))
    router = DialogueRouter(FailingLLM(), user_repo, memory_repo)
    user_id = user_repo.get_or_create_user(42)
    result = await router.generate_reply(user_id, "test")
    assert "Извини" in result["text"] or "Прости" in result["text"]
