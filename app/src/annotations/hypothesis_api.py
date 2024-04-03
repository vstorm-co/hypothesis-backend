import logging
from asyncio import create_task
from datetime import datetime

import requests

from src.annotations.schemas import (
    AnnotationFormInput,
    HypothesisAnnotationCreateInput,
    HypothesisAnnotationCreateOutput,
)
from src.annotations.validations import validate_data_tags
from src.chat.manager import connection_manager as manager
from src.chat.schemas import APIInfoBroadcastData

logger = logging.getLogger(__name__)


class HypothesisAPI:
    BASE_URL = "https://api.hypothes.is/api"

    def __init__(self, data: AnnotationFormInput):
        self.room_id: str = data.room_id
        self.api_key: str | None = data.api_key

    async def get_hypothesis_user_id(self) -> str:
        if not self.api_key:
            logger.error("API key is missing")
            return ""

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.BASE_URL}/profile"

        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="Hypothesis API",
                    type="sent",
                    data={"url": url},
                )
            )
        )
        response = requests.get(url, headers=headers)
        res_json = response.json()
        user_id = res_json["userid"]

        return user_id

    async def create_hypothesis_annotation(
        self, data: HypothesisAnnotationCreateInput, form_data: AnnotationFormInput
    ) -> HypothesisAnnotationCreateOutput | None:
        if not form_data.api_key:
            logger.error("API key is missing")
            return None

        headers = {
            "Authorization": f"Bearer {form_data.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.BASE_URL}/annotations"

        logger.info(f"Creating hypothesis annotation: {data.uri}...")
        model_dump: dict = data.model_dump()
        if not validate_data_tags(model_dump["tags"]):
            # delete tags if they are not valid
            logger.info("Deleting tags from model dump")
            model_dump.pop("tags")

        logger.info(f"Model dump: {model_dump}")
        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="Hypothesis API",
                    type="sent",
                    data=model_dump,
                )
            )
        )
        response = requests.post(url, headers=headers, json=model_dump)

        if response.status_code != 200:
            logger.error(f"Failed to create annotation: {response.text}")
            return None
        res_json = response.json()
        annotation = HypothesisAnnotationCreateOutput(**res_json)

        await create_task(
            manager.broadcast_api_info(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="Hypothesis API",
                    type="recd",
                    data=res_json,
                )
            )
        )

        logger.info(f"Hypothesis annotation created: {annotation.id}!!")
        return annotation

    def get_hypothesis_annotation_by_id(
        self, annotation_id: str
    ) -> HypothesisAnnotationCreateOutput | None:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = f"{self.BASE_URL}/annotations/{annotation_id}"

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to get annotation: {response.text}")
            return None

        res_json = response.json()
        annotation = HypothesisAnnotationCreateOutput(**res_json)

        return annotation
