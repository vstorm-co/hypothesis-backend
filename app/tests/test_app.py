import pytest

from src.config import get_settings

settings = get_settings()

@pytest.mark.asyncio
async def test_get_root(client):
    response = await client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
