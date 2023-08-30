import unittest

from async_asgi_testclient import TestClient
from fastapi import status
from sqlalchemy import delete

from src.auth.jwt import create_access_token
from src.auth.service import get_or_create_user
from src.chat.schemas import RoomCreateWithUserId
from src.chat.service import create_room_in_db
from src.database import database, auth_user, room
from src.main import app


class TestChat(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await database.connect()
        self.client = TestClient(app)
        self.user = await get_or_create_user({"email": "test_user@mail.com"})
        self.token = create_access_token(user=self.user)
        self.room_uuid = None

    async def asyncTearDown(self) -> None:
        if self.room_uuid:
            delete_query_1 = delete(room).where(room.c.uuid == self.room_uuid)
            await database.execute(delete_query_1)
        delete_query = delete(auth_user).where(auth_user.c.email == "test_user@mail.com")
        await database.execute(delete_query)
        await database.disconnect()
        self.user = None

    async def test_create_room(self) -> None:
        resp = await self.client.post(
            "/chat/room",
            json={
                "name": "MyRoom",
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == status.HTTP_200_OK
        self.room_uuid = resp_json['room']['uuid']  # Store the room UUID for later deletion
        assert resp_json['room']['name'] == "MyRoom"
        assert "uuid" in resp_json['room']
        assert "user_id" in resp_json['room']

    async def test_update_room(self) -> None:
        room = await create_room_in_db(RoomCreateWithUserId(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid  # Store the room UUID for updating
        resp = await self.client.put(
            f"/chat/room/{self.room_uuid}",
            json={
                "name": "PutName"
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == status.HTTP_200_OK
        assert resp_json['name'] == "PutName"


if __name__ == "__main__":
    unittest.main()
