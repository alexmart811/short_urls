from sqlalchemy import Table, Column, Integer, TIMESTAMP, MetaData, String
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

urls = Table(
    "urls",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", UUID(as_uuid=True)),
    Column("orig_url", String, unique=True, nullable=False),
    Column("short_url", String, unique=True, nullable=False),
    Column("expires_at", TIMESTAMP(timezone=True)),
    Column("date_of_create", TIMESTAMP),
    Column("last_usage", TIMESTAMP),
    Column("count_ref", Integer)
)