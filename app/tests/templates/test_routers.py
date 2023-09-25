import unittest

from async_asgi_testclient import TestClient
from sqlalchemy import delete
from starlette import status

from src.auth.jwt import create_access_token
from src.auth.service import get_or_create_user
from src.database import database, template
from src.main import app
from src.templates.schemas import TemplateCreateInputDetails, TemplateUpdate
from src.templates.service import create_template_in_db

TEST_USER = "test_user@mail.com"


class TestTemplate(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await database.connect()
        self.client = TestClient(app)
        self.user = await get_or_create_user({"email": f"{TEST_USER}"})
        self.token = create_access_token(user=self.user)
        self.template_uuid = None

    async def asyncTearDown(self) -> None:
        database.force_rollback()
        if self.template_uuid:
            delete_query_1 = delete(template).where(template.c.uuid == self.template_uuid)
            await database.execute(delete_query_1)
        await database.disconnect()
        self.user = None

    # CREATE
    async def test_create_template(self) -> None:
        resp = await self.client.post(
            "/template",
            json={
                "name": "MyTemplate",
                "content": "TemplateContent"
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == status.HTTP_200_OK
        self.template_uuid = resp_json["uuid"]
        assert resp_json["name"] == "MyTemplate"
        assert resp_json["content"] == "TemplateContent"
        assert resp_json["share"] is False
        assert resp_json["visibility"] == "just_me"

    #UPDATE
    async def test_update_template_name(self) -> None:
        test_template = await create_template_in_db(TemplateCreateInputDetails(user_id=self.user.id, name="MyTemplate",
                                                                               content="TemplateContent"))
        self.template_uuid = test_template.uuid

        update_input = TemplateUpdate(name="NewName")
        resp = await self.client.patch(
            f"/template/{self.template_uuid}",
            json=update_input.model_dump(),
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json['name'] == "NewName"

    async def test_update_template_share(self) -> None:
        test_template = await create_template_in_db(TemplateCreateInputDetails(user_id=self.user.id, name="MyTemplate",
                                                                               content="TemplateContent"))
        self.template_uuid = test_template.uuid

        update_input = TemplateUpdate(
            share=True
        )
        resp = await self.client.patch(
            f"/template/{self.template_uuid}",
            json=update_input.model_dump(),
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json['share'] is True

    async def test_update_template_content(self) -> None:
        test_template = await create_template_in_db(TemplateCreateInputDetails(user_id=self.user.id, name="MyTemplate",
                                                                               content="TemplateContent"))
        self.template_uuid = test_template.uuid

        update_input = TemplateUpdate(
            content="NewContent"
        )
        resp = await self.client.patch(
            f"/template/{self.template_uuid}",
            json=update_input.model_dump(),
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json['content'] == "NewContent"

    async def test_update_template_visibility(self) -> None:
        test_template = await create_template_in_db(TemplateCreateInputDetails(user_id=self.user.id, name="MyTemplate",
                                                                               content="TemplateContent"))
        self.template_uuid = test_template.uuid

        update_input = TemplateUpdate(
            visibility="organization"
        )
        resp = await self.client.patch(
            f"/template/{self.template_uuid}",
            json=update_input.model_dump(),
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()

        assert resp.status_code == status.HTTP_200_OK
        assert resp_json['visibility'] == "organization"

    #GET
    async def test_get_templates_without_id(self) -> None:
        test_template1 = await create_template_in_db(TemplateCreateInputDetails(user_id=self.user.id, name="MyTemplate1",
                                                                               content="TemplateContent1"))
        test_template2 = await create_template_in_db(TemplateCreateInputDetails(user_id=self.user.id, name="MyTemplate2",
                                                                               content="TemplateContent2"))
        resp = await self.client.get(
            "/template",
            headers={"Authorization": f"Bearer {self.token}"})
        resp_json = resp.json()
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp_json) == 2
        assert resp_json[0]["name"] == "MyTemplate1"
        assert resp_json[1]["name"] == "MyTemplate2"

    async def test_get_template_with_id(self) -> None:
        test_template = await create_template_in_db(TemplateCreateInputDetails(user_id=self.user.id, name="MyTemplate",
                                                                               content="TemplateContent"))
        self.template_uuid = test_template.uuid
        resp = await self.client.get(
            f"/template/{self.template_uuid}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["name"] == "MyTemplate"
        assert resp_json["content"] == "TemplateContent"

    #DELETE
    async def test_template_delete(self) -> None:
        test_template = await create_template_in_db(TemplateCreateInputDetails(user_id=self.user.id, name="MyTemplate",
                                                                               content="TemplateContent"))
        self.template_uuid = test_template.uuid
        resp = await self.client.delete(
            f"/template/{self.template_uuid}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        resp_json = resp.json()
        assert resp.status_code == status.HTTP_200_OK
        assert resp_json["status"] == "success"


if __name__ == '__main__':
    unittest.main()
