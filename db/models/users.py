from sqlalchemy import Column, BigInteger, Text, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from ..session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(Text, unique=True)
    password_hash = Column(Text)
    display_name = Column(Text)
    avatar_url = Column(Text)
    role = Column(Text)
    is_active = Column(Boolean, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
