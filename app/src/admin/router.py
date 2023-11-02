import logging

from fastapi import APIRouter

from src.admin.service import clean_entire_database

logger = logging.getLogger(__name__)

router = APIRouter()


# TODO Delete this
@router.delete("")
async def delete_database():
    await clean_entire_database()
    return "Done"
