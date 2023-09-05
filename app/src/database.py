import uuid

from databases import Database
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
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

# Define the auth_user table
auth_user = Table(
    "auth_user",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("email", String, nullable=False),
    Column("password", LargeBinary, nullable=False),
    Column("is_admin", Boolean, server_default="false", nullable=False),
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

room = Table(
    "room",
    metadata,
    Column("uuid", UUID, primary_key=True),
    Column("name", String, nullable=False),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    Column("user_id", ForeignKey("auth_user.id", ondelete="NO ACTION"), nullable=True),
)

message = Table(
    "message",
    metadata,
    Column("uuid", UUID, primary_key=True, default=uuid.uuid4),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
    Column("room_id", ForeignKey("room.uuid", ondelete="CASCADE"), nullable=False),
    Column("created_by", String, nullable=False),
    Column("content", String, nullable=True),
)

users_teams = Table(
    "user_teams",
    metadata,
    Column("team_uuid", UUID, ForeignKey("team.uuid"), primary_key=True),
    Column("auth_user_id", Integer, ForeignKey("auth_user.id"), primary_key=True),
)

team = Table(
    "team",
    metadata,
    Column("uuid", UUID, primary_key=True),
    Column("name", String, nullable=True),
)

auth_user_teams: relationship = relationship(
    "team", secondary="users_teams", back_populates="users"
)
team_auth_user: relationship = relationship(
    "auth_user", secondary="users_teams", back_populates="teams"
)
