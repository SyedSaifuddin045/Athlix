"""APScheduler-based notification scheduler.

Runs three job functions every 30 minutes:
- check_morning_motivations
- check_inactivity_nudges
- check_milestones

Uses SQLAlchemyJobStore for persistent job storage in PostgreSQL.
"""

import logging
import random
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.notifications.repository import NotificationRepository
from app.notifications.service import NotificationService

logger = logging.getLogger(__name__)

# ── Content Templates ──────────────────────────────────────────────

MOTIVATION_TEMPLATES: dict[str, list[str]] = {
    "strength": [
        "{name}, time to add plates! Today's focus: progressive overload.",
        "Strength gains don't happen by accident. Let's lift, {name}!",
        "Every rep adds a pound. Keep pushing, {name}!",
    ],
    "hypertrophy": [
        "{name}, muscle grows in the kitchen and the gym. Let's get that pump!",
        "Volume + consistency = results. You've got this, {name}!",
        "Time to tear some muscle fibers, {name}. Growth happens outside your comfort zone.",
    ],
    "weight_loss": [
        "{name}, every workout burns calories. Stay consistent!",
        "Fat loss is a marathon, not a sprint. Keep showing up, {name}!",
        "One workout won't change your body — but 100 will. Keep stacking, {name}!",
    ],
    "endurance": [
        "{name}, your cardio capacity builds one session at a time. Let's go!",
        "Endurance is built on days you don't feel like it. Today's one of those, {name}!",
        "Your heart thanks you for every session. Keep it pumping, {name}!",
    ],
    "maintenance": [
        "Stay sharp, {name}! Maintenance is still progress.",
        "Consistency > intensity. Keep the habit alive, {name}!",
        "You're already winning by showing up, {name}. Don't stop now.",
    ],
}

FALLBACK_MOTIVATION = [
    "Ready to crush today's workout, {name}? Let's go!",
    "Your future self will thank you for today's workout, {name}!",
    "Consistency compounds. Keep showing up, {name}!",
]

INACTIVITY_TEMPLATES = [
    "Hey {name}, it's been {days} days since {workout}. Even a quick session keeps the streak alive!",
    "{name}, your last {workout} was {days} days ago. Time to get back in the gym!",
    "It's been {days} days, {name}! Your muscles are recovered and ready.",
]

NO_WORKOUT_TEMPLATES = [
    "Hey {name}, it's been a while since your last workout. Ready to get back at it?",
    "{name}, we miss you! Start small — even 20 minutes counts.",
]

MILESTONE_LABELS: dict[int, str] = {
    10: "double digits",
    25: "a quarter century",
    50: "half a hundred",
    100: "triple digits",
    250: "a quarter grand",
    500: "five hundred!",
    1000: "legendary",
}


def _get_name(user_id: int) -> str:
    """Fetch user's first name or username for personalization."""
    from app.models.user import User
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user:
            return user.first_name or user.username or "Athlete"
        return "Athlete"
    finally:
        db.close()


def _check_recently_sent(user_id: int, notif_type: str, hours: int = 24) -> bool:
    """Check if this notification type was sent to user within last N hours."""
    from sqlalchemy import select, and_
    from app.notifications.models import NotificationHistory
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc)
        result = db.execute(
            select(NotificationHistory.id)
            .where(
                and_(
                    NotificationHistory.user_id == user_id,
                    NotificationHistory.title.like(f"%{notif_type}%"),
                    NotificationHistory.created_at >= cutoff,
                )
            )
            .limit(1)
        ).first()
        return result is not None
    finally:
        db.close()


# ── Job Functions ──────────────────────────────────────────────────

async def check_morning_motivations(notification_service: NotificationService | None):
    """Send morning motivation to users whose local time matches preferred_send_hour."""
    if notification_service is None:
        logger.warning("Notification service not available, skipping morning motivation")
        return

    import pytz

    db = SessionLocal()
    try:
        repo = NotificationRepository(db)
        settings_list = repo.get_settings_all_enabled("morning_motivation")
        utc_now = datetime.now(pytz.UTC)

        for settings in settings_list:
            try:
                tz = pytz.timezone(settings.timezone)
                local_hour = utc_now.astimezone(tz).hour
            except Exception:
                local_hour = utc_now.hour  # fallback to UTC

            if local_hour != settings.preferred_send_hour:
                continue

            if _check_recently_sent(settings.user_id, "morning_motivation"):
                continue

            name = _get_name(settings.user_id)
            message = random.choice(FALLBACK_MOTIVATION).format(name=name)

            await notification_service.send_to_user(
                user_id=settings.user_id,
                title="Morning Motivation",
                body=message,
                data={"screen": "home"},
            )
            logger.info("Morning motivation sent to user %d", settings.user_id)

    except Exception as exc:
        logger.error("Morning motivation check failed: %s", exc)
    finally:
        db.close()


async def check_inactivity_nudges(notification_service: NotificationService | None):
    """Send inactivity nudges to users who haven't worked out past their threshold."""
    if notification_service is None:
        return

    db = SessionLocal()
    try:
        repo = NotificationRepository(db)
        eligible = repo.get_eligible_for_inactivity_nudge(threshold_hours=72)

        for user_id, tz_name, last_workout_name, days_since in eligible:
            if _check_recently_sent(user_id, "inactivity"):
                continue

            name = _get_name(user_id)

            if last_workout_name and days_since < 999:
                body = random.choice(INACTIVITY_TEMPLATES).format(
                    name=name, days=days_since, workout=last_workout_name
                )
            else:
                body = random.choice(NO_WORKOUT_TEMPLATES).format(name=name)

            await notification_service.send_to_user(
                user_id=user_id,
                title="Don't Lose Your Streak",
                body=body,
                data={"screen": "home"},
            )
            logger.info("Inactivity nudge sent to user %d", user_id)

    except Exception as exc:
        logger.error("Inactivity nudge check failed: %s", exc)
    finally:
        db.close()


async def check_milestones(notification_service: NotificationService | None):
    """Send milestone celebrations to users who hit new workout count thresholds."""
    if notification_service is None:
        return

    db = SessionLocal()
    try:
        repo = NotificationRepository(db)
        eligible = repo.get_eligible_for_milestone()

        for user_id, tz_name, count in eligible:
            if _check_recently_sent(user_id, "milestone", hours=48):
                continue

            name = _get_name(user_id)
            milestone_label = MILESTONE_LABELS.get(count, f"{count} workouts")
            body = (
                f"{name} just completed {count} workouts! "
                f"That's {milestone_label}. Incredible consistency!"
            )

            await notification_service.send_to_user(
                user_id=user_id,
                title="Milestone Unlocked",
                body=body,
                data={"screen": "progress"},
            )

            repo.update_milestone_sent(user_id, count)
            logger.info("Milestone (%d) sent to user %d", count, user_id)

    except Exception as exc:
        logger.error("Milestone check failed: %s", exc)
    finally:
        db.close()


# ── Scheduler Setup ────────────────────────────────────────────────

def create_scheduler(database_url: str) -> AsyncIOScheduler:
    """Create and configure the APScheduler instance.

    Uses SQLAlchemyJobStore backed by PostgreSQL for persistent job storage.
    """
    jobstore = SQLAlchemyJobStore(url=database_url)
    scheduler = AsyncIOScheduler(
        jobstores={"default": jobstore},
        timezone="UTC",
        job_defaults={
            "coalesce": True,       # Combine missed runs into one
            "max_instances": 1,     # Don't overlap runs
            "misfire_grace_time": 600,  # 10 min grace
        },
    )
    return scheduler


def register_jobs(scheduler: AsyncIOScheduler, notification_service: NotificationService | None):
    """Register the three notification job functions."""
    from functools import partial

    scheduler.add_job(
        partial(check_morning_motivations, notification_service),
        trigger=IntervalTrigger(minutes=30),
        id="check_morning_motivations",
        name="Check and send morning motivation notifications",
        replace_existing=True,
    )

    scheduler.add_job(
        partial(check_inactivity_nudges, notification_service),
        trigger=IntervalTrigger(minutes=30),
        id="check_inactivity_nudges",
        name="Check and send inactivity nudge notifications",
        replace_existing=True,
    )

    scheduler.add_job(
        partial(check_milestones, notification_service),
        trigger=IntervalTrigger(minutes=30),
        id="check_milestones",
        name="Check and send milestone celebration notifications",
        replace_existing=True,
    )

    logger.info("Registered 3 notification scheduler jobs (30-min interval)")
