import unittest

from sqlalchemy import delete
from async_asgi_testclient import TestClient

from src.auth.jwt import create_access_token
from src.auth.service import get_or_create_user
from src.database import database, organization, auth_user, settings
from src.main import app
from src.organizations.schemas import OrganizationCreate
from src.organizations.service import create_organization_in_db, delete_organization_from_db

TEST_USER_ADMIN = "test_admin@mail.com"
TEST_USER = "test_user@mail.com"

class TestOrganization(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await database.connect()
        self.client = TestClient(app)
        self.user_admin = await get_or_create_user({"email": f"{TEST_USER_ADMIN}"}, is_admin=True)
        self.user = await get_or_create_user({"email": f"{TEST_USER}"})
        self.token = create_access_token(user=self.user)
        self.admin_token = create_access_token(user=self.user_admin)
        self.organization_uuid = None

    async def asyncTearDown(self) -> None:
        if self.organization_uuid:
            delete_query_1 = delete(organization).where(organization.c.uuid == self.organization_uuid)
            await database.execute(delete_query_1)
        delete_query = delete(auth_user).where(auth_user.c.email == f"{TEST_USER}")
        await database.execute(delete_query)
        await database.disconnect()
        self.user = None

    # CREATE
    async def test_create_organization_by_admin(self) -> None:
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 201
        self.organization_uuid = resp_json["uuid"]

    async def test_create_organization_by_user(self) -> None:
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 403
        assert resp_json["detail"] == "Authorization failed. User has no access."


    # UPDATE
    async def test_update_organization_name_by_admin(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid
        resp = await self.client.put(
            f"/organization/{self.organization_uuid}",
            json={
                "name": "PutName"
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 200
        assert resp_json["name"] == "PutName"

    async def test_update_organization_name_by_user(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid
        resp = await self.client.put(
            f"/organization/{self.organization_uuid}",
            json={
                "name": "PutName"
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 403
        assert resp_json["detail"] == "Authorization failed. User has no access."

    async def test_update_organization_name_by_admin_with_invalid_uuid(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid
        resp = await self.client.put(
            f"/organization/{str(self.organization_uuid)[:-1]}1",
            json={
                "name": "PutName"
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 404
        assert resp_json["detail"] == "Organization with this id does not exist!"


    # GET BY UUID
    async def test_get_organization_by_admin(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid
        resp = await self.client.get(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 200
        assert resp_json["name"] == "MyOrganization"

    async def test_get_organization_by_user(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid
        resp = await self.client.get(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 200
        assert resp_json["name"] == "MyOrganization"

    async def test_get_organization_by_admin_with_invalid_uuid(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid
        resp = await self.client.get(
            f"/organization/{str(self.organization_uuid)[:-1]}1",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 404
        assert resp_json["detail"] == "Organization with this id does not exist!"

    # GET ALL
    async def test_get_organizations_by_admin(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        org2 = await create_organization_in_db(OrganizationCreate(name="MyOrganization2"))

        resp = await self.client.get(
            f"/organization",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 200
        assert len(resp_json) == 2
        assert resp_json[0]["name"] == "MyOrganization"

    async def test_get_organizations_by_user(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        org2 = await create_organization_in_db(OrganizationCreate(name="MyOrganization2"))

        resp = await self.client.get(
            f"/organization",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 403
        assert resp_json["detail"] == "Authorization failed. User has no access."

    # DELETE
    async def test_delete_organization_by_admin(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid
        resp = await self.client.delete(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 200
        assert resp_json["status"] == "Deleted"


    async def test_delete_organization_by_user(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid
        resp = await self.client.delete(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 403
        assert resp_json["detail"] == "Authorization failed. User has no access."

    async def test_delete_organization_by_admin_with_invalid_uuid(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid
        resp = await self.client.delete(
            f"/organization/{str(self.organization_uuid)[:-1]}1",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 404
        assert resp_json["detail"] == "Organization with this id does not exist!"

    # SET USER ORGANIZATION
    async def test_set_user_organization_by_admin(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid

        # create user
        user = await get_or_create_user({"email": "test@user.com"})
        user_id = user.id

        resp = await self.client.post(
            f"/organization/set-user-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "user_id": user_id
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 200
        assert resp_json["status"] == "User organization set"

        # delete org from db
        await delete_organization_from_db(self.organization_uuid)

    async def test_set_user_organization_by_user(self) -> None:
        # create organization
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization"))
        self.organization_uuid = org.uuid

        # create user
        user = await get_or_create_user({"email": "a@b.cd"})
        user_id = user.id

        resp = await self.client.post(
            f"/organization/set-user-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "user_id": user_id
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == 403
        assert resp_json["detail"] == "Authorization failed. User has no access."
