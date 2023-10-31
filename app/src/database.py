import uuid
from typing import Any

from databases import Database
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Integer,
    LargeBinary,
    MetaData,
    String,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

from src.config import get_settings
from src.constants import DB_NAMING_CONVENTION

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
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

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
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

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
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())


class RefreshToken(Base):
    __tablename__ = "auth_refresh_token"

    uuid = Column(UUID, primary_key=True)
    user_id = Column(ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())


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
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())
    user_id = Column(ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=False)
    organization_uuid = Column(
        ForeignKey("organization.uuid", ondelete="CASCADE"), nullable=True
    )


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
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    room_id = Column(ForeignKey("room.uuid", ondelete="CASCADE"), nullable=False)
    created_by = Column(String, nullable=False)
    content = Column(String, nullable=True)
    content_html = Column(String, nullable=True)
    user_id = Column(ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=True)
    sender_picture = Column(String, nullable=True)


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
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    domain = Column(String, nullable=True)


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
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())
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
