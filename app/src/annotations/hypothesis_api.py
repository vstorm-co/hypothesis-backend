import logging

import requests

from src.annotations.schemas import (
    HypothesisAnnotationCreateInput,
    HypothesisAnnotationCreateOutput,
)

logger = logging.getLogger(__name__)


def get_hypothesis_user_id(api_key: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    url = "https://api.hypothes.is/api/profile"
    response = requests.get(url, headers=headers)
    res_json = response.json()
    user_id = res_json["userid"]

    return user_id


def create_hypothesis_annotation(
    data: HypothesisAnnotationCreateInput, api_key: str
) -> HypothesisAnnotationCreateOutput | None:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = "https://api.hypothes.is/api/annotations"

    logger.info(f"Creating hypothesis annotation: {data.uri}...")
    response = requests.post(url, headers=headers, json=data.model_dump())

    if response.status_code != 200:
        logger.error(f"Failed to create annotation: {response.text}")
        return None
    res_json = response.json()
    annotation = HypothesisAnnotationCreateOutput(**res_json)

    logger.info(f"Hypothesis annotation created: {annotation.id}!!")
    return annotation


def get_hypothesis_annotation_by_id(
    annotation_id: str, api_key: str | None = None
) -> HypothesisAnnotationCreateOutput | None:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    url = f"https://api.hypothes.is/api/annotations/{annotation_id}"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to get annotation: {response.text}")
        return None

    res_json = response.json()
    annotation = HypothesisAnnotationCreateOutput(**res_json)

    return annotation
