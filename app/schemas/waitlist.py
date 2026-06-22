from .base_schema import BaseSchema


class WaitlistCreate(BaseSchema):
    name: str
    email: str
