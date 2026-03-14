from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

SCHEMA_NAME = "app_schema"

metadata = MetaData(schema=SCHEMA_NAME)

class Base(DeclarativeBase):
    metadata = metadata