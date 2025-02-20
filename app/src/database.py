import uuid
from typing import Any

from databases import Database
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Enum,
    Float,
    ForeignKey,
    Identity,
    Integer,
    LargeBinary,
    MetaData,
    Sequence,
    String,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy_utils.types import TSVectorType

from src.config import get_settings
from src.constants import DB_NAMING_CONVENTION
from src.db_types import AwareDateTime

settings = get_settings()

if settings.ENVIRONMENT.is_testing:
    DATABASE_URL = settings.TEST_DATABASE_URL
else:
    DATABASE_URL = settings.DATABASE_URL

database = Database(
    DATABASE_URL.unicode_string(), force_rollback=settings.ENVIRONMENT.is_testing
)
engine = create_engine(DATABASE_URL.unicode_string())
metadata = MetaData(naming_convention=DB_NAMING_CONVENTION)

# if someone finds out how to type it properly, please change it
Base: Any = declarative_base()


class OrganizationUser(Base):
    __tablename__ = "organization_user"

    id = Column(Integer, Identity(), primary_key=True)
    organization_uuid = Column(
        ForeignKey("organization.uuid", ondelete="CASCADE"), nullable=False
    )
    auth_user_id = Column(
        ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "organization_uuid", "auth_user_id", name="uq_org_user_org_user"
        ),
    )


class OrganizationAdmin(Base):
    __tablename__ = "organization_admin"

    id = Column(Integer, Identity(), primary_key=True)
    organization_uuid = Column(
        ForeignKey("organization.uuid", ondelete="CASCADE"), nullable=False
    )
    auth_user_id = Column(
        ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "organization_uuid", "auth_user_id", name="uq_org_admin_org_user"
        ),
    )


class User(Base):
    __tablename__ = "auth_user"

    id = Column(Integer, Identity(), primary_key=True)
    email = Column(String, nullable=False)
    password = Column(LargeBinary, nullable=False)
    is_admin = Column(Boolean, server_default="false", nullable=False)
    picture = Column(String, nullable=True)
    name = Column(String, nullable=True)
    credentials = Column(JSON, nullable=True)
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(  # type: ignore
        AwareDateTime,
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
    )


class RefreshToken(Base):
    __tablename__ = "auth_refresh_token"

    uuid = Column(UUID, primary_key=True)
    user_id = Column(ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(AwareDateTime, nullable=False)
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(  # type: ignore
        AwareDateTime,
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
    )


visibility_choices = ("just_me", "organization")


class Room(Base):
    __tablename__ = "room"

    uuid = Column(UUID, primary_key=True)
    name = Column(String, nullable=False)
    share = Column(Boolean, server_default="false", nullable=False)
    visibility = Column(
        Enum(*visibility_choices, name="visibility_enum"),
        nullable=False,
        server_default="just_me",
    )
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(  # type: ignore
        AwareDateTime,
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    user_id = Column(ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=False)
    organization_uuid = Column(
        ForeignKey("organization.uuid", ondelete="CASCADE"), nullable=True
    )

    # Define a relationship to access active users
    # active_user: relationship = relationship("ActiveRoomUsers", backref="room")


visibility_enum = Enum(*visibility_choices, name="visibility_enum")
visibility_enum.create(bind=engine, checkfirst=True)


class Message(Base):
    __tablename__ = "message"

    uuid = Column(
        UUID,
        primary_key=True,
        server_default=str(uuid.uuid4()),
        default=str(uuid.uuid4()),
    )
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)
    room_id = Column(ForeignKey("room.uuid", ondelete="CASCADE"), nullable=False)
    content = Column(String, nullable=True)
    content_dict = Column(JSON, nullable=True)
    content_html = Column(String, nullable=True)
    user_id = Column(ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=True)
    sender_picture = Column(String, nullable=True)
    created_by = Column(String, nullable=False)
    updated_at = Column(  # type: ignore
        AwareDateTime,
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
    )
    token_usage_id = Column(
        ForeignKey("token_usage.id", ondelete="CASCADE"), nullable=True
    )
    elapsed_time = Column(Float, nullable=True)
    # Add the search vector
    search_vector = Column(TSVectorType("content"))


class Organization(Base):
    __tablename__ = "organization"

    uuid = Column(
        UUID,
        primary_key=True,
        server_default=str(uuid.uuid4()),
        default=str(uuid.uuid4()),
    )
    name = Column(String, unique=True, nullable=False)
    picture = Column(String, nullable=True)
    domain = Column(String, nullable=True)
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(  # type: ignore
        AwareDateTime,
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
    )


template_visibility_choices = ("just_me", "organization")


class Template(Base):
    __tablename__ = "template"

    uuid = Column(UUID, primary_key=True)
    name = Column(String, nullable=False)
    share = Column(Boolean, server_default="false", nullable=False)
    content = Column(String, nullable=True)
    visibility = Column(
        Enum(*template_visibility_choices, name="template_visibility_choices"),
        nullable=False,
        server_default="just_me",
    )
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(  # type: ignore
        AwareDateTime,
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
    )
    user_id = Column(ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=False)
    organization_uuid = Column(
        ForeignKey("organization.uuid", ondelete="CASCADE"), nullable=True
    )
    content_html = Column(String, nullable=True)


auth_user_organization_admin: relationship = relationship(
    "organization",
    secondary="organization_admins",
    back_populates="admins",
)

organization_auth_user_admin: relationship = relationship(
    "auth_user",
    secondary="organization_admins",
    back_populates="admin_organizations",
)

auth_user_organization: relationship = relationship(
    "organization", secondary="organizations_users", back_populates="users"
)

organization_auth_user: relationship = relationship(
    "auth_user", secondary="organizations_users", back_populates="organizations"
)


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, Sequence("token_usage_id_seq", start=1000), primary_key=True)
    count = Column(Integer, nullable=False)
    value = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)


class ActiveRoomUsers(Base):
    __tablename__ = "active_room_user"

    id = Column(Integer, Identity(), primary_key=True)
    room_uuid = Column(ForeignKey("room.uuid", ondelete="CASCADE"), nullable=False)
    user_id = Column(ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(  # type: ignore
        AwareDateTime,
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("room_uuid", "user_id", name="uq_active_room_user"),
    )


auth_user_room: relationship = relationship(
    "room", secondary="active_room_users", back_populates="active_users"
)

room_auth_user: relationship = relationship(
    "auth_user", secondary="active_room_users", back_populates="active_rooms"
)


class UserFile(Base):
    __tablename__ = "user_file"

    uuid = Column(UUID, primary_key=True)
    content = Column(String, nullable=True)
    optimized_content = Column(String, nullable=True)
    source_type = Column(String, nullable=False)
    source_value = Column(String, nullable=False)
    title = Column(String, nullable=False)
    extension = Column(String, nullable=True)
    user = Column(ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=False)
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)
    updated_at = Column(  # type: ignore
        AwareDateTime,
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
    )


class UserModel(Base):
    __tablename__ = "user_model"

    uuid = Column(UUID, primary_key=True)
    provider = Column(String, nullable=False)
    defaultSelected = Column(String, nullable=True)
    api_key = Column(String, nullable=False)
    default = Column(Boolean, server_default="false", nullable=False)
    user = Column(ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=False)


class OrganizationModel(Base):
    __tablename__ = "organization_model"

    uuid = Column(UUID, primary_key=True, default=uuid.uuid4)
    organization_uuid = Column(
        ForeignKey("organization.uuid", ondelete="CASCADE"), nullable=False
    )
    user_model_uuid = Column(
        ForeignKey("user_model.uuid", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(AwareDateTime, server_default=func.now(), nullable=False)


user_model_organization: relationship = relationship(
    "organization",
    secondary="organization_models",
    back_populates="models_model",
)

organization_user_model: relationship = relationship(
    "user_model",
    secondary="organization_models",
    back_populates="organizations_model",
)
