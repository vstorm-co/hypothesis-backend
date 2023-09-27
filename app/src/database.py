import uuid

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
    Table,
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
Base = declarative_base()


auth_user = Table(
    "auth_user",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("email", String, nullable=False),
    Column("password", LargeBinary, nullable=False),
    Column("is_admin", Boolean, server_default="false", nullable=False),
    Column("picture", String, nullable=True),
    Column("name", String, nullable=True),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    Column("updated_at", DateTime, onupdate=func.now()),
)

refresh_tokens = Table(
    "auth_refresh_token",
    metadata,
    Column("uuid", UUID, primary_key=True),
    Column("user_id", ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False),
    Column("refresh_token", String, nullable=False),
    Column("expires_at", DateTime, nullable=False),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    Column("updated_at", DateTime, onupdate=func.now()),
)

visibility_choices = ("just_me", "organization")

room = Table(
    "room",
    metadata,
    Column("uuid", UUID, primary_key=True),
    Column("name", String, nullable=False),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    Column("user_id", ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=False),
    Column("share", Boolean, server_default="false", nullable=False),
    Column(
        "visibility",
        Enum(*visibility_choices, name="visibility_enum"),
        nullable=False,
        server_default="just_me",
    ),
    Column(
        "organization_uuid",
        ForeignKey("organization.uuid", ondelete="CASCADE"),
        nullable=True,
    ),
)

visibility_enum = Enum(*visibility_choices, name="visibility_enum")
visibility_enum.create(bind=engine, checkfirst=True)

message = Table(
    "message",
    metadata,
    Column(
        "uuid",
        UUID,
        primary_key=True,
        server_default=str(uuid.uuid4()),
        default=str(uuid.uuid4()),
    ),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    Column("room_id", ForeignKey("room.uuid", ondelete="CASCADE"), nullable=False),
    Column("created_by", String, nullable=False),
    Column("content", String, nullable=True),
    Column("user_id", ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=True),
    Column("sender_picture", String, nullable=True),
)


organization = Table(
    "organization",
    metadata,
    Column(
        "uuid",
        UUID,
        primary_key=True,
        server_default=str(uuid.uuid4()),
        default=str(uuid.uuid4()),
    ),
    Column("name", String, unique=True, nullable=False),
    Column("picture", String, nullable=True),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    Column("domain", String, nullable=True)
)

organizations_users = Table(
    "organization_user",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("organization_uuid", ForeignKey("organization.uuid", ondelete="CASCADE")),
    Column("auth_user_id", ForeignKey("auth_user.id", ondelete="CASCADE")),
    UniqueConstraint("organization_uuid", "auth_user_id", name="uq_org_user_org_user"),
)

auth_user_organization: relationship = relationship(
    "organization", secondary="organizations_users", back_populates="users"
)

organization_auth_user: relationship = relationship(
    "auth_user", secondary="organizations_users", back_populates="organizations"
)

organization_admins = Table(
    "organization_admin",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("organization_uuid", ForeignKey("organization.uuid", ondelete="CASCADE")),
    Column("auth_user_id", ForeignKey("auth_user.id", ondelete="CASCADE")),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    UniqueConstraint("organization_uuid", "auth_user_id", name="uq_org_admin_org_user"),
)

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

template_visibility_choices = ("just_me", "organization")

template = Table(
    "template",
    metadata,
    Column("uuid", UUID, primary_key=True),
    Column("user_id", ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=False),
    Column("name", String, nullable=False),
    Column("content", String, nullable=True),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    Column("share", Boolean, server_default="false", nullable=False),
    Column(
        "visibility",
        Enum(*template_visibility_choices, name="template_visibility_choices"),
        nullable=False,
        server_default="just_me",
    ),
)
