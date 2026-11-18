from app import db
from app.models import Notification


def send_notification(user_id: int, title: str, message: str, report_id: int = None, category: str = 'status_update'):
    """Create an in-app notification for a user."""
    try:
        notif = Notification(
            user_id=user_id,
            report_id=report_id,
            title=title,
            message=message,
            category=category,
            is_read=False
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception as e:
        db.session.rollback()
        return None
