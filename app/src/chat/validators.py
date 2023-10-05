from sqlalchemy import select

from src.chat.enums import VisibilityChoices
from src.chat.schemas import RoomDB
from src.database import database, OrganizationUser
from src.organizations.schemas import OrganizationUserDB


def is_room_private(room_schema: RoomDB, user_id: int) -> bool:
    return (
        room_schema.visibility == VisibilityChoices.JUST_ME
        and not room_schema.share
        and room_schema.user_id != user_id
    )


async def in_the_same_org(room_user_id: int, user_id: int) -> bool:
    """
    this is a total mess because of the way we understand organizations
    in Figma there is only a button to share a room with an organization
    there is no way to select with which organizations to share a room
    thus we have to check if the user is in the same organization as the room owner
    """

    # get room owner's organizations
    room_owner_organizations_query = select(OrganizationUser).where(
        OrganizationUser.auth_user_id == room_user_id
    )
    org_users_db = await database.fetch_all(room_owner_organizations_query)
    room_owners_org_users = [
        OrganizationUserDB(**dict(org_user)) for org_user in org_users_db
    ]

    # get user's organizations
    user_organizations_query = select(OrganizationUser).where(
        OrganizationUser.auth_user_id == user_id
    )
    user_org_users_db = await database.fetch_all(user_organizations_query)
    user_org_users = [
        OrganizationUserDB(**dict(org_user)) for org_user in user_org_users_db
    ]

    # TEMPORARY SOLUTION
    # PROBABLY THERE IS A BETTER WAY TO DO THIS
    # ROOM_SCHEMA.VISIBILITY SHOULD BE A LIST OF ORGANIZATION IDS
    # THEN WE CAN JUST CHECK IF ANY OF USER ORGS IS IN THAT LIST

    # if any of the user's organizations is in the room owner's organizations

    same_org = False
    for user_org in user_org_users:
        for room_owner_org in room_owners_org_users:
            if user_org.organization_uuid == room_owner_org.organization_uuid:
                same_org = True
    if not user_org_users and not room_owners_org_users:
        same_org = True

    return same_org


async def not_shared_for_organization(room_schema: RoomDB, user_id: int) -> bool:
    same_org = await in_the_same_org(room_schema.user_id, user_id)
    return (
        room_schema.visibility == VisibilityChoices.ORGANIZATION
        and not room_schema.share
        and not same_org
    )
