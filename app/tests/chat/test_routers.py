import unittest

from async_asgi_testclient import TestClient
from fastapi import status
from sqlalchemy import delete

from src.auth.jwt import create_access_token
from src.auth.service import get_or_create_user
from src.chat.schemas import RoomCreateInputDetails
from src.chat.service import create_room_in_db
from src.database import database, auth_user, room
from src.main import app

TEST_USER = "test_user@mail.com"


class TestChat(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await database.connect()
        self.client = TestClient(app)
        self.user = await get_or_create_user({"email": f"{TEST_USER}"})
        self.token = create_access_token(user=self.user)
        self.room_uuid = None

    async def asyncTearDown(self) -> None:
        if self.room_uuid:
            delete_query_1 = delete(room).where(room.c.organization_uuid == self.room_uuid)
            await database.execute(delete_query_1)
        delete_query = delete(auth_user).where(auth_user.c.email == f"{TEST_USER}")
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
        self.room_uuid = resp_json["uuid"]  # Store the room UUID for later deletion
        assert resp_json["name"] == "MyRoom"
        assert "uuid" in resp_json
        assert "user_id" in resp_json

    async def test_update_room_name(self) -> None:
        room = await create_room_in_db(RoomCreateInputDetails(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid  # Store the room UUID for updating
        resp = await self.client.patch(
            f"/chat/room/{self.room_uuid}",
            json={
                "name": "PutName"
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["name"] == "PutName"

    async def test_update_room_share(self) -> None:
        room = await create_room_in_db(RoomCreateInputDetails(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid
        resp = await self.client.patch(
            f"/chat/room/{self.room_uuid}",
            json={
                "share": True
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["share"] == True

    async def test_delete_room(self) -> None:
        room = await create_room_in_db(RoomCreateInputDetails(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid

        resp = await self.client.delete(
            f"/chat/room/{self.room_uuid}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["status"] == "success"

    async def test_get_rooms(self) -> None:
        room = await create_room_in_db(RoomCreateInputDetails(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid

        resp = await self.client.get(
            "/chat/rooms",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert len(resp_json) == 1

    async def test_get_room_with_messages(self) -> None:
        room = await create_room_in_db(RoomCreateInputDetails(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid

        resp = await self.client.get(
            f"/chat/room/{self.room_uuid}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["name"] == "test_name"
        assert resp_json["uuid"] == str(self.room_uuid)
        assert len(resp_json["messages"]) == 0


if __name__ == "__main__":
    unittest.main()
