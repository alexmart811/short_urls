from sqlalchemy import Column, String, Integer, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    email = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    # username = Column(String, unique=True, nullable=False)
    # registered_at = Column(TIMESTAMP, default=datetime.now)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    
    urls = relationship("Urls", back_populates="user")



# class Urls(Base):
#     __tablename__ = "urls"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("user.id"))
#     orig_url = Column(String, unique=True, nullable=False)
#     short_url = Column(String, unique=True, nullable=False)
#     expires_at = Column(TIMESTAMP, default=datetime.now() + timedelta(weeks=1))
#     date_of_create = Column(TIMESTAMP, default=datetime.now())
#     last_usage = Column(TIMESTAMP, default=datetime.now())
#     count_ref = Column(Integer, default=0)

#     user = relationship("User", back_populates="urls")