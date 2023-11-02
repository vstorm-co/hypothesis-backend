import logging

from fastapi import APIRouter

from src.admin.service import clean_entire_database
from src.admin.utils import delete_files_from_media

logger = logging.getLogger(__name__)

router = APIRouter()


# TODO Delete this
# https://hypothesis-vstorm.atlassian.net/jira/software/projects/PA/boards/2?selectedIssue=PA-84
@router.delete("")
async def delete_database():
    await clean_entire_database()
    delete_files_from_media()
    return {"status": "ok", "message": "Database cleaned"}
