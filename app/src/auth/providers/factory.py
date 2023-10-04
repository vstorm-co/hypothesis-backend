from abc import ABC, abstractmethod
from logging import getLogger

from src.auth.exceptions import InvalidCredentials, InvalidToken
from src.auth.jwt import create_access_token
from src.auth.providers.constants import FORBIDDEN_ORGANIZATION_NAMES
from src.auth.schemas import UserDB, VerifyResponse, OrganizationInfoVerifyResponse
from src.auth.service import create_refresh_token, get_or_create_user
from src.organizations.schemas import OrganizationCreateDetails
from src.organizations.service import get_or_create_organization_on_user_login

logger = getLogger(__name__)


class AuthProviderFactory(ABC):
    def __init__(self, config: dict[str, str]):
        self.config = config

    @abstractmethod
    async def get_user_info(self):
        raise NotImplementedError

    async def handle_login(self) -> VerifyResponse:
        user_info = await self.get_user_info()

        if isinstance(user_info, InvalidToken):
            raise InvalidCredentials()

        user = await get_or_create_user(user_info.model_dump())

        if not user:
            raise InvalidCredentials()

        # use pydantic to create a UserDB object
        user_schema = UserDB(**dict(user))

        # create organization based on user's email domain
        domain = user_schema.email.split("@")[1]
        org_name = domain.split(".")[0]

        # add organization to user on login
        # if the organization is not in the forbidden list
        created = False  # flag for organization creation info
        if org_name not in FORBIDDEN_ORGANIZATION_NAMES:
            organization_details = OrganizationCreateDetails(
                name=org_name,
                domain=domain,
            )

            created = await get_or_create_organization_on_user_login(
                organization_details=organization_details,
                user=user_schema,
            )

        # create refresh token
        refresh_token_value = await create_refresh_token(user_id=user_schema.id)

        return VerifyResponse(
            **user_info.model_dump(),
            user_id=user_schema.id,
            access_token=create_access_token(user=user),
            refresh_token=refresh_token_value,
            organization=OrganizationInfoVerifyResponse(
                name=org_name,
                created=created,
            )
        )
