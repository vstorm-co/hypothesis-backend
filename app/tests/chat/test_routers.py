import asyncio
import datetime
import unittest

import pytest
from async_asgi_testclient import TestClient
from fastapi import status
from sqlalchemy import delete

from src.auth.jwt import create_access_token
from src.auth.service import get_or_create_user
from src.chat.schemas import RoomCreateWithUserId
from src.chat.service import create_room_in_db
from src.main import app
from src.database import database, auth_user


def mock_jwt_token():
    return {"user_id": 123}


class TestChat(unittest.IsolatedAsyncioTestCase):

    # async def customSetUp(self) -> None:

    async def asyncSetUp(self) -> None:
        await database.connect()
        self.client = TestClient(app)
        self.user = await get_or_create_user({"email": "test_user@mail.com"})
        self.token = create_access_token(user=self.user)
        room = await create_room_in_db(RoomCreateWithUserId(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid

    async def asyncTearDown(self) -> None:
        delete_query = delete(auth_user).where(auth_user.c.email) == "test_user@mail.com"
        # await database.fetch_one(delete_query)
        self.user = None

    # def setUpSync(self):
    #     loop = asyncio.get_event_loop()
    #     loop.run_until_complete(self.customSetUp())
    #
    # def tearDownSync(self):
    #     loop = asyncio.get_event_loop()
    #     loop.run_until_complete(self.customTearDown())

    #
    # async def customTearDown(self) -> None:
    #     delete_query = delete(auth_user).where(auth_user.c.email) == "test_user@mail.com"
    #     await database.fetch_one(delete_query)
    #     self.user = None

    async def test_create_room(self) -> None:
        # self.setUpSync()
        # client = TestClient(app)
        resp = await self.client.post(
            "/chat/room",
            json={
                "name": "MyRoom",
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == status.HTTP_200_OK
        # print(resp_json)
        assert resp_json['room']['name'] == "MyRoom"
        # assert resp_json['room']['created_at'] == datetime.datetime.now()
        assert "uuid" in resp_json['room']
        assert "user_id" in resp_json['room']

    async def test_update_room(self) -> None:
        resp = await self.client.put(
            f"/chat/room/{self.room_uuid}",
            json={
                "name": "PutName"
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == status.HTTP_200_OK
        assert resp_json['room']['name'] == "PutName"
    #
    # async def test_get_rooms(self) -> None:
    #     pass
