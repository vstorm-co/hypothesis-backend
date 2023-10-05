import unittest
from async_asgi_testclient import TestClient
from src.main import app
from src.database import database
from src.auth.jwt import create_access_token
from src.auth.service import get_or_create_user
from src.organizations.service import (
    create_organization_in_db,
    delete_organization_from_db, get_users_from_organization_by_id_from_db, get_admins_from_organization_by_id_from_db,
)
from src.organizations.schemas import OrganizationCreate

TEST_USER_ADMIN = "test_admin@mail.com"
TEST_USER = "test_user@mail.com"
TEST_USER2 = "test_user2@mail.com"
TEST_USER3 = "test_user3@mail.com"

class TestOrganization(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await database.connect()
        self.client = TestClient(app)
        self.user_admin = await get_or_create_user({"email": f"{TEST_USER_ADMIN}"}, is_admin=True)
        self.user = await get_or_create_user({"email": f"{TEST_USER}"})
        self.user2 = await get_or_create_user({"email": f"{TEST_USER2}"})
        self.user3 = await get_or_create_user({"email": f"{TEST_USER3}"})
        self.token = create_access_token(user=self.user)
        self.token2 = create_access_token(user=self.user2)
        self.token3 = create_access_token(user=self.user3)
        self.admin_token = create_access_token(user=self.user_admin)
        self.organization_uuid = None

    async def asyncTearDown(self) -> None:
        if self.organization_uuid:
            await delete_organization_from_db(self.organization_uuid)
        await database.disconnect()

    async def test_create_organization_by_admin(self):
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
                "picture": "org.png"  # Add a picture for testing
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 201
        self.organization_uuid = resp.json()["uuid"]

        users = await get_users_from_organization_by_id_from_db(self.organization_uuid)
        assert len(users) == 1
        admins = await get_admins_from_organization_by_id_from_db(self.organization_uuid)
        assert len(admins) == 1

    async def test_create_organization_by_user(self):
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
                "picture": "org.png"  # Add a picture for testing
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 201
        self.organization_uuid = resp.json()["uuid"]

        users = await get_users_from_organization_by_id_from_db(self.organization_uuid)
        assert len(users) == 1
        admins = await get_admins_from_organization_by_id_from_db(self.organization_uuid)
        assert len(admins) == 1


    async def test_update_organization_name_by_global_admin(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        resp = await self.client.put(
            f"/organization/{self.organization_uuid}",
            json={
                "name": "PutName",
                "picture": "org_updated.png"
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "PutName"

    async def test_update_organization_name_by_organization_admin(self):
        # create organization with post
        # that will create an admin for the organization
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
                "picture": "org.png"  # Add a picture for testing
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "MyOrganization"
        self.organization_uuid = resp.json()["uuid"]

        resp = await self.client.put(
            f"/organization/{self.organization_uuid}",
            json={
                "name": "PutName",
                "picture": "org_updated.png"
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "PutName"

    # GET ALL ORGS
    async def test_get_organizations_by_global(self):
        await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        await create_organization_in_db(OrganizationCreate(name="MyOrganization2", picture="org2.png"))

        resp = await self.client.get(
            "/organization",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        assert resp.json()[0]["name"] == "MyOrganization"
        assert resp.json()[1]["name"] == "MyOrganization2"

    async def test_get_organizations_by_user(self):
        await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))

        resp = await self.client.get(
            "/organization",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Authorization failed. User has no access."

    # GET ORG BY ID
    async def test_get_organization_by_global_admin(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        resp = await self.client.get(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "MyOrganization"

    async def test_get_organization_by_organization_admin(self):
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
                "picture": "org.png"  # Add a picture for testing
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "MyOrganization"
        self.organization_uuid = resp.json()["uuid"]

        resp = await self.client.get(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "MyOrganization"

        users = await get_users_from_organization_by_id_from_db(self.organization_uuid)
        assert len(users) == 1
        admins = await get_admins_from_organization_by_id_from_db(self.organization_uuid)
        assert len(admins) == 1
        assert admins[0].id == self.user.id

    async def test_get_organization_by_user(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        resp = await self.client.get(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Organization with this id does not exist!"


    # Delete
    async def test_delete_organization_by_organization_admin(self):
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
                "picture": "org.png"  # Add a picture for testing
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.organization_uuid = resp.json()["uuid"]

        resp = await self.client.delete(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Organization deleted"

    async def test_delete_organization_by_global_admin(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org["uuid"]

        resp = await self.client.delete(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Organization deleted"

    async def test_delete_organization_by_user_not_owner(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org["uuid"]

        resp = await self.client.delete(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Authorization failed. User has no access."

    async def test_delete_organization_by_another_user(self):
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
                "picture": "org.png"  # Add a picture for testing
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.organization_uuid = resp.json()["uuid"]

        resp = await self.client.delete(
            f"/organization/{self.organization_uuid}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Authorization failed. User has no access."


    # Add users to organization
    async def test_add_users_to_organization_by_global_admin(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        resp = await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "user_ids": [
                    self.user.id,
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Users added to the organization"

    async def test_add_users_to_organization_by_organization_admin(self):
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
                "picture": "org.png"  # Add a picture for testing
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.organization_uuid = resp.json()["uuid"]

        resp = await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "user_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Users added to the organization"

    async def test_add_users_to_organization_by_user_not_owner(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        resp = await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "user_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User cannot add another user to organization!"

    async def test_add_admins_to_organization_by_global_admin(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        resp = await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "admin_ids": [
                    self.user.id,
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Users added to the organization"

    async def test_add_admins_to_organization_by_organization_admin(self):
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
                "picture": "org.png"  # Add a picture for testing
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.organization_uuid = resp.json()["uuid"]

        resp = await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "admin_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Users added to the organization"

    async def test_add_admins_to_organization_by_user_not_owner(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        resp = await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "admin_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User cannot add another user to organization!"


    # delete users from organization
    async def test_remove_users_from_organization_by_global_admin(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "user_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp = await self.client.delete(
            f"/organization/delete-users-from-organization/{self.organization_uuid}",
            json={
                "user_ids": [
                    self.user2.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Users removed from the organization"

    async def test_remove_users_from_organization_by_organization_admin(self):
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
                "picture": "org.png"
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.organization_uuid = resp.json()["uuid"]
        await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "user_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp = await self.client.delete(
            f"/organization/delete-users-from-organization/{self.organization_uuid}",
            json={
                "user_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Users removed from the organization"

    async def test_remove_users_from_organization_by_user_not_owner(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "user_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp = await self.client.delete(
            f"/organization/delete-users-from-organization/{self.organization_uuid}",
            json={
                "user_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User cannot delete another user from organization!"

    async def test_remove_admins_from_organization_by_global_admin(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "admin_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp = await self.client.delete(
            f"/organization/delete-users-from-organization/{self.organization_uuid}",
            json={
                "admin_ids": [
                    self.user2.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Users removed from the organization"

    async def test_remove_admins_from_organization_by_organization_admin(self):
        resp = await self.client.post(
            "/organization",
            json={
                "name": "MyOrganization",
                "picture": "org.png"
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.organization_uuid = resp.json()["uuid"]
        await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "admin_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp = await self.client.delete(
            f"/organization/delete-users-from-organization/{self.organization_uuid}",
            json={
                "admin_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Users removed from the organization"

    async def test_remove_admins_from_organization_by_user_not_owner(self):
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "admin_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp = await self.client.delete(
            f"/organization/delete-users-from-organization/{self.organization_uuid}",
            json={
                "admin_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User cannot delete another user from organization!"


    async def test_remove_all_admins_from_organization_by_global_admin(self):
        """We cannot delete all admins from an organization, because there must be at least one admin in an organization"""
        org = await create_organization_in_db(OrganizationCreate(name="MyOrganization", picture="org.png"))
        self.organization_uuid = org.uuid
        await self.client.post(
            f"/organization/add-users-to-organization",
            json={
                "organization_uuid": str(self.organization_uuid),
                "admin_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        resp = await self.client.delete(
            f"/organization/delete-users-from-organization/{self.organization_uuid}",
            json={
                "admin_ids": [
                    self.user2.id,
                    self.user3.id,
                ],
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User cannot delete another user from organization!"
