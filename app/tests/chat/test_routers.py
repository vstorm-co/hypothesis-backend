import unittest
import uuid

from async_asgi_testclient import TestClient
from fastapi import status
from sqlalchemy import delete

from src.auth.jwt import create_access_token
from src.auth.service import get_or_create_user
from src.chat.enums import VisibilityChoices
from src.chat.schemas import RoomCreateInputDetails, RoomUpdate
from src.chat.service import create_room_in_db
from src.database import database, auth_user, room
from src.main import app
from src.organizations.schemas import OrganizationCreate
from src.organizations.service import create_organization_in_db, add_users_to_organization_in_db

TEST_USER = "test_user@mail.com"


class TestChat(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        await database.connect()
        self.client = TestClient(app)
        self.user = await get_or_create_user({"email": f"{TEST_USER}"}, is_admin=True)
        self.token = create_access_token(user=self.user)
        self.room_uuid = None

    async def asyncTearDown(self) -> None:
        if self.room_uuid:
            delete_query_1 = delete(room).where(room.c.uuid == self.room_uuid)
            await database.execute(delete_query_1)
        delete_query = delete(auth_user).where(auth_user.c.email == f"{TEST_USER}")
        await database.execute(delete_query)
        await database.disconnect()
        self.user = None

    # CREATE
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

    # UPDATE
    async def test_update_room_name(self) -> None:
        room = await create_room_in_db(RoomCreateInputDetails(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid  # Store the room UUID for updating

        update_input = RoomUpdate(
            name="PutName",
        )
        resp = await self.client.patch(
            f"/chat/room/{self.room_uuid}",
            json=update_input.model_dump(),
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["name"] == "PutName"

    async def test_update_room_share(self) -> None:
        room = await create_room_in_db(RoomCreateInputDetails(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid

        update_input = RoomUpdate(
            share=True,
        )
        resp = await self.client.patch(
            f"/chat/room/{self.room_uuid}",
            json=update_input.model_dump(),
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["share"] == True

    # DELETE
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

    # GET ALL ROOMS
    async def test_get_rooms(self) -> None:
        room = await create_room_in_db(RoomCreateInputDetails(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid

        resp = await self.client.get(
            "/chat/rooms",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert len(resp_json) == 5

    # GET ROOM BY ID
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

    async def test_get_room_with_messages_not_found(self) -> None:
        room = await create_room_in_db(RoomCreateInputDetails(user_id=self.user.id, name="test_name"))
        self.room_uuid = room.uuid
        resp = await self.client.get(
            f"/chat/room/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp_json["detail"] == "Room with this id does not exist!"

    async def test_get_room_with_messages_not_shared_user_not_owner(self) -> None:
        room = await create_room_in_db(
            RoomCreateInputDetails(
                user_id=self.user.id,
                name="test_name",
            )
        )
        self.room_uuid = room.uuid

        # create not owner user
        not_owner_user = await get_or_create_user({"email": "notAnOwner@example.com"})
        not_owner_token = create_access_token(user=not_owner_user)

        resp = await self.client.get(
            f"/chat/room/{self.room_uuid}",
            headers={"Authorization": f"Bearer {not_owner_token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp_json["detail"] == "Room with this id does not exist!"

    async def test_get_room_with_messages_not_shared_user_is_owner(self) -> None:
        room = await create_room_in_db(
            RoomCreateInputDetails(
                user_id=self.user.id,
                name="test_name"
            )
        )
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

    async def test_get_room_with_messages_shared_user_not_owner_not_the_same_organization(self) -> None:
        room = await create_room_in_db(
            RoomCreateInputDetails(
                user_id=self.user.id,
                name="test_name"
            )
        )
        self.room_uuid = room.uuid

        # create not owner user
        not_owner_user = await get_or_create_user({"email": "notAnOwner@example.com"})
        not_owner_token = create_access_token(user=not_owner_user)

        # create organizations
        org1 = await create_organization_in_db(OrganizationCreate(name="org1"))
        org2 = await create_organization_in_db(OrganizationCreate(name="org2"))

        # update users with organizations
        await add_users_to_organization_in_db(
            organization_uuid=org1["uuid"],
            user_ids=[self.user.id]
        )
        await add_users_to_organization_in_db(
            organization_uuid=org2["uuid"],
            user_ids=[not_owner_user.id]
        )

        resp = await self.client.get(
            f"/chat/room/{self.room_uuid}",
            headers={"Authorization": f"Bearer {not_owner_token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp_json["detail"] == "Room with this id does not exist!"

    async def test_get_room_with_messages_shared_user_not_owner_the_same_organization(self) -> None:
        room = await create_room_in_db(
            RoomCreateInputDetails(
                user_id=self.user.id,
                name="test_name",
                share=True,
            )
        )
        self.room_uuid = room.uuid

        # create not owner user
        not_owner_user = await get_or_create_user({"email": "notAnOwner@example.com"})
        not_owner_token = create_access_token(user=not_owner_user)

        # create organizations
        org1 = await create_organization_in_db(OrganizationCreate(name="org1"))

        # update users with organizations
        await add_users_to_organization_in_db(
            organization_uuid=org1["uuid"],
            user_ids=[self.user.id, not_owner_user.id]
        )

        resp = await self.client.get(
            f"/chat/room/{self.room_uuid}",
            headers={"Authorization": f"Bearer {not_owner_token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["name"] == "test_name"
        assert resp_json["uuid"] == str(self.room_uuid)
        assert len(resp_json["messages"]) == 0

    async def test_get_room_with_messages_shared_visibility_organization_user_not_owner_not_the_same_organization(self) -> None:
        room = await create_room_in_db(
            RoomCreateInputDetails(
                user_id=self.user.id,
                name="test_name",
                visibility=VisibilityChoices.ORGANIZATION.value,
                share=True,
            )
        )
        self.room_uuid = room.uuid

        # create not owner user
        not_owner_user = await get_or_create_user({"email": "notAnOwner@example.com"})
        not_owner_token = create_access_token(user=not_owner_user)

        # create organizations
        org1 = await create_organization_in_db(OrganizationCreate(name="org1"))
        org2 = await create_organization_in_db(OrganizationCreate(name="org2"))

        # update users with organizations
        await add_users_to_organization_in_db(
            organization_uuid=org1["uuid"],
            user_ids=[self.user.id]
        )
        await add_users_to_organization_in_db(
            organization_uuid=org2["uuid"],
            user_ids=[not_owner_user.id]
        )

        resp = await self.client.get(
            f"/chat/room/{self.room_uuid}",
            headers={"Authorization": f"Bearer {not_owner_token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["name"] == "test_name"
        assert resp_json["uuid"] == str(self.room_uuid)
        assert len(resp_json["messages"]) == 0


    async def test_get_room_with_messages_shared_visibility_organization_user_not_owner_the_same_organization(self) -> None:
        room = await create_room_in_db(
            RoomCreateInputDetails(
                user_id=self.user.id,
                name="test_name",
                visibility=VisibilityChoices.ORGANIZATION.value,
                share=True,
            )
        )
        self.room_uuid = room.uuid

        # create not owner user
        not_owner_user = await get_or_create_user({"email": "notAnOwner@example.com"})
        not_owner_token = create_access_token(user=not_owner_user)

        # create organizations
        org1 = await create_organization_in_db(OrganizationCreate(name="org1"))

        # update users with organizations
        await add_users_to_organization_in_db(
            organization_uuid=org1["uuid"],
            user_ids=[self.user.id, not_owner_user.id]
        )

        resp = await self.client.get(
            f"/chat/room/{self.room_uuid}",
            headers={"Authorization": f"Bearer {not_owner_token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["name"] == "test_name"
        assert resp_json["uuid"] == str(self.room_uuid)
        assert len(resp_json["messages"]) == 0


    async def test_get_room_with_messages_not_shared_visibility_organization_user_not_owner_not_the_same_organization(self) -> None:
        room = await create_room_in_db(
            RoomCreateInputDetails(
                user_id=self.user.id,
                name="test_name",
                visibility=VisibilityChoices.ORGANIZATION.value,
                share=False,
            )
        )
        self.room_uuid = room.uuid

        # create not owner user
        not_owner_user = await get_or_create_user({"email": "notAnOwner@x.com"})
        not_owner_token = create_access_token(user=not_owner_user)

        # create organizations
        org1 = await create_organization_in_db(OrganizationCreate(name="org1"))
        org2 = await create_organization_in_db(OrganizationCreate(name="org2"))

        # update users with organizations
        await add_users_to_organization_in_db(
            organization_uuid=org1["uuid"],
            user_ids=[self.user.id]
        )
        await add_users_to_organization_in_db(
            organization_uuid=org2["uuid"],
            user_ids=[not_owner_user.id]
        )

        resp = await self.client.get(
            f"/chat/room/{self.room_uuid}",
            headers={"Authorization": f"Bearer {not_owner_token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp_json["detail"] == "Room with this id does not exist!"

    async def test_get_room_with_messages_not_shared_visibility_organization_user_not_owner_the_same_organization(self) -> None:
        room = await create_room_in_db(
            RoomCreateInputDetails(
                user_id=self.user.id,
                name="test_name",
                visibility=VisibilityChoices.ORGANIZATION.value,
                share=False,
            )
        )
        self.room_uuid = room.uuid

        # create not owner user
        not_owner_user = await get_or_create_user({"email": "notAnOwner@example.com"})
        not_owner_token = create_access_token(user=not_owner_user)

        # create organizations
        org1 = await create_organization_in_db(OrganizationCreate(name="org1"))

        # update users with organizations
        await add_users_to_organization_in_db(
            organization_uuid=org1["uuid"],
            user_ids=[self.user.id, not_owner_user.id]
        )

        resp = await self.client.get(
            f"/chat/room/{self.room_uuid}",
            headers={"Authorization": f"Bearer {not_owner_token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["name"] == "test_name"
        assert resp_json["uuid"] == str(self.room_uuid)
        assert len(resp_json["messages"]) == 0


if __name__ == "__main__":
    unittest.main()
