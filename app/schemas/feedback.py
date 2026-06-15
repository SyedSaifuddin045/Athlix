from datetime import datetime
from enum import Enum

from .base_schema import BaseSchema


class FeedbackType(str, Enum):
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    REVIEW = "review"


class FeedbackStatus(str, Enum):
    UNDER_REVIEW = "under_review"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DECLINED = "declined"


class FeedbackCreate(BaseSchema):
    type: FeedbackType
    title: str | None = None
    description: str
    category: str | None = None


class FeedbackUpdate(BaseSchema):
    title: str | None = None
    description: str | None = None
    category: str | None = None


class FeedbackAdminUpdate(BaseSchema):
    status: FeedbackStatus | None = None
    admin_notes: str | None = None


class FeedbackCommentCreate(BaseSchema):
    content: str


class FeedbackUserBrief(BaseSchema):
    id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None


class FeedbackResponse(BaseSchema):
    id: int
    type: FeedbackType
    title: str | None
    description: str
    category: str | None
    status: FeedbackStatus
    admin_notes: str | None
    is_public: bool
    upvotes_count: int
    has_upvoted: bool | None = None
    comment_count: int = 0
    user: FeedbackUserBrief
    created_at: datetime
    updated_at: datetime


class FeedbackListResponse(BaseSchema):
    items: list[FeedbackResponse]
    total: int


class FeedbackCommentResponse(BaseSchema):
    id: int
    feedback_id: int
    content: str
    user: FeedbackUserBrief
    created_at: datetime
