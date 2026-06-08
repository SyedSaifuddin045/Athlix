from pydantic import BaseModel


class ClerkWebhookEvent(BaseModel):
    type: str
    data: dict
    object: str | None = None
    timestamp: int | None = None
