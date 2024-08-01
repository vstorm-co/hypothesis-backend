import asyncio
import json
import logging
from datetime import datetime
from time import time

import requests

from src.annotations.schemas import (
    AnnotationFormInput,
    HypothesisAnnotationCreateInput,
    HypothesisAnnotationCreateOutput,
    HypothesisApiInput,
)
from src.annotations.validations import validate_data_tags
from src.chat.schemas import APIInfoBroadcastData
from src.redis import pub_sub_manager

logger = logging.getLogger(__name__)


class HypothesisAPI:
    BASE_URL = "https://api.hypothes.is/api"

    def __init__(self, data: HypothesisApiInput):
        self.room_id: str = data.room_id
        self.api_key: str | None = data.api_key

    async def get_hypothesis_user_id(self) -> str:
        time()
        if not self.api_key:
            logger.error("API key is missing")
            return ""

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.BASE_URL}/profile"

        await pub_sub_manager.publish(
            self.room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="Hypothesis API",
                    type="sent",
                    data={
                        "url": url,
                        "why_you_see_this": """We need to get user id from
                        hypothesis API basing on the API key provided""",
                    },
                ).model_dump(
                    mode="json",
                    exclude={
                        "model",
                    },
                )
            ),
        )
        response = requests.get(url, headers=headers)
        res_json = response.json()
        user_id = res_json["userid"]

        return user_id

    async def create_hypothesis_annotation(
        self, data: HypothesisAnnotationCreateInput, form_data: AnnotationFormInput
    ) -> HypothesisAnnotationCreateOutput | None:
        start_time = time()
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
        await pub_sub_manager.publish(
            self.room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="Hypothesis API",
                    type="sent",
                    data=model_dump,
                ).model_dump(
                    mode="json",
                    exclude={
                        "model",
                    },
                )
            ),
        )

        response = requests.post(url, headers=headers, json=model_dump)

        if response.status_code != 200:
            logger.error(f"Failed to create annotation: {response.text}")
            return None
        res_json = response.json()
        annotation = HypothesisAnnotationCreateOutput(**res_json)

        await pub_sub_manager.publish(
            self.room_id,
            json.dumps(
                APIInfoBroadcastData(
                    room_id=self.room_id,
                    date=datetime.now().isoformat(),
                    api="Hypothesis API",
                    type="recd",
                    elapsed_time=time() - start_time,
                    data=res_json,
                ).model_dump(
                    mode="json",
                    exclude={
                        "model",
                    },
                )
            ),
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

    def get_user_annotations_of_url(
        self, user_id: str, url: str
    ) -> list[HypothesisAnnotationCreateOutput]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = f"{self.BASE_URL}/search?user={user_id}&uri={url}"

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to get annotations: {response.text}")
            return []

        res_json = response.json()
        annotations = [
            HypothesisAnnotationCreateOutput(**annotation)
            for annotation in res_json["rows"]
        ]

        return annotations

    async def delete_user_annotations_of_url(
        self, user_id: str, input_url: str
    ) -> None:
        annotations: list[
            HypothesisAnnotationCreateOutput
        ] = self.get_user_annotations_of_url(user_id, input_url)

        for annotation in annotations:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            url = f"{self.BASE_URL}/annotations/{annotation.id}"

            response = requests.delete(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to delete annotation: {response.text}")
                return None

            await pub_sub_manager.publish(
                self.room_id,
                json.dumps(
                    APIInfoBroadcastData(
                        room_id=self.room_id,
                        date=datetime.now().isoformat(),
                        api="Hypothesis API",
                        type="sent",
                        data={
                            "action": "delete",
                            "url": url,
                            "annotation_id": annotation.id,
                        },
                    ).model_dump(
                        mode="json",
                        exclude={
                            "model",
                        },
                    )
                ),
            )
            logger.info(f"Annotation deleted: {annotation.id}!!")

        return None

    def delete_user_annotation(self, annotation_id: str) -> None:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = f"{self.BASE_URL}/annotations/{annotation_id}"

        response = requests.delete(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to delete annotation: {response.text}")
            return None
        logger.info(f"Annotation deleted: {annotation_id}!!")

        return None


async def main():
    hypo_api = HypothesisAPI(
        HypothesisApiInput(
            room_id="room_id",
            api_key="6879-Ylsz1RbeiCN7ibWJn6n1civurTrWIdOJqZzov4iifSA",
        )
    )
    user_id = await hypo_api.get_hypothesis_user_id()

    ann = hypo_api.get_user_annotations_of_url(
        user_id=user_id, url="https://arxiv.org/pdf/2406.06326"
    )
    return ann


if __name__ == "__main__":
    asyncio.run(main())
